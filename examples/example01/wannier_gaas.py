#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
import sys

from aiida.plugins import DataFactory
from aiida.common import exceptions as exc
from aiida.engine import run, submit
from aiida.orm import load_node, Code
from aiida_wannier90.orbitals import generate_projections

Dict = DataFactory('dict')
StructureData = DataFactory('structure')
KpointsData = DataFactory('array.kpoints')

try:
    send_param = sys.argv[1]
    if send_param == "--dont-send":
        submit_test = True
    elif send_param == "--send":
        submit_test = False
    else:
        raise IndexError
except IndexError:
    print(("The first parameter can only be either "
           "--send or --dont-send"),
          file=sys.stderr)
    sys.exit(1)

try:
    codename = sys.argv[2]
except IndexError:
    print(("Must provide as second parameter the main code"), file=sys.stderr)
    sys.exit(1)

# We should catch exceptions also here...
code = Code.get_from_string(codename)
if code.get_input_plugin_name() != 'wannier90.wannier90':
    print(("Code with pk={} is not a Wannier90 code".format(code.pk)),
          file=sys.stderr)
    sys.exit(1)

do_preprocess = False
try:
    input_mode = sys.argv[3]
    if input_mode == "local":
        local_input = True
    elif input_mode == "remote":
        local_input = False
    elif input_mode == "preprocess":
        do_preprocess = True
    else:
        raise IndexError
except IndexError:
    print((
        'Must provide as third parameter the input mode ("local" for a FolderData with the .mmn, "remote" for a RemoteData \
        with the .mmn, or "preprocess" for the preprocess step)'
    ),
          file=sys.stderr)
    sys.exit(1)

if not do_preprocess:
    try:
        input_folder_pk = int(sys.argv[4])
        input_folder = load_node(input_folder_pk)
    except (IndexError, ValueError):
        print((
            "Must provide as third parameter the pk of the {} input folder node"
            .format('local' if local_input else 'remote')
        ),
              file=sys.stderr)
        print((
            "If you don't have it, run the script 'create_local_input_folder.py' and then use that pk with the 'local' option"
        ),
              file=sys.stderr)
        sys.exit(1)
    except exc.NotExistent:
        print(("A node with pk={} does not exist".format(input_folder_pk)),
              file=sys.stderr)
        sys.exit(1)

###############SETTING UP WANNIER PARAMETERS ###################################

exclude_bands = [1, 2, 3, 4, 5]
parameter = Dict(
    dict={
        'bands_plot': False,
        'num_iter': 300,
        'guiding_centres': True,
        'num_wann': 4,
        'exclude_bands': exclude_bands,
        # 'wannier_plot':True,
        # 'wannier_plot_list':[1]
    }
)

# in angstrom; it was 5.367 * 2 bohr; this is the lattice parameter
a = 5.68018817933178
structure = StructureData(
    cell=[[-a / 2., 0, a / 2.], [0, a / 2., a / 2.], [-a / 2., a / 2., 0]]
)
structure.append_atom(symbols=['Ga'], position=(0., 0., 0.))
structure.append_atom(symbols=['As'], position=(-a / 4., a / 4., a / 4.))

kpoints = KpointsData()
kpoints.set_kpoints_mesh([2, 2, 2])

kpoint_path = Dict(
    dict={
        'point_coords': {
            'G': [0.0, 0.0, 0.0],
            'K': [0.375, 0.375, 0.75],
            'L': [0.5, 0.5, 0.5],
            'U': [0.625, 0.25, 0.625],
            'W': [0.5, 0.25, 0.75],
            'X': [0.5, 0.0, 0.5]
        },
        'path': [('G', 'X'), ('X', 'W'), ('W', 'K'), ('K', 'G'), ('G', 'L'),
                 ('L', 'U'), ('U', 'W'), ('W', 'L'), ('L', 'K'), ('U', 'X')]
    }
)

builder = code.get_builder()
builder.metadata.options.max_wallclock_seconds = 30 * 60  # 30 min
builder.metadata.options.resources = {"num_machines": 1}

#Two methods to define projections are available
#Method 1
projections = generate_projections(
    dict(
        position_cart=(1, 2, 0.5),
        radial=2,
        ang_mtm_l=2,
        ang_mtm_mr=5,
        spin=None,
        #zona=1.1,
        zaxis=(0, 1, 0),
        xaxis=(0, 0, 1),
        spin_axis=None
    ),
    structure=structure
)

## Method 1bis, when you want to complete missing orbitals with random ones
## This converts instead the 'projections' OrbitalData object to a list of strings, and passes
## directly to Wannier90. DISCOURAGED: better to pass the OrbitalData object,
## that contains 'parsed' information and is easier to query, and set
## random_projections = True in the input 'settings' Dict node.
#from aiida_wannier90.io._write_win import _format_all_projections
#projections_list = List()
#projections_list.extend(_format_all_projections(projections, random_projections=True))
#projections = projections_list

## Method 2
#projections = List()
#projections.extend(['As:s','As:p'])
#projections.extend(['random','As:s'])

if not do_preprocess:
    if local_input:
        builder.local_input_folder = input_folder
    else:
        builder.remote_input_folder = input_folder
builder.structure = structure
builder.projections = projections
builder.parameters = parameter
builder.kpoints = kpoints
builder.kpoint_path = kpoint_path

# settings that can only be enabled if parent is nscf
settings_dict = {'seedname': 'gaas', 'random_projections': True}
if do_preprocess:
    settings_dict.update({'postproc_setup': True}
                         )  # for setup calculation (preprocessing, -pp flag)
if settings_dict:
    settings = Dict(dict=settings_dict)
    builder.settings = settings

if submit_test:
    builder.metadata.dry_run = True
    builder.metadata.store_provenance = False
    run(builder)
    print("dry-run executed, submit files in subfolder")
else:
    calc = submit(builder)
    print(
        "submitted calculation; calc=Calculation(uuid='{}') # ID={}".format(
            calc.uuid, calc.pk
        )
    )
