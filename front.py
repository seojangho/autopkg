#!/usr/bin/python3

from aur import AURBackend
from gshellext import GnomeShellExtensionBackend
from repo import Repo
from chroot import Chroot
import sys

if len(sys.argv) <= 1:
    with Repo.for_backend('aur') as aurrepo:
        with Repo.for_backend('gshellext') as gshellextrepo:
            aurplan = AURBackend.generate_plan(aurrepo)
            print(aurplan)
            gshellextplan = GnomeShellExtensionBackend.generate_plan(gshellextrepo)
            print(gshellextplan)
            if not aurplan.empty() or not gshellextplan.empty():
                with Chroot() as chroot:
                    with Repo.for_chroot() as chrootrepo:
                        AURBackend.execute_plan(aurplan, aurrepo, chroot, chrootrepo)
                        GnomeShellExtensionBackend.execute_plan(gshellextplan, gshellextrepo,
                                chroot, chrootrepo)
            AURBackend.autoremove(aurplan, aurrepo)
            GnomeShellExtensionBackend.autoremove(gshellextplan, gshellextrepo)
else:
    if sys.argv[1] == 'aur':
        backend = AURBackend
    elif sys.argv[1] == 'gshellext':
        backend = GnomeShellExtensionBackend
    else:
        raise Exception('Invalid backend')
    if sys.argv[2] == 'add':
        backend.add(sys.argv[3])
    elif sys.argv[2] == 'remove':
        backend.remove(sys.argv[3])
    elif sys.argv[2] == 'list':
        print(backend.list())
    else:
        raise Exception('Invalid command')
