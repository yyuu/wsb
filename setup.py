#!/usr/bin/env python

from __future__ import with_statement
import contextlib
import logging
import re

try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages

setup(
    name='wsb',
    version='0.0.1git',
    description='Yet another WebSocket benchmarking tool.',
    author='Yamashita, Yuu',
    author_email='yamashita@geishatokyo.com',
    url='http://www.geishatokyo.com/',
    install_requires=[
        "autobahn",
    ],
    packages=find_packages(),
    py_modules=["app"],
    entry_points={
        'console_scripts': [
            'wsb=wsb:main',
        ],
    },
)

# vim:set ft=python :
