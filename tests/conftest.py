# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name
"""Initialise a text database and profile for pytest."""
from __future__ import absolute_import

import os
import collections

import pytest
import six

pytest_plugins = ['aiida.manage.tests.pytest_fixtures']  # pylint: disable=invalid-name


@pytest.fixture(scope='function')
def fixture_sandbox():
    """Return a `SandboxFolder`."""
    from aiida.common.folders import SandboxFolder
    with SandboxFolder() as folder:
        yield folder


@pytest.fixture
def fixture_localhost(aiida_localhost):
    """Return a localhost `Computer`."""
    localhost = aiida_localhost
    localhost.set_default_mpiprocs_per_machine(1)
    return localhost


@pytest.fixture
def fixture_code(fixture_localhost):
    """Return a `Code` instance configured to run calculations of given entry point on localhost `Computer`."""
    def _fixture_code(entry_point_name):
        from aiida.orm import Code
        return Code(
            input_plugin_name=entry_point_name,
            remote_computer_exec=[fixture_localhost, '/bin/true']
        )

    return _fixture_code


@pytest.fixture
def fixture_folderdata():
    """
    Return a `FolderData` with contents from the specified directory. Optionally a
    mapping of strings to replace in the filenames can be passed. Note that the order
    of replacement is not guaranteed.
    """

    # TODO: wrap 'replacement_mapping in 'types.MappingProxyType' after Python2 support
    # is dropped, for immutability.
    def _fixture_folderdata(dir_path, replacement_mapping=None):
        if replacement_mapping is None:
            replacement_mapping = {}
        dir_path = str(
            dir_path
        )  # TODO: Remove cast to 'str' when Python2 support is dropped.
        from aiida.orm import FolderData
        folder = FolderData()
        for file_path in os.listdir(dir_path):
            abs_path = os.path.abspath(os.path.join(dir_path, file_path))
            res_file_path = file_path
            for old, new in replacement_mapping.items():
                res_file_path = res_file_path.replace(old, new)
            folder.put_object_from_file(abs_path, res_file_path)
        return folder

    return _fixture_folderdata


@pytest.fixture
def generate_calc_job():
    """Fixture to construct a new `CalcJob` instance and call `prepare_for_submission` for testing `CalcJob` classes.

    The fixture will return the `CalcInfo` returned by `prepare_for_submission` and the temporary folder that was passed
    to it, into which the raw input files will have been written.
    """
    def _generate_calc_job(folder, entry_point_name, inputs=None):
        """Fixture to generate a mock `CalcInfo` for testing calculation jobs."""
        from aiida.engine.utils import instantiate_process
        from aiida.manage.manager import get_manager
        from aiida.plugins import CalculationFactory

        manager = get_manager()
        runner = manager.get_runner()

        process_class = CalculationFactory(entry_point_name)
        process = instantiate_process(runner, process_class, **inputs)

        calc_info = process.prepare_for_submission(folder)

        return calc_info

    return _generate_calc_job


