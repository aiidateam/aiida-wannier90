# -*- coding: utf-8 -*-

import os

import pytest

from gaas_sample import *


def test_caching(create_gaas_calc, configure_with_daemon, assert_finished):
    from aiida.work.run import run
    from aiida.orm import load_node
    from aiida.common.hashing import make_hash
    process, inputs = create_gaas_calc()
    output, pid = run(process, _return_pid=True, **inputs)
    output2, pid2 = run(process, _use_cache=True, _return_pid=True, **inputs)
    assert 'cached_from' in load_node(pid2).extras()
    assert all(key in output for key in ['retrieved', 'output_parameters'])
    assert all(key in output2 for key in ['retrieved', 'output_parameters'])
    assert_finished(pid)
    assert_finished(pid2)
