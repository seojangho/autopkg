#!/usr/bin/python3

from enum import Enum

# TODO build_item: wrilte_pkgbuild_to, package_base_info, chroot_required


class DependencyType(Enum):
    """ Type of dependencies """

    root = 0
    run = 1
    make = 2
    check = 3


class DependencyVertex:
    """ Represents dependency node. """

    def __init__(self, build_item, edges):
        """ :param build_item: The corresponding build item.
        :param edges: List of edges that represents dependency for building this package-base.
        """
        self.build_item = build_item
        self.edges = edges


class DependencyEdge:
    """ Represents dependency relationship. """

    def __init__(self, pkgname, dependency_type):
        """ :param pkgname: The package name to depend on.
        :param dependency_type: The type of dependency.
        """
        self.pkgname = pkgname
        self.is_resolved = False
        self.vertex_to = None
        self.dependency_type = dependency_type

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

    @classmethod
    def from_package_base_info(cls, package_base_info):
        """ :param package_base_info: The PackageBaseInfo.
        :return: List of DependencyEdges.
        """
        dependencies = []
        for dependency in set(package_base_info.depends + package_base_info.makedepends +
                              package_base_info.checkdepends):
            if dependency in package_base_info.makedepends:
                dependencies.append(DependencyEdge(dependency, DependencyType.make))
            elif dependency in package_base_info.checkdepends:
                dependencies.append(DependencyEdge(dependency, DependencyType.check))
            else:
                dependencies.append(DependencyEdge(dependency, DependencyType.run))
        return dependencies


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
    """ Obtain dependency graph with BuildItems as vertices and DependencyEdges as edges.
    :param pkgnames: List of package names.
    :param backends: List of backends, sorted by priority.
    :return: List of DependencyEdges from the root vertex of the graph.
    """
    root_edges = [DependencyEdge(pkgname, DependencyType.root) for pkgname in set(pkgnames)]
    pkgname_to_vertex = dict()
    unresolved_edges = list(root_edges)
    while len(unresolved_edges) > 0:
        unresolved_pkgnames = [unresolved_edge.pkgname for unresolved_edge in unresolved_edges]
        new_vertices = list()
        for build_item in query_by_pkgnames(unresolved_pkgnames, backends):
            add_vertex_to_graph = False
            for package_info in build_item.package_base_info.package_infos:
                if package_info.name in unresolved_pkgname:
                    unresolved_pkgnames.remove(package_info.name)
                    add_vertex_to_graph = True
            if not add_vertex_to_graph:
                # Since this BuildItem does not contribute to resolving packages, discard it.
                continue
            new_vertex = DependencyVertex(build_item,
                                          DependencyEdge.from_package_base_info(build_item.package_base_info))
            new_vertices.append(new_vertex)
            for package_info in build_item.package_base_info.package_infos:
                if package_info.name not in pkgname_to_vertex:
                    pkgname_to_vertex[package_info.name] = new_vertex
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
