#!/usr/bin/python3

from os.path import join
from os.path import exists
from utils import run
from tarfile import open as tarfile_open
from package import PackageInfo
from package import PackageTinyInfo


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

        self.db_path = join(path, name + '.db')
        if not exists(self.db_path):
            run(['repo-add', self.db_path], sudo=sudo)

        packages = [PackageTinyInfo.from_repodb_directory_name(member.name) for member
                    in tarfile_open(self.db_path).getmembers() if member.isdir()]
        self.packages = {package.name: package for package in packages}

    def add(self, package_file_path):
        """ Adds a package to the repository.
        :param package_file_path: The path to the package file.
        """
        package = PackageInfo.from_package_file_path(package_file_path)
        if package.name in self.packages and self.packages[package.name].version == package.version:
            return
        run(['cp', package_file_path, self.directory], sudo=self.sudo)
        repository_package_path = join(self.directory, package.package_file_name())
        if self.sign_key:
            run(['gpg', '--detach-sign', '--no-armor', '--default-key', self.sign_key, repository_package_path],
                sudo=self.sudo)
        run(['repo-add', '-R'] + self.sign_parameters + [self.db_path, repository_package_path], sudo=self.sudo)
        self.packages[package.name] = package

    # TODO remove...
