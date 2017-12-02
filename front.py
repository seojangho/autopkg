#!/usr/bin/python3

from aur import AURBackend
from repo import Repo
from chroot import Chroot
import sys

if len(sys.argv) <= 1:
    with Repo.for_backend('aur') as aurrepo:
        plan = AURBackend.generate_plan(aurrepo)
        print(plan)
        if len(plan.build) != 0:
            with Chroot() as chroot:
                with Repo.for_chroot() as chrootrepo:
                    AURBackend.execute_plan(plan, aurrepo, chroot, chrootrepo)
elif sys.argv[1] == 'add':
    AURBackend.add(sys.argv[2])
elif sys.argv[1] == 'remove':
    AURBackend.remove(sys.argv[2])
elif sys.argv[1] == 'list':
    print(AURBackend.list())
else:
    sys.exit(1)
