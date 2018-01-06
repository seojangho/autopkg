#!/usr/bin/python3

from utils import log
from utils import LogLevel


class Plan:
    """ Physical build/keep plan. """

    def __init__(self, buildable, requisites):
        """ :param buildable: The Buildable to execute.
        :param requisites: List of names of packages that this plan depends on.
        """
        self.buildable = buildable
        self.requisites = requisites
        self.build = []
        self.keep = []

    @classmethod
    def from_buildable(cls, buildable):
        """ :param buildable: The Buildable from backend.
        :return: Plan to build this Buildable.
        """
        return cls(buildable, list(set(buildable.package_info.makedepends + buildable.package_info.checkdepends)))

    @property
    def chroot(self):
        """ :return: Whether to execute this build in chroot environment or not. """
        return self.buildable.chroot_required or len(self.requisites) > 0

    def add_build(self, pkgname):
        """ :param pkgname: The name of the package to add to the build list. """
        if pkgname not in self.build:
            self.build.append(pkgname)

    def add_keep(self, pkgname):
        """ :param pkgname: The name of the package to add to the keep list. """
        if pkgname not in self.keep:
            self.keep.append(pkgname)

    def add(self, pkgname, repository):
        """ Investigate repository version and decide how to add this package to this plan (build or keep).
        :param pkgname: The name of the package.
        :param repository: The Repository.
        """
        repository_version = repository.packages[pkgname]
        pkgbuild_version = self.buildable.package_info.version
        if repository_version == pkgbuild_version:
            self.add_keep(pkgname)
        else:
            self.add_build(pkgname)


def convert_graph_to_plan(graph, repository):
    """ :param graph: List of DependencyEdges from the root vertex of the package dependency graph.
    :param repository: The current repository.
    :return: List of BuildPlans to execute in order.
    """
    for not_found in [edge.pkgname for edge in graph if edge.vertex_to is None]:
        log(LogLevel.error, "Not found: {}", not_found)
    # Root buildable with 'light' dependencies comes first.
    root_edges = [edge for edge in graph if edge.vertex_to is not None]
    root_edges.sort(key=lambda edge: edge.vertex_to.num_build_time_dependencies)
    pkgbase_to_plan = dict()
    lists_of_plans = [do_visit_vertex(edge.vertex_to, repository, [], pkgbase_to_plan) for edge in root_edges]
    return [plan for plans in lists_of_plans for plan in plans]


def do_visit_vertex(vertex, repository, required_by, pkgbase_to_plan):
    """ :param vertex: The DependencyVertex.
    :param repository: The Repository.
    :param required_by: List of names of packages that requires building this package for building and checking.
    :param pkgbase_to_plan: Dictionary with each entry from pkgbase reference to Plan. Treated as a mutable object.
    :return: List of BuildPlans to build packages specified by this subtree.
    """
    pkgname = vertex.buildable.package_info.pkgname
    if pkgname in required_by:
        raise CyclicDependencyError(vertex.buildable.package_info.pkgname)
    plan = list()
    for edge in vertex.edges:
        if not edge.is_resolved:
            raise Exception('Edge {} is not resolved'.format(edge))
        if edge.vertex_to is None:
            continue
        sub_vertex = edge.vertex_to
        if sub_vertex.buildable.pkgbase_reference in pkgbase_to_plan:
            # Merge into existing Plan.
            pkgbase_to_plan[sub_vertex.buildable.pkgbase_reference].add(edge.pkgname, repository)
            continue
        # Allow cyclic dependency for runtime dependency.
        sub_required_by = required_by + [pkgname] if edge.is_build_time_dependency else required_by
        try:
            plan.extend(do_visit_vertex(sub_vertex, repository, sub_required_by, pkgbase_to_plan))
        except CyclicDependencyError as e:
            e.chain(pkgname)
            raise e
    pkgbase = vertex.buildable.pkgbase_reference
    # Recursive incarnation of 'do_visit_vertex' may have created Plan for this package
    # while resolving cyclic dependency due to runtime dependencies.
    # So we double-check the existence.
    if pkgbase not in pkgbase_to_plan:
        pkgbase_to_plan[pkgbase] = Plan.from_buildable(vertex.buildable)
        plan.append(pkgbase_to_plan[pkgbase])
    pkgbase_to_plan[pkgbase].add(pkgname, repository)
    return plan


class CyclicDependencyError(Exception):
    """ Cyclic build-time dependency error. """

    def __init__(self, pkgname):
        """ :param pkgname: The name of the package of which this error is triggered. """
        self.chain = [pkgname]
        self.terminal = pkgname
        self.closed = False

    def chain(self, pkgname):
        """ :param pkgname: The name of the package to add to the chain. """
        if self.closed:
            return
        self.chain.insert(0, pkgname)
        if pkgname == self.terminal:
            self.closed = True

    def __str__(self):
        return '→'.join(self.chain)

    def __repr__(self):
        return '\'{}\''.format('->'.join(self.chain))
