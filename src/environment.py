#!/usr/bin/python3

from pathlib import Path
from os.path import join
from os import environ
from subprocess import run as subprocess_run
from subprocess import PIPE


home = str(Path.home())
autopkg_home = environ.get('AUTOPKG_HOME', join(home, '.autopkg'))
workspaces_home = join(autopkg_home, 'workspaces')
config_home = join(autopkg_home, 'config')


def run(command, sudo=False):
    """
    :param command: The command to run.
    :param sudo: Whether to execute the command using sudo(1) or not.
    :return: The captured standard output.
    """
    prefix = ['sudo'] if sudo else []
    return subprocess_run(prefix + command, stdout=PIPE, stderr=PIPE, check=True, encoding='utf-8').stdout


def mkdir(path, sudo=False):
    """ Recursively create directories.
    :param path: The leaf directory to create.
    :param sudo: Whether to execute using sudo(1) or not.
    :return: The path to the leaf directory.
    """
    run(['mkdir', '-p', path], sudo=sudo)
    return path
