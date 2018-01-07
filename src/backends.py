#!/usr/bin/python3

from utils import run
from utils import url_read
from utils import config
from utils import workspace
from utils import log
from utils import LogLevel
from gzip import decompress
from json import loads
from package import PackageInfo
from package import Version
from os.path import join
from os.path import split
from os.path import basename
from urllib.error import HTTPError
from contextlib import AbstractContextManager
from contextlib import contextmanager


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
        return hash((self.backend, self.source))

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


@contextmanager
def config_git_backend():
    with config('git') as config_data:
        if config_data.json is None:
            config_data.json = []
        yield config_data


def git_backend(pkgnames):
    try:
        git_backend.pkgname_to_buildable
    except AttributeError:
        git_backend.pkgname_to_buildable = do_git()
    return [git_backend.pkgname_to_buildable[pkgname] for pkgname in pkgnames
            if pkgname in git_backend.pkgname_to_buildable]


def do_git():
    with config_git_backend() as config_data:
        with Workspaces() as wss:
            repo_url_to_workspace = dict()
            pkgname_to_buildable = dict()
            for source in config_data.json:
                repo_url = source['repository']
                repo_path = source.get('path', '/')
                branch = source.get('branch', 'master')
                if repo_url not in repo_url_to_workspace:
                    ws = wss.new_workspace()
                    run(['git', 'clone', '--depth', '1', '--branch', branch, repo_url, ws], capture=False)
                    repo_url_to_workspace[repo_url] = ws
                ws = repo_url_to_workspace[repo_url]
                path = join(ws, repo_path)
                run(['git', 'checkout', branch], cwd=ws, quiet=True)
                version = Version.from_components(value_from_pkgbuild(path, 'pkgver'),
                                                  value_from_pkgbuild(path, 'pkgrel'),
                                                  epoch=value_from_pkgbuild(path, 'epoch'))
                pkgname = value_from_pkgbuild(path, 'pkgname')
                package_info = PackageInfo(pkgname, version,
                                           pkgbase=value_from_pkgbuild(path, 'pkgbase'),
                                           depends=array_from_pkgbuild(path, 'depends'),
                                           makedepends=array_from_pkgbuild(path, 'makedepends'),
                                           checkdepends=array_from_pkgbuild(path, 'checkdepends'))
                source_reference = GitSourceReference(repo_url, repo_path, branch)
                buildable = GitBuildable(package_info, source_reference, repo_url, repo_path, branch)
                if pkgname in pkgname_to_buildable:
                    log(LogLevel.warn, 'Multiple git sources for pkgname {}', pkgname)
                else:
                    pkgname_to_buildable[pkgname] = buildable
    return pkgname_to_buildable


class GitBuildable(AbstractBuildable):
    def __init__(self, package_info, source_reference, repo_url, path, branch):
        super().__init__(package_info, source_reference)
        self.repo_url = repo_url
        self.path = path
        self.branch = branch

    def write_pkgbuild_to(self, path):
        """ :param path: Path to workspace.
        :return: Path to the leaf directory where PKGBUILD resides.
        """
        run(['git', 'clone', '--depth', '1', '--branch', self.branch, self.repo_url, path], capture=False)
        return join(path, self.path)

    @property
    def chroot_required(self):
        """ :return: True. """
        return True


class GitSourceReference:
    def __init__(self, repo_url, path, branch):
        self.repo_url = repo_url
        self.path = path
        self.branch = branch

    def __str__(self):
        repo_url_tuple = split(self.repo_url)
        last_component = repo_url_tuple[1] if repo_url_tuple[1] else basename(repo_url_tuple[0])
        return '{}{}{}'.format(last_component, '({})'.format(self.branch) if self.branch != 'master' else '',
                               self.path if self.path != '/' else '')

    def __repr__(self):
        return '\'{}\''.format(self)

    def __hash__(self):
        return hash((self.repo_url, self.path, self.branch))

    def __eq__(self, other):
        if not isinstance(other, GitSourceReference):
            return False
        return self.repo_url == other.repo_url and self.path == other.path and self.branch == other.branch


def value_from_pkgbuild(cwd, name):
    stdout = run(['bash', '-c', 'set +u && . PKGBUILD && echo "${}"'.format(name)], cwd=cwd, quiet=True).strip()
    if len(stdout):
        return stdout
    else:
        return None


def array_from_pkgbuild(cwd, name):
    stdout = run(['bash', '-c', 'set +u && . PKGBUILD && printf "%s\\n" "${{{}[@]}}"'.format(name)],
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
