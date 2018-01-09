#!/usr/bin/python3

from os.path import join
from os.path import exists
from os.path import basename
from tarfile import open as tarfile_open
from .utils import run
from .package import PackageTinyInfo
from .package import pick_package_file


class Repository:
    """ An Arch repository. """

    def __init__(self, name, path, sign_key=None, sudo=False):
        """ :param name: The name of this repository.
        :param path: Path to this repository.
        :param sign_key: GPG key to sign. None means no signing.
        :param sudo: Whether to modify this repository using sudo(1) or not.
        """
        self.name = name
        self.directory = path
        self.sign_key = sign_key
        self.sign_parameters = ['-s', '-k', sign_key] if sign_key else []
        self.sudo = sudo

        self.db_path = join(path, name + '.db.tar.gz')
        if not exists(self.db_path):
            run(['repo-add', self.db_path], sudo=sudo, capture=False)

        packages = [PackageTinyInfo.from_repodb_directory_name(member.name) for member
                    in tarfile_open(self.db_path).getmembers() if member.isdir()]
        self.packages = {package.name: package for package in packages}

    def __str__(self):
        return 'Repository {} at {} (key={}, sudo={})'.format(self.name, self.directory, self.sign_key, self.sudo)

    def __repr__(self):
        return 'Repository({}, {}, sign_key={}, sudo={})'.format(repr(self.name), repr(self.directory),
                                                                 repr(self.sign_key), repr(self.sudo))

    def add(self, package_file_path):
        """ Adds a package to the repository.
        :param package_file_path: The path to the package file.
        """
        package = PackageTinyInfo.from_package_file_path(package_file_path)
        if package.name in self.packages and self.packages[package.name].version == package.version:
            return
        run(['cp', package_file_path, self.directory], sudo=self.sudo)
        repository_package_path = join(self.directory, basename(package_file_path))
        if self.sign_key:
            run(['gpg', '--detach-sign', '--no-armor', '--default-key', self.sign_key, repository_package_path],
                sudo=self.sudo, capture=False)
        run(['repo-add', '-R'] + self.sign_parameters + [self.db_path, repository_package_path],
            sudo=self.sudo, capture=False)
        self.packages[package.name] = package

    def find_package_file_path(self, pkgname):
        """ :param pkgname: The name of the package to find. """
        if pkgname not in self.packages:
            raise Exception('Package {} not in {}'.format(pkgname, self))
        file_name = pick_package_file(pkgname, self.directory)
        return join(self.directory, file_name)

    def remove(self, pkgname):
        """ :param pkgname: The name of the package to remove. """
        file_path = self.find_package_file_path(pkgname)
        run(['rm', '-f', file_path], sudo=self.sudo)
        run(['rm', '-f', file_path + '.sig'], sudo=self.sudo)
        run(['repo-remove'] + self.sign_parameters + [self.db_path, pkgname], sudo=self.sudo, capture=False)
        del self.packages[pkgname]
