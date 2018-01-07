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
from fcntl import flock
from fcntl import LOCK_EX
from fcntl import LOCK_UN
from re import sub
from time import strftime
from sys import stderr


home = str(Path.home())
autopkg_home = environ.get('AUTOPKG_HOME', join(home, '.autopkg'))
workspaces_home = join(autopkg_home, 'workspaces')
config_home = join(autopkg_home, 'config')
repository_home = join(autopkg_home, 'repository')
sign_key = environ.get('AUTOPKG_KEY', None)
num_retrials = int(environ.get('AUTOPKG_RETRY', 3))


def run(command, sudo=False, cwd=None, capture=True, quiet=False, stdin=None, allow_error=False):
    """
    :param command: The command to run.
    :param sudo: Whether to execute the command using sudo(1) or not.
    :param cwd: Working directory.
    :param capture: Whether to capture stdout and stderr or not.
    :param quiet: Do not log the command.
    :param stdin: Input string.
    :param allow_error: Whether to allow error or not.
    :return: The captured standard output.
    """
    prefix = ['sudo'] if sudo else []
    cmd = prefix + command
    if not quiet:
        log(LogLevel.fine, ' '.join(cmd))
    file = PIPE if capture else None
    try:
        completed = subprocess_run(cmd, cwd=cwd, stdout=file, stderr=file, check=True, encoding='utf-8', input=stdin)
        if capture:
            return completed.stdout
        else:
            return None
    except CalledProcessError as e:
        if allow_error:
            return None
        log(LogLevel.error, 'Error while running: {}', ' '.join(cmd))
        log(LogLevel.error, 'Return code: {}', e.returncode)
        if capture:
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
    run(['mkdir', '-p', path], sudo=sudo, quiet=True)
    return path


@contextmanager
def workspace():
    """ :return: Context manager for a directory that can be used as workspace. """
    with TemporaryDirectory(dir=mkdir(workspaces_home)) as path:
        yield path


@contextmanager
def advisory_lock(file):
    """ :param file: File to get a lock.
    :return: Context manager for advisory lock on the file.
    """
    flock(file, LOCK_EX)
    yield
    flock(file, LOCK_UN)


@contextmanager
def run_lock():
    """ :return: Context manager for run lock. """
    with open(join(mkdir(autopkg_home), 'run.lock'), mode='a') as file:
        with advisory_lock(file):
            yield


@contextmanager
def config(name):
    """ :param name: Name of the configuration file.
    :return: Context manager for the configuration file.
    """
    with open(join(mkdir(config_home), name + '.json'), mode='a+t') as file:
        with advisory_lock(file):
            file.seek(0)
            try:
                json = loads(file.read())
            except JSONDecodeError:
                json = None
            config_data = ConfigData(json)
            yield config_data
            if config_data.json is not None:
                file.truncate(0)
                file.seek(0)
                file.write(dumps(config_data.json))


class ConfigData:
    """ Config data. """

    def __init__(self, json):
        """ :param json: Initial json data. """
        self._json = json

    @property
    def json(self):
        return self._json

    @json.setter
    def json(self, value):
        self._json = value


class LogLevel(Enum):
    """ Log levels. """

    error = 0
    warn = 1
    info = 2
    header = 3
    good = 4
    fine = 5
    debug = 6


LOG_LEVEL_TO_COLOR = {LogLevel.error: [31],
                      LogLevel.warn: [33],
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


def remove_color(text):
    """ :param text: The text.
    :return: Text without color tags.
    """
    return sub('\033\[[0-9]+m', '', text)


def log(log_level, content, *args):
    """ Emit log entry.
    :param log_level: The LogLevel.
    :param content: The log content.
    :param args: Arguments for the format string.
    """
    try:
        log.file
    except AttributeError:
        log.file = open(join(mkdir(autopkg_home), 'log'), mode='a+t')
    text = str(content).format(*args)
    log.file.write('{}:{}\t{}\n'.format(strftime('%Y-%m-%dT%H:%M:%S%z'), log_level.name, remove_color(text)))
    log.file.flush()
    codes = LOG_LEVEL_TO_COLOR[log_level]
    if codes is None:
        return
    print(color(text, codes), file=stderr)
