#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
import sys

from aiida.plugins import DataFactory
from aiida.common import exceptions as exc
from aiida.engine import run, submit
from aiida.orm import load_node, Code

Dict = DataFactory('dict')


try:
    send_param = sys.argv[1]
    if send_param == "--dont-send":
        submit_test = True
    elif send_param == "--send":
        submit_test = False
    else:
        raise IndexError
except IndexError:
    print((
        "The first parameter can only be either "
        "--send or --dont-send"
    ), file=sys.stderr)
    sys.exit(1)


try:
    input_nnpk_pk = int(sys.argv[2])
    input_nnpk = load_node(input_nnpk_pk)
except (IndexError, ValueError):
    print("Must provide as second parameter the pk of the singledata nnpk node", file=sys.stderr)
    sys.exit(1)
except exc.NotExistent:
    print((
        "A node with pk={} does not exist".format(input_nnpk_pk)), file=sys.stderr)
    sys.exit(1)

try:
    parent_folder_pk = int(sys.argv[3])
    parent_folder = load_node(parent_folder_pk)
except (IndexError, ValueError):
    print("Must provide as third parameter the pk of the parent folder RemoteData node", file=sys.stderr)
    sys.exit(1)
except exc.NotExistent:
    print((
        "A node with pk={} does not exist".format(parent_folder_pk)), file=sys.stderr)
    sys.exit(1)

try:
    codename = sys.argv[4]
except IndexError:
    print(("Must provide as fourth parameter the main code"), file=sys.stderr)
    sys.exit(1)

# We should catch exceptions also here...
code = Code.get_from_string(codename)
if code.get_input_plugin_name() != 'quantumespresso.pw2wannier90':
    print((
        "Code with pk={} is not a pw2wan code".format(code.pk)), file=sys.stderr)
    sys.exit(1)


###############SETTING UP WANNIER PARAMETERS ###################################

#exclude_bands = []
parameter = Dict(
    dict={
        'INPUTPP': {
            'write_amn': True,
            'write_mmn': True,
            'write_eig': True,
        }
    }
)

builder = code.get_builder()
builder.metadata.options.max_wallclock_seconds = 30 * 60 # 30 min
builder.metadata.options.resources = {"num_machines": 1}
builder.nnkp_file = input_nnpk
builder.parameters = parameter
builder.parent_folder = parent_folder

settings_dict = {}
#settings_dict.update({})
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
    print("submitted calculation; calc=Calculation(uuid='{}') # ID={}".format(
        calc.uuid, calc.pk
    ))
