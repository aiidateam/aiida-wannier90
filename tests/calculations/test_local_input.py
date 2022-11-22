################################################################################
# Copyright (c), AiiDA team and individual contributors.                       #
#  All rights reserved.                                                        #
# This file is part of the AiiDA-wannier90 code.                               #
#                                                                              #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-wannier90 #
# For further information on the license, see the LICENSE.txt file             #
################################################################################

# pylint: disable=redefined-outer-name
"""Tests for the `PwCalculation` class."""

import pytest

from aiida import orm
from aiida.common import datastructures
from aiida.common.exceptions import InputValidationError

ENTRY_POINT_NAME = "wannier90.wannier90"


@pytest.fixture
def generate_common_inputs_gaas(
    shared_datadir,
    fixture_folderdata,
    fixture_code,
    generate_win_params_gaas,
):
    """Generate inputs for a `Wannier90Calculation`."""

    def _generate_common_inputs_gaas(inputfolder_seedname):
        inputs = dict(
            code=fixture_code(ENTRY_POINT_NAME),
            metadata={
                "options": {
                    "resources": {"num_machines": 1},
                    "max_wallclock_seconds": 3600,
                    "withmpi": False,
                }
            },
            local_input_folder=fixture_folderdata(
                shared_datadir / "gaas", {"gaas": inputfolder_seedname}
            ),
            **generate_win_params_gaas(),
        )

        return inputs

    return _generate_common_inputs_gaas


@pytest.fixture(params=(None, "aiida", "wannier"))
def seedname(request):
    """Generate seedname."""
    return request.param


