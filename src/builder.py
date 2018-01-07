#!/usr/bin/python3

from contextlib import contextmanager
from utils import workspace
from utils import run
from utils import mkdir
from utils import repository_home
from utils import sign_key
from os.path import join
from os.path import isdir
from repository import Repository
from backends import git_backend
from backends import gshellext_backend
from backends import aur_backend
from graph import build_dependency_graph
from plan import convert_graph_to_plans


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
        run(['btrfs', 'subvolume', 'delete', join(path, 'var', 'lib', 'machines')], sudo=True)
        run(['btrfs', 'subvolume', 'delete', path], sudo=True)
    else:
        run(['rm', '-rf', path], sudo=True)


class ArchRoot:
    """ An Arch chroot. """

    def __init__(self, path):
        """ :param ws: Pato for the chroot. """
        self.path = path
        repository_path = join(path, 'root', 'repo')
        mkdir(repository_path, sudo=True)
        self.repository = Repository('autopkg', repository_path, sudo=True)

    def build(self, pkgbuild_dir):
        """ Build packages in chroot environment.
        :param pkgbuild_dir: The path to the directory where PKGBUILD resides.
        """
        run(['makechrootpkg', '-c', '-u', '-l', 'working', '-r', self.path], cwd=pkgbuild_dir, capture=False)


def build(pkgbuild_dir):
    """ Build packages in non-chroot environment.
    :param pkgbuild_dir: The path to the directory where PKGBUILD resides.
    """
    run(['makepkg'], cwd=pkgbuild_dir, capture=False)


BACKENDS = [git_backend, gshellext_backend, aur_backend]


def main_repository():
    """ :return: Main repository. """
    return Repository('autopkg', repository_home, sign_key=sign_key, sudo=False)


def generate_plans(pkgnames):
    """ :param pkgnames: The list of names of packages.
    :return: Plan to build those packages.
    """
    repository = main_repository()
    graph = build_dependency_graph(pkgnames, BACKENDS)
    plans = convert_graph_to_plans(graph, repository)
    return plans


def execute_plans_build(plans):
    """ :param plans: Plans to execute. """
    if sum(1 for plan in plans if plan.chroot and len(plan.build) > 0) > 0:
        # Chroot required.
        with arch_root() as chroot:
            do_build(plans, chroot)
    else:
        do_build(plans)


def do_build(plans, chroot=None):
    """ :param plans: Plans to execute.
    :param chroot: Chroot environment.
    """
    repository = main_repository()
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
            built_package_file = join(pkgbuild_dir, buildable.pacakge_info.pick_package_file_at(pkgbuild_dir))
            repository.add(built_package_file)


def execute_plans_autoremove(plans):
    """ :param plans: Plans to execute.
    :return: The names of packages auto-removed.
    """
    needed = [pkgname for plan in plans for pkgname in plan.build + plan.keep]
    repository = main_repository()
    to_remove = list()
    for pkgname in repository.packages.keys():
        if pkgname not in needed:
            to_remove.append(pkgname)
    for pkgname in to_remove:
        repository.remove(pkgname)
    return to_remove
