#!/usr/bin/python3

from utils import run
from os.path import basename


class Package:
    """ A reference that represents a particular package. """
    def __init__(self, name, version, arch=None):
        """ :param name: The pkgname of this package.
        :param version: The package version.
        :param arch: The target architecture of this package. None means unknown.
        """
        self.name = name
        self.version = Version(version) if type(version) is str else version
        self.arch = arch

    @classmethod
    def from_repodb_directory_name(cls, directory_name):
        """ Obtains package reference from a directory name in repository db.
        :param directory_name: The directory name.
        :return: The package reference.
        """
        split = directory_name.split('-')
        return cls('-'.join(split[:-2]), '-'.join(split[-2:]))

    @classmethod
    def from_package_file_path(cls, path):
        """ Obtains package reference from the path to a package file.
        :param path: The path to the package file.
        :return: The package reference.
        """
        split = basename(path).split('-')
        return cls('-'.join(split[:-3]), '-'.join(split[-3:-1]), arch=split[-1].split('.')[0])

    def __str__(self):
        """ :return: Representation of this package reference. """
        return '{}-{}-{}'.format(self.name, self.version, 'UNKNOWN' if self.arch is None else self.arch)

    def __repr__(self):
        """ :return: Formal representation of this package reference. """
        return '\'' + self.__str__() + '\''

    def package_file_name_pattern(self):
        """ :return: Prefix of the possible name of package file. """
        # TODO "Pick" package file from the specified directory
        return '{}-{}-{}'.format(self.name, self.version, '' if self.arch is None else self.arch)


class PackageInfo:
    # TODO AURBuildItem: aurbuilditem.write_pkgbuild_to(path)
    # TODO GitBuildItem: gitbuilditem.write_pkgbuild_to(path)
    # TODO GShellExtBuildItem: gshellextbuilditem.write_pkgbuild_to(path)
    # TODO AUR backend: use aur.archlinux.org/packages.gz

    # TODO type(aurbuilditem.pkgbuild) is package.PkgBuild
    # TODO type(aurbuilditem.chroot_required) is bool
    # TODO type(aurbuilditem.build_dependencies) is list of other BuildItems

    # TODO builder 1) resolves dependencies 2) builds builditems as needed

    # TODO in short, backend provides two thigns - 1) .write_pkgbuild_to 2) query PackageInfo from package name
    pass


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
