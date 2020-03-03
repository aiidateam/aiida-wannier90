# -*- coding: utf-8 -*-
################################################################################
# Copyright (c), AiiDA team and individual contributors.                       #
#  All rights reserved.                                                        #
# This file is part of the AiiDA-wannier90 code.                               #
#                                                                              #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-wannier90 #
# For further information on the license, see the LICENSE.txt file             #
################################################################################
from __future__ import absolute_import


def test_create_win_string(generate_win_params_gaas, file_regression):
    from aiida_wannier90.io._write_win import _create_win_string

    file_regression.check(
        _create_win_string(**generate_win_params_gaas()),
        encoding='utf-8',
        extension='.win'
    )
