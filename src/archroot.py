#!/usr/bin/python3

from contextlib import contextmanager
from utils import workspace
from utils import run
from utils import mkdir
from os.path import join
from os.path import isdir
from repository import Repository


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
        """ Build the package.
        :param pkgbuild_dir: The path to the directory where PKGBUILD resides.
        """
        run(['makechrootpkg', '-c', '-u', '-l', 'working', '-r', self.path], cwd=pkgbuild_dir, capture=False)
