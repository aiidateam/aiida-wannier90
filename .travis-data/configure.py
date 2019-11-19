#!/usr/bin/env python
"""
Usage: python configure.py travis_data_folder test_folder
"""

from __future__ import absolute_import
import sys
from os.path import join, realpath

travis_data_folder = sys.argv[1]
in_file = join(travis_data_folder, 'test_config.yml')
wannier90_path = realpath(join(travis_data_folder, 'wannier90/wannier90.x'))

out_file = join(sys.argv[2], 'config.yml')

with open(in_file, 'r') as f:
    res = f.read().format(wannier90_path=wannier90_path)
with open(out_file, 'w') as f:
    f.write(res)
