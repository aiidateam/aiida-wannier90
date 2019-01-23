#!/usr/bin/env runaiida
# -*- coding: utf-8 -*-

import argparse
from aiida.common.exceptions import NotExistent
from aiida.orm.data.base import Str
from aiida.orm.data.parameter import ParameterData
from aiida.orm.data.structure import StructureData
from aiida.orm.data.array.kpoints import KpointsData
from aiida.work.run import run, submit
from aiida_wannier90.workflows.W90 import SimpleWannier90WorkChain
from aiida.orm.data.base import List
scf_parameters = ParameterData(
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
nscf_parameters = ParameterData(dict={
    'SYSTEM': {
        'nbnd': 10,
    },
})
scf_settings = ParameterData(dict={})
max_wallclock_seconds = 60 * 30
scf_options = ParameterData(
    dict={
        'resources': {
            'num_machines': 1,
            'tot_num_mpiprocs': 28,
        },
        'max_wallclock_seconds': max_wallclock_seconds,
    }
)
pw2wannier90_options = ParameterData(
    dict={
        'resources': {
            'num_machines': 1,
            'tot_num_mpiprocs': 28,
        },
        'max_wallclock_seconds': 60 * 60 * 10,
    }
)
wannier90_parameters = ParameterData(
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

print 'launched WorkChain pk {}'.format(wc.pid)
