# -*- coding: utf-8 -*-

from __future__ import absolute_import
import io
import json
import os

from setuptools import setup, find_packages

if __name__ == '__main__':
    THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
    with open('setup.json', 'r') as info:
        kwargs = json.load(info)
    setup(
        include_package_data=True,
        setup_requires=['reentry'],
        reentry_register=True,
        long_description=io.open(
            os.path.join(THIS_FOLDER, 'README.md'), encoding='utf-8'
        ).read(),
        long_description_content_type='text/markdown',
        packages=find_packages(exclude=['aiida']),
        **kwargs
    )
