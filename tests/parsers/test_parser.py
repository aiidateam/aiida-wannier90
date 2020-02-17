# -*- coding: utf-8 -*-

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