@pytest.fixture
def generate_calc_job_node(shared_datadir):
    """Fixture to generate a mock `CalcJobNode` for testing parsers."""
    def flatten_inputs(inputs, prefix=''):
        """Flatten inputs recursively like :meth:`aiida.engine.processes.process::Process._flatten_inputs`."""
        flat_inputs = []
        for key, value in six.iteritems(inputs):
            if isinstance(value, collections.Mapping):
                flat_inputs.extend(
                    flatten_inputs(value, prefix=prefix + key + '__')
                )
            else:
                flat_inputs.append((prefix + key, value))
        return flat_inputs

    def _generate_calc_job_node(  # pylint: disable=too-many-arguments,too-many-locals
        entry_point_name,
        computer,
        seedname=None,
        test_name=None,
        inputs=None,
        attributes=None,
    ):
        """Fixture to generate a mock `CalcJobNode` for testing parsers.

        :param entry_point_name: entry point name of the calculation class
        :param computer: a `Computer` instance
        :param test_name: relative path of directory with test output files in the `fixtures/{entry_point_name}` folder.
        :param inputs: any optional nodes to add as input links to the corrent CalcJobNode
        :param attributes: any optional attributes to set on the node
        :return: `CalcJobNode` instance with an attached `FolderData` as the `retrieved` node
        """
        from aiida import orm
        from aiida.common import LinkType
        from aiida.plugins.entry_point import format_entry_point_string

        entry_point = format_entry_point_string(
            'aiida.calculations', entry_point_name
        )

        # If no seedname is specified, use the default 'aiida'
        evaluated_seedname = seedname or 'aiida'
        node = orm.CalcJobNode(computer=computer, process_type=entry_point)
        node.set_attribute(
            'input_filename', '{}.win'.format(evaluated_seedname)
        )
        node.set_attribute(
            'output_filename', '{}.wout'.format(evaluated_seedname)
        )
        node.set_attribute(
            'error_filename', '{}.werr'.format(evaluated_seedname)
        )
        node.set_option(
            'resources', {
                'num_machines': 1,
                'num_mpiprocs_per_machine': 1
            }
        )
        node.set_option('max_wallclock_seconds', 1800)
        node.set_option('seedname', evaluated_seedname)

        if attributes:
            node.set_attribute_many(attributes)

        if inputs:
            for link_label, input_node in flatten_inputs(inputs):
                input_node.store()
                node.add_incoming(
                    input_node,
                    link_type=LinkType.INPUT_CALC,
                    link_label=link_label
                )

        node.store()

        if test_name is not None:
            # TODO: remove cast to 'str' when Python2 support is dropped
            filepath = str(shared_datadir / test_name)

            retrieved = orm.FolderData()
            retrieved.put_object_from_tree(filepath)
            retrieved.add_incoming(
                node, link_type=LinkType.CREATE, link_label='retrieved'
            )
            retrieved.store()

            remote_folder = orm.RemoteData(
                computer=computer, remote_path='/tmp'
            )
            remote_folder.add_incoming(
                node, link_type=LinkType.CREATE, link_label='remote_folder'
            )
            remote_folder.store()

        return node

    return _generate_calc_job_node


@pytest.fixture(scope='session')
def generate_parser():
    """Fixture to load a parser class for testing parsers."""
    def _generate_parser(entry_point_name):
        """Fixture to load a parser class for testing parsers.

        :param entry_point_name: entry point name of the parser class
        :return: the `Parser` sub class
        """
        from aiida.plugins import ParserFactory
        return ParserFactory(entry_point_name)

    return _generate_parser


@pytest.fixture(scope='session')
def generate_structure_gaas():
    """Return a `StructureData` representing bulk GaAs."""
    def _generate_structure():
        """Return a `StructureData` representing bulk GaAs."""

        from aiida import orm

        param = 2.84
        structure = orm.StructureData(
            cell=[[-param, 0, param], [0, param, param], [-param, param, 0]]
        )

        structure.append_atom(symbols='Ga', position=[0, 0, 0])
        structure.append_atom(
            symbols='As', position=[-0.5 * param, 0.5 * param, 0.5 * param]
        )
        return structure

    return _generate_structure


@pytest.fixture
def generate_win_params_gaas(generate_structure_gaas, generate_kpoints_mesh):
    # TODO: when Python2 support is dropped, wrap 'projections_dict'
    # in 'types.MappingProxyType' for immutability.
    def _generate_win_params_gaas(projections_dict=None):
        from aiida import orm
        from aiida.tools import get_kpoints_path
        from aiida_wannier90.orbitals import generate_projections
        if projections_dict is None:
            projections_dict = {'kind_name': 'As', 'ang_mtm_name': 'sp3'}
        structure = generate_structure_gaas()
        inputs = {
            'structure':
            structure,
            'kpoints':
            generate_kpoints_mesh(2),
            'kpoint_path':
            get_kpoints_path(structure, method='legacy')['parameters'],
            'parameters':
            orm.Dict(
                dict={
                    "num_wann": 4,
                    "num_iter": 12,
                    "wvfn_formatted": True
                }
            ),
            'projections':
            generate_projections(projections_dict, structure=structure)
        }

        return inputs

    return _generate_win_params_gaas


@pytest.fixture
def generate_kpoints_mesh():
    """Return a `KpointsData` node."""
    def _generate_kpoints_mesh(npoints):
        """Return a `KpointsData` with a mesh of npoints in each direction."""
        from aiida.orm import KpointsData

        kpoints = KpointsData()
        kpoints.set_kpoints_mesh([npoints] * 3)

        return kpoints

    return _generate_kpoints_mesh
