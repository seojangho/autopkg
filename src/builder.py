#!/usr/bin/python3

from contextlib import contextmanager
from utils import workspace
from utils import run
from utils import mkdir
from utils import num_retrials
from utils import log
from utils import LogLevel
from os.path import join
from os.path import isdir
from repository import Repository
from graph import build_dependency_graph
from plan import convert_graph_to_plans
from subprocess import CalledProcessError


@contextmanager
def arch_root():
    """ :return: Context manager for an Arch chroot. """
    with workspace() as path:
        chroot_root = join(path, 'root')
        chroot_working = join(path, 'working')
        run(['mkarchroot', chroot_root, 'base-devel'], capture=False)
        run(['tee', '-a', chroot_root + '/etc/pacman.conf'], sudo=True,
            stdin='\n[autopkg]\nSigLevel = Never\nServer = file:///repo\n')
        yield ArchRoot(path)
        if isdir(chroot_root):
            chroot_cleanup(chroot_root)
        if isdir(chroot_working):
            chroot_cleanup(chroot_working)


def chroot_cleanup(path):
    """ Clears the specified chroot.
    :param path: Path to the chroot.
    """
    if run(['stat', '-f', '-c', '%T', path], quiet=True).strip() == 'btrfs':
        run(['btrfs', 'subvolume', 'delete', join(path, 'var', 'lib', 'machines')], sudo=True, allow_error=True)
        run(['btrfs', 'subvolume', 'delete', path], sudo=True, allow_error=True)
    else:
        run(['rm', '-rf', path], sudo=True)


class ArchRoot:
    """ An Arch chroot. """

    def __init__(self, path):
        """ :param ws: Path for the chroot. """
        self.path = path
        repository_path = join(path, 'root', 'repo')
        self.repository = Repository('autopkg', mkdir(repository_path, sudo=True), sudo=True)

    def build(self, pkgbuild_dir):
        """ Build packages in chroot environment.
        :param pkgbuild_dir: The path to the directory where PKGBUILD resides.
        """
        for i in range(num_retrials):
            try:
                run(['makechrootpkg', '-c', '-u', '-l', 'working', '-r', self.path], cwd=pkgbuild_dir, capture=False)
                return
            except CalledProcessError:
                pass
        message = 'Failed to build {} after {} trial(s)'.format(pkgbuild_dir, num_retrials)
        log(LogLevel.error, message)
        raise Exception(message)


def build(pkgbuild_dir):
    """ Build packages in non-chroot environment.
    :param pkgbuild_dir: The path to the directory where PKGBUILD resides.
    """
    run(['makepkg'], cwd=pkgbuild_dir, capture=False)


def generate_plans(pkgnames, backends, repository):
    """ :param pkgnames: The list of names of packages.
    :param backends: The list of backends to use.
    :param repository: The main repository.
    :return: Plan to build those packages.
    """
    graph = build_dependency_graph(pkgnames, backends)
    plans = convert_graph_to_plans(graph, repository)
    return plans


def execute_plans_update(plans, repository):
    """ :param plans: Plans to execute.
    :param repository: The main repository.
    """
    if sum(1 for plan in plans if plan.chroot and len(plan.build) > 0) > 0:
        # Chroot required.
        with arch_root() as chroot:
            do_build(plans, repository, chroot)
    else:
        do_build(plans, repository)


def do_build(plans, repository, chroot=None):
    """ :param plans: Plans to execute.
    :param repository: The main repository.
    :param chroot: Chroot environment.
    """
    for plan in plans:
        if len(plan.build) == 0:
            continue
        if plan.chroot:
            for requisite in plan.requisites:
                chroot.repository.add(repository.find_package_file_path(requisite))
        buildable = plan.buildable
        with workspace() as pkgbuild_workspace:
            pkgbuild_dir = buildable.write_pkgbuild_to(pkgbuild_workspace)
            if plan.chroot:
                chroot.build(pkgbuild_dir)
            else:
                build(pkgbuild_dir)
            built_package_file = join(pkgbuild_dir, buildable.package_info.pick_package_file_at(pkgbuild_dir))
            repository.add(built_package_file)
        log(LogLevel.good, 'Successfully built {} from {}', plan.buildable.package_info,
            plan.buildable.pkgbase_reference)


def execute_plans_autoremove(plans, repository):
    """ :param plans: Plans to execute.
    :param repository: The main repository.
    :return: The names of packages auto-removed.
    """
    needed = [pkgname for plan in plans for pkgname in plan.build + plan.keep]
    to_remove = list()
    for pkgname in repository.packages.keys():
        if pkgname not in needed:
            to_remove.append(pkgname)
    for pkgname in to_remove:
        repository.remove(pkgname)
        log(LogLevel.good, 'Removed {}', pkgname)
    return to_remove
