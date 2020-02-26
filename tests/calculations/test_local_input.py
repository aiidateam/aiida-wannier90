# -*- coding: utf-8 -*-
"""Tests for the `PwCalculation` class."""
from __future__ import absolute_import, print_function

import pytest

from aiida import orm
from aiida.common import datastructures
from aiida.common.exceptions import InputValidationError

ENTRY_POINT_NAME = 'wannier90.wannier90'


@pytest.fixture
def generate_common_inputs_gaas(
    shared_datadir,
    fixture_folderdata,
    fixture_code,
    generate_win_params_gaas,
):
    def _generate_common_inputs_gaas(inputfolder_seedname):
        inputs = dict(
            code=fixture_code(ENTRY_POINT_NAME),
            metadata={
                'options': {
                    'resources': {
                        'num_machines': 1
                    },
                    'max_wallclock_seconds': 3600,
                    'withmpi': False,
                }
            },
            local_input_folder=fixture_folderdata(
                shared_datadir / 'gaas', {'gaas': inputfolder_seedname}
            ),
            **generate_win_params_gaas()
        )

        return inputs

    return _generate_common_inputs_gaas


@pytest.fixture(params=(None, "aiida", "wannier"))
def seedname(request):
    return request.param


def test_default(#pylint: disable=too-many-locals
    fixture_sandbox, generate_calc_job, generate_common_inputs_gaas,
    file_regression, seedname
):
    """Test a default `Wannier90Calculation` with local input folder."""

    input_seedname = seedname or 'aiida'
    inputs = generate_common_inputs_gaas(inputfolder_seedname=input_seedname)
    if seedname is not None:
        inputs['metadata']['options']['seedname'] = seedname

    calc_info = generate_calc_job(
        folder=fixture_sandbox,
        entry_point_name=ENTRY_POINT_NAME,
        inputs=inputs
    )

    cmdline_params = [input_seedname]
    local_copy_list = [(val, val) for val in (
        'UNK00001.1', 'UNK00002.1', 'UNK00003.1', 'UNK00004.1', 'UNK00005.1',
        'UNK00006.1', 'UNK00007.1', 'UNK00008.1',
        '{}.mmn'.format(input_seedname), '{}.amn'.format(input_seedname)
    )]
    retrieve_list = [
        input_seedname + suffix for suffix in (
            '.wout', '.werr', '.r2mn', '_band.dat', '_band.dat', '_band.agr',
            '_band.kpt', '.bxsf', '_w.xsf', '_w.cube', '_centres.xyz',
            '_hr.dat', '_tb.dat', '_r.dat', '.bvec', '_wsvec.dat', '_qc.dat',
            '_dos.dat', '_htB.dat', '_u.mat', '_u_dis.mat', '.vdw',
            '_band_proj.dat'
        )
    ]
    retrieve_temporary_list = []

    # Check the attributes of the returned `CalcInfo`
    assert isinstance(calc_info, datastructures.CalcInfo)
    code_info = calc_info.codes_info[0]
    assert code_info.cmdline_params == cmdline_params
    # ignore UUID - keep only second and third entry
    local_copy_res = [tup[1:] for tup in calc_info.local_copy_list]
    assert sorted(local_copy_res) == sorted(local_copy_list)
    assert sorted(calc_info.retrieve_list) == sorted(retrieve_list)
    assert sorted(calc_info.retrieve_temporary_list
                  ) == sorted(retrieve_temporary_list)
    assert sorted(calc_info.remote_symlink_list) == sorted([])

    with fixture_sandbox.open('{}.win'.format(input_seedname)) as handle:
        input_written = handle.read()

    # Checks on the files written to the sandbox folder as raw input
    assert sorted(fixture_sandbox.get_content_list()
                  ) == sorted(['{}.win'.format(input_seedname)])
    file_regression.check(input_written, encoding='utf-8', extension='.win')


def test_no_projections( #pylint: disable=too-many-locals
    fixture_sandbox, generate_calc_job, generate_common_inputs_gaas,
    file_regression
):
    """Test a `Wannier90Calculation` where the projections are not specified."""

    inputs = generate_common_inputs_gaas(inputfolder_seedname='aiida')
    del inputs['projections']

    calc_info = generate_calc_job(
        folder=fixture_sandbox,
        entry_point_name=ENTRY_POINT_NAME,
        inputs=inputs
    )

    cmdline_params = ['aiida']
    local_copy_list = [(val, val) for val in (
        'UNK00001.1', 'UNK00002.1', 'UNK00003.1', 'UNK00004.1', 'UNK00005.1',
        'UNK00006.1', 'UNK00007.1', 'UNK00008.1', 'aiida.mmn', 'aiida.amn'
    )]
    retrieve_list = [
        "aiida" + suffix for suffix in (
            '.wout', '.werr', '.r2mn', '_band.dat', '_band.dat', '_band.agr',
            '_band.kpt', '.bxsf', '_w.xsf', '_w.cube', '_centres.xyz',
            '_hr.dat', '_tb.dat', '_r.dat', '.bvec', '_wsvec.dat', '_qc.dat',
            '_dos.dat', '_htB.dat', '_u.mat', '_u_dis.mat', '.vdw',
            '_band_proj.dat'
        )
    ]
    retrieve_temporary_list = []

    # Check the attributes of the returned `CalcInfo`
    assert isinstance(calc_info, datastructures.CalcInfo)
    code_info = calc_info.codes_info[0]
    assert code_info.cmdline_params == cmdline_params
    # ignore UUID - keep only second and third entry
    local_copy_res = [tup[1:] for tup in calc_info.local_copy_list]
    assert sorted(local_copy_res) == sorted(local_copy_list)
    assert sorted(calc_info.retrieve_list) == sorted(retrieve_list)
    assert sorted(calc_info.retrieve_temporary_list
                  ) == sorted(retrieve_temporary_list)
    assert calc_info.remote_symlink_list == []

    with fixture_sandbox.open('aiida.win') as handle:
        input_written = handle.read()

    # Checks on the files written to the sandbox folder as raw input
    assert fixture_sandbox.get_content_list() == ['aiida.win']
    file_regression.check(input_written, encoding='utf-8', extension='.win')


