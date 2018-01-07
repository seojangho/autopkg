#!/usr/bin/python3

from backends import git_backend
from backends import gshellext_backend
from backends import aur_backend
from graph import build_dependency_graph
from plan import convert_graph_to_plan
from repository import Repository
from utils import run_lock
from utils import log
from utils import LogLevel
from sys import argv
from os import environ
from archroot import arch_root
from time import sleep

BACKENDS = [git_backend, gshellext_backend, aur_backend]


def test(pkgnames):
    with run_lock():
        repository = Repository('testrepo', '/home/jangho/workspace/testrepo')
        graph = build_dependency_graph(pkgnames, BACKENDS)
        plan = convert_graph_to_plan(graph, repository)
        return plan


def chroot():
    with arch_root():
        sleep(10)
        pass


if __name__ == '__main__':
    log(LogLevel.debug, 'argv: {}', argv)
    log(LogLevel.debug, 'AUTOPKG_HOME: {}', environ.get('AUTOPKG_HOME', None))
    log(LogLevel.debug, 'AUTOPKG_KEY: {}', environ.get('AUTOPKG_KEY', None))
    log(LogLevel.debug, 'AUTOPKG_RETRY: {}', environ.get('AUTOPKG_RETRY', None))
