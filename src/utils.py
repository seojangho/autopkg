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
from enum import Enum


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
    cmd = prefix + command
    log(LogLevel.fine, ' '.join(cmd))
    return subprocess_run(cmd, stdout=PIPE, stderr=PIPE, check=True, encoding='utf-8').stdout


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


class LogLevel(Enum):
    """ Log levels. """

    error = 0
    warning = 1
    info = 2
    header = 3
    good = 4
    fine = 5


LOG_LEVEL_TO_COLOR = {LogLevel.error: [31],
                      LogLevel.warning: [33],
                      LogLevel.info: [],
                      LogLevel.header: [1, 4],
                      LogLevel.good: [32],
                      LogLevel.fine: [2]}


def log(log_level, content, *args):
    """ Emit log entry.
    :param log_level: The LogLevel.
    :param content: The log content.
    :param args: Arguments for the format string.
    """
    text = str(content).format(*args)
    color_code_start = ''.join(['\033[{}m'.format(code) for code in LOG_LEVEL_TO_COLOR[log_level]])
    print('{}{}\033[0m'.format(color_code_start, text))
