#!/usr/bin/python3

from utils import run
from utils import url_read
from utils import config
from utils import workspace
from gzip import decompress
from json import loads
from package import PackageInfo
from os.path import join
from urllib.error import HTTPError
from contextlib import AbstractContextManager


class SourceReference:
    """ Reference to specific package source from specific backend. """

    def __init__(self, backend, source):
        """
        :param backend: The backend.
        :param source: The source.
        """
        self.backend = backend
        self.source = source

    def __str__(self):
        return '{}/{}'.format(self.backend, self.source)

    def __repr__(self):
        return '\'{}\''.format(self)

    def __hash__(self):
        return hash(self.source)

    def __eq__(self, other):
        if not isinstance(other, SourceReference):
            return False
        return self.source == other.source and self.backend == other.backend


class AbstractBuildable:
    def __init__(self, package_info, source_reference):
        self.package_info = package_info
        self.source_reference = source_reference

    def __str__(self):
        return '{}→{}'.format(self.source_reference, self.package_info)

    def __repr__(self):
        return '\'{}->{}\''.format(self.source_reference, self.package_info)


class AURBuildable(AbstractBuildable):
    def __init__(self, package_info):
        super().__init__(package_info, SourceReference('aur', package_info.pkgbase))

    def write_pkgbuild_to(self, path):
        """ :param path: Path to workspace.
        :return: Path to the leaf directory where PKGBUILD resides.
        """
        giturl = 'https://aur.archlinux.org/{}.git'.format(self.package_info.pkgbase)
        run(['git', 'clone', '--depth', '1', giturl, path], capture=False)
        return path

    @property
    def chroot_required(self):
        """ :return: True. """
        return True


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


GSHELLEXT_PKGREL = '-1'
GSHELLEXT_PREFIX = 'gnome-shell-extension-'
GSHELLEXT_PKGBUILD_FORMAT = """
pkgname='{}'
pkgver={}
pkgrel=1
pkgdesc='{}'
arch=('any')
url='https://extensions.gnome.org{}'
license=('custom')
depends=('gnome-shell')
source=('https://extensions.gnome.org/download-extension/{}.shell-extension.zip?version_tag={}')
sha256sums=('SKIP')

package() {{
  extension_uuid='{}'
  symlink_name='{}.shell-extension.zip?version_tag={}'
  rm -f "$symlink_name"
  install -d "${{pkgdir}}/usr/share/gnome-shell/extensions/${{extension_uuid}}"
  [[ -d schemas ]] && find schemas -name '*.xml' -exec install -Dm644 -t "$pkgdir/usr/share/glib-2.0/schemas/" '{{}}' +
  [[ -d locale ]] && cp -af locale "${{pkgdir}}/usr/share/locale/"
  cp -af * "${{pkgdir}}/usr/share/gnome-shell/extensions/${{extension_uuid}}"
  find "$pkgdir" -type d -exec chmod 755 {{}} \;
  find "$pkgdir" -type f -exec chmod 644 {{}} \;
}}
"""


class GShellExtBuildable(AbstractBuildable):
    def __init__(self, package_info, uuid, version, version_tag, description, link):
        super().__init__(package_info, SourceReference('gshellext', uuid))
        self.uuid = uuid
        self.version = version
        self.version_tag = version_tag
        self.description = description
        self.link = link

    def write_pkgbuild_to(self, path):
        """ :param path: Path to workspace.
        :return: Path to the leaf directory where PKGBUILD resides.
        """
        pkgbuild = GSHELLEXT_PKGBUILD_FORMAT.format(self.package_info.pkgname, self.version, self.description,
                                                    self.link, self.uuid, self.version_tag, self.uuid, self.uuid,
                                                    self.version_tag)
        with open(join(path, 'PKGBUILD'), 'w') as f:
            f.write(pkgbuild)
        return path

    @property
    def chroot_required(self):
        """ :return: False. """
        return False


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
        try:
            json = loads(url_read('https://extensions.gnome.org/extension-info/?uuid={}', uuid).decode())
        except HTTPError:
            continue
        recent_version_pair = max(json['shell_version_map'].values(), key=lambda pair: pair['version'])
        recent_version = recent_version_pair['version']
        recent_version_tag = recent_version_pair['pk']
        escaped_description = json['description'].replace('\'', '\'\"\'\"\'')
        package_info = PackageInfo(GSHELLEXT_PREFIX + uuid.lower(), str(recent_version) + GSHELLEXT_PKGREL)
        buildable = GShellExtBuildable(package_info, uuid, recent_version, recent_version_tag, escaped_description,
                                       json['link'])
        gshellext_backend.uuid_to_buildable[uuid] = buildable
        buildables.append(buildable)
    return buildables


GIT_CONFIG_NAME = 'git'


def git_backend(pkgnames):
    try:
        git_backend.pkgname_to_buildable
    except AttributeError:
        git_backend.pkgname_to_buildable = do_git()
    return list()


def do_git():
    with config(GIT_CONFIG_NAME) as config_data:
        with Workspaces() as wss:
            repo_url_to_workspace = dict()
            pkgname_to_buildable = dict()
            for source in config_data:
                repo_url = source['repository']
                if repo_url not in repo_url_to_workspace:
                    ws = wss.new_workspace()
                    run(['git', 'clone', '--depth', '1', repo_url, ws], capture=False)
                    repo_url_to_workspace[repo_url] = ws
                ws = repo_url_to_workspace[repo_url]
                path = join(ws, source.get('path', '/'))
                branch = source.get('branch', 'master')
                run(['git', 'checkout', branch], cwd=ws, quiet=True)
    return pkgname_to_buildable


def value_from_pkgbuild(cwd, name):
    stdout = run(['bash', '-c', '\'set +u && . PKGBUILD && echo \"${}\"\''.format(name)], cwd=cwd, quiet=True).strip()
    if len(stdout):
        return stdout
    else:
        return None


def array_from_pkgbuild(cwd, name):
    stdout = run(['bash', '-c', '\'set +u && . PKGBUILD && printf "%s\\n" echo "${{{}[@]}}"\''.format(name)],
                 cwd=cwd, quiet=True)
    return [value for value in stdout.splitlines() if len(value)]


class Workspaces(AbstractContextManager):
    def __init__(self):
        self.workspaces = list()

    def new_workspace(self):
        ws = workspace()
        path = ws.__enter__()
        self.workspaces.append(ws)
        return path

    def __exit__(self, exc_type, exc_value, traceback):
        ret = None
        for ws in self.workspaces:
            sub_ret = ws.__exit__(exc_type, exc_value, traceback)
            if sub_ret:
                ret = sub_ret
        return ret
