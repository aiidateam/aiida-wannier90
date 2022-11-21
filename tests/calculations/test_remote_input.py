################################################################################
# Copyright (c), AiiDA team and individual contributors.                       #
#  All rights reserved.                                                        #
# This file is part of the AiiDA-wannier90 code.                               #
#                                                                              #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-wannier90 #
# For further information on the license, see the LICENSE.txt file             #
################################################################################
"""Test the `Wannier90Calculation` with remote data as input."""
# pylint: disable=redefined-outer-name

import os

import pytest

from aiida.common import datastructures

ENTRY_POINT_NAME = "wannier90.wannier90"


@pytest.fixture()
def generate_common_inputs_gaas_remotedata(
    fixture_code, generate_win_params_gaas, fixture_remotedata
):
    """Generate the inputs for a `Wannier90Calculation` with remote input folder."""

    def _generate_common_inputs_gaas():
        inputs = dict(
            code=fixture_code(ENTRY_POINT_NAME),
            metadata={
                "options": {
                    "resources": {"num_machines": 1},
                    "max_wallclock_seconds": 3600,
                    "withmpi": False,
                }
            },
            remote_input_folder=fixture_remotedata,
            **generate_win_params_gaas(),
        )

        return inputs

    return _generate_common_inputs_gaas


def test_default_remote(
    fixture_sandbox,
    generate_calc_job,
    generate_common_inputs_gaas_remotedata,
    file_regression,
):
    """Test a default `Wannier90Calculation` with remote input folder."""
    seedname = "aiida"  # This is hardcoded in the generate_common_inputs_remotedata
    inputs = generate_common_inputs_gaas_remotedata()
    if seedname is not None:
        inputs["metadata"]["options"]["input_filename"] = f"{seedname}.win"
        inputs["metadata"]["options"]["output_filename"] = f"{seedname}.wout"

    calc_info = generate_calc_job(
        folder=fixture_sandbox, entry_point_name=ENTRY_POINT_NAME, inputs=inputs
    )

    cmdline_params = [seedname]
    local_copy_list = []
    remote_symlink_list_files = [
        "aiida.mmn",
        "aiida.amn",
        "*.eig",
        "*.spn",
        "*.uHu",
        "*_htB.dat",
        "*_htL.dat",
        "*_htR.dat",
        "*_htC.dat",
        "*_htLC.dat",
        "*_htCR.dat",
        "*.unkg",
    ]
    remote_copy_list_files = ["*.chk"]
    retrieve_list = [
        seedname + suffix
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
    assert sorted(
        os.path.basename(elem[1]) for elem in calc_info.remote_symlink_list
    ) == sorted(remote_symlink_list_files)
    assert sorted(
        os.path.basename(elem[1]) for elem in calc_info.remote_copy_list
    ) == sorted(remote_copy_list_files)

    with fixture_sandbox.open(f"{seedname}.win") as handle:
        input_written = handle.read()

    # Checks on the files written to the sandbox folder as raw input
    assert sorted(fixture_sandbox.get_content_list()) == sorted([f"{seedname}.win"])
    file_regression.check(input_written, encoding="utf-8", extension=".win")


def test_unk_symlink(
    fixture_sandbox,
    generate_calc_job,
    generate_common_inputs_gaas_remotedata,
    file_regression,
):
    """Test a `Wannier90Calculation` for UNK files symlinks."""
    from aiida.orm import Dict

    seedname = "aiida"  # This is hardcoded in the generate_common_inputs_remotedata
    inputs = generate_common_inputs_gaas_remotedata()
    if seedname is not None:
        inputs["metadata"]["options"]["input_filename"] = f"{seedname}.win"
        inputs["metadata"]["options"]["output_filename"] = f"{seedname}.wout"

    parameters = inputs["parameters"].get_dict()
    parameters["wannier_plot"] = True
    inputs["parameters"] = Dict(parameters)

    calc_info = generate_calc_job(
        folder=fixture_sandbox, entry_point_name=ENTRY_POINT_NAME, inputs=inputs
    )

    cmdline_params = [seedname]
    local_copy_list = []
    remote_symlink_list_files = [
        "UNK*",
        "aiida.mmn",
        "aiida.amn",
        "*.eig",
        "*.spn",
        "*.uHu",
        "*_htB.dat",
        "*_htL.dat",
        "*_htR.dat",
        "*_htC.dat",
        "*_htLC.dat",
        "*_htCR.dat",
        "*.unkg",
    ]
    remote_copy_list_files = ["*.chk"]
    retrieve_list = [
        seedname + suffix
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
    assert sorted(
        os.path.basename(elem[1]) for elem in calc_info.remote_symlink_list
    ) == sorted(remote_symlink_list_files)
    assert sorted(
        os.path.basename(elem[1]) for elem in calc_info.remote_copy_list
    ) == sorted(remote_copy_list_files)

    with fixture_sandbox.open(f"{seedname}.win") as handle:
        input_written = handle.read()

    # Checks on the files written to the sandbox folder as raw input
    assert sorted(fixture_sandbox.get_content_list()) == sorted([f"{seedname}.win"])
    file_regression.check(input_written, encoding="utf-8", extension=".win")
