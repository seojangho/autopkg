#!/usr/bin/python3

from contextlib import contextmanager
from tempfile import TemporaryDirectory
from pathlib import Path
from os.path import join
from os import environ
from subprocess import run as subprocess_run
from subprocess import PIPE
from json import loads
from json import dumps
from json.decoder import JSONDecodeError


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


@contextmanager
def config(name):
    """ :param name: Name of the configuration file.
    :return: Context manager for the configuration file.
    """
    with open(join(mkdir(config_home), name + '.json'), mode='a+t') as file:
        try:
            json = loads(file.read())
        except JSONDecodeError:
            json = None
        yield json
        if json is not None:
            file.truncate(0)
            file.seek(0)
            file.write(dumps(json))
