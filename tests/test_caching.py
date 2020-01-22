# -*- coding: utf-8 -*-

from __future__ import absolute_import


def test_caching(create_gaas_calc, configure_with_daemon, assert_finished):  #pylint: disable=unused-argument
    from aiida.engine import run_get_pk
    from aiida.orm import load_node
    from aiida.manage.caching import enable_caching
    builder = create_gaas_calc()
    output, pk = run_get_pk(builder)
    with enable_caching():
        output2, pk2 = run_get_pk(builder)
    assert '_aiida_cached_from' in load_node(pk2).extras
    assert all(key in output for key in ['retrieved', 'output_parameters'])
    assert all(key in output2 for key in ['retrieved', 'output_parameters'])
    assert_finished(pk)
    assert_finished(pk2)
