#!/usr/bin/python3

from utils import run_lock
from utils import log
from utils import LogLevel
from sys import argv
from os import environ
from backends import git_backend
from backends import gshellext_backend
from backends import aur_backend
from repository import Repository
from utils import repository_home
from utils import sign_key
from utils import config
from contextlib import contextmanager
from utils import mkdir


BACKENDS = [git_backend, gshellext_backend, aur_backend]


def unknown_command(command):
    log(LogLevel.error, 'Unknown command: {}', command)


@contextmanager
def config_targets():
    with config('targets') as config_data:
        if config_data.json is None:
            config_data.json = []
        yield config_data


def do_targets(arguments):
    if len(arguments) == 0:
        return
    cmdlet = arguments[0]
    targets = arguments[1:]
    with config_targets() as config_data:
        if cmdlet == 'add':
            config_data.json = list(set(config_data.json + targets))
        elif cmdlet == 'remove':
            config_data.json = [pkgname for pkgname in config_data.json if pkgname not in targets]
        elif cmdlet == 'list':
            log(LogLevel.header, 'List of Targets:')
            for pkgname in config_data.json:
                log(LogLevel.info, ' - {}', pkgname)
        else:
            unknown_command(cmdlet)


def do_packages(arguments):
    pass


def front(arguments):
    with run_lock():
        log(LogLevel.debug, 'arguments: {}', arguments)
        log(LogLevel.debug, 'AUTOPKG_HOME: {}', environ.get('AUTOPKG_HOME', None))
        log(LogLevel.debug, 'AUTOPKG_KEY: {}', environ.get('AUTOPKG_KEY', None))
        log(LogLevel.debug, 'AUTOPKG_RETRY: {}', environ.get('AUTOPKG_RETRY', None))
        repository = Repository('autopkg', mkdir(repository_home), sign_key=sign_key, sudo=False)
        plans = None
        for index, cmdlet in enumerate(arguments):
            if cmdlet == 'targets':
                do_targets(arguments[index + 1:])
                break
            elif cmdlet == 'packages':
                do_packages(arguments[index + 1:])
                break
            elif cmdlet == 'update':
                pass
            elif cmdlet == 'autoremove':
                pass
            else:
                unknown_command(cmdlet)
                break
        log(LogLevel.debug, 'Exiting...')


if __name__ == '__main__':
    front(argv)
