#!/usr/bin/python3


class BuildPlan:
    """ Physical build plan. """

    def __init__(self, buildable, requisites):
        """ :param buildable: The Buildable to execute.
        :param requisites: List of names of packages that this build_item depends on.
        """
        self.buildable = buildable
        self.requisites = requisites
        self.pkgnames = []

    @property
    def chroot(self):
        """ :return: Whether to execute this build in chroot environment or not. """
        return self.buildable.chroot_required or len(self.requisites) > 0

    def add_target_package(self, pkgname):
        """ :param pkgname: The name of the package to add to the target list. """
        self.pkgnames.append(pkgname)


class KeepPlan:
    """ Plan to keep a package in the repository. """

    def __init__(self, pkgname):
        """ :param pkgname: The package name. """
        self.pkgname = pkgname


def convert_graph_to_plan(graph, repository):
    """ :param graph: List of DependencyEdges from the root vertex of the package dependency graph.
    :param repository: The current repository.
    :return: List of BuildPlans to execute in order.
    """
    # Root buildable with 'light' dependencies comes first.
    root_edges = [edge for edge in graph if edge.vertex_to is not None].sort(
        key=lambda edge: edge.vertex_to.num_build_time_dependencies)


def do_visit_vertex(vertex, repository, pkgbase_reference_to_build_plan):
    pass
