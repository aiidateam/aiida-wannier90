# -*- coding: utf-8 -*-

import os

import pytest

from gaas_sample import *

def test_local_input(create_gaas_calc, configure_with_daemon, assert_finished):
    from aiida.work.run import run
    process, inputs = create_gaas_calc()
    output, pid = run(process, _return_pid=True, **inputs)
    assert all(key in output for key in ['retrieved', 'output_parameters'])
    assert_finished(pid)

def test_changed_seedname(create_gaas_calc, configure_with_daemon, assert_finished):
    from aiida.work.run import run
    process, inputs = create_gaas_calc(seedname='wannier90')
    output, pid = run(process, _return_pid=True, **inputs)
    assert all(key in output for key in ['retrieved', 'output_parameters'])
    assert_finished(pid)

def test_changed_seedname_empty_settings(create_gaas_calc, configure_with_daemon, assert_state):
    from aiida.work.run import run
    from aiida.orm import DataFactory
    from aiida.common.datastructures import calc_states
    process, inputs = create_gaas_calc(seedname='wannier90')
    inputs.settings = DataFactory('parameter')()
    output, pid = run(process, _return_pid=True, **inputs)
    assert_state(pid, calc_states.SUBMISSIONFAILED)

def test_empty_settings(create_gaas_calc, configure_with_daemon, assert_state):
    from aiida.work.run import run
    from aiida.orm import DataFactory
    from aiida.common.datastructures import calc_states
    process, inputs = create_gaas_calc()
    inputs.settings = DataFactory('parameter')()
    output, pid = run(process, _return_pid=True, **inputs)
    assert_state(pid, calc_states.FINISHED)

def test_changed_seedname_no_settings(create_gaas_calc, configure_with_daemon, assert_state):
    from aiida.work.run import run
    from aiida.common.datastructures import calc_states
    process, inputs = create_gaas_calc(seedname='wannier90')
    del inputs.settings
    output, pid = run(process, _return_pid=True, **inputs)
    assert_state(pid, calc_states.SUBMISSIONFAILED)

def test_duplicate_exclude_bands(create_gaas_calc, configure_with_daemon, assert_state):
    from aiida.work.run import run
    from aiida.orm import DataFactory
    from aiida.common.datastructures import calc_states
    process, inputs = create_gaas_calc(
        projections_dict={'kind_name': 'As', 'ang_mtm_name': 's'}
    )
    inputs.parameters = DataFactory('parameter')(dict=dict(
        num_wann=1,
        num_iter=12,
        wvfn_formatted=True,
        exclude_bands=[1] * 2 + [2, 3]
    ))
    output, pid = run(process, _return_pid=True, **inputs)
    assert all(key in output for key in ['retrieved', 'output_parameters'])
    assert_state(pid, calc_states.FAILED)
