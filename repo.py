#!/usr/bin/python3

import utils
import os
import subprocess
import fcntl
import tarfile
import shutil

def pkgname_pkgver(pkgpath):
    split = os.path.basename(pkgpath).split('-')
    pkgname = '-'.join(split[:-3])
    pkgver = '-'.join(split[-3:-1])
    return (pkgname, pkgver)


def get_pkgfile_path(directory, pkgname, pkgver=None):
    files = [name for name in os.listdir(directory) if
            os.path.isfile(os.path.join(directory, name))]
    for name in files:
        pkgname_test, pkgver_test = pkgname_pkgver(name)
        if pkgname_test == pkgname and (pkgver is None or pkgver_test == pkgver):
            return os.path.join(directory, name)
    return None


class Repo:
    def __init__(self, repodir, reponame, sign=True, sudo=False):
        self.dir = repodir
        self.name = reponame
        self.db = '{}/{}.db.tar.gz'.format(repodir, reponame)
        self.sudo = sudo
        self.sudocmd = ['sudo'] if sudo else []
        self.sign = sign
        self.signcmd = ['-s', '-k', utils.Config.gpgkey()] if sign else []

    @classmethod
    def for_backend(cls, backend):
        return cls(utils.Config.repo(backend), utils.Config.repo_prefix() + backend)

    @classmethod
    def for_chroot(cls):
        return cls(utils.Config.chroot() + '/root/repo', 'autopkg', sudo=True, sign=False)

    def __enter__(self):
        if not os.path.isdir(self.dir):
            subprocess.run(self.sudocmd + ['mkdir', self.dir])
            subprocess.run(self.sudocmd + ['repo-add', self.db])
        self.fd = open(self.db, mode='r')
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        self.packages = {'-'.join(member.name.split('-')[:-2]):
                '-'.join(member.name.split('-')[-2:]) for member in
                tarfile.open(self.db).getmembers() if member.isdir()}
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        self.fd.close()

    def add(self, pkgfilepath):
        pkgname, pkgver = pkgname_pkgver(pkgfilepath)
        subprocess.run(self.sudocmd + ['cp', pkgfilepath, self.dir])
        if self.sign:
            subprocess.run(self.sudocmd + ['gpg', '--detach-sign', '--no-armor', pkgfilepath])
            subprocess.run(self.sudocmd + ['cp', pkgfilepath + '.sig', self.dir])
        subprocess.run(self.sudocmd + ['repo-add', '-R'] + self.signcmd + [self.db, pkgfilepath])
        self.packages[pkgname] = pkgver

    def remove(self, pkgname):
        del self.packages[pkgname]
        subprocess.run(self.sudocmd + ['repo-remove'] + self.signcmd + [self.db, pkgname])
        os.unlink(self.pkgfile_path(pkgname))
        if self.sign:
            os.unlink(self.pkgfile_path(pkgname + '.sig'))

    def pkgfile_path(self, pkgname):
        return get_pkgfile_path(self.dir, pkgname)
