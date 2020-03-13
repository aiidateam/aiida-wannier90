Documentation of the inputs of the aiida-wannier90 plugin
=========================================================

Inputs
++++++

``parameters``
--------------
A :py:class:`Dict <aiida.orm.Dict>` node containing the input parameters
for the Wannier90 calculation to be performed.
Unlike the Wannier90 code, which does not check capitilization
(see the Wannier90 documentation for more details),
this plugin is *case sensitive*.
All keys **must** be lowercase, e.g. ``num_wann`` is acceptable
but ``NUM_WANN`` is not.

``structure``
-------------
A :py:class:`StructureData <aiida.orm.StructureData>` node with the
crystal structure.

``kpoints``
-----------
A :py:class:`KpointsData <aiida.orm.KpointsData>` node containing the
reciprocal space k-points used to build the Wannier functions.
This must be an evenly-spaced grid and must be constructed using an ``mp_grid``
k-point mesh that should be the same used in the NSCF step of the preliminary
DFT calculation.

If you are using ``aiida-quantumespresso`` for the preliminary DFT
calculations, you can construct the explicit list of k-points using
``{'FORCE_KPOINTS_LIST': True}`` in the settings of the calculation.
In this case, for Quantum ESPRESSO set also ``nosym=True`` in the ``SYSTEM``
namelist of the NSCF step.


``remote_input_folder``
-----------------------
A :py:class:`RemoteData <aiida.orm.RemoteData>`
node pointing to a folder with the needed preliminary files, stored on a
remote computer.
These include both the files created by a DFT post-processing code
(``.amn``, ``.mmn``, ...) and/or the ``.chk`` checkpoint file created by
Wannier90 and needed in a restart. This folder must not be specified
when running Wannier90 in post-processing mode (``-pp`` option).
See also the option ``postproc_setup`` in the input ``settings`` node.

See :ref:`my-ref-to-wannier90-filescopy-doc` for more details.

``local_input_folder``
----------------------
A :py:class:`FolderData <aiida.orm.FolderData>`
node containing the needed preliminary files (as for the
``remote_input_folder``).

This folder must not be specified
when running Wannier90 in post-processing mode (``-pp`` option).
See also the option ``postproc_setup`` in the input ``settings`` node.

The two inputs ``remote_input_folder`` and ``local_input_folder`` cannot
be specified at the same time.
You can choose between them depending on whether you decided to store
the preliminary files (``.amn``, ``.mmn``, ...) in the AiiDA repository,
or just on the supercomputer.

See :ref:`my-ref-to-wannier90-filescopy-doc` for more details.

``kpoints_path``
----------------
An optional :py:class:`Dict <aiida.orm.Dict>` node,
specifying a set of pairs of k-points. These define the endpoints
of each segment along which to plot a band structure.
I must contain, in particular:

- a list ``path`` of length-2 tuples with the labels of the endpoints of
  the path;
- a dictionary ``point_coords`` giving the scaled coordinates for
  each high-symmetry endpoint.


``projections``
---------------
A specification of which projections to use for the Wannierisation. Multiple
node types are accepted as discussed below.

You can construct the projections using the convenience method
:py:meth:`~aiida_wannier90.orbitals.generate_projections`.

This will produce an :py:class:`OrbitalData <aiida.orm.OrbitalData>` node
startinf from a list of dictionaries specifying the projection-orbital
symmetries and properties.

Some examples, taken directly from the wannier90 user guide:

* Material: CuO. :math:`s`, :math:`p`, and :math:`d` orbitals on all Cu
  atoms, and :math:`sp^3` hyrbrids on all oxygen atoms.

    In Wannier90 one would specify::

      Cu:l=0;l=1;l=2
      O:l=-3

  (or ``O:sp3``).

  The list of dictionaries to provide to
  :py:meth:`~aiida_wannier90.orbitals.generate_projections`
  is::

    [
      {
        'kind_name': 'Cu',
        'ang_mtm_name': ['SP','P','D']
      },
      {
        'kind_name': 'O',
        'ang_mtm_l_list':-3
      }
    ]

  (or equivalently ``{..., 'ang_mtm_name': ['SP3']}``).

* A single projection onto a :math:`p_z` orbital orientated in the (1, 1, 1)
  direction.

  In Wannier90::

    c=0,0,0:l=1:z=1,1,1

  or ``c=0,0,0:pz:z=1,1,1``.

  The list of dictionaries to provide to
  :py:meth:`~aiida_wannier90.orbitals.generate_projections`
  is::

    [
      {
        'position_cart': (0,0,0)
        'ang_mtm_l_list': 1,
        'zaxis':(1,1,1)
      }
    ]

  or ``{... , 'ang_mtm_name':'PZ',...}``.

