Documentation of the inputs of the aiida-wannier90 plugin
=========================================================

We describe here with an example the format of the inputs expected by the Wannier90 plugin.

You can check also the folder ``examples/example01`` in the source repository for an actual script that you can run.

use_parameters
--------------
Pass a :py:class:`~aiida.orm.data.parameter.ParameterData` with the input keys for Wannier90. An example::

    parameter = ParameterData(dict={'bands_plot':False,
                                    'num_iter': 12,
                                    'guiding_centres': True,
                                    'num_wann': 4,
                                    'wannier_plot':True,
                                    'wannier_plot_list':[1]
                                    })

use_structure
-------------
Pass a :py:class:`~aiida.orm.data.structure.StructureData` for the input structure.

use_kpoints
-----------
Pass a k-points mesh to be used as size of the Monkhorst-Pack grid of the DFT calculation.
Example::

    kpoints = KpointsData()
    kpoints.set_kpoints_mesh([2, 2, 2])

use_kpoint_path
---------------
Optional, pass a :py:class:`~aiida.orm.data.parameter.ParameterData` to specify the path to follow for the interpolated band structure.
The dictionary should *only* have two entries:

- ``path``: a list of length-2 lists, with the labels for the extremes of each path
- ``point_coords``: a dictionary that for each label gives the coordinates (in fractional coordinates
  with respect to the primitive reciprocal lattice vectors).

This information can, e.g., be easily obtained from the output of seekpath_.

Example::

  {
    'path': [
      ['GAMMA', 'X'],
      ['X', 'U'],
      ['K', 'GAMMA'],
      ['GAMMA', 'L'],
      ['L', 'W'],
      ['W', 'X']
    ],
    'point_coords':
    {
      'GAMMA': [0.0, 0.0, 0.0],
      'K': [0.375, 0.375, 0.75],
      'L': [0.5, 0.5, 0.5],
      'U': [0.625, 0.25, 0.625],
      'W': [0.5, 0.25, 0.75],
      'W_2': [0.75, 0.25, 0.5],
      'X': [0.5, 0.0, 0.5]
    }
  }

.. _seekpath: https://github.com/giovannipizzi/seekpath/


use_local_input_folder or use_remote_input_folder
-------------------------------------------------
Pass the parent folder with the .amn, .mmn, ... files. It can either be a :py:class:`~aiida.orm.data.folder.FolderData`
(for ``use_local_input_folder``)
containing the files, or a :py:class:`~aiida.orm.data.remote.RemoteData` with the output of e.g. a
``quantumespresso.pw2wannier90`` calculation.
If you pass both, files will be taken from both, with precedence from the local folder.

use_projections
---------------
To pass the information on the mesh to use. We provide a helper function to prepare the proper
:py:class:`~aiida.orm.data.orbital.OrbitalData` class,
called ``generate_projections``. For instance, the following puts a projection at the given
Cartesian coordinate ``(1,2,0.5)``, with given properties (radial, angular momentum, ...)::

    from aiida_wannier90.orbitals import generate_projections
    projections = generate_projections(dict(position_cart=(1,2,0.5),
                             radial=2,
                             ang_mtm_l=2,
                             ang_mtm_mr=5, spin=None,
                             #zona=1.1,
                             zaxis=(0,1,0),xaxis=(0,0,1), spin_axis=None),structure=structure)

As a second option, you can pass directly a :py:class:`~aiida.orm.data.base.List` object, with
a list of strings that will be put in the input file of Wannier90.
Note, however, that this format is **discouraged**: better to pass the :py:class:`~aiida.orm.data.orbital.OrbitalData` object,
that contains 'parsed' information and is easier to query, and set
``random_projections = True`` in the input 'settings' :py:class:`~aiida.orm.data.parameter.ParameterData` node.
For instance::

    from aiida.orm.data.base import List
    projections = List()
    projections.extend(['As:s','As:p'])
    projections.extend(['random','As:s'])

If really needed (but strongly discouraged for the reason explained above), if you have a
:py:class:`~aiida.orm.data.orbital.OrbitalData` as in the first
example, you can convert to an explicit list as in the second example with the following snippet
(the optional ``random_projections`` additional flag adds a ``random`` string in the flag,
to tell Wannier90 that missing projections should be selected randomly)::

    from aiida_wannier90.io._write_win import _format_all_projections
    projections_list = List()
    projections_list.extend(_format_all_projections(projections, random_projections=True))
    projections = projections_list


use_settings
------------
An optional :py:class:`~aiida.orm.data.parameter.ParameterData` with additional settings.
The possible values are:

- ``seedname``: pass a string if the seedname is not the default ``aiida`` (e.g. if you run the calculation
  manually and the ``.mmn``, ``.amn``, ... files use a different seedname
- ``random_projections``: if ``True``, adds the string ``random`` to the projections, needed in case you
  are specifying less projections than Wannier functions
- ``postproc_setup``: if ``True``, run just with the ``-pp`` options (preprocessing, to generate the ``.nnkp`` file).
- ``retrieve_hoppings``: if ``True``, retrieve also hopping files needed to obtain the Hamiltonian
  (``<seedname>_hr.dat``, ``<seedname>_centres.xyz``, ``<seedname>_wsvec.dat``).








