#!/usr/bin/python3

from contextlib import contextmanager
from tempfile import TemporaryDirectory
from environment import mkdir
from environment import workspaces_home


@contextmanager
def workspace():
    """ :return: Context manager for a directory that can be used as workspace. """
    with TemporaryDirectory(dir=mkdir(workspaces_home)) as directory:
        yield directory