* Project onto :math:`s`, :math:`p`, and :math:`d` orbitals
  (with no radial nodes), and :math:`s` and :math:`p` (with one radial node)
  in silicon.

  In Wannier90::

    Si:l=0;l=1;l=2
    Si:l=0;l=1;r=2

  The list of dictionaries to provide to
  :py:meth:`~aiida_wannier90.orbitals.generate_projections`
  is::

    [
      {
        'kind_name': 'Si',
        'ang_mtm_l_list': [0,1,2]
      },
      {
        'kind_name': 'Si',
        'ang_mtm_l_list': [0,1],
        'radial_nodes':2
      }
    ]

``settings``
------------
A :py:class:`Dict <aiida.orm.Dict>` node with additional settings to control
the Wannier90 calculation.
It can contain the following file handling options:

*  ``additional_retrieve_list``: List of additional filenames to be retrieved.

*  ``additional_remote_symlink_list``:  List of custom files to link on the
   remote.

*  ``additional_remote_copy_list``: List of custom files to copy from a
   different folder on the remote.

*  ``additional_local_copy_list``: List of custom files to copy from
   a local source (a folder in the AiiDA repository).

*  ``exclude_retrieve_list``:  List of filename patterns to exclude when
   retrieving. It does not affect files listed in ``additional_retrieve_list``.

Besides, the following general options are available:

*  ``random_projections``: Enables using random projections if not enough
   projections are defined.

*  ``postproc_setup``: Use Wannier90 in preprocessing mode.
   This affects which input and output files are expected (see .

.. _my-ref-to-wannier90-filescopy-doc:

Files Copied
++++++++++++

Uploaded files
--------------
Which files are copied and which are symlinked during the upload phase (or a
calculation having a ``remote_input_folder`` or a ``folder_input_folder``
depends on the startup settings used, and what the parent calculation was.

The goal is to copy the minimum number of files. However, we do not
symlink files that are rewritten during the run (e.g. the ``.chk`` file), as
in this case multiple runs (restarts) could try to change the same file.

The list of files to copy or symlink is generated from the content of the
``local_input_folder`` or ``remote_input_folder``,
which are mutually exclusive.
The following operations will be performed on the files:

* *copy*: the file, if present, is copied from the parent;
* *symlink*: the file, if present, is symlinked to the parent;
* *nothing*: the file will neither be copied nor symlinked.

In particular, the files ``.amn`` and ``.mmn`` are always required and
are symlinked.
Additional input files (that are not required, as they are needed only for
some types of calculations) are symlinked, if present:
``.eig``, ``.spn``, ``.uHu``, ``_htB.dat``, ``_htL.dat``, ``_htR.dat``,
``_htC.dat``, ``_htLC.dat``, ``_htCR.dat``, ``.unkg``.

To add some files in the list to copy or symlink on the remote, or
to copy from the AiiDA repository, the user can modify the corresponding file
list in the ``settings`` node: ``additional_remote_symlink_list``,
``additional_remote_copy_list`` and ``additional_local_copy_list``.

At variance, the file ``.chk`` is not required ,but if present is always
copied by default (since this can be overwritten).

Retrieved files
---------------

All the output files of Wannier90 are retrieved by default, if present,
except the ``.nnkp`` file (which is handled separately and stored as a
:py:class:`~aiida.orm.SinglefileData` node for a ``postproc_setup``
calculation) and the ``.chk`` file (checkpoint files are large and usually
not needed, so by default they are not retrieved.

Here is the complete list of suffixes of the files to retrieve:
``.wout``, ``.werr``, ``.r2mn``, ``_band.dat``, ``_band.agr``,
``_band.kpt``, ``.bxsf``, ``_w.xsf``, ``_w.cube``,
``_centres.xyz``, ``_hr.dat``, ``_tb.dat``, ``_r.dat``,
``.bvec``, ``_wsvec.dat``, ``_qc.dat``, ``_dos.dat``, ``_htB.dat``,
``_u.mat``, ``_u_dis.mat``, ``.vdw``, ``_band_proj.dat``,
``_band.labelinfo.dat``.

To exclude or include specific files from the retrieved list, one can
respectively use the ``exclude_retrieve_list`` and
``additional_retrieve_list`` settings described above.








