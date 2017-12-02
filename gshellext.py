#!/usr/bin/python3

import urllib
import urllib.request as urlreq
import json
import utils
import os
import repo
import shutil
import subprocess

PACKAGE_NAME_FORMAT = 'gnome-shell-extension-{}'
PKGBUILD_FORMAT = """
pkgname='{}'
pkgver={}
pkgrel=1
pkgdesc='{}'
arch=('any')
url='{}'
license=('custom')
depends=('gnome-shell')
source=('{}')
sha256sums=('SKIP')

build() {{
  true
}}

package() {{
  extension_uuid='{}'
  symlink_name='{}'
  rm -f "$symlink_name"
  install -d "${{pkgdir}}/usr/share/gnome-shell/extensions/${{extension_uuid}}"
  [[ -d schemas ]] && find schemas -name '*.xml' -exec install -Dm644 -t "$pkgdir/usr/share/glib-2.0/schemas/" '{{}}' +
  [[ -d locale ]] && cp -af locale "${{pkgdir}}/usr/share/locale/"
  rm -rf schemas locale
  cp -af * "${{pkgdir}}/usr/share/gnome-shell/extensions/${{extension_uuid}}"
  find "$pkgdir" -type d -exec chmod 755 {{}} \;
  find "$pkgdir" -type f -exec chmod 644 {{}} \;
}}
"""

class GnomeShellExtensionBackend:
    @classmethod
    def add(cls, target):
        with utils.JSONStore(utils.Config.db('gshellext')) as store:
            targets = store.read([])
            if target not in targets:
                targets.append(target)
                store.write(targets)

    @classmethod
    def remove(cls, target):
        with utils.JSONStore(utils.Config.db('gshellext')) as store:
            targets = store.read([])
            try:
                targets.remove(target)
                store.write(targets)
            except ValueError:
                pass

    @classmethod
    def list(cls):
        with utils.JSONStore(utils.Config.db('gshellext')) as store:
            return store.read([])

    @classmethod
    def generate_plan(cls, gshellextrepo):
        return BuildPlan.for_extensions(gshellextrepo, cls.list())

    @classmethod
    def execute_plan(cls, plan, gshellextrepo):
        for info in plan.build:
            pkgbuilddir = '{}/{}'.format(utils.Config.workspace('gshellext'), info.uuid)
            os.mkdir(pkgbuilddir)
            pkgbuild = PKGBUILD_FORMAT.format(info.pkgname, info.version, info.description,
                    info.link, info.download_url, info.uuid, info.download_url.split('/')[-1])
            with open(pkgbuilddir + '/PKGBUILD', 'w') as f:
                f.write(pkgbuild)
            subprocess.run(['makepkg', '--nodeps', utils.Config.chroot()], cwd=pkgbuilddir)
            built = repo.get_pkgfile_path(pkgbuilddir, info.pkgname, '{}-1'.format(info.version))
            if built is None:
                raise Exception('Build error')
            gshellextrepo.add(built)
            shutil.rmtree(pkgbuilddir)

    @classmethod
    def autoremove(cls, plan, gshellextrepo):
        build = [item.pkgname for item in plan.build]
        keep = [item.pkgname for item in plan.keep]
        autoremove = []
        for pkgname in gshellextrepo.packages.keys():
            if pkgname in build:
                continue
            if pkgname in keep:
                continue
            autoremove.append(pkgname)
        for pkgname in autoremove:
            print('Removing \'{}\'...'.format(pkgname))
            aurrepo.remove(pkgname)


class BuildPlan:
    def __init__(self, build, keep):
        self.build = build
        self.keep = keep

    def __str__(self):
        return 'BuildPlan build: {}, keep: {}'.format(self.build, self.keep)

    def empty(self):
        return len(self.build) == 0

    @classmethod
    def for_extension(cls, localrepo, uuid):
        return cls.for_extensions(localrepo, [uuid])

    @classmethod
    def for_extensions(cls, localrepo, uuids):
        build = []
        keep = []
        for uuid in uuids:
            info = ExtensionInfo.from_uuid(uuid)
            if info.pkgname in localrepo.packages and int(
                    localrepo.packages[info.pkgname].split('-')[0]) >= info.version:
                keep.append(info)
            else:
                build.append(info)
        return cls(build, keep)


class ExtensionInfo:
    cache_by_uuid = {}
    API_URL = 'https://extensions.gnome.org/extension-info/?uuid={}'
    DOWNLOAD_URL = 'https://extensions.gnome.org/download-extension/{}.shell-extension.zip?version_tag={}'
    LINK_URL = 'https://extensions.gnome.org{}'

    def __init__(self, uuid, version, download_url, description, link):
        self.uuid = uuid
        self.pkgname = PACKAGE_NAME_FORMAT.format(uuid.lower())
        self.version = version
        self.download_url = download_url
        self.description = description
        self.link = link

    def __str__(self):
        return self.uuid

    def __repr__(self):
        return str(self)

    @classmethod
    def from_uuid(cls, uuid):
        if uuid in cls.cache_by_uuid:
            return cls.cache_by_uuid[uuid]
        else:
            info = cls.from_uuid_uncached(uuid)
            cls.cache_by_uuid[uuid] = info
            return info

    @classmethod
    def from_uuid_uncached(cls, uuid):
        try:
            with urlreq.urlopen(cls.API_URL.format(uuid)) as response:
                decoded = json.loads(response.read().decode())
                version = None
                version_tag = None
                for version_pair in decoded['shell_version_map'].values():
                    if (version is None or version < version_pair['version']):
                        version = version_pair['version']
                        version_tag = version_pair['pk']
                download_url = cls.DOWNLOAD_URL.format(uuid, version_tag)
                description = decoded['description']
                link = cls.LINK_URL.format(decoded['link'])
                return cls(uuid, version, download_url, description, link)
        except urllib.error.HTTPError:
            raise ExtensionNotFoundError(uuid)

class ExtensionNotFoundError(Exception):
    def __init__(self, name):
        super().__init__('Extension \'{}\' not found'.format(name))
