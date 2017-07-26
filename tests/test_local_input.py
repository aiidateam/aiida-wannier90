# -*- coding: utf-8 -*-

import os

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

def test_duplicate_exclude_bands(create_gaas_calc, configure_with_daemon, assert_finished):
    from aiida.work.run import run
    from aiida.orm import DataFactory
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
    assert_finished(pid)
