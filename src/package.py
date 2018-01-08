#!/usr/bin/python3

from utils import run
from os.path import basename
from re import escape
from os import listdir
from os.path import join
from os.path import isfile
from re import match


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

    @classmethod
    def from_package_file_path(cls, path):
        """ Obtains package reference from the path to a package file.
        :param path: The path to the package file.
        :return: The package reference.
        """
        split = basename(path).split('-')
        return cls('-'.join(split[:-3]), '-'.join(split[-3:-1]))

    def __str__(self):
        """ :return: Representation of this package reference. """
        return '{} ({})'.format(self.name, self.version)

    def __repr__(self):
        """ :return: Formal representation of this package reference. """
        return '\'' + self.__str__() + '\''

    def pick_package_file_at(self, directory):
        """ :param directory: The directory.
        :return: The name of the package file in the directory.
        """
        pattern = '^{}-([0-9]+:)?[a-z0-9_.@+]+-[a-z0-9_.@+]+-[a-z0-9_.@+]+\.pkg\.tar\.xz$'.format(escape(self.name))
        matched = [file_name for file_name in listdir(directory) if isfile(join(directory, file_name))
                   and match(pattern, file_name)]
        if len(matched) != 1:
            raise Exception('The number of picked package file for {} at {}: {}'.format(self, directory, len(matched)))
        return matched[0]


class PackageInfo:
    """ Subset of PKGBUILD. """

    def __init__(self, pkgname, version, pkgbase=None, depends=[], makedepends=[], checkdepends=[]):
        """ :param pkgname: The name of this package.
        :param version: The version.
        :param pkgbase: The pkgbase.
        :param depends: List of names of packages this package depends on for running.
        :param makedepends: List of names of packages this package depends on for building.
        :param checkdepends: List of names of packages this package depends on for build-time checking.
        """
        self.pkgname = pkgname
        self.version = Version(version) if type(version) is str else version
        self.pkgbase = pkgbase if pkgbase is not None else pkgname
        self.depends = depends
        self.makedepends = makedepends
        self.checkdepends = checkdepends
        self.tiny_info = PackageTinyInfo(pkgname, version)

    def __str__(self):
        """ :return: Representation of this package reference. """
        return str(self.tiny_info)

    def __repr__(self):
        """ :return: Formal representation of this package reference. """
        return repr(self.tiny_info)

    def pick_package_file_at(self, directory):
        """ :param directory: The directory.
        :return: The name of the package file in the directory.
        """
        return self.tiny_info.pick_package_file_at(directory)


class Version:
    """ Represents package version, including pkgver, pkgrel, and epoch. """

    def __init__(self, version):
        """ :param version: A string that represents the version. """
        self.version = version

    @classmethod
    def from_components(cls, pkgver, pkgrel, epoch=None):
        epoch_string = '{}:'.format(epoch) if epoch is not None and int(epoch) != 0 else ''
        return cls('{}{}-{}'.format(epoch_string, pkgver, pkgrel))

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
        return int(run(['vercmp', str(self.version), str(other.version)], quiet=True))

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
