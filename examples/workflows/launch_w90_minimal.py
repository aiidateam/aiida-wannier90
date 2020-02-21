from __future__ import absolute_import
from __future__ import print_function
from aiida.plugins import DataFactory
from aiida_wannier90.workflows.minimal import MinimalW90WorkChain
from aiida.orm import load_code, Str, Dict
from aiida.engine import run
from aiida_wannier90.orbitals import generate_projections

####Input needed to run the workchain
UpfData = DataFactory('upf')
KpointsData = DataFactory('array.kpoints')
StructureData = DataFactory('structure')

# GaAs structure
a = 5.68018817933178
structure = StructureData(
    cell=[[-a / 2., 0, a / 2.], [0, a / 2., a / 2.], [-a / 2., a / 2., 0]]
)
structure.append_atom(symbols=['Ga'], position=(0., 0., 0.))
structure.append_atom(symbols=['As'], position=(-a / 4., a / 4., a / 4.))

kpoints_scf = KpointsData()
# method mesh
kpoints_scf_mesh = 4
kpoints_scf.set_kpoints_mesh([
    kpoints_scf_mesh, kpoints_scf_mesh, kpoints_scf_mesh
])

kpoints_nscf = KpointsData()
# method mesh
kpoints_nscf_mesh = 10
kpoints_nscf.set_kpoints_mesh([
    kpoints_nscf_mesh, kpoints_nscf_mesh, kpoints_nscf_mesh
])

# method path
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
        'path': [('G', 'X'), ('X', 'U'), ('K', 'G'), ('G',
                                                      'L'), ('L',
                                                             'W'), ('W', 'X')]
    }
)
# projections
projections = generate_projections(
    dict(
        position_cart=(-1.42, 1.42, 1.42),
        ang_mtm_l=-3,
        spin=None,
        spin_axis=None
    ),
    structure=structure
)

settings = {'postproc_setup': True}
settings_pp = Dict(dict=settings)
print(('settings', settings_pp))

run(
    MinimalW90WorkChain,
    pw_code=load_code('pw-6.4-release@localhost'),
    structure=structure,
    pseudo_family=Str('SSSP_efficiency_pseudos'),
    kpoints_scf=kpoints_scf,
    kpoints_nscf=kpoints_nscf,
    wannier_code=load_code('wannier90-3-desktop@localhost'),
    kpoint_path=kpoint_path,
    projections=projections,
    pw2wannier90_code=load_code('pw2wannier90-6.4-release@localhost')
)
