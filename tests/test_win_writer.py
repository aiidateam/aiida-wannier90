# -*- coding: utf-8 -*-

from __future__ import absolute_import
from aiida.manage.fixtures import PluginTestCase
from gaas_sample import create_gaas_win_params

#@pytest.fixture #NOTE: not sure if we need the pytest fixture
def compare_equal(compare_data):
    import operator
    return lambda data, tag=None: compare_data(operator.eq, data, tag)

class TestCreate(PluginTestCase):
    def setUp(self):
        from click.testing import CliRunner
        self.runner = CliRunner()

    def test_create_win_string(self):
        from aiida.plugins import DataFactory
        from aiida_wannier90.io._write_win import _create_win_string

        gaas_win_params = create_gaas_win_params()
        compare_equal(_create_win_string(**gaas_win_params).splitlines())
