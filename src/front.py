#!/usr/bin/python3

from utils import run_lock
from utils import log
from utils import LogLevel
from os import environ
from backends import git_backend
from backends import gshellext_backend
from backends import aur_backend
from repository import Repository
from utils import repository_home
from utils import sign_key
from utils import config
from contextlib import contextmanager
from utils import mkdir
from builder import generate_plans
from builder import execute_plans_update
from builder import execute_plans_autoremove


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
        return
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
        return
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


def do_plans(repository):
    with config_targets() as config_data:
        return generate_plans(config_data.json, BACKENDS, repository)


def help(name):
    print('''Usage:\t{0} targets add [target-package-name-to-add]*
\t{0} targets remove [target-package-name-to-remove]*
\t{0} targets list
\t{0} packages add [path-to-the-package-file-to-add]*
\t{0} packages remove [package-name-to-remove]*
\t{0} packages list
\t{0} update
\t{0} autoremove
\t{0} update autoremove'''.format(name))


def front(name, arguments):
    with run_lock():
        log(LogLevel.debug, 'arguments: {}', arguments)
        log(LogLevel.debug, 'AUTOPKG_HOME: {}', environ.get('AUTOPKG_HOME', None))
        log(LogLevel.debug, 'AUTOPKG_KEY: {}', environ.get('AUTOPKG_KEY', None))
        log(LogLevel.debug, 'AUTOPKG_RETRY: {}', environ.get('AUTOPKG_RETRY', None))
        repository = Repository('autopkg', mkdir(repository_home), sign_key=sign_key, sudo=False)
        plans = None
        for index, cmdlet in enumerate(arguments):
            if cmdlet == 'targets':
                do_targets(arguments[index + 1:])
                break
            elif cmdlet == 'packages':
                do_packages(arguments[index + 1:], repository)
                break
            elif cmdlet == 'update':
                if plans is None:
                    plans = do_plans(repository)
                execute_plans_update(plans, repository)
            elif cmdlet == 'autoremove':
                if plans is None:
                    plans = do_plans(repository)
                execute_plans_autoremove(plans, repository)
            else:
                help(name)
                if cmdlet != '--help':
                    unknown_command(cmdlet)
                break
        log(LogLevel.debug, 'Exiting...')
