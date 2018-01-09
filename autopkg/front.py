#!/usr/bin/python3

from os import environ
from os.path import join
from contextlib import contextmanager
from enum import Enum
from .utils import run_lock
from .utils import log
from .utils import LogLevel
from .utils import repository_home
from .utils import repository_name
from .utils import sign_key
from .utils import config
from .utils import mkdir
from .backends import git_backend
from .backends import gshellext_backend
from .backends import aur_backend
from .backends import config_git_backend
from .repository import Repository
from .graph import build_dependency_graph
from .plan import convert_graph_to_plans
from .builder import execute_plans_update
from .builder import execute_plans_autoremove
from .builder import autoremovable_packages


BACKENDS = [git_backend, gshellext_backend, aur_backend]


def unknown_command(command):
    log(LogLevel.error, 'Unknown command: {}', command)


@contextmanager
def config_targets():
    with config('targets') as config_data:
        if config_data.json is None:
            config_data.json = []
        yield config_data


def do_targets(arguments):
    if len(arguments) == 0:
        cmdlet = 'list'
    else:
        cmdlet = arguments[0]
    targets = arguments[1:]
    with config_targets() as config_data:
        if cmdlet == 'add':
            config_data.json = list(set(config_data.json + targets))
        elif cmdlet == 'remove':
            for pkgname in [pkgname for pkgname in targets if pkgname not in config_data.json]:
                log(LogLevel.warn, 'Not in targets list: {}', pkgname)
            config_data.json = [pkgname for pkgname in config_data.json if pkgname not in targets]
        elif cmdlet == 'list':
            log(LogLevel.header, 'List of Targets:')
            for pkgname in config_data.json:
                log(LogLevel.info, ' - {}', pkgname)
        else:
            unknown_command(cmdlet)


def do_packages(arguments, repository):
    if len(arguments) == 0:
        cmdlet = 'list'
    else:
        cmdlet = arguments[0]
    targets = arguments[1:]
    if cmdlet == 'add':
        for target in targets:
            repository.add(target)
    elif cmdlet == 'remove':
        for target in targets:
            repository.remove(target)
    elif cmdlet == 'list':
        log(LogLevel.header, 'List of Packages in the Repository:')
        for package_tiny_info in repository.packages.values():
            log(LogLevel.info, ' - {}', package_tiny_info)
    else:
        unknown_command(cmdlet)


def do_git(arguments):
    if len(arguments) == 0:
        cmdlet = 'list'
    else:
        cmdlet = arguments[0]
    targets = arguments[1:]
    with config_git_backend() as config_data:
        if cmdlet == 'add':
            repo_url = targets[0]
            path = targets[1] if len(targets) > 1 else ''
            branch = targets[2] if len(targets) > 2 else 'master'
            config_data.json.append({'repository': repo_url, 'path': path, 'branch': branch})
        elif cmdlet == 'remove':
            for index in sorted([int(index) for index in targets], reverse=True):
                try:
                    del config_data.json[index]
                except IndexError:
                    log(LogLevel.warn, 'Out of index: {}', index)
        elif cmdlet == 'list':
            log(LogLevel.header, 'List of Git Sources:')
            for index, source in enumerate(config_data.json):
                log(LogLevel.info, ' - {}', index)
                log(LogLevel.info, '     Repository {}', source['repository'])
                log(LogLevel.info, '           Path {}', source['path'])
                log(LogLevel.info, '         Branch {}', source['branch'])
        else:
            unknown_command(cmdlet)


def do_plans(repository):
    with config_targets() as config_data:
        log(LogLevel.header, 'Querying Backends...')
        graph = build_dependency_graph(config_data.json, BACKENDS)
        plans = convert_graph_to_plans(graph, repository)
        # Now we can assure that the graph is acyclic (a 'tree')
        log(LogLevel.header, 'Dependency Tree:')
        for root_edge in graph:
            log_graph(root_edge, repository, 0)
        log(LogLevel.header, 'Plan:')
        log_plans(plans)
        to_remove = autoremovable_packages(plans, repository)
        if len(to_remove) > 0:
            log(LogLevel.header, 'Auto-removable Packages:')
            for pkgname in to_remove:
                log(LogLevel.info, ' - {}', pkgname)
        return plans


class Transition(Enum):
    keep = 0
    new = 1
    upgrade = 2
    downgrade = 3
    remove = 4


TRANSITION_TO_COLOR = {Transition.keep: [],
                       Transition.new: [34],
                       Transition.upgrade: [32],
                       Transition.downgrade: [33],
                       Transition.remove: [31]}


