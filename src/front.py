#!/usr/bin/python3

from backends import git_backend
from backends import gshellext_backend
from backends import aur_backend
from graph import build_dependency_graph
from plan import convert_graph_to_plan
from repository import Repository


BACKENDS = [git_backend, gshellext_backend, aur_backend]


def test(pkgnames):
    repository = Repository('testrepo', '/home/jangho/workspace/testrepo')
    graph = build_dependency_graph(pkgnames, BACKENDS)
    plan = convert_graph_to_plan(graph, repository)
    return plan
