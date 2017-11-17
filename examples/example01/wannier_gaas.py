#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-
import sys
import os
from aiida.orm import DataFactory, CalculationFactory
from aiida.common.example_helpers import test_and_get_code
import pymatgen
from aiida.orm.data.base import List
from aiida_wannier90.orbitals import generate_projections

ParameterData = DataFactory('parameter')
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
    print >> sys.stderr, ("The first parameter can only be either "
                          "--send or --dont-send")
    sys.exit(1)

try:
    input_mode = sys.argv[2]
    if input_mode == "local":
        local_input = True
    elif input_mode == "remote":
        local_input = False
    else:
        raise IndexError
except IndexError:
    print >> sys.stderr, ('Must provide the input mode ("local" or "remote")')
    sys.exit(1)

try:
    input_folder_pk = int(sys.argv[3])
    #calc.use_parent_calculation(parent_calc)
    input_folder = load_node(input_folder_pk)  

except (IndexError, ValueError):
    print >> sys.stderr, ("Must provide as third parameter the pk of the {} input folder node".format(
        'local' if local_input else 'remote'))
    print >> sys.stderr, ("If you don't have it, run the script 'create_local_input_folder.py' and then use that pk with the 'local' option")    
    sys.exit(1)


try:
    codename = sys.argv[4]
except IndexError:
    print >> sys.stderr, ("Must provide as fourth parameter the main code")
    sys.exit(1)



code = test_and_get_code(codename, expected_code_type='wannier90.wannier90')

#parent_calc = Calculation.get_subclass_from_pk(parent_id)



###############SETTING UP WANNIER PARAMETERS ###################################

#exclude_bands = []
parameter = ParameterData(dict={'bands_plot':False,
                                'num_iter': 12,
                                'guiding_centres': True,
                                'num_wann': 4,
                                #'exclude_bands': exclude_bands,
                                # 'wannier_plot':True,
                                # 'wannier_plot_list':[1]
                                })

a = 5.367 * pymatgen.core.units.bohr_to_ang
structure_pmg = pymatgen.Structure(
            lattice=[[-a, 0, a], [0, a, a], [-a, a, 0]],
            species=['Ga', 'As'],
            coords=[[0] * 3, [0.25] * 3]
        )
structure = StructureData()
structure.set_pymatgen_structure(structure_pmg)

kpoints = KpointsData()
kpoints.set_kpoints_mesh([2, 2, 2])

kpoints_path_tmp = KpointsData()
kpoints_path_tmp.set_cell_from_structure(structure)
kpoints_path_tmp.set_kpoints_path()
point_coords, path = kpoints_path_tmp.get_special_points()
kpoints_path = ParameterData(dict = {
        'path': path,
        'point_coords': point_coords,
    })

calc = code.new_calc()
calc.set_max_wallclock_seconds(30*60) # 30 min
calc.set_resources({"num_machines": 1})

#Two methods to define projections are available
#Method 1
projections = generate_projections(dict(position_cart=(1,2,0.5),
                         radial=2,
                         ang_mtm_l=2,
                         ang_mtm_mr=5, spin=None,
                         #zona=1.1,
                         zaxis=(0,1,0),xaxis=(0,0,1), spin_axis=None),structure=structure)

## Method 1bis, when you want to complete missing orbitals with random ones
## This converts instead the 'projections' OrbitalData object to a list of strings, and passes
## directly to Wannier90. DISCOURAGED: better to pass the OrbitalData object,
## that contains 'parsed' information and is easier to query, and set 
## random_projections = True in the input 'settings' ParameterData node.
#from aiida_wannier90.io._write_win import _format_all_projections
#projections_list = List()
#projections_list.extend(_format_all_projections(projections, random_projections=True))
#projections = projections_list

## Method 2
#projections = List()
#projections.extend(['As:s','As:p'])
#projections.extend(['random','As:s'])

if local_input:
    calc.use_local_input_folder(input_folder)
else:
    calc.use_remote_input_folder(input_folder)
calc.use_structure(structure)
calc.use_projections(projections)
calc.use_parameters(parameter)
calc.use_kpoints(kpoints)
calc.use_kpoint_path(kpoints_path)


# settings that can only be enabled if parent is nscf
settings_dict = {'seedname':'gaas','random_projections':True}
# settings_dict.update({'INIT_ONLY':True}) # for setup calculation

if settings_dict:
    settings = ParameterData(dict=settings_dict)
    calc.use_settings(settings)

if submit_test:
    subfolder, script_filename = calc.submit_test()
    print "Test_submit for calculation (uuid='{}')".format(
        calc.uuid)
    print "Submit file in {}".format(os.path.join(
        os.path.relpath(subfolder.abspath),
        script_filename
    ))
else:
    calc.store_all()
    print "created calculation; calc=Calculation(uuid='{}') # ID={}".format(
        calc.uuid, calc.dbnode.pk)
    calc.submit()
    print "submitted calculation; calc=Calculation(uuid='{}') # ID={}".format(
        calc.uuid, calc.dbnode.pk)
