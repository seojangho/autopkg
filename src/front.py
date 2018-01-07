#!/usr/bin/python3

from utils import run_lock
from utils import log
from utils import LogLevel
from sys import argv
from os import environ


def front(arguments):
    with run_lock():
        log(LogLevel.debug, 'arguments: {}', arguments)
        log(LogLevel.debug, 'AUTOPKG_HOME: {}', environ.get('AUTOPKG_HOME', None))
        log(LogLevel.debug, 'AUTOPKG_KEY: {}', environ.get('AUTOPKG_KEY', None))
        log(LogLevel.debug, 'AUTOPKG_RETRY: {}', environ.get('AUTOPKG_RETRY', None))
        plans = None
        for cmdlet in arguments:
            if cmdlet == 'target':
                break
            elif cmdlet == 'package':
                break
            elif cmdlet == 'update':
                pass
            elif cmdlet == 'autoremove':
                pass
            else:
                log(LogLevel.error, 'Unknown command: {}', cmdlet)
                break
        log(LogLevel.debug, 'Exiting...')


if __name__ == '__main__':
    front(argv)
