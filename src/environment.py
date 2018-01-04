#!/usr/bin/python3

from pathlib import Path
from os.path import join
from os import environ
from os import makedirs
from subprocess import run
from subprocess import PIPE


home = str(Path.home())
autopkg_home = environ.get('AUTOPKG_HOME', join(home, '.autopkg'))
workspaces_home = join(autopkg_home, 'workspaces')
config_home = join(autopkg_home, 'config')


def mkdir(path, sudo=False):
    """ Recursively create directories.
    :param path: The leaf directory to create.
    :param sudo: Whether to execute using sudo(1) or not.
    :return: The path to the leaf directory.
    """
    if sudo:
        run(['sudo', 'mkdir', '-p', path], stderr=PIPE).check_returncode()
    else:
        makedirs(path, exist_ok=True)
    return path
