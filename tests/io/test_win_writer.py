# -*- coding: utf-8 -*-
from __future__ import absolute_import


def test_create_win_string(generate_win_params_gaas, file_regression):
    from aiida_wannier90.io._write_win import _create_win_string

    file_regression.check(
        _create_win_string(**generate_win_params_gaas()),
        encoding='utf-8',
        extension='.win'
    )
