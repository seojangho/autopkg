#!/usr/bin/python3

from utils import run
from os.path import basename


class PackageTinyInfo:
    """ A reference that represents a particular package. """

    def __init__(self, name, version):
        """ :param name: The pkgname of this package.
        :param version: The package version.
        """
        self.name = name
        self.version = Version(version) if type(version) is str else version

    @classmethod
    def from_repodb_directory_name(cls, directory_name):
        """ Obtains package reference from a directory name in repository db.
        :param directory_name: The directory name.
        :return: The package reference.
        """
        split = directory_name.split('-')
        return cls('-'.join(split[:-2]), '-'.join(split[-2:]))

    def __str__(self):
        """ :return: Representation of this package reference. """
        return '{}({})'.format(self.name, self.version)

    def __repr__(self):
        """ :return: Formal representation of this package reference. """
        return '\'' + self.__str__() + '\''


class PackageMiniInfo:
    """ Same as PackageTinyInfo, but it has 'arch' attribute. """

    def __init__(self, name, version, arch):
        """ :param name: The pkgname of this package.
        :param version: The package version.
        :param arch: The target architecture of this package.
        """
        self.name = name
        self.version = Version(version) if type(version) is str else version
        self.arch = arch

    @classmethod
    def from_package_file_path(cls, path):
        """ Obtains package reference from the path to a package file.
        :param path: The path to the package file.
        :return: The package reference.
        """
        split = basename(path).split('-')
        return cls('-'.join(split[:-3]), '-'.join(split[-3:-1]), split[-1].split('.')[0])

    def __str__(self):
        """ :return: Representation of this package reference. """
        return '{}({}, {})'.format(self.name, self.version, self.arch)

    def __repr__(self):
        """ :return: Formal representation of this package reference. """
        return '\'' + self.__str__() + '\''

    def package_file_name(self):
        """ :return: The name of package file. """
        return '{}-{}-{}.pkg.tar.xz'.format(self.name, self.version, self.arch)


class PackageInfo:
    """ Subset of PKGBUILD. """

    # TODO AUR backend: use aur.archlinux.org/packages.gz

    def __init__(self, pkgname, version, arch, pkgbase=None, depends=[], makedepends=[], checkdepends=[]):
        """ :param pkgname: The name of this package.
        :param version: The version.
        :param arch: The architecture.
        :param pkgbase: The pkgbase.
        :param depends: List of names of packages this package depends on for running.
        :param makedepends: List of names of packages this package depends on for building.
        :param checkdepends: List of names of packages this package depends on for build-time checking.
        """
        self.pkgname = pkgname
        self.version = Version(version) if type(version) is str else version
        self.arch = arch
        self.pkgbase = pkgbase
        self.depends = depends
        self.makedepends = makedepends
        self.checkdepends = checkdepends
        self.mini_info = PackageMiniInfo(pkgname, version, arch)

    def __str__(self):
        """ :return: Representation of this package reference. """
        return str(self.mini_info)

    def __repr__(self):
        """ :return: Formal representation of this package reference. """
        return repr(self.mini_info)

    def package_file_name(self):
        """ :return: The name of package file. """
        return self.mini_info.package_file_name()


class Version:
    """ Represents package version, including pkgver, pkgrel, and epoch. """

    def __init__(self, version):
        """ :param version: A string that represents the version. """
        self.version = version

    def __str__(self):
        """ :return: Representation of the version. """
        return self.version

    def __repr__(self):
        """ :return: Formal representation of the version. """
        return self.version.__repr__()

    def cmp(self, other):
        """ :param other: The other version.
        :return: A negative integer if self < other, zero if self == other, a positive integer if self > other.
        """
        return int(run(['vercmp', self.version, other.version]))

    def __eq__(self, other):
        """ :param other: The other version.
        :return: True if and only if the two versions are equal.
        """
        return self.cmp(other) == 0

    def __ne__(self, other):
        """ :param other: The other version.
        :return: True if and only if the two versions are NOT equal.
        """
        return self.cmp(other) != 0

    def __lt__(self, other):
        """ :param other: The other version.
        :return: True if and only if self < other.
        """
        return self.cmp(other) < 0

    def __le__(self, other):
        """ :param other: The other version.
        :return: True if and only if self <= other.
        """
        return self.cmp(other) <= 0

    def __gt__(self, other):
        """ :param other: The other version.
        :return: True if and only if self > other.
        """
        return self.cmp(other) > 0

    def __ge__(self, other):
        """ :param other: The other version.
        :return: True if and only if self >= other.
        """
        return self.cmp(other) >= 0
