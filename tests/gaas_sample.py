#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import pytest
import pymatgen

@pytest.fixture
def create_gaas_win_params(configure):
    def inner(projections_dict={'kind_name': 'As', 'ang_mtm_name': 'sp3'}):
        from aiida.orm import DataFactory, CalculationFactory
        from aiida_wannier90.orbitals import generate_projections

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
            projections_dict,
            structure=structure
        )

        KpointsData = DataFactory('array.kpoints')
        kpoints = KpointsData()
        kpoints.set_kpoints_mesh([2, 2, 2])
        res['kpoints'] = kpoints

        kpoint_path = KpointsData()
        kpoint_path.set_cell_from_structure(structure)
        kpoint_path.set_kpoints_path()
        res['kpoint_path'] = kpoint_path

        res['parameters'] = DataFactory('parameter')(dict=dict(
            num_wann=4,
            num_iter=12,
            wvfn_formatted=True
        ))
        return res
    return inner

@pytest.fixture
def create_gaas_calc(get_process_inputs, sample, configure, create_gaas_win_params):
    def inner(projections_dict={'kind_name': 'As', 'ang_mtm_name': 'sp3'}, seedname='aiida'):
        from aiida.orm import DataFactory, CalculationFactory
        from aiida_wannier90.orbitals import generate_projections

        process, inputs = get_process_inputs(
            calculation_string='wannier90.wannier90',
            code_string='wannier90'
        )
        inputs.update(create_gaas_win_params(projections_dict=projections_dict))

        FolderData = DataFactory('folder')
        local_input_folder = FolderData()
        sample_folder = sample('gaas')
        exclude_list = ['gaas.win']
        for path in os.listdir(sample_folder):
            if path in exclude_list:
                continue
            abs_path = os.path.join(sample_folder, path)
            local_input_folder.add_path(abs_path, path.replace('gaas', seedname))
        inputs.local_input_folder = local_input_folder
        if seedname != 'aiida':
            inputs.settings = DataFactory('parameter')(dict=dict(seedname=seedname))

        return process, inputs
    return inner
