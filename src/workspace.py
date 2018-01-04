#!/usr/bin/python3

from contextlib import contextmanager
from tempfile import TemporaryDirectory
from environment import mkdir
from environment import workspaces_home


@contextmanager
def workspace():
    """ :return: Context manager for a directory that can be used as workspace. """
    with TemporaryDirectory(dir=mkdir(workspaces_home)) as path:
        yield Workspace(path)


class Workspace:
    """ A workspace. """

    def __init__(self, path):
        """ :param path: Path to the workspace. """
        self.path = path
