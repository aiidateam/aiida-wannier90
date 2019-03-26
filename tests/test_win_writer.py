# -*- coding: utf-8 -*-

from __future__ import absolute_import
from gaas_sample import create_gaas_win_params


def test_create_win_string(configure, create_gaas_win_params, compare_equal):
    from aiida.plugins import DataFactory
    from aiida_wannier90.io._write_win import _create_win_string

    compare_equal(_create_win_string(**create_gaas_win_params()).splitlines())
