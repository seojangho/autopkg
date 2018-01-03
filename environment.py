#!/usr/bin/python3

from pathlib import Path
from os.path import join
from os import environ
from os import makedirs


home = str(Path.home())
autopkg_home = environ.get('AUTOPKG_HOME', join(home, '.autopkg'))
workspaces_home = join(autopkg_home, 'workspaces')
config_home = join(autopkg_home, 'config')


def mkdir(path):
    """ Recursively create directories.
    :param path: The leaf directory to create.
    :return: The path to the leaf directory.
    """
    makedirs(path, mode=0o700, exist_ok=True)
    return path
