#!/usr/bin/env python
# -*- coding: utf-8 -*-
################################################################################
# Copyright (c), AiiDA team and individual contributors.                       #
#  All rights reserved.                                                        #
# This file is part of the AiiDA-wannier90 code.                               #
#                                                                              #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-wannier90 #
# For further information on the license, see the LICENSE.txt file             #
################################################################################

import os

import click

from aiida.engine import run
from aiida.orm import Str, Dict, Group
from aiida.orm.nodes.data import upf
from aiida.plugins import DataFactory
from aiida.cmdline.params import options, types
from aiida.cmdline.utils import decorators

from aiida_wannier90.orbitals import generate_projections
from aiida_wannier90.workflows.minimal import MinimalW90WorkChain


def get_static_inputs():
    """Return a dictionary of static inputs for this example.

    Other dynamic inputs depending on the user configuration (e.g., code names)
    are generated outside."""
    ####Input needed to run the workchain
    KpointsData = DataFactory('array.kpoints')
    StructureData = DataFactory('structure')

    # GaAs structure
    a = 5.68018817933178  # angstrom
    structure = StructureData(
        cell=[[-a / 2., 0, a / 2.], [0, a / 2., a / 2.], [-a / 2., a / 2., 0]]
    )
    structure.append_atom(symbols=['Ga'], position=(0., 0., 0.))
    structure.append_atom(symbols=['As'], position=(-a / 4., a / 4., a / 4.))

    kpoints_scf = KpointsData()
    # 4x4x4 k-points mesh for the SCF
    kpoints_scf_mesh = 4
    kpoints_scf.set_kpoints_mesh([
        kpoints_scf_mesh, kpoints_scf_mesh, kpoints_scf_mesh
    ])

    kpoints_nscf = KpointsData()
    # 10x10x10 k-points mesh for the NSCF/Wannier90 calculations
    kpoints_nscf_mesh = 10
    kpoints_nscf.set_kpoints_mesh([
        kpoints_nscf_mesh, kpoints_nscf_mesh, kpoints_nscf_mesh
    ])

    # k-points path for the band structure
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
            'path': [('G', 'X'), ('X', 'U'), ('K',
                                              'G'), ('G',
                                                     'L'), ('L',
                                                            'W'), ('W', 'X')]
        }
    )
    # sp^3 projections, centered on As
    projections = generate_projections(
        dict(
            position_cart=(-a / 4., a / 4., a / 4.),
            ang_mtm_l=-3,
            spin=None,
            spin_axis=None
        ),
        structure=structure
    )

    return {
        'structure': structure,
        'kpoints_scf': kpoints_scf,
        'kpoints_nscf': kpoints_nscf,
        'kpoint_path': kpoint_path,
        'projections': projections
    }


def get_or_create_pseudo_family():
    """Check if the pseudos are already in the DB, create them otherwise.

    Then create (if needed) also a pseudopotential family including it (or pick any already existing)
    and return the name.
    If the family does not exist, it will be created with name 'GaAs-Wannier-example' and a possible prefix.
    """
    UpfData = DataFactory('upf')

    # Get absolute filenames
    pseudos_filenames = [
        'As.pbe-n-rrkjus_psl.0.2.UPF', 'Ga.pbe-dn-kjpaw_psl.1.0.0.UPF'
    ]
    this_script_folder = os.path.dirname(os.path.realpath(__file__))
    pseudos_full_path = [
        os.path.join(this_script_folder, 'pseudos', filename)
        for filename in pseudos_filenames
    ]

    # Will collect pseudopotential nodes that either were created or were found
    pseudo_nodes = []

    # set of family names that include both pseudos
    family_names = None
    # Create the UpfData node if there is no pseudo with that MD5, otherwise reuse it
    # Also, get a set of all family names that include both pseudos
    for fname in pseudos_full_path:
        pseudo_node, _ = UpfData.get_or_create(
            fname, use_first=True, store_upf=True
        )
        pseudo_nodes.append(pseudo_node)
        if family_names is None:
            family_names = set(pseudo_node.get_upf_family_names())
        else:
            family_names = family_names.intersection(
                pseudo_node.get_upf_family_names()
            )

    if family_names:
        # return any of the available family names (in practice, the first in alphabetical order)
        family_name = sorted(family_names)[0]
        print("Using existing UPF group '{}'".format(family_name))
        return family_name

    # no family found: I create one and return its name
    family_name_prefix = 'GaAs-Wannier-example'

    # Try to create the group
    family_name = family_name_prefix
    group, group_created = Group.objects.get_or_create(
        label=family_name,
        type_string=upf.UPFGROUP_TYPE  # pylint: disable=no-member # TODO: fix
    )

    # continue trying creating the group if the previous one existed
    safe_counter = 0
    while not group_created:
        safe_counter += 1
        if safe_counter > 10:
            raise ValueError("Too many groups existing, stopping...")

        family_name = "{}-{}".format(family_name_prefix, safe_counter)
        group, group_created = Group.objects.get_or_create(
            label=family_name,
            type_string=upf.UPFGROUP_TYPE  # pylint: disable=no-member # TODO: fix
        )

    # Update description of the group
    group.description = "Automatic group created by the aiida-Wannier90 minimal workflow example"
    # Put the pseudos in the group
    group.add_nodes(pseudo_nodes)

    print(
        "Created new UPF group '{}' with nodes {}".format(
            family_name, ", ".join(str(node.pk) for node in pseudo_nodes)
        )
    )
    return family_name


PWCODE = options.OverridableOption(
    '-s',
    '--pwscf-code',
    required=True,
    type=types.CodeParamType(entry_point='quantumespresso.pw'),
    help="The Quantum ESPRESSO pw.x (PWscf) code"
)
PW2WANCODE = options.OverridableOption(
    '-p',
    '--pw2wannier90-code',
    required=True,
    type=types.CodeParamType(entry_point='quantumespresso.pw2wannier90'),
    help="The Quantum ESPRESSO pw2wannier90.x code"
)

WANCODE = options.OverridableOption(
    '-w',
    '--wannier-code',
    required=True,
    type=types.CodeParamType(entry_point='wannier90.wannier90'),
    help="The Wannier90 wannier90.x code"
)


@click.command()
@click.help_option('-h', '--help')
@PWCODE()
@PW2WANCODE()
@WANCODE()
@decorators.with_dbenv()
def run_wf(pwscf_code, pw2wannier90_code, wannier_code):
    """Run a simple workflow running Quantum ESPRESSO+wannier90 for GaAs."""
    static_inputs = get_static_inputs()

    pseudo_family_name = get_or_create_pseudo_family()

    # Run the workflow
    run(
        MinimalW90WorkChain,
        pw_code=pwscf_code,  #load_code('pw-6.4-release@localhost'),
        pseudo_family=Str(pseudo_family_name
                          ),  #Str('SSSP_efficiency_pseudos'),
        wannier_code=wannier_code,  #load_code('wannier90-3-desktop@localhost'),
        pw2wannier90_code=
        pw2wannier90_code,  #load_code('pw2wannier90-6.4-release@localhost'),
        **static_inputs
    )


if __name__ == "__main__":
    run_wf()  #  pylint: disable=no-value-for-parameter
