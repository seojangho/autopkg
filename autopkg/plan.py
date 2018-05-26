#!/usr/bin/python3

from .utils import log
from .utils import LogLevel
from .utils import dedup


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
    def from_buildable(cls, buildable, plans):
        """ :param buildable: The Buildable from backend.
        :param plans: The plans to be executed ahead of this plan.
        :return: Plan to build this Buildable.
        """
        package_info = buildable.package_info
        dependencies = dedup(package_info.depends + package_info.makedepends + package_info.checkdepends)
        pkgname_to_plan = dict()  # a map from name of a package to the plan that resolves the package
        for plan in plans:
            for pkgname in plan.build + plan.keep:
                pkgname_to_plan[pkgname] = plan
        return cls(buildable, dedup([resolved_dependency for pkgname in dependencies for resolved_dependency in cls.track_dependency(pkgname, pkgname_to_plan)]))

    @classmethod
    def track_dependency(cls, dependency, pkgname_to_plan):
        if dependency in pkgname_to_plan:
            plan = pkgname_to_plan[dependency]
            return [dependency] + dedup([resolved_dependency for pkgname in plan.requisites for resolved_dependency in cls.track_dependency(pkgname, pkgname_to_plan)])
        else:
            return []

    def __str__(self):
        return '{}→[{}]'.format(self.buildable.source_reference, ', '.join(self.build + self.keep))

    def __repr__(self):
        return '\'{}\''.format(self)

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
        if pkgname in repository.packages and repository.packages[pkgname] >= self.buildable.package_info.version:
            self.add_keep(pkgname)
        else:
            self.add_build(pkgname)


def convert_graph_to_plans(graph, repository):
    """ :param graph: List of DependencyEdges from the root vertex of the package dependency graph.
    :param repository: The current repository.
    :return: List of Plans to execute in order.
    """
    for not_found in [edge.pkgname for edge in graph if edge.vertex_to is None]:
        log(LogLevel.error, "Not found: {}", not_found)
    # Root buildable with 'light' dependencies comes first.
    root_edges = [edge for edge in graph if edge.vertex_to is not None]
    root_edges.sort(key=lambda edge: edge.vertex_to.num_build_time_dependencies)
    source_to_plan = dict()
    lists_of_plans = [do_visit_vertex(edge.vertex_to, repository, [], source_to_plan) for edge in root_edges]
    return dedup([plan for plans in lists_of_plans for plan in plans])


def do_visit_vertex(vertex, repository, required_by, source_to_plan):
    """ :param vertex: The DependencyVertex.
    :param repository: The Repository.
    :param required_by: List of names of packages that requires building this package for building and checking.
    :param source_to_plan: Dictionary with each entry from source reference to Plan. Treated as a mutable object.
    :return: List of Plans to build packages specified by this subtree.
    """
    pkgname = vertex.buildable.package_info.pkgname
    if pkgname in required_by:
        raise CyclicDependencyError(vertex.buildable.package_info.pkgname)
    plans = list()
    for edge in vertex.edges:
        if not edge.is_resolved:
            raise Exception('Edge {} is not resolved'.format(edge))
        if edge.vertex_to is None:
            continue
        sub_vertex = edge.vertex_to
        if sub_vertex.buildable.source_reference in source_to_plan:
            # Merge into existing Plan.
            existing_plan = source_to_plan[sub_vertex.buildable.source_reference]
            existing_plan.add(edge.pkgname, repository)
            plans.append(existing_plan)
            continue
        try:
            plans.extend(do_visit_vertex(sub_vertex, repository, required_by + [pkgname], source_to_plan))
        except CyclicDependencyError as e:
            e.chain(pkgname)
            raise e
    plans = dedup(plans)
    source = vertex.buildable.source_reference
    # Recursive incarnation of 'do_visit_vertex' may have created Plan for this package
    # while resolving cyclic dependency due to runtime dependencies.
    # So we double-check the existence.
    if source not in source_to_plan:
        source_to_plan[source] = Plan.from_buildable(vertex.buildable, plans)
        plans.append(source_to_plan[source])
    source_to_plan[source].add(pkgname, repository)
    return plans


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
