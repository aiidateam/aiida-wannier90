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
import pytest

from aiida import orm

ENTRY_POINT_CALC_JOB = 'wannier90.wannier90'
ENTRY_POINT_PARSER = 'wannier90.wannier90'


@pytest.mark.parametrize("seedname", ("aiida", "wannier"))
def test_wannier_default(#pylint: disable=too-many-arguments
    fixture_localhost, generate_calc_job_node, generate_parser,
    generate_win_params_gaas, data_regression, seedname
):
    """Basic check of parsing a Wannier90 calculation."""
    node = generate_calc_job_node(
        entry_point_name=ENTRY_POINT_CALC_JOB,
        computer=fixture_localhost,
        test_name='gaas/seedname_{}'.format(seedname),
        inputs=generate_win_params_gaas(),
        seedname=seedname
    )
    parser = generate_parser(ENTRY_POINT_PARSER)
    results, calcfunction = parser.parse_from_node(
        node, store_provenance=False
    )

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_finished_ok, calcfunction.exit_message
    assert not orm.Log.objects.get_logs_for(node)
    assert 'output_parameters' in results

    data_regression.check({
        'output_parameters':
        results['output_parameters'].get_dict(),
    })


def test_no_kpoint_path(
    fixture_localhost,
    generate_calc_job_node,
    generate_parser,
    generate_win_params_gaas,
    data_regression,
):
    """Check that parsing still works if the 'kpoint_path' is not set."""
    inputs = generate_win_params_gaas()
    del inputs['kpoint_path']
    node = generate_calc_job_node(
        entry_point_name=ENTRY_POINT_CALC_JOB,
        computer=fixture_localhost,
        test_name='gaas/seedname_aiida',
        inputs=inputs,
    )
    parser = generate_parser(ENTRY_POINT_PARSER)
    results, calcfunction = parser.parse_from_node(
        node, store_provenance=False
    )

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_finished_ok, calcfunction.exit_message
    assert not orm.Log.objects.get_logs_for(node)
    assert 'output_parameters' in results

    data_regression.check({
        'output_parameters':
        results['output_parameters'].get_dict(),
    })


@pytest.mark.parametrize("band_parser", ("new", "legacy"))
def test_band_parser(#pylint: disable=too-many-arguments
    fixture_localhost, generate_calc_job_node, generate_parser,
    generate_win_params_o2sr, data_regression, band_parser
):
    """Check that band parser returns correct dimension and labels."""
    inputs = generate_win_params_o2sr()
    node = generate_calc_job_node(
        entry_point_name=ENTRY_POINT_CALC_JOB,
        computer=fixture_localhost,
        test_name='o2sr/band_{}'.format(band_parser),
        inputs=inputs
    )
    parser = generate_parser(ENTRY_POINT_PARSER)
    results, calcfunction = parser.parse_from_node(
        node, store_provenance=False
    )

    assert calcfunction.is_finished, calcfunction.exception
    assert calcfunction.is_finished_ok, calcfunction.exit_message
    assert not orm.Log.objects.get_logs_for(node)
    assert 'output_parameters' in results

    data_regression.check({
        'output_parameters':
        results['output_parameters'].get_dict(),
    })

    bands = results['interpolated_bands']

    if band_parser == "new":
        assert bands.get_kpoints().shape == (607, 3)
        assert bands.get_bands().shape == (607, 21)
        assert bands.labels == [(0, 'GAMMA'), (100, 'X'), (137, 'P'),
                                (208, 'N'), (288, 'GAMMA'), (362, 'M'),
                                (413, 'S'), (414, 'S_0'), (504, 'GAMMA'),
                                (505, 'X'), (533, 'R'), (534, 'G'), (606, 'M')]
    elif band_parser == "legacy":
        assert bands.get_kpoints().shape == (604, 3)
        assert bands.get_bands().shape == (604, 21)
        assert bands.labels == [(0, 'GAMMA'), (100, 'X'), (137, 'P'),
                                (208, 'N'), (288, 'GAMMA'), (362, 'M'),
                                (412, 'S'), (413, 'S_0'), (502, 'GAMMA'),
                                (503, 'X'), (530, 'R'), (531, 'G'), (603, 'M')]