def test_list_projections(#pylint: disable=too-many-locals
    fixture_sandbox, generate_calc_job, generate_common_inputs_gaas,
    file_regression
):
    """Test a `Wannier90Calculation` where the projections are specified as a list."""

    inputs = generate_common_inputs_gaas(inputfolder_seedname='aiida')
    inputs['projections'] = orm.List(list=['random', 'Ga:s'])

    calc_info = generate_calc_job(
        folder=fixture_sandbox,
        entry_point_name=ENTRY_POINT_NAME,
        inputs=inputs
    )

    cmdline_params = ['aiida']
    local_copy_list = [(val, val) for val in (
        'UNK00001.1', 'UNK00002.1', 'UNK00003.1', 'UNK00004.1', 'UNK00005.1',
        'UNK00006.1', 'UNK00007.1', 'UNK00008.1', 'aiida.mmn', 'aiida.amn'
    )]
    retrieve_list = [
        "aiida" + suffix for suffix in (
            '.wout', '.werr', '.r2mn', '_band.dat', '_band.dat', '_band.agr',
            '_band.kpt', '.bxsf', '_w.xsf', '_w.cube', '_centres.xyz',
            '_hr.dat', '_tb.dat', '_r.dat', '.bvec', '_wsvec.dat', '_qc.dat',
            '_dos.dat', '_htB.dat', '_u.mat', '_u_dis.mat', '.vdw',
            '_band_proj.dat'
        )
    ]
    retrieve_temporary_list = []

    # Check the attributes of the returned `CalcInfo`
    assert isinstance(calc_info, datastructures.CalcInfo)
    code_info = calc_info.codes_info[0]
    assert code_info.cmdline_params == cmdline_params
    # ignore UUID - keep only second and third entry
    local_copy_res = [tup[1:] for tup in calc_info.local_copy_list]
    assert sorted(local_copy_res) == sorted(local_copy_list)
    assert sorted(calc_info.retrieve_list) == sorted(retrieve_list)
    assert sorted(calc_info.retrieve_temporary_list
                  ) == sorted(retrieve_temporary_list)
    assert calc_info.remote_symlink_list == []

    with fixture_sandbox.open('aiida.win') as handle:
        input_written = handle.read()

    # Checks on the files written to the sandbox folder as raw input
    assert fixture_sandbox.get_content_list() == ['aiida.win']
    file_regression.check(input_written, encoding='utf-8', extension='.win')


def test_wrong_seedname(
    fixture_sandbox, generate_calc_job, generate_common_inputs_gaas, seedname
):
    """
    Test that an InputValidationError is raised when the given seedname does
    not match the actual inputs.
    """

    inputs = generate_common_inputs_gaas(inputfolder_seedname='something_else')
    if seedname is not None:
        inputs['metadata']['options']['seedname'] = seedname

    with pytest.raises(InputValidationError):
        generate_calc_job(
            folder=fixture_sandbox,
            entry_point_name=ENTRY_POINT_NAME,
            inputs=inputs
        )


def test_duplicate_exclude_bands(
    fixture_sandbox, generate_calc_job, generate_common_inputs_gaas
):
    """Test that giving a duplicate band index in 'exclude_bands' raises an error."""

    inputs = generate_common_inputs_gaas(inputfolder_seedname='aiida')
    # Overwrite the 'parameters' input
    inputs['parameters'] = orm.Dict(
        dict=dict(
            num_wann=1,
            num_iter=12,
            wvfn_formatted=True,
            exclude_bands=[1] * 2 + [2, 3]
        )
    )

    with pytest.raises(InputValidationError):
        generate_calc_job(
            folder=fixture_sandbox,
            entry_point_name=ENTRY_POINT_NAME,
            inputs=inputs
        )


def test_mixed_case_settings_key(
    fixture_sandbox, generate_calc_job, generate_common_inputs_gaas
):
    """
    Test that using mixed case keys in 'settings' raises an InputValidationError.
    """
    inputs = generate_common_inputs_gaas(inputfolder_seedname='aiida')
    # Add an incorrect 'settings' input.
    inputs['settings'] = orm.Dict(dict=dict(PostpROc_SeTup=True))

    with pytest.raises(InputValidationError):
        generate_calc_job(
            folder=fixture_sandbox,
            entry_point_name=ENTRY_POINT_NAME,
            inputs=inputs
        )
