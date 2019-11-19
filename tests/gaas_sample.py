#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
import os

import pytest

PROJECTIONS_DICT = {'kind_name': 'As', 'ang_mtm_name': 'sp3'}


@pytest.fixture
def create_gaas_win_params(configure):
    def inner(projections_dict=PROJECTIONS_DICT):
        from aiida.tools import get_kpoints_path
        from aiida.orm import KpointsData, StructureData, Dict
        from aiida_wannier90.orbitals import generate_projections

        res = dict()

        a = 2.84
        structure = StructureData(cell=[[-a, 0, a], [0, a, a], [-a, a, 0]])

        structure.append_atom(symbols='Ga', position=[0, 0, 0])
        structure.append_atom(
            symbols='As', position=[-0.5 * a, 0.5 * a, 0.5 * a]
        )

        res['structure'] = structure

        res['projections'] = generate_projections(
            projections_dict, structure=structure
        )

        kpoints = KpointsData()
        kpoints.set_kpoints_mesh([2, 2, 2])
        res['kpoints'] = kpoints

        # Using 'legacy' method so that we don't have a depenendency on seekpath.
        res['kpoint_path'] = get_kpoints_path(structure,
                                              method='legacy')['parameters']

        res['parameters'] = Dict(
            dict=dict(num_wann=4, num_iter=12, wvfn_formatted=True)
        )
        return res

    return inner


@pytest.fixture
def create_gaas_calc(
    get_process_builder, sample, configure, create_gaas_win_params
):
    def inner(projections_dict=PROJECTIONS_DICT, seedname='aiida'):
        from aiida.orm import FolderData, Dict

        builder = get_process_builder(
            calculation_string='wannier90.wannier90', code_string='wannier90'
        )
        builder.update(
            create_gaas_win_params(projections_dict=projections_dict)
        )

        local_input_folder = FolderData()
        sample_folder = sample('gaas')
        exclude_list = ['gaas.win']
        for path in os.listdir(sample_folder):
            if path in exclude_list:
                continue
            abs_path = os.path.join(sample_folder, path)
            local_input_folder.put_object_from_file(
                abs_path, path.replace('gaas', seedname)
            )
        builder.local_input_folder = local_input_folder

        if seedname != 'aiida':
            builder.metadata.options['seedname'] = seedname

        return builder

    return inner
