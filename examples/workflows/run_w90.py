#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function
from aiida.orm import Str
from aiida.orm import Dict
from aiida.orm import load_node, Code
from aiida.orm.nodes.data.array.kpoints import KpointsData
from aiida.engine import submit
from aiida_wannier90.workflows.W90 import SimpleWannier90WorkChain  # pylint:  disable=import-error
from aiida.orm import List
scf_parameters = Dict(
    dict={
        'CONTROL': {
            'restart_mode': 'from_scratch',
        },
        'SYSTEM': {
            'ecutwfc': 30.,
            'ecutrho': 240.,
        },
    }
)
nscf_parameters = Dict(dict={
    'SYSTEM': {
        'nbnd': 10,
    },
})
scf_settings = Dict(dict={})
max_wallclock_seconds = 60 * 30
scf_options = Dict(
    dict={
        'resources': {
            'num_machines': 1,
            'tot_num_mpiprocs': 28,
        },
        'max_wallclock_seconds': max_wallclock_seconds,
    }
)
pw2wannier90_options = Dict(
    dict={
        'resources': {
            'num_machines': 1,
            'tot_num_mpiprocs': 28,
        },
        'max_wallclock_seconds': 60 * 60 * 10,
    }
)
wannier90_parameters = Dict(
    dict={
        'bands_plot': False,
        'num_iter': 12,
        'guiding_centres': True,
        'num_wann': 4,
        #'exclude_bands': exclude_bands,
        # 'wannier_plot':True,
        # 'wannier_plot_list':[1]
    }
)
structure = load_node(152)
scf_kpoints = KpointsData()
scf_kpoints.set_kpoints_mesh([4, 4, 4])
nscf_kpoints = KpointsData()
nscf_kpoints.set_kpoints_mesh([4, 4, 4])
projections = List()
projections.extend(['As:s', 'As:p'])
wc = submit(
    SimpleWannier90WorkChain,
    pw_code=Code.get_from_string('pw_6.1@fidis'),
    pw2wannier90_code=Code.get_from_string('pw2wannier90_6.1@fidis'),
    wannier90_code=Code.get_from_string('wannier90_2.1@fidis'),
    #orbital_projections=projections,
    structure=structure,
    pseudo_family=Str('SSSP_efficiency_v0.95'),
    #wannier90_parameters=wannier90_parameters,
    scf={
        'parameters': scf_parameters,
        'kpoints': scf_kpoints,
        'settings': scf_settings,
        'options': scf_options
    },
    nscf={
        'parameters': nscf_parameters,
        'kpoints': nscf_kpoints
    },
    mlwf={
        'projections': projections,
        'parameters': wannier90_parameters
    },
    matrices={},  #'_options':pw2wannier90_options},
    restart_options={
        'scf_workchain': load_node(712),
        'nscf_workchain': load_node(776),
        'mlwf_pp': load_node(1256)
    },
)

print(('launched WorkChain pk {}'.format(wc.pid)))
