#!/usr/bin/python3

from os.path import join
from os.path import exists
from environment import run


class Repository:
    """ An Arch repository. """

    def __init__(self, name, path):
        """ :param name: The name of this repository.
        :param path: Path to this repository.
        """
        self.name = name
        self.path = path

        db = join(path, name + '.db')
        if not exists(db):
            run(['repo-add', db])
