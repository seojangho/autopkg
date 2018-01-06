#!/usr/bin/python3

from enum import Enum

# TODO buildable: wrilte_pkgbuild_to, package_info, chroot_required, pkgbase_reference


class DependencyType(Enum):
    """ Type of dependencies """

    explicit = 0
    run = 1
    make = 2
    check = 3


class DependencyVertex:
    """ Represents dependency node. """

    def __init__(self, buildable, edges):
        """ :param buildable: The corresponding buildable from the backend.
        :param edges: List of edges that represents dependency for running or building this package.
        """
        self.buildable = buildable
        self.edges = edges

    @classmethod
    def from_buildable(cls, buildable):
        """ :param buildable: The Buildable.
        :return: The DependencyVertex for this Buildable.
        """
        edges = []
        package_info = buildable.package_info
        for dependency in set(package_info.depends + package_info.makedepends + package_info.checkdepends):
            if dependency in package_info.makedepends:
                edges.append(DependencyEdge(dependency, DependencyType.make))
            elif dependency in package_info.checkdepends:
                edges.append(DependencyEdge(dependency, DependencyType.check))
            else:
                edges.append(DependencyEdge(dependency, DependencyType.run))
        return cls(buildable, edges)

    def __str__(self):
        """ :return: Representation for this DependencyVertex. """
        return 'DependencyVertex({})'.format(self.buildable.package_info.pkgname)

    def __repr__(self):
        """ :return: Formal representation for this DependencyVertex. """
        return 'DependencyVertex({}, {})'.format(repr(self.buildable), repr(self.edges))

    @property
    def num_build_time_dependencies(self):
        """ :return: The number of build-time dependencies. """
        return sum(1 for edge in self.edges if edge.is_build_time_dependency)


class DependencyEdge:
    """ Represents dependency relationship. """

    def __init__(self, pkgname, dependency_type):
        """ :param pkgname: The name of package to depend on
        :param dependency_type: The type of dependency.
        """
        self.pkgname = pkgname
        self.dependency_type = dependency_type
        self.is_resolved = False
        self.vertex_to = None

    def __str__(self):
        """ :return: Representation for this DependencyEdge. """
        return 'DependencyEdge({}, {}, is_resolved={}, vertex_to={})'.format(self.pkgname, self.dependency_type,
                                                                             self.is_resolved, self.vertex_to)

    def __repr__(self):
        """ :return: Formal representation for this DependencyEdge. """
        return 'DependencyEdge({}, {}, is_resolved={}, vertex_to={})'.format(self.pkgname, self.dependency_type,
                                                                             self.is_resolved, repr(self.vertex_to))

    def resolve(self, vertex_to):
        """ Resolve the dependency by setting appropriate DependencyVertex for this edge.
        :param vertex_to: The DependencyVertex. None means unable to obtain build items using backends.
        """
        if self.is_resolved:
            raise Exception("Re-assigning vertex is not allowed.")
        self.vertex_to = vertex_to
        self.is_resolved = True

    @property
    def is_build_time_dependency(self):
        """ :return: True if and only if this dependency relationship is build-time dependency. """
        return self.dependency_type != DependencyType.run


def query_by_pkgnames(pkgnames, backends):
    """ Obtain BuildItems from package names.
    :param pkgnames: List of package names.
    :param backends: List of backends, sorted by priority.
    :return: List of the found buildables.
    """
    names = list(pkgnames)
    buildables = list()
    for backend in backends:
        new_buildables = backend(names)
        buildables += new_buildables
        resolved = [buildable.package_info.pkgname for buildable in new_buildables]
        names = [name for name in names if name not in resolved]
    return buildables


def build_dependency_graph(pkgnames, backends):
    """ Obtain dependency graph with DependencyVertex as vertices and DependencyEdges as edges.
    :param pkgnames: List of package names.
    :param backends: List of backends, sorted by priority.
    :return: List of DependencyEdges from the root vertex of the graph.
    """
    root_edges = [DependencyEdge(pkgname, DependencyType.explicit) for pkgname in set(pkgnames)]
    pkgname_to_vertex = dict()
    unresolved_edges = list(root_edges)
    while len(unresolved_edges) > 0:
        unresolved_pkgnames = [unresolved_edge.pkgname for unresolved_edge in unresolved_edges]
        new_vertices = list()
        for buildable in query_by_pkgnames(unresolved_pkgnames, backends):
            if buildable.package_info.pkgname not in unresolved_pkgname:
                # Since this BuildItem does not contribute to resolving packages, discard it.
                # Maybe buildable.package_info.pkgname has been resolved by other Buildable ahead.
                continue
            unresolved_pkgnames.remove(buildable.package_info.pkgname)
            new_vertex = DependencyVertex.from_buildable(buildable)
            new_vertices.append(new_vertex)
            pkgname_to_vertex[buildable.package_info.pkgname] = new_vertex
        for unresolved_pkgname in unresolved_pkgnames:
            # We have tried to find BuildItem for unresolved_pkgname, but it was unable to obtain.
            # Maybe it's from official repositories.
            pkgname_to_vertex[unresolved_pkgname] = None
        for unresolved_edge in unresolved_edges:
            unresolved_edge.resolve(pkgname_to_vertex[unresolved_edge.pkgname])
        for unresolved_edge in [edge for vertex in new_vertices for edge in vertex.edges]:
            # Resolve dependencies for newly added vertices, if possible.
            if unresolved_edge.pkgname in pkgname_to_vertex:
                unresolved_edge.resolve(pkgname_to_vertex[unresolved_edge.pkgname])
        # Unresolved dependencies for newly added vertices will be handled in the next round.
        unresolved_edges = [edge for vertex in new_vertices for edge in vertex.edges if not edge.is_resolved]
    return root_edges
