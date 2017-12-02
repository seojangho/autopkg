#!/usr/bin/python3

import urllib
import urllib.request as urlreq
import json

class ExtensionInfo:
    cache_by_uuid = {}
    API_URL = 'https://extensions.gnome.org/extension-info/?uuid={}'
    DOWNLOAD_URL = 'https://extensions.gnome.org/download-extension/{}.shell-extension.zip?version_tag={}'

    def __init__(self, uuid, version, download_url, description):
        self.uuid = uuid
        self.pkgname = uuid.lower()
        self.version = version
        self.download_url = download_url
        self.description = description

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
                return cls(uuid, version, download_url, description)
        except urllib.error.HTTPError:
            raise ExtensionNotFoundError(uuid)

class ExtensionNotFoundError(Exception):
    def __init__(self, name):
        super().__init__('Extension \'{}\' not found'.format(name))
