# -*- coding: utf-8 -*-

import os

import pytest
import pymatgen

@pytest.fixture
def create_gaas_calc(get_process_inputs, sample, configure):
    def inner(projections_dict={'kind_name': 'As', 'ang_mtm_name': 'sp3'}):
        from aiida.orm import DataFactory, CalculationFactory
        from aiida_wannier90.orbitals import generate_projections

        process, inputs = get_process_inputs(
            calculation_string='wannier90.wannier90',
            code_string='wannier90'
        )

        FolderData = DataFactory('folder')
        local_input_folder = FolderData()
        sample_folder = sample('gaas')
        exclude_list = ['gaas.win']
        for path in os.listdir(sample_folder):
            if path in exclude_list:
                continue
            abs_path = os.path.join(sample_folder, path)
            local_input_folder.add_path(abs_path, path.replace('gaas', 'aiida'))
        inputs.local_input_folder = local_input_folder

        a = 5.367 * pymatgen.core.units.bohr_to_ang
        structure_pmg = pymatgen.Structure(
            lattice=[[-a, 0, a], [0, a, a], [-a, a, 0]],
            species=['Ga', 'As'],
            coords=[[0] * 3, [0.25] * 3]
        )
        structure = DataFactory('structure')()
        structure.set_pymatgen_structure(structure_pmg)
        inputs.structure = structure

        inputs.projections = generate_projections(
            projections_dict,
            structure=structure
        )

        KpointsData = DataFactory('array.kpoints')
        kpoints = KpointsData()
        kpoints.set_kpoints_mesh([2, 2, 2])
        inputs.kpoints = kpoints

        kpoints_path = KpointsData()
        kpoints_path.set_cell_from_structure(structure)
        kpoints_path.set_kpoints_path()
        inputs.kpoints_path = kpoints_path

        inputs.parameters = DataFactory('parameter')(dict=dict(
            num_wann=4,
            num_iter=12,
            wvfn_formatted=True
        ))
        return process, inputs
    return inner

def test_local_input(create_gaas_calc, configure_with_daemon):
    from aiida.work.run import run
    process, inputs = create_gaas_calc()
    output = run(process, **inputs)
    assert all(key in output for key in ['retrieved', 'output_parameters'])

def test_duplicate_exclude_bands(create_gaas_calc, configure_with_daemon):
    from aiida.work.run import run
    from aiida.orm import DataFactory
    process, inputs = create_gaas_calc(
        projections_dict={'kind_name': 'As', 'ang_mtm_name': 's'}
    )
    inputs.parameters = DataFactory('parameter')(dict=dict(
        num_wann=1,
        num_iter=12,
        wvfn_formatted=True,
        exclude_bands=[1] * 2 + [2, 3]
    ))
    output = run(process, **inputs)
    assert all(key in output for key in ['retrieved', 'output_parameters'])
