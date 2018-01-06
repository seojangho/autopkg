#!/usr/bin/python3

from utils import run


class PkgbaseReference:
    def __init__(self, pkgbase, backend):
        if pkgbase is None:
            raise Exception('pkgbase=None is not allowed')
        self.pkgbase = pkgbase
        self.backend = backend

    def __str__(self):
        return str(self.pkgbase)

    def __repr__(self):
        return repr(self.pkgbase)

    def __hash__(self):
        return hash(self.pkgbase)

    def __eq__(self, other):
        if not isinstance(other, PkgbaseReference):
            return False
        return self.pkgbase == other.pkgbase and self.backend == other.backend


class AURBuildable:
    def __init__(self, package_info):
        self.package_info = package_info
        self.pkgbase = package_info.pkgbase if package_info.pkgbase is not None else package_info.pkgname
        self.pkgbase_reference = PkgbaseReference(self.pkgbase, 'aur')

    def write_pkgbuild_to(self, path):
        """ :param path: Path to workspace.
        :return: Path to the leaf directory where PKGBUILD resides.
        """
        giturl = 'https://aur.archlinux.org/{}.git'.format(self.pkgbase)
        run(['git', 'clone', giturl, path])
        return path

    @property
    def chroot_required(self):
        return True


def aur_backend(pkgnames):
    """ :param pkgnames: The names of the packages to lookup.
    :return: List of related AURBuildables.
    """
