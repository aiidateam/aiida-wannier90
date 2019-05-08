#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
import os

import pytest
import pymatgen

PROJECTIONS_DICT={'kind_name': 'As',
                  'ang_mtm_name': 'sp3'},
SEEDNAME='aiida' 

def create_gaas_win_params():
    from aiida.plugins import DataFactory, CalculationFactory
    from aiida_wannier90.orbitals import generate_projections
    from aiida.tools import get_kpoints_path

    res = dict()

    a = 5.367 * pymatgen.core.units.bohr_to_ang
    structure_pmg = pymatgen.Structure(
        lattice=[[-a, 0, a], [0, a, a], [-a, a, 0]],
        species=['Ga', 'As'],
        coords=[[0] * 3, [0.25] * 3]
    )
    structure = DataFactory('structure')()
    structure.set_pymatgen_structure(structure_pmg)
    res['structure'] = structure

    res['projections'] = generate_projections(
        PROJECTIONS_DICT, structure=structure
    )

    KpointsData = DataFactory('array.kpoints')
    kpoints = KpointsData()
    kpoints.set_kpoints_mesh([2, 2, 2])
    res['kpoints'] = kpoints

    kpoint_path = get_kpoints_path(structure)['parameters']
    res['kpoint_path'] = kpoint_path

    res['parameters'] = DataFactory('dict')(
        dict=dict(num_wann=4, num_iter=12, wvfn_formatted=True)
    )
    return res


@pytest.fixture
def create_gaas_calc(
    get_process_inputs, sample, configure, create_gaas_win_params
):
    def inner():
        from aiida.plugins import DataFactory, CalculationFactory
        from aiida_wannier90.orbitals import generate_projections

        process, inputs = get_process_inputs(
            calculation_string='wannier90.wannier90', code_string='wannier90'
        )
        inputs.update(
            create_gaas_win_params(PROJECTIONS_DICT=PROJECTIONS_DICT)
        )

        FolderData = DataFactory('folder')
        local_input_folder = FolderData()
        sample_folder = sample('gaas')
        exclude_list = ['gaas.win']
        for path in os.listdir(sample_folder):
            if path in exclude_list:
                continue
            abs_path = os.path.join(sample_folder, path)
            local_input_folder.add_path(
                abs_path, path.replace('gaas', SEEDNAME)
            )
        inputs.local_input_folder = local_input_folder

        if SEEDNAME != 'aiida':
            inputs.settings = DataFactory('dict')(
                dict=dict(SEEDNAME=SEEDNAME)
            )

        return process, inputs

    return inner
