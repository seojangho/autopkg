#!/usr/bin/python3


class BuildPlan:
    """ Physical build plan. """

    def __init__(self, build_item, requisites, chroot):
        """ :param build_item: The BuildItem to execute.
        :param requisites: List of package names that this build_item depends on.
        :param chroot: Whether to run build in chroot environment or not.
        """
        if len(requisites) > 0 and not chroot:
            raise Exception("Cannot handle requisites in non-chroot build environment.")
        self.build_item = build_item
        self.requisites = requisites
        self.chroot = chroot