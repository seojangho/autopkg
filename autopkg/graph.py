#!/usr/bin/python3

from enum import Enum


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
        return len(self.edges)


class DependencyEdge:
    """ Represents dependency relationship. """

    def __init__(self, pkgname, dependency_type):
        """ :param pkgname: The name of package to depend on. CASE SENSITIVE.
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


class CaseInsensitiveStringList:
    """ A list of strings that ignores case, except for 'get'. """

    def __init__(self, lst):
        self.list_original = lst
        self.list_lower = [string.lower() for string in lst]
        if len(self.list_lower) != len(set(self.list_lower)):
            raise Exception('Cannot build case insensitive list with unique elements.')

    def __contains__(self, item):
        return item.lower() in self.list_lower

    def __len__(self):
        return len(self.list_original)

    def get(self):
        return self.list_original

    def get_lower(self):
        return self.list_lower

    def remove(self, string):
        try:
            index = self.list_lower.index(string.lower())
            del self.list_original[index]
            del self.list_lower[index]
        except ValueError:
            pass

    def remove_strings(self, strings):
        for string in strings:
            self.remove(string)


def query_by_pkgnames(pkgnames, backends):
    """ Obtain BuildItems from package names.
    :param pkgnames: List of package names.
    :param backends: List of backends, sorted by priority.
    :return: List of the found buildables.
    """
    names = CaseInsensitiveStringList(list(set(pkgnames)))
    buildables = list()
    for backend in backends:
        new_buildables = backend(names.get())
        buildables += new_buildables
        names.remove_strings([buildable.package_info.pkgname for buildable in new_buildables])
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
        unresolved_pkgnames = CaseInsensitiveStringList(
            list(set([unresolved_edge.pkgname for unresolved_edge in unresolved_edges])))
        new_vertices = list()
        for buildable in query_by_pkgnames(unresolved_pkgnames.get(), backends):
            if buildable.package_info.pkgname not in unresolved_pkgnames:
                # Since this BuildItem does not contribute to resolving packages, discard it.
                # Maybe buildable.package_info.pkgname has been resolved by other Buildable ahead.
                continue
            unresolved_pkgnames.remove(buildable.package_info.pkgname)
            new_vertex = DependencyVertex.from_buildable(buildable)
            new_vertices.append(new_vertex)
            pkgname_to_vertex[buildable.package_info.pkgname] = new_vertex
        for unresolved_pkgname in unresolved_pkgnames.get_lower():
            # We have tried to find BuildItem for unresolved_pkgname, but it was unable to obtain.
            # Maybe it's from official repositories.
            pkgname_to_vertex[unresolved_pkgname] = None
        for unresolved_edge in unresolved_edges:
            unresolved_edge.resolve(pkgname_to_vertex[unresolved_edge.pkgname.lower()])
        for unresolved_edge in [edge for vertex in new_vertices for edge in vertex.edges]:
            # Resolve dependencies for newly added vertices, if possible.
            if unresolved_edge.pkgname.lower() in pkgname_to_vertex:
                unresolved_edge.resolve(pkgname_to_vertex[unresolved_edge.pkgname.lower()])
        # Unresolved dependencies for newly added vertices will be handled in the next round.
        unresolved_edges = [edge for vertex in new_vertices for edge in vertex.edges if not edge.is_resolved]
    return root_edges
