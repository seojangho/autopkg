#!/usr/bin/python3


class DependencyVertex:
    """ Represents build-time dependency node. """

    def __init__(self, package_base_info, edges):
        """ :param package_base_info: The PackageBaseInfo.
        :param edges: List of edges that represents build-time dependency for building this package-base.
        """
        self.package_base_info = package_base_info
        self.edges = edges


class DependencyEdge:
    """ Represents build-time dependency relationship. """

    def __init__(self, pkgname):
        """ :param pkgname: The package name to depend on. """
        self.pkgname = pkgname
        self.is_resolved = False
        self.vertex_to = None

    def resolve(self, vertex_to=None):
        """ Resolve the dependency by setting appropriate DependencyVertex for this edge.
        :param vertex_to: The DependencyVertex. None means unable to build using autopkg.
        """
        if self.is_resolved:
            raise Exception("Re-assigning vertex is not allowed.")
        self.vertex_to = vertex_to
        self.is_resolved = True


def query_by_pkgnames(pkgnames, backends):
    """ Obtain BuildItems from package names.
    :param pkgnames: List of package names.
    :param backends: List of backends, sorted by priority.
    :return: Dictionary with each entry from name of package to the corresponding BuildItem, or None for not found.
    """
    names = list(pkgnames)
    mapping = dict()
    for backend in backends:
        build_items = backend(names)
        for build_item in build_items:
            for package_info in build_item.package_base_info.package_infos:
                if package_info.name not in mapping:
                    mapping[package_info.name] = build_item
                try:
                    names.remove(package_info.name)
                except ValueError:
                    pass
    for name in names:
        mapping[name] = None
    return mapping


def build_dependency_graph(pkgnames, backends):
    """ Obtain build-time dependency graph with BuildItems as vertices and DependencyEdges as edges.
    :param pkgnames: List of package names.
    :param backends: List of backends, sorted by priority.
    :return: List of DependencyEdges from the root vertex of the graph.
    """
    pkgname_to_vertex = dict()
    root_edges = [DependencyEdge(pkgname) for pkgname in set(pkgnames)]
    unresolved_edges = list(root_edges)
    while len(unresolved_edges) != 0:
        pass
    return root_edges
