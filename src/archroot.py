#!/usr/bin/python3

from contextlib import contextmanager
from workspace import workspace
from environment import mkdir
from os.path import join


@contextmanager
def arch_root():
    """ :return: Context manager for an Arch chroot. """
    with workspace() as ws:
        pass
        # mkdir(join(ws.path, 'root'))


class ArchRoot:
    """ An Arch chroot. """

    def __init__(self, ws):
        """ :param ws: Workspace for this chroot. """
        self.workspace = ws

    def build(self, pkgbuild_dir):
        """ Build the package.
        :param pkgbuild_dir: The path to the directory where PKGBUILD resides.
        """
        pass
