#!/usr/bin/python3

import subprocess
import fcntl
import os
import json

class Config:
    default_config = {
            'workspace': os.getenv('HOME') + '/.autopkg',
            'gpgkey': 'EE37EBD527ECFE87A96A7BDB6503B6817E24FCA3'
            }

    @classmethod
    def get(cls):
        try:
            return cls.config
        except AttributeError:
            with JSONStore(os.getenv('HOME') + '/.autopkg.json') as f:
                cls.config = f.read(cls.default_config, write_default=True)
            return cls.config

    @classmethod
    def gpgkey(cls):
        return cls.get()['gpgkey']

    @classmethod
    def get_backend_path(cls, backend, path):
        cfg = cls.get()
        os.makedirs('{}/{}'.format(cfg['workspace'], backend), exist_ok=True)
        return '{}/{}/{}'.format(cfg['workspace'], backend, path)

    @classmethod
    def db(cls, backend):
        return cls.get_backend_path(backend, 'db.json')

    @classmethod
    def workspace(cls, backend):
        path = cls.get_backend_path(backend, 'workspace')
        os.makedirs(path, exist_ok=True)
        return path

    @classmethod
    def repo(cls, backend):
        return cls.get_backend_path(backend, 'repo')

    @classmethod
    def chroot(cls):
        cfg = cls.get()
        path = '{}/{}'.format(cfg['workspace'], 'chroot')
        os.makedirs(path, exist_ok=True)
        return path


def vercmp(v1, v2):
    return int(subprocess.run(['vercmp', v1, v2], stdout=subprocess.PIPE).stdout.decode())


def is_official_package(pkgname):
    this = is_official_package
    try:
        return pkgname in this.cached
    except AttributeError:
        this.cached = [row.split()[1] for row in
                subprocess.run(['pacman', '-Sl', 'core', 'extra', 'community'],
                stdout=subprocess.PIPE).stdout.decode().split('\n') if row != '']
        return pkgname in this.cached


class JSONStore:
    def __init__(self, path):
        self.path = path
        self.lockfile = '{}.lock'.format(path)

    def __enter__(self):
        self.file = open(self.path, mode='w+t')
        fcntl.flock(self.file, fcntl.LOCK_EX)
        if os.path.isfile(self.lockfile):
            raise LockfileExistsError(self.path)
        with open(self.lockfile, 'a'):
            os.utime(self.lockfile)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        os.remove(self.lockfile)
        fcntl.flock(self.file, fcntl.LOCK_UN)
        self.file.close()

    def read(self, default=None, write_default=False):
        self.file.seek(0)
        try:
            return json.loads(self.file.read())
        except json.decoder.JSONDecodeError as e:
            if default is None:
                raise e
            if write_default:
                self.write(default)
            return default

    def write(self, content):
        self.file.truncate(0)
        self.file.seek(0)
        self.file.write(json.dumps(content))


class LockfileExistsError(Exception):
    def __init__(self, fname):
        super().__init__('Lockfile for \'{}\' already exists.'.format(fname))
