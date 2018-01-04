#!/usr/bin/python3

from contextlib import contextmanager
from os.path import join
from environment import mkdir
from environment import config_home
from json import loads
from json import dumps
from json.decoder import JSONDecodeError


@contextmanager
def config(name):
    """ :param name: Name of the configuration file.
    :return: Context manager for the configuration file.
    """
    with open(join(mkdir(config_home), name + '.json'), mode='a+t') as file:
        try:
            json = loads(file.read())
        except JSONDecodeError:
            json = None
        yield json
        if json is not None:
            file.truncate(0)
            file.seek(0)
            file.write(dumps(json))
