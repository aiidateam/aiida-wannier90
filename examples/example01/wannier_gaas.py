#!/usr/bin/env runaiida
################################################################################
# Copyright (c), AiiDA team and individual contributors.                       #
#  All rights reserved.                                                        #
# This file is part of the AiiDA-wannier90 code.                               #
#                                                                              #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-wannier90 #
# For further information on the license, see the LICENSE.txt file             #
################################################################################
"""Run a Wannier90 calculation on GaAs."""
# pylint: disable=redefined-outer-name

import sys

from aiida.common import exceptions as exc
from aiida.engine import run, submit
from aiida.orm import Code, load_node
from aiida.plugins import DataFactory

from aiida_wannier90.orbitals import generate_projections

Dict = DataFactory("core.dict")
StructureData = DataFactory("core.structure")
KpointsData = DataFactory("core.array.kpoints")
RemoteData = DataFactory("core.remote")
FolderData = DataFactory("core.folder")


def create_builder(code, input_folder=None, submit_test=False):
    """Return a dictionary of inputs to be passed to `run` or `submit`.

    :param code: a `wannier90.wannier90` code.
    :param input_folder: an input folder. It can be `None`, in which case
        this function assumes this is a pre-process step. Or it can be either
        a RemoteData node, or a FolderData local node.
    :param submit_test: if True, runs a submit test (dry run, and with store_provenance=False)
    """
    exclude_bands = [1, 2, 3, 4, 5]
    parameter = Dict(
        {
            "bands_plot": False,
            "num_iter": 300,
            "guiding_centres": True,
            "num_wann": 4,
            "exclude_bands": exclude_bands,
            # 'wannier_plot':True,
            # 'wannier_plot_list':[1]
        }
    )

    # in angstrom; it was 5.367 * 2 bohr; this is the lattice parameter
    a = 5.68018817933178
    structure = StructureData(
        cell=[[-a / 2.0, 0, a / 2.0], [0, a / 2.0, a / 2.0], [-a / 2.0, a / 2.0, 0]]
    )
    structure.append_atom(symbols=["Ga"], position=(0.0, 0.0, 0.0))
    structure.append_atom(symbols=["As"], position=(-a / 4.0, a / 4.0, a / 4.0))

    kpoints = KpointsData()
    kpoints.set_kpoints_mesh([2, 2, 2])

    kpoint_path = Dict(
        {
            "point_coords": {
                "G": [0.0, 0.0, 0.0],
                "K": [0.375, 0.375, 0.75],
                "L": [0.5, 0.5, 0.5],
                "U": [0.625, 0.25, 0.625],
                "W": [0.5, 0.25, 0.75],
                "X": [0.5, 0.0, 0.5],
            },
            "path": [
                ("G", "X"),
                ("X", "W"),
                ("W", "K"),
                ("K", "G"),
                ("G", "L"),
                ("L", "U"),
                ("U", "W"),
                ("W", "L"),
                ("L", "K"),
                ("U", "X"),
            ],
        }
    )

    builder = code.get_builder()
    builder.metadata.options.max_wallclock_seconds = 30 * 60  # 30 min
    builder.metadata.options.resources = {"num_machines": 1}

    # Two methods to define projections are available
    # Method 1
    projections = generate_projections(
        dict(
            position_cart=(1, 2, 0.5),
            radial=2,
            ang_mtm_l_list=2,
            ang_mtm_mr_list=5,
            spin=None,
            # zona=1.1,
            zaxis=(0, 1, 0),
            xaxis=(0, 0, 1),
            spin_axis=None,
        ),
        structure=structure,
    )

    ## Method 1bis, when you want to complete missing orbitals with random ones
    ## This converts instead the 'projections' OrbitalData object to a list of strings, and passes
    ## directly to Wannier90. DISCOURAGED: better to pass the OrbitalData object,
    ## that contains 'parsed' information and is easier to query, and set
    ## random_projections = True in the input 'settings' Dict node.
    # from aiida_wannier90.io._write_win import _format_all_projections
    # projections_list = List()
    # projections_list.extend(_format_all_projections(projections, random_projections=True))
    # projections = projections_list

    ## Method 2
    # projections = List()
    # projections.extend(['As:s','As:p'])
    # projections.extend(['random','As:s'])

    do_preprocess = input_folder is None

    if not do_preprocess:
        if isinstance(input_folder, FolderData):
            builder.local_input_folder = input_folder
        elif isinstance(input_folder, RemoteData):
            builder.remote_input_folder = input_folder
        else:
            raise TypeError(
                "Unknown type for the input_folder, it can only be a RemoteData or a FolderData"
            )
    builder.structure = structure
    builder.projections = projections
    builder.parameters = parameter
    builder.kpoints = kpoints
    builder.kpoint_path = kpoint_path

    settings_dict = {"random_projections": True}
    if do_preprocess:
        settings_dict.update(
            {"postproc_setup": True}
        )  # for setup calculation (preprocessing, -pp flag)
    builder.settings = Dict(settings_dict)

    if submit_test:
        builder.metadata.dry_run = True
        builder.metadata.store_provenance = False

    return builder


if __name__ == "__main__":  # noqa
    try:
        send_param = sys.argv[1]
        if send_param == "--dont-send":
            submit_test = True
        elif send_param == "--send":
            submit_test = False
        else:
            raise IndexError
    except IndexError:
        print(
            "The first parameter can only be either --send or --dont-send",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        codename = sys.argv[2]
    except IndexError:
        print("Must provide as second parameter the main code", file=sys.stderr)
        sys.exit(1)

    # We should catch exceptions also here...
    code = Code.get_from_string(codename)
    if code.get_input_plugin_name() != "wannier90.wannier90":
        print(f"Code with pk={code.pk} is not a Wannier90 code", file=sys.stderr)
        sys.exit(1)

    do_preprocess = False
    try:
        input_mode = sys.argv[3]
        if input_mode == "main":
            local_input = False
        elif input_mode == "preprocess":
            do_preprocess = True
        else:
            raise IndexError
    except IndexError:
        print(
            (
                'Must provide as third parameter the run mode ("main" for a main Wannier90 run, '
                "requiring an additional parameter with either a FolderData or a RemoteData with "
                'the .mmn/.amn files; or "preprocess" for the preprocess step)'
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    input_folder = None
    if not do_preprocess:
        try:
            input_folder_pk = int(sys.argv[4])
            input_folder = load_node(input_folder_pk)
        except (IndexError, ValueError):
            print(
                "Must provide as fourth parameter the pk of the FolderData/RemoteData input folder node",
                file=sys.stderr,
            )
            print(
                "If you don't have it, run the script 'create_local_input_folder.py'.",
                file=sys.stderr,
            )
            sys.exit(1)
        except exc.NotExistent:
            print(f"A node with pk={input_folder_pk} does not exist", file=sys.stderr)
            sys.exit(1)

    builder = create_builder(
        code=code, input_folder=input_folder, submit_test=submit_test
    )

    if submit_test:
        run(builder)
        print("dry-run executed, submit files in subfolder")
    else:
        calc = submit(builder)
        print(
            f"submitted calculation; calc=Calculation(uuid='{calc.uuid}') # ID={calc.pk}"
        )
