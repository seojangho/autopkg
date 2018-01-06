#!/usr/bin/python3

# TODO build_item: wrilte_pkgbuild_to, package_base_info


class DependencyVertex:
    """ Represents build-time dependency node. """

    def __init__(self, build_item, edges):
        """ :param build_item: The corresponding build item.
        :param edges: List of edges that represents build-time dependency for building this package-base.
        """
        self.build_item = build_item
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
        :param vertex_to: The DependencyVertex. None means unable to obtain build items using backends.
        """
        if self.is_resolved:
            raise Exception("Re-assigning vertex is not allowed.")
        self.vertex_to = vertex_to
        self.is_resolved = True


def query_by_pkgnames(pkgnames, backends):
    """ Obtain BuildItems from package names.
    :param pkgnames: List of package names.
    :param backends: List of backends, sorted by priority.
    :return: List of the found build items.
    """
    names = list(pkgnames)
    build_items = list()
    for backend in backends:
        items = backend(names)
        build_items += items
        resolved = [package_info.name for item in items for package_info in item.package_base_info.package_infos]
        names = [name for name in names if name not in resolved]
    return build_items


def build_dependency_graph(pkgnames, backends):
    """ Obtain build-time dependency graph with BuildItems as vertices and DependencyEdges as edges.
    :param pkgnames: List of package names.
    :param backends: List of backends, sorted by priority.
    :return: List of DependencyEdges from the root vertex of the graph.
    """
    root_edges = [DependencyEdge(pkgname) for pkgname in set(pkgnames)]
    pkgname_to_vertex = dict()
    unresolved_edges = list(root_edges)
    while len(unresolved_edges) != 0:
        unresolved_pkgnames = [unresolved_edge.pkgname for unresolved_edge in unresolved_edges]
        new_vertices = list()
        for build_item in query_by_pkgnames(unresolved_pkgnames, backends):
            add_vertex_to_graph = False
            edges = [DependencyEdge(name) for name
                     in set(build_item.package_base_info.makedepends + build_item.package_base_info.checkdepends)]
            new_vertex = DependencyVertex(build_item, edges)
            for package_info in build_item.package_base_info.package_infos:
                if package_info.name in unresolved_pkgname:
                    unresolved_pkgnames.remove(package_info.name)
                    add_vertex_to_graph = True
            if not add_vertex_to_graph:
                continue
            new_vertices.append(new_vertex)
            for package_info in build_item.package_base_info.package_infos:
                if package_info.name not in pkgname_to_vertex:
                    pkgname_to_vertex[package_info.name] = new_vertex
        for unresolved_pkgname in unresolved_pkgnames:
            pkgname_to_vertex[unresolved_pkgname] = None
        for unresolved_edge in unresolved_edges:
            unresolved_edge.resolve(pkgname_to_vertex[unresolved_edge.pkgname])
        unresolved_edges = [edge for vertex in new_vertices for edge in vertex.edges]
    return root_edges
