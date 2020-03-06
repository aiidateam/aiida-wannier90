# -*- coding: utf-8 -*-
################################################################################
# Copyright (c), AiiDA team and individual contributors.                       #
#  All rights reserved.                                                        #
# This file is part of the AiiDA-wannier90 code.                               #
#                                                                              #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-wannier90 #
# For further information on the license, see the LICENSE.txt file             #
################################################################################
"""Test that the example provided in the top-level `examples` folder works."""
import os
import pytest

ENTRY_POINT_NAME = 'wannier90.wannier90'


@pytest.fixture
def prepare_for_submission_from_builder():
    def _generate_calc_job(folder, builder):
        """Fixture to generate a mock `CalcInfo` for testing calculation jobs."""
        from aiida.engine.utils import instantiate_process
        from aiida.manage.manager import get_manager

        manager = get_manager()
        runner = manager.get_runner()

        process_class = builder._process_class  # pylint: disable=protected-access
        process = instantiate_process(runner, process_class, **dict(builder))

        calc_info = process.prepare_for_submission(folder)

        return calc_info

    return _generate_calc_job


def load_module(module_name, full_path):
    import importlib.util  # pylint: disable=import-error
    spec = importlib.util.spec_from_file_location(module_name, full_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def test_example_gaas(
    fixture_code, fixture_sandbox, prepare_for_submission_from_builder
):
    """Dynamically load the example and try to submit it to see that it works."""
    example_folder = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), os.pardir, os.pardir,
        'examples', 'example01'
    )

    create_local_input_folder = load_module(
        'create_local_input_folder',
        os.path.join(example_folder, 'create_local_input_folder.py')
    )

    wannier_gaas = load_module(
        'wannier_gaas', os.path.join(example_folder, 'wannier_gaas.py')
    )

    code = fixture_code(ENTRY_POINT_NAME)

    folder_data = create_local_input_folder.get_unstored_folder_data()
    builder = wannier_gaas.create_builder(
        code, input_folder=folder_data, submit_test=False
    )

    with fixture_sandbox as folder:
        calc_info = prepare_for_submission_from_builder(folder, builder)

    code_info = calc_info.codes_info[0]
    assert code_info.cmdline_params == ['aiida']
