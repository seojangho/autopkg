#!/usr/bin/python3

from contextlib import contextmanager
from urllib.request import urlopen
from tempfile import TemporaryDirectory
from pathlib import Path
from os.path import join
from os import environ
from subprocess import run as subprocess_run
from subprocess import PIPE
from subprocess import CalledProcessError
from json import loads
from json import dumps
from json.decoder import JSONDecodeError
from enum import Enum


home = str(Path.home())
autopkg_home = environ.get('AUTOPKG_HOME', join(home, '.autopkg'))
workspaces_home = join(autopkg_home, 'workspaces')
config_home = join(autopkg_home, 'config')


def run(command, sudo=False, cwd=None, capture=True, quiet=False):
    """
    :param command: The command to run.
    :param sudo: Whether to execute the command using sudo(1) or not.
    :param cwd: Working directory.
    :param capture: Whether to capture stdout and stderr or not.
    :param quiet: Do not log the command.
    :return: The captured standard output.
    """
    prefix = ['sudo'] if sudo else []
    cmd = prefix + command
    if not quiet:
        log(LogLevel.fine, ' '.join(cmd))
    file = PIPE if capture else None
    try:
        return subprocess_run(cmd, cwd=cwd, stdout=file, stderr=file, check=True, encoding='utf-8').stdout
    except CalledProcessError as e:
        log(LogLevel.error, e.stderr)
        raise e


def url_read(url_format, *args):
    """ :param url_format: Format string for the URL of the resource.
    :param args: Format arguments.
    :return: Fetched response.
    """
    url = url_format.format(*args)
    log(LogLevel.fine, url)
    with urlopen(url) as response:
        return response.read()


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
        yield path


@contextmanager
def config(name):
    """ :param name: Name of the configuration file.
    :return: Context manager for the configuration file.
    """
    # TODO config lockfile
    # TODO autopkg run_lock
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
    debug = 6


LOG_LEVEL_TO_COLOR = {LogLevel.error: [31],
                      LogLevel.warning: [33],
                      LogLevel.info: [],
                      LogLevel.header: [1, 4],
                      LogLevel.good: [32],
                      LogLevel.fine: [2],
                      LogLevel.debug: None}


def color(text, codes):
    """ :param text: The text.
    :param codes: Color codes to apply.
    :return: Colored text for terminal.
    """
    return '{}{}\033[0m'.format(''.join(['\033[{}m'.format(code) for code in codes]), text)


def log(log_level, content, *args):
    """ Emit log entry.
    :param log_level: The LogLevel.
    :param content: The log content.
    :param args: Arguments for the format string.
    """
    text = str(content).format(*args)
    # TODO: Write to log file
    codes = LOG_LEVEL_TO_COLOR[log_level]
    if codes is None:
        return
    print(color(text, codes))
