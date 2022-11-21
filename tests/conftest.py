################################################################################
# Copyright (c), AiiDA team and individual contributors.                       #
#  All rights reserved.                                                        #
# This file is part of the AiiDA-wannier90 code.                               #
#                                                                              #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-wannier90 #
# For further information on the license, see the LICENSE.txt file             #
################################################################################
# pylint: disable=redefined-outer-name
"""Initialise a text database and profile for pytest."""

import collections
import os
import shutil
import tempfile
import types

import pytest

pytest_plugins = ["aiida.manage.tests.pytest_fixtures"]


@pytest.fixture(scope="function")
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
            remote_computer_exec=[fixture_localhost, "/bin/true"],
        )

    return _fixture_code


@pytest.fixture
def fixture_remotedata(fixture_localhost, shared_datadir):
    """Return a `RemoteData` with contents from the specified directory.

    Optionally a mapping of strings to replace in the filenames can be passed. Note that the order
    of replacement is not guaranteed.

    The RemoteData node is yielded and points to a folder in /tmp, and is removed at the end.
    """
    from aiida.orm import RemoteData

    replacement_mapping = {"gaas": "aiida"}
    dir_path = shared_datadir / "gaas"

    with tempfile.TemporaryDirectory() as tmpdir:
        remote = RemoteData(remote_path=tmpdir, computer=fixture_localhost)
        for file_path in dir_path.iterdir():
            abs_path = str(file_path.resolve())
            res_file_path = os.path.join(tmpdir, file_path.name)
            for old, new in replacement_mapping.items():
                res_file_path = res_file_path.replace(old, new)
            shutil.copyfile(src=abs_path, dst=res_file_path)
        yield remote


