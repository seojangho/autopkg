#!/usr/bin/python3

from contextlib import contextmanager


@contextmanager
def repository(path):
    """ :param path: Path to the repository.
    :return: Context manager for the Arch repository.
    """
    yield Repository(path)


class Repository:
    """ An Arch repository. """

    def __init__(self, path):
        """ :param path: Path to this repository. """
        self.path = path
