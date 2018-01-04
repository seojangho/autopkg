#!/usr/bin/python3

from subprocess import run
from subprocess import PIPE


class Version:
    """ Represents package version. """

    def __init__(self, version):
        """ :param version: A string that represents the version. """
        self.version = version

    def __repr__(self):
        """ :return: Formal representation of the version. """
        return self.version.__repr__()

    def cmp(self, other):
        """ :param other: The other version.
        :return: A negative integer if self < other, zero if self == other, a positive integer if self > other.
        """
        return int(run(['vercmp', self.version, other.version], stdout=PIPE).stdout.decode())

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