def test_default(
    fixture_sandbox,
    generate_calc_job,
    generate_common_inputs_gaas,
    file_regression,
    seedname,
):
    """Test a default `Wannier90Calculation` with local input folder."""

    input_seedname = seedname or "aiida"
    inputs = generate_common_inputs_gaas(inputfolder_seedname=input_seedname)
    if seedname is not None:
        inputs["metadata"]["options"]["input_filename"] = f"{seedname}.win"
        inputs["metadata"]["options"]["output_filename"] = f"{seedname}.wout"

    calc_info = generate_calc_job(
        folder=fixture_sandbox, entry_point_name=ENTRY_POINT_NAME, inputs=inputs
    )

    cmdline_params = [input_seedname]
    local_copy_list = [
        (val, val) for val in (f"{input_seedname}.mmn", f"{input_seedname}.amn")
    ]
    retrieve_list = [
        input_seedname + suffix
        for suffix in (
            ".wout",
            ".werr",
            ".r2mn",
            "_band.dat",
            "_band.dat",
            "_band.agr",
            "_band.kpt",
            ".bxsf",
            "_w.xsf",
            "_w.cube",
            "_centres.xyz",
            "_hr.dat",
            "_tb.dat",
            "_r.dat",
            ".bvec",
            "_wsvec.dat",
            "_qc.dat",
            "_dos.dat",
            "_htB.dat",
            "_u.mat",
            "_u_dis.mat",
            ".vdw",
            "_band_proj.dat",
            "_band.labelinfo.dat",
            ".node_00001.werr",
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
    assert sorted(calc_info.retrieve_temporary_list) == sorted(retrieve_temporary_list)
    assert sorted(calc_info.remote_symlink_list) == sorted([])

    with fixture_sandbox.open(f"{input_seedname}.win") as handle:
        input_written = handle.read()

    # Checks on the files written to the sandbox folder as raw input
    assert sorted(fixture_sandbox.get_content_list()) == sorted(
        [f"{input_seedname}.win"]
    )
    file_regression.check(input_written, encoding="utf-8", extension=".win")


def test_default_plot(
    fixture_sandbox, generate_calc_job, generate_common_inputs_gaas, file_regression
):
    """Test a default `Wannier90Calculation` with local input folder, with wannier_plot = True."""

    input_seedname = "aiida"
    inputs = generate_common_inputs_gaas(inputfolder_seedname=input_seedname)
    inputs["metadata"]["options"]["input_filename"] = f"{input_seedname}.win"
    inputs["metadata"]["options"]["output_filename"] = f"{input_seedname}.wout"
    parameters = inputs["parameters"].get_dict()
    parameters["wannier_plot"] = True
    inputs["parameters"] = orm.Dict(parameters)

    calc_info = generate_calc_job(
        folder=fixture_sandbox, entry_point_name=ENTRY_POINT_NAME, inputs=inputs
    )

    cmdline_params = [input_seedname]
    local_copy_list = [
        (val, val)
        for val in (
            "UNK00001.1",
            "UNK00002.1",
            "UNK00003.1",
            "UNK00004.1",
            "UNK00005.1",
            "UNK00006.1",
            "UNK00007.1",
            "UNK00008.1",
            f"{input_seedname}.mmn",
            f"{input_seedname}.amn",
        )
    ]
    retrieve_list = [
        input_seedname + suffix
        for suffix in (
            ".wout",
            ".werr",
            ".r2mn",
            "_band.dat",
            "_band.dat",
            "_band.agr",
            "_band.kpt",
            ".bxsf",
            "_w.xsf",
            "_w.cube",
            "_centres.xyz",
            "_hr.dat",
            "_tb.dat",
            "_r.dat",
            ".bvec",
            "_wsvec.dat",
            "_qc.dat",
            "_dos.dat",
            "_htB.dat",
            "_u.mat",
            "_u_dis.mat",
            ".vdw",
            "_band_proj.dat",
            "_band.labelinfo.dat",
            ".node_00001.werr",
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
    assert sorted(calc_info.retrieve_temporary_list) == sorted(retrieve_temporary_list)
    assert sorted(calc_info.remote_symlink_list) == sorted([])

    with fixture_sandbox.open(f"{input_seedname}.win") as handle:
        input_written = handle.read()

    # Checks on the files written to the sandbox folder as raw input
    assert sorted(fixture_sandbox.get_content_list()) == sorted(
        [f"{input_seedname}.win"]
    )
    file_regression.check(input_written, encoding="utf-8", extension=".win")


def test_wrong_input_filename(
    fixture_sandbox, generate_calc_job, generate_common_inputs_gaas
):
    """Test that passing an input filename that does not end in .win fails."""

    inputs = generate_common_inputs_gaas(inputfolder_seedname="test")
    inputs["metadata"]["options"]["input_filename"] = "does_not_end_in_dot_win.txt"
    inputs["metadata"]["options"]["output_filename"] = "test.wout"

    with pytest.raises(InputValidationError):
        generate_calc_job(
            folder=fixture_sandbox, entry_point_name=ENTRY_POINT_NAME, inputs=inputs
        )


def test_mismatch_input_output_filename(
    fixture_sandbox, generate_calc_job, generate_common_inputs_gaas
):
    """Test that passing an input and output filenames check the consistency and raise error if not."""

    inputs = generate_common_inputs_gaas(inputfolder_seedname="test")
    inputs["metadata"]["options"]["input_filename"] = "test1.win"
    inputs["metadata"]["options"]["output_filename"] = "test2.wout"

    with pytest.raises(InputValidationError):
        generate_calc_job(
            folder=fixture_sandbox, entry_point_name=ENTRY_POINT_NAME, inputs=inputs
        )


def test_werr_retrieved_with_custom_seedname(
    fixture_sandbox, generate_calc_job, generate_common_inputs_gaas
):
    """Test the file seedname.werr is produced if the inputs are correct."""

    inputs = generate_common_inputs_gaas(inputfolder_seedname="test3")
    inputs["metadata"]["options"]["input_filename"] = "test3.win"
    inputs["metadata"]["options"]["output_filename"] = "test3.wout"

    calc_info = generate_calc_job(
        folder=fixture_sandbox, entry_point_name=ENTRY_POINT_NAME, inputs=inputs
    )

    assert "test3.werr" in calc_info.retrieve_list


def test_no_projections(
    fixture_sandbox, generate_calc_job, generate_common_inputs_gaas, file_regression
):
    """Test a `Wannier90Calculation` where the projections are not specified."""

    inputs = generate_common_inputs_gaas(inputfolder_seedname="aiida")
    del inputs["projections"]

    calc_info = generate_calc_job(
        folder=fixture_sandbox, entry_point_name=ENTRY_POINT_NAME, inputs=inputs
    )

    cmdline_params = ["aiida"]
    local_copy_list = [(val, val) for val in ("aiida.mmn", "aiida.amn")]
    retrieve_list = [
        "aiida" + suffix
        for suffix in (
            ".wout",
            ".werr",
            ".r2mn",
            "_band.dat",
            "_band.dat",
            "_band.agr",
            "_band.kpt",
            ".bxsf",
            "_w.xsf",
            "_w.cube",
            "_centres.xyz",
            "_hr.dat",
            "_tb.dat",
            "_r.dat",
            ".bvec",
            "_wsvec.dat",
            "_qc.dat",
            "_dos.dat",
            "_htB.dat",
            "_u.mat",
            "_u_dis.mat",
            ".vdw",
            "_band_proj.dat",
            "_band.labelinfo.dat",
            ".node_00001.werr",
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
    assert sorted(calc_info.retrieve_temporary_list) == sorted(retrieve_temporary_list)
    assert calc_info.remote_symlink_list == []

    with fixture_sandbox.open("aiida.win") as handle:
        input_written = handle.read()

    # Checks on the files written to the sandbox folder as raw input
    assert fixture_sandbox.get_content_list() == ["aiida.win"]
    file_regression.check(input_written, encoding="utf-8", extension=".win")


def test_list_projections(
    fixture_sandbox, generate_calc_job, generate_common_inputs_gaas, file_regression
):
    """Test a `Wannier90Calculation` where the projections are specified as a list."""

    inputs = generate_common_inputs_gaas(inputfolder_seedname="aiida")
    inputs["projections"] = orm.List(list=["random", "Ga:s"])

    calc_info = generate_calc_job(
        folder=fixture_sandbox, entry_point_name=ENTRY_POINT_NAME, inputs=inputs
    )

    cmdline_params = ["aiida"]
    local_copy_list = [(val, val) for val in ("aiida.mmn", "aiida.amn")]
    retrieve_list = [
        "aiida" + suffix
        for suffix in (
            ".wout",
            ".werr",
            ".r2mn",
            "_band.dat",
            "_band.dat",
            "_band.agr",
            "_band.kpt",
            ".bxsf",
            "_w.xsf",
            "_w.cube",
            "_centres.xyz",
            "_hr.dat",
            "_tb.dat",
            "_r.dat",
            ".bvec",
            "_wsvec.dat",
            "_qc.dat",
            "_dos.dat",
            "_htB.dat",
            "_u.mat",
            "_u_dis.mat",
            ".vdw",
            "_band_proj.dat",
            "_band.labelinfo.dat",
            ".node_00001.werr",
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
    assert sorted(calc_info.retrieve_temporary_list) == sorted(retrieve_temporary_list)
    assert calc_info.remote_symlink_list == []

    with fixture_sandbox.open("aiida.win") as handle:
        input_written = handle.read()

    # Checks on the files written to the sandbox folder as raw input
    assert fixture_sandbox.get_content_list() == ["aiida.win"]
    file_regression.check(input_written, encoding="utf-8", extension=".win")


def test_wrong_seedname(
    fixture_sandbox, generate_calc_job, generate_common_inputs_gaas, seedname
):
    """Test that an InputValidationError is raised when the given seedname does not match the actual inputs."""

    inputs = generate_common_inputs_gaas(inputfolder_seedname="something_else")
    if seedname is not None:
        inputs["metadata"]["options"]["input_filename"] = f"{seedname}.win"
        inputs["metadata"]["options"]["output_filename"] = f"{seedname}.wout"

    with pytest.raises(InputValidationError):
        generate_calc_job(
            folder=fixture_sandbox, entry_point_name=ENTRY_POINT_NAME, inputs=inputs
        )


def test_duplicate_exclude_bands(
    fixture_sandbox, generate_calc_job, generate_common_inputs_gaas
):
    """Test that giving a duplicate band index in 'exclude_bands' raises an error."""

    inputs = generate_common_inputs_gaas(inputfolder_seedname="aiida")
    # Overwrite the 'parameters' input
    inputs["parameters"] = orm.Dict(
        dict=dict(
            num_wann=1, num_iter=12, wvfn_formatted=True, exclude_bands=[1] * 2 + [2, 3]
        )
    )

    with pytest.raises(InputValidationError):
        generate_calc_job(
            folder=fixture_sandbox, entry_point_name=ENTRY_POINT_NAME, inputs=inputs
        )


def test_mixed_case_settings_key(
    fixture_sandbox, generate_calc_job, generate_common_inputs_gaas
):
    """Test that using mixed case keys in 'settings' raises an InputValidationError."""
    inputs = generate_common_inputs_gaas(inputfolder_seedname="aiida")
    # Add an incorrect 'settings' input.
    inputs["settings"] = orm.Dict(dict(PostpROc_SeTup=True))

    with pytest.raises(InputValidationError):
        generate_calc_job(
            folder=fixture_sandbox, entry_point_name=ENTRY_POINT_NAME, inputs=inputs
        )


def test_diffusivity(
    fixture_sandbox, generate_calc_job, generate_common_inputs_gaas, file_regression
):
    """Test a `Wannier90Calculation` with various advanced combinations of the projections.

    For instance, using both diffusivity and radial_nodes, or diffusivity only,
    and in combination with/without zaxis and xaxis.
    """
    from aiida_wannier90.orbitals import generate_projections

    seedname = "aiida"
    inputs = generate_common_inputs_gaas(inputfolder_seedname=seedname)

    # Replace projections
    projections_dict_list = [
        {"kind_name": "As", "ang_mtm_name": "s"},
        {"kind_name": "As", "ang_mtm_name": "s", "zona": 2},  # only diffusivity
        {"kind_name": "As", "ang_mtm_name": "s", "radial": 3},  # only radial_nodes
        {
            "kind_name": "As",
            "ang_mtm_name": "s",
            "zona": 2,
            "radial": 3,
        },  # both diffusivity and radial_nodes
        {"kind_name": "Ga", "ang_mtm_name": "s", "xaxis": [0, -1, 0]},
        {
            "kind_name": "Ga",
            "ang_mtm_name": "s",
            "zaxis": [-1, 0, 0],
        },  # only diffusivity
        {
            "kind_name": "Ga",
            "ang_mtm_name": "s",
            "xaxis": [0, -1, 0],
            "zaxis": [-1, 0, 0],
            "zona": 2,
        },  # only radial_nodes
        {
            "kind_name": "Ga",
            "ang_mtm_name": "s",
            "zona": 2,
            "radial": 3,
        },  # both diffusivity and radial_nodes
    ]
    inputs["projections"] = generate_projections(
        projections_dict_list, structure=inputs["structure"]
    )

    generate_calc_job(
        folder=fixture_sandbox, entry_point_name=ENTRY_POINT_NAME, inputs=inputs
    )

    with fixture_sandbox.open(f"{seedname}.win") as handle:
        input_written = handle.read()

    file_regression.check(input_written, encoding="utf-8", extension=".win")


def test_spin_projections(
    fixture_sandbox, generate_calc_job, generate_common_inputs_gaas, file_regression
):
    """Test a ``Wannier90Calculation`` with various advanced combinations of the projections when using also spin.

    For instance, using both diffusivity and radial_nodes, or diffusivity only,
    and in combination with/without zaxis and xaxis.
    """
    from aiida.orm import Dict

    from aiida_wannier90.orbitals import generate_projections

    seedname = "aiida"
    inputs = generate_common_inputs_gaas(inputfolder_seedname=seedname)

    # Replace projections
    projections_dict_list = [
        {"kind_name": "As", "ang_mtm_name": "s", "spin": "u"},
        {
            "kind_name": "As",
            "ang_mtm_name": "s",
            "zona": 2,
            "spin": "d",
        },  # only diffusivity
        {
            "kind_name": "As",
            "ang_mtm_name": "s",
            "radial": 3,
            "spin": 1,
        },  # only radial_nodes
        {
            "kind_name": "As",
            "ang_mtm_name": "s",
            "zona": 2,
            "radial": 3,
            "spin": -1,
        },  # both diffusivity and radial_nodes
        {
            "kind_name": "Ga",
            "ang_mtm_name": "s",
            "xaxis": [0, -1, 0],
            "spin": "U",
            "spin_axis": [0, 1, 0],
        },
        {
            "kind_name": "Ga",
            "ang_mtm_name": "s",
            "zaxis": [-1, 0, 0],
            "spin": "D",
            "spin_axis": [0, 1, 0],
        },  # only diffusivity
        {
            "kind_name": "Ga",
            "ang_mtm_name": "s",
            "xaxis": [0, -1, 0],
            "zaxis": [-1, 0, 0],
            "zona": 2,
            "spin": "U",
            "spin_axis": [0, -1, 0],
        },  # only radial_nodes
        {
            "kind_name": "Ga",
            "ang_mtm_name": "s",
            "zona": 2,
            "radial": 3,
            "spin": "D",
            "spin_axis": [0, -1, 0],
        },  # both diffusivity and radial_nodes
    ]
    inputs["projections"] = generate_projections(
        projections_dict_list, structure=inputs["structure"]
    )

    param_dict = inputs["parameters"].get_dict()
    param_dict["spinors"] = True
    inputs["parameters"] = Dict(param_dict)

    generate_calc_job(
        folder=fixture_sandbox, entry_point_name=ENTRY_POINT_NAME, inputs=inputs
    )

    with fixture_sandbox.open(f"{seedname}.win") as handle:
        input_written = handle.read()

    file_regression.check(input_written, encoding="utf-8", extension=".win")


def test_bands_kpoints(
    fixture_sandbox, generate_calc_job, generate_common_inputs_gaas, file_regression
):
    """Test a `Wannier90Calculation` with inputs `bands_kpoints`."""

    seedname = "aiida"
    inputs = generate_common_inputs_gaas(inputfolder_seedname=seedname)

    # Replace kpoint_path by bands_kpoints
    kpoint_path = inputs.pop("kpoint_path")
    point_coords = kpoint_path["point_coords"]
    labels = []
    kpoints = []
    for label, coords in point_coords.items():
        labels.append(label)
        kpoints.append(coords)
    label_numbers = list(range(len(labels)))
    bands_kpoints = orm.KpointsData()
    bands_kpoints.set_kpoints(kpoints)
    bands_kpoints.base.attributes.set("labels", labels)
    bands_kpoints.base.attributes.set("label_numbers", label_numbers)
    inputs["bands_kpoints"] = bands_kpoints

    generate_calc_job(
        folder=fixture_sandbox, entry_point_name=ENTRY_POINT_NAME, inputs=inputs
    )

    with fixture_sandbox.open(f"{seedname}.win") as handle:
        input_written = handle.read()

    file_regression.check(input_written, encoding="utf-8", extension=".win")
