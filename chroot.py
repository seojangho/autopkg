#!/usr/bin/python3

import utils
import subprocess
import os

class Chroot:
    def __enter__(self):
        chroot = utils.Config.chroot()
        chroot_root = chroot + '/root'
        if not os.path.isdir(chroot_root):
            subprocess.run(['mkarchroot', chroot_root, 'base-devel'])
            subprocess.run(['sudo', 'tee', '-a', chroot_root + '/etc/pacman.conf'],
                    input='\n[autopkg]\nSigLevel = Never\nServer = file:///repo\n', encoding='utf-8')
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        subprocess.run(['sudo', 'rm', '-rf', utils.Config.chroot()])
        if utils.is_chroot_btrfs():
            subprocess.run(['sudo', 'btrfs', 'subvolume', 'delete',
                utils.Config.chroot() + '/working'])
            subprocess.run(['sudo', 'btrfs', 'subvolume', 'delete',
                utils.Config.chroot() + '/root/var/lib/machines'])
            subprocess.run(['sudo', 'rm', '-rf', utils.Config.chroot() + '/root/var'])
            subprocess.run(['sudo', 'btrfs', 'subvolume', 'delete',
                utils.Config.chroot() + '/root'])
            subprocess.run(['sudo', 'rm', '-rf', utils.Config.chroot()])

    def build(self, makepkgdir):
        subprocess.run(['makechrootpkg', '-c', '-u', '-l', 'working', '-r',
            utils.Config.chroot()], cwd=makepkgdir)
