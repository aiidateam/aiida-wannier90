# -*- coding: utf-8 -*-

from __future__ import absolute_import

import sys

from gaas_sample import create_gaas_win_params


def test_create_win_string(configure, create_gaas_win_params, compare_equal):
    from aiida_wannier90.io._write_win import _create_win_string

    # The 'tag' is an ugly workaround because win_writer changes
    # behavior between Python versions 2 and 3.
    compare_equal(
        _create_win_string(**create_gaas_win_params()).splitlines(),
        tag=str(sys.version_info.major)
    )
