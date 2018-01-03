#!/usr/bin/python3


class Version:
    """ Represents package version. """

    def __init__(self, version):
        """ :param version: A string that represents the version.
        """
        self.version = version

    def __cmp__(self, other):

