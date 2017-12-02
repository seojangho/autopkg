#!/usr/bin/python3

from repo import Repo
from aur import BuildPlan
from aur import build_and_install
from chroot import Chroot

with Repo.for_backend('aur') as aurrepo:
    #plan = BuildPlan.for_packages(aurrepo, ['intellij-idea-ultimate-edition-jre','intellij-idea-ultimate-edition', 'keybase-bin'])
    plan = BuildPlan.for_packages(aurrepo, ['yaourt'])
    print(plan)
    if len(plan.build) != 0:
        with Chroot() as chroot:
            with Repo.for_chroot() as chrootrepo:
                for builditem in plan.build:
                    build_and_install(builditem, aurrepo, chroot)