@pytest.fixture
def fixture_folderdata():
    """Return a `FolderData` with contents from the specified directory.

    Optionally a mapping of strings to replace in the filenames can be passed. Note that the order
    of replacement is not guaranteed.
    """

    def _fixture_folderdata(dir_path, replacement_mapping=types.MappingProxyType({})):

        from aiida.orm import FolderData

        folder = FolderData()
        for file_path in os.listdir(dir_path):
            abs_path = os.path.abspath(os.path.join(dir_path, file_path))
            res_file_path = file_path
            for old, new in replacement_mapping.items():
                res_file_path = res_file_path.replace(old, new)
            folder.base.repository.put_object_from_file(abs_path, res_file_path)
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

    def flatten_inputs(inputs, prefix=""):
        """Flatten inputs recursively like :meth:`aiida.engine.processes.process::Process._flatten_inputs`."""
        flat_inputs = []
        for key, value in inputs.items():
            if isinstance(value, collections.abc.Mapping):
                flat_inputs.extend(flatten_inputs(value, prefix=prefix + key + "__"))
            else:
                flat_inputs.append((prefix + key, value))
        return flat_inputs

    def _generate_calc_job_node(  # pylint: disable=too-many-arguments
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

        entry_point = format_entry_point_string("aiida.calculations", entry_point_name)

        # If no seedname is specified, use the default 'aiida'
        evaluated_seedname = seedname or "aiida"
        node = orm.CalcJobNode(computer=computer, process_type=entry_point)
        node.base.attributes.set("input_filename", f"{evaluated_seedname}.win")
        node.base.attributes.set("output_filename", f"{evaluated_seedname}.wout")
        node.base.attributes.set("error_filename", f"{evaluated_seedname}.werr")
        node.set_option("resources", {"num_machines": 1, "num_mpiprocs_per_machine": 1})
        node.set_option("max_wallclock_seconds", 1800)
        node.set_option("seedname", evaluated_seedname)

        if attributes:
            node.set_attribute_many(attributes)

        if inputs:
            for link_label, input_node in flatten_inputs(inputs):
                input_node.store()
                node.base.links.add_incoming(
                    input_node, link_type=LinkType.INPUT_CALC, link_label=link_label
                )

        node.store()

        if test_name is not None:
            filepath = str(shared_datadir / test_name)

            retrieved = orm.FolderData()
            retrieved.base.repository.put_object_from_tree(filepath)
            retrieved.base.links.add_incoming(
                node, link_type=LinkType.CREATE, link_label="retrieved"
            )
            retrieved.store()

            remote_folder = orm.RemoteData(computer=computer, remote_path="/tmp")
            remote_folder.base.links.add_incoming(
                node, link_type=LinkType.CREATE, link_label="remote_folder"
            )
            remote_folder.store()

        return node

    return _generate_calc_job_node


@pytest.fixture(scope="session")
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


@pytest.fixture(scope="session")
def generate_structure_gaas():
    """Return a `StructureData` representing bulk GaAs."""

    def _generate_structure():
        """Return a `StructureData` representing bulk GaAs."""

        from aiida import orm

        param = 2.84
        structure = orm.StructureData(
            cell=[[-param, 0, param], [0, param, param], [-param, param, 0]]
        )

        structure.append_atom(symbols="Ga", position=[0, 0, 0])
        structure.append_atom(
            symbols="As", position=[-0.5 * param, 0.5 * param, 0.5 * param]
        )
        return structure

    return _generate_structure


@pytest.fixture
def generate_win_params_gaas(generate_structure_gaas, generate_kpoints_mesh):
    """Generate paramters for GaAs."""

    def _generate_win_params_gaas(
        projections_dict=types.MappingProxyType(
            {"kind_name": "As", "ang_mtm_name": "sp3"}
        )
    ):
        from aiida import orm
        from aiida.tools import get_kpoints_path

        from aiida_wannier90.orbitals import generate_projections

        projections_dict_mutable = {**projections_dict}
        structure = generate_structure_gaas()
        inputs = {
            "structure": structure,
            "kpoints": generate_kpoints_mesh(2),
            "kpoint_path": get_kpoints_path(structure, method="legacy")["parameters"],
            "parameters": orm.Dict(
                dict={"num_wann": 4, "num_iter": 12, "wvfn_formatted": True}
            ),
            "projections": generate_projections(
                projections_dict_mutable, structure=structure
            ),
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


@pytest.fixture(scope="session")
def generate_structure_o2sr():
    """Return a `StructureData` representing bulk O2Sr."""

    def _generate_structure():
        """Return a `StructureData` representing bulk O2Sr."""

        from aiida import orm

        structure = orm.StructureData(
            cell=[
                [-1.7828864010, 1.7828864010, 3.3905324933],
                [1.7828864010, -1.7828864010, 3.3905324933],
                [1.7828864010, 1.7828864010, -3.3905324933],
            ]
        )

        structure.append_atom(symbols="Sr", position=[0, 0, 0])
        structure.append_atom(
            symbols="O", position=[1.7828864010, 1.7828864010, 0.7518485043]
        )
        structure.append_atom(symbols="O", position=[0, 0, 2.6386839890])
        return structure

    return _generate_structure


@pytest.fixture
def generate_win_params_o2sr(generate_structure_o2sr, generate_kpoints_mesh):
    """Generate paramters for O2Sr."""

    def _generate_win_params_o2sr():
        from aiida import orm

        structure = generate_structure_o2sr()
        inputs = {
            "structure": structure,
            "kpoints": generate_kpoints_mesh(9),
            "kpoint_path":
            # To avoid dependency on seekpath, I paste here the result of
            # get_kpoints_path(structure)['parameters']
            orm.Dict(
                dict={
                    "point_coords": {
                        "GAMMA": [0.0, 0.0, 0.0],
                        "M": [0.5, 0.5, -0.5],
                        "X": [0.0, 0.0, 0.5],
                        "P": [0.25, 0.25, 0.25],
                        "N": [0.0, 0.5, 0.0],
                        "S_0": [
                            -0.3191276083914903,
                            0.3191276083914903,
                            0.3191276083914903,
                        ],
                        "S": [
                            0.3191276083914903,
                            0.6808723916085098,
                            -0.3191276083914903,
                        ],
                        "R": [-0.1382552167829806, 0.1382552167829806, 0.5],
                        "G": [0.5, 0.5, -0.1382552167829806],
                    },
                    "path": [
                        ("GAMMA", "X"),
                        ("X", "P"),
                        ("P", "N"),
                        ("N", "GAMMA"),
                        ("GAMMA", "M"),
                        ("M", "S"),
                        ("S_0", "GAMMA"),
                        ("X", "R"),
                        ("G", "M"),
                    ],
                }
            ),
            "parameters": orm.Dict(
                dict={
                    "num_wann": 21,
                    "num_bands": 31,
                    "num_iter": 200,
                    "bands_plot": True,
                    "auto_projections": True,
                }
            ),
        }

        return inputs

    return _generate_win_params_o2sr


@pytest.fixture(scope="session")
def generate_structure_ca4mg8():
    """Return a `StructureData` representing bulk Ca4Mg8."""

    def _generate_structure():
        """Return a `StructureData` representing bulk Ca4Mg8."""

        from aiida import orm

        structure = orm.StructureData(
            cell=[
                [3.1235488629, -5.4101154125, 0.0000000000],
                [3.1235488629, 5.4101154125, 0.0000000000],
                [0.0000000000, 0.0000000000, 10.0402257142],
            ]
        )

        structure.append_atom(
            symbols="Ca", position=[3.1235488629, 7.2135064307, 5.6428504986]
        )
        structure.append_atom(
            symbols="Ca", position=[3.1235488629, 3.6067243943, 4.3973752156]
        )
        structure.append_atom(
            symbols="Ca", position=[3.1235488629, 3.6067243943, 0.6227376415]
        )
        structure.append_atom(
            symbols="Ca", position=[3.1235488629, 7.2135064307, 9.4174880727]
        )
        structure.append_atom(
            symbols="Mg", position=[3.1235488629, 0.0000000000, 5.0201128571]
        )
        structure.append_atom(
            symbols="Mg", position=[3.1235488629, 0.0000000000, 0.0000000000]
        )
        structure.append_atom(
            symbols="Mg", position=[1.5416212587, 9.9069482534, 7.5301692857]
        )
        structure.append_atom(
            symbols="Mg", position=[3.1235488629, 1.8266571732, 7.5301692857]
        )
        structure.append_atom(
            symbols="Mg", position=[4.7054764671, 9.9069482534, 7.5301692857]
        )
        structure.append_atom(
            symbols="Mg", position=[4.7054764671, 0.9132825716, 2.5100564285]
        )
        structure.append_atom(
            symbols="Mg", position=[3.1235488629, 8.9935736518, 2.5100564285]
        )
        structure.append_atom(
            symbols="Mg", position=[1.5416212587, 0.9132825716, 2.5100564285]
        )
        return structure

    return _generate_structure


@pytest.fixture
def generate_win_params_ca4mg8(
    generate_structure_ca4mg8,
):
    """Generate parameters for Ca4Mg8."""

    def _generate_win_params_ca4mg8():
        from aiida import orm

        structure = generate_structure_ca4mg8()
        kpoints = orm.KpointsData()
        kpoints.set_kpoints_mesh([6, 6, 4])
        inputs = {
            "structure": structure,
            "kpoints": kpoints,
            "parameters": orm.Dict(
                dict={
                    "num_wann": 72,
                    "num_bands": 86,
                    "num_iter": 400,
                    "auto_projections": True,
                }
            ),
        }

        return inputs

    return _generate_win_params_ca4mg8


@pytest.fixture(scope="session")
def generate_structure_br2fe():
    """Return a `StructureData` representing bulk Br2Fe."""

    def _generate_structure():
        """Return a `StructureData` representing bulk Br2Fe."""

        from aiida import orm

        structure = orm.StructureData(
            cell=[
                [3.1218481617, 1.8023993833, 0.0000000000],
                [-3.1218481617, 1.8023993833, 0.0000000000],
                [-0.0010222890, 0.0000000000, 6.6558096562],
            ]
        )

        structure.append_atom(
            symbols="Fe", position=[0.0000000000, 0.0000000000, 0.0000000000]
        )
        structure.append_atom(
            symbols="Br", position=[5.2020635002, 1.8023993833, 5.3570235967]
        )
        structure.append_atom(
            symbols="Br", position=[4.1624586959, 0.0000000000, 1.2987860595]
        )
        return structure

    return _generate_structure


@pytest.fixture
def generate_win_params_br2fe(
    generate_structure_br2fe,
):
    """Generate parameters for Br2Fe."""

    def _generate_win_params_br2fe():
        from aiida import orm

        structure = generate_structure_br2fe()
        kpoints = orm.KpointsData()
        kpoints.set_kpoints_mesh([11, 11, 5])
        inputs = {
            "structure": structure,
            "kpoints": kpoints,
            "parameters": orm.Dict(
                dict={
                    "num_wann": 17,
                    "num_bands": 21,
                    "num_iter": 400,
                    "auto_projections": True,
                }
            ),
        }

        return inputs

    return _generate_win_params_br2fe
