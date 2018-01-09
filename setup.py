#!/usr/bin/python3

from distutils.core import setup
from .autopkg.front import VERSION

setup(
    name='autopkg',
    version=VERSION,
    author='JangHo Seo',
    author_email='jangho@jangho.io',
    packages=['autopkg'],
    scripts=['bin/autopkg'],
    url='https://git.jangho.io/system/autopkg.git/',
    license='LICENSE.txt',
    description='Personal package manager for Arch.',
)
