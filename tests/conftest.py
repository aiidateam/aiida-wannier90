#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import

import os
import json
import shutil
import operator
import tempfile

import pytest

# Use fixtures from AiiDA core
## Probably add back this line when dropping aiida_pytest
#pytest_plugins = ['aiida.manage.tests.pytest_fixtures'] # pylint: disable=invalid-name

#TODO: try to break dependencies here
# from aiida_pytest import configure, config_dict
# All dependent pytest fixtures need to be imported, not only the
# explicitly used ones.
from aiida_pytest import *  # pylint: disable=unused-wildcard-import