def log_graph(edge, repository, depth):
    vertex = edge.vertex_to
    if vertex is None:
        return
    buildable = vertex.buildable
    package_info = buildable.package_info
    source_reference = buildable.source_reference
    pkgname = package_info.pkgname
    if pkgname in repository.packages:
        old = repository.packages[pkgname].version
    else:
        old = None
    new = package_info.version
    log_string = ' {}+ {} {} [{}] [{}]'.format(' ' * (depth * 2), pkgname, transition_string(old, new),
                                               source_reference, edge.dependency_type.name)
    log(LogLevel.info, log_string)
    for edge in vertex.edges:
        log_graph(edge, repository, depth + 1)


def transition_string(old, new):
    transition_color_code = ''.join(['\033[{}m'.format(code) for code in TRANSITION_TO_COLOR[transition(old, new)]])
    old_symbol = '✗' if old is None else old
    new_symbol = '✗' if new is None else new
    if type(old_symbol) == type(new_symbol) and old_symbol == new_symbol:
        return '{}({})\033[0m'.format(transition_color_code, new_symbol)
    else:
        return '{}({}→{})\033[0m'.format(transition_color_code, old_symbol, new_symbol)


def transition(old, new):
    if old is None:
        if new is None:
            return Transition.keep
        else:
            return Transition.new
    else:
        if new is None:
            return Transition.remove
    if old < new:
        return Transition.upgrade
    elif old > new:
        return Transition.downgrade
    else:
        return Transition.keep


def log_plans(plans):
    for plan in plans:
        buildable = plan.buildable
        log(LogLevel.info, ' - {}{}', buildable.source_reference, ' [chroot]' if plan.chroot else '')
        for pkgname in plan.requisites:
            log(LogLevel.info, '       \033[2mWith {}\033[0m', pkgname)
        for pkgname in plan.build:
            log(LogLevel.info, '      \033[1mBuild {}\033[0m', pkgname)
        for pkgname in plan.keep:
            log(LogLevel.info, '       \033[2mKeep {}\033[0m', pkgname)


def do_help(name):
    print('''Usage:\t{0} targets add [target-package-name-to-add]*
\t{0} targets remove [target-package-name-to-remove]*
\t{0} targets list
\t{0} packages add [path-to-the-package-file-to-add]*
\t{0} packages remove [package-name-to-remove]*
\t{0} packages list
\t{0} git add [repository-url] [path-in-repository]? [branch]?
\t{0} git remove [index]*
\t{0} git list
\t{0} plan
\t{0} update
\t{0} autoremove
\t{0} update autoremove
Environment variables:
 - AUTOPKG_HOME
 - AUTOPKG_REPO_NAME
 - AUTOPKG_KEY: GPG key to sign packages and the repository.
 - AUTOPKG_RETRY: The number of retrials in build packages in chroot environment.'''.format(name))


def front(name, arguments):
    with run_lock():
        log(LogLevel.debug, 'arguments: {}', arguments)
        log(LogLevel.debug, 'AUTOPKG_HOME: {}', environ.get('AUTOPKG_HOME', None))
        log(LogLevel.debug, 'AUTOPKG_REPO_HOME: {}', environ.get('AUTOPKG_REPO_HOME', None))
        log(LogLevel.debug, 'AUTOPKG_KEY: {}', environ.get('AUTOPKG_KEY', None))
        log(LogLevel.debug, 'AUTOPKG_RETRY: {}', environ.get('AUTOPKG_RETRY', None))
        repository = Repository(repository_name, mkdir(join(repository_home, repository_name)), sign_key=sign_key,
                                sudo=False)
        plans = None
        for index, cmdlet in enumerate(arguments):
            if cmdlet == 'targets':
                do_targets(arguments[index + 1:])
                break
            elif cmdlet == 'packages':
                do_packages(arguments[index + 1:], repository)
                break
            elif cmdlet == 'git':
                do_git(arguments[index + 1:])
                break
            elif cmdlet == 'update':
                if plans is None:
                    plans = do_plans(repository)
                execute_plans_update(plans, repository)
            elif cmdlet == 'autoremove':
                if plans is None:
                    plans = do_plans(repository)
                execute_plans_autoremove(plans, repository)
            elif cmdlet == 'plan':
                if plans is None:
                    plans = do_plans(repository)
            else:
                do_help(name)
                if cmdlet != '--help':
                    unknown_command(cmdlet)
                break
        if len(arguments) == 0:
            do_help(name)
        log(LogLevel.debug, 'Exiting...')
