#!/usr/bin/python3

from utils import run
from utils import url_read
from gzip import decompress
from json import loads
from package import PackageInfo


class PkgbaseReference:
    """ Reference to specific pkgbase from specific backend. """

    def __init__(self, pkgbase, backend):
        """ :param pkgbase: The pkgbase.
        :param backend: The backend.
        """
        if pkgbase is None:
            raise Exception('pkgbase=None is not allowed')
        self.pkgbase = pkgbase
        self.backend = backend

    def __str__(self):
        return '{}/{}'.format(self.backend, self.pkgbase)

    def __repr__(self):
        return '\'{}\''.format(self)

    def __hash__(self):
        return hash(self.pkgbase)

    def __eq__(self, other):
        if not isinstance(other, PkgbaseReference):
            return False
        return self.pkgbase == other.pkgbase and self.backend == other.backend


class AURBuildable:
    def __init__(self, package_info):
        self.package_info = package_info
        self.pkgbase_reference = PkgbaseReference(self.package_info.pkgbase, 'aur')

    def write_pkgbuild_to(self, path):
        """ :param path: Path to workspace.
        :return: Path to the leaf directory where PKGBUILD resides.
        """
        giturl = 'https://aur.archlinux.org/{}.git'.format(self.package_info.pkgbase)
        run(['git', 'clone', giturl, path])
        return path

    @property
    def chroot_required(self):
        """ :return: True. """
        return True

    def __str__(self):
        return '{}→{}'.format(self.pkgbase_reference, self.package_info)

    def __repr__(self):
        return '\'{}->{}\''.format(self.pkgbase_reference, self.package_info)


def extract_package_names(depends):
    """ :param depends: List of depends in AUR rpc result.
    :return: List of names of packages.
    """
    return [depend.split('>')[0].split('<')[0].split('=')[0] for depend in depends]


def aur_backend(pkgnames):
    """ :param pkgnames: The names of the packages to lookup.
    :return: List of related AURBuildables.
    """
    try:
        aur_backend.aur_packages
    except AttributeError:
        fetched = url_read('https://aur.archlinux.org/packages.gz')
        aur_backend.aur_packages = [name for name in decompress(fetched).decode().splitlines()
                                    if len(name) > 0 and name[0] != '#']
        aur_backend.pkgname_to_buildable = dict()
    buildables = [aur_backend.pkgname_to_buildable[pkgname] for pkgname in pkgnames
                  if pkgname in aur_backend.pkgname_to_buildable]
    query_targets = ['&arg[]=' + pkgname for pkgname in pkgnames if pkgname not in aur_backend.pkgname_to_buildable
                     and pkgname in aur_backend.aur_packages]
    if len(query_targets) > 0:
        json = loads(url_read('https://aur.archlinux.org/rpc/?v=5&type=info' + ''.join(query_targets)).decode())
        for result in json['results']:
            buildable = AURBuildable(PackageInfo(result['Name'], result['Version'], pkgbase=result['PackageBase'],
                                     depends=extract_package_names(result.get('Depends', list())),
                                     makedepends=extract_package_names(result.get('MakeDepends', list())),
                                     checkdepends=extract_package_names(result.get('CheckDepends', list()))))
            aur_backend.pkgname_to_buildable[buildable.package_info.pkgname] = buildable
            buildables.append(buildable)
    return buildables


GSHELLEXT_PREFIX = 'gnome-shell-extension-'
GSHELLEXT_PKGBUILD_FORMAT = """
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

package() {{
  extension_uuid='{}'
  symlink_name='{}'
  rm -f "$symlink_name"
  install -d "${{pkgdir}}/usr/share/gnome-shell/extensions/${{extension_uuid}}"
  [[ -d schemas ]] && find schemas -name '*.xml' -exec install -Dm644 -t "$pkgdir/usr/share/glib-2.0/schemas/" '{{}}' +
  [[ -d locale ]] && cp -af locale "${{pkgdir}}/usr/share/locale/"
  cp -af * "${{pkgdir}}/usr/share/gnome-shell/extensions/${{extension_uuid}}"
  find "$pkgdir" -type d -exec chmod 755 {{}} \;
  find "$pkgdir" -type f -exec chmod 644 {{}} \;
}}
"""


class GShellExtBuildable:
    def __init__(self, package_info):
        self.package_info = package_info
        self.pkgbase_reference = PkgbaseReference(self.pkgbase, 'gshellext')

    def write_pkgbuild_to(self, path):
        """ :param path: Path to workspace.
        :return: Path to the leaf directory where PKGBUILD resides.
        """
        giturl = 'https://aur.archlinux.org/{}.git'.format(self.pkgbase)
        run(['git', 'clone', giturl, path])
        return path

    @property
    def chroot_required(self):
        """ :return: True. """
        return True

    def __str__(self):
        return '{}→{}'.format(self.pkgbase_reference, self.package_info)

    def __repr__(self):
        return '\'{}->{}\''.format(self.pkgbase_reference, self.package_info)


def gshellext_backend(pkgnames):
    """ :param pkgnames: The names of the packages to lookup.
    :return: List of related AURBuildables.
    """
    try:
        gshellext_backend.uuid_to_buildable
    except AttributeError:
        gshellext_backend.uuid_to_buildable = dict()
    buildables = list()
    for pkgname in pkgnames:
        if not pkgname.startswith(GSHELLEXT_PREFIX):
            continue
        uuid = pkgname[len(GSHELLEXT_PREFIX):]
        if uuid in gshellext_backend.uuid_to_buildable:
            buildables.append(gshellext_backend.uuid_to_buildable[uuid])
            continue
    return buildables


def git_backend(pkgnames):
    return list()