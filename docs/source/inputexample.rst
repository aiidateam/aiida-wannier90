Documentation of the inputs of the aiida-wannier90 plugin
=========================================================

Input description
^^^^^^^^^^^^^^^^^

.. _my-ref-to-wannier90-doc:

Wannier90
+++++++++

Supported codes
---------------
* tested on Wannier90 v2.0.1

.. _my-ref-to-wannier90-inputs-doc:

Inputs
------
* **remote_input_folder**, The remote input folder can either be a PW calculation or Wannier90. See :ref:`my-ref-to-wannier90-filescopy-doc` for more details. #TODO

  .. note:: There are no direct links between calculations. The use_parent_calculation will set a link to the RemoteFolder attached to that calculation. Alternatively, the method **use_parent_folder** can be used to set this link directly.

* **kpoints**, class :py:class:`KpointsData <aiida.orm.KpointsData>`
  Reciprocal space points on which to build the wannier functions. Note that this must be an evenly spaced grid and must be constructed using an mp_grid kpoint mesh, with `{'FORCE_KPOINTS_LIST': True}` setting in the PW nscf calculation. It is a requirement of Wannier90, though not of this plugin, that symmetry not be used in the parent calculation, that is the setting card ``['SYSTEM'].update({'nosym': True})`` be applied in the parent calculation.

* **kpoints_path**, class :py:class:`KpointsData <aiida.orm.KpointsData>` (optional)
  A set of kpoints which indicate the path to be plotted by wannier90 band plot feature.

* **parameters**, class :py:class:`Dict <aiida.orm.Dict>`
  Input parameters that defines the calculations to be performed, and their parameters. Unlike the wannier90 code, which does not check capitilization, this plugin is case sensitive. All keys must be lowercase e.g. ``num_wann`` is acceptable but ``NUM_WANN`` is not. See the Wannier90 documentation for more details.

* **structure**, class :py:class:`StructureData <aiida.orm.StructureData>`
  Input structure mandatory for execution of the code.

* **projections**, class :py:class:`OrbitalData <aiida.orm.OrbitalData>`
  An OrbitalData object containing it it a list of orbitals


.. note:: 
    You should construct the projections using the convenience method :py:meth:`generate_projections <aiida_wannier90.orbitals.generate_projections>`. Which will produce an :py:class:`OrbitalData <aiida.orm.OrbitalData>` given a list of dictionaries. Some examples, taken directly from the wannier90 user guide, would be:

        #. CuO, SP, P, and D on all Cu; SP3 hyrbrids on O.

           In Wannier90 ``Cu:l=0;l=1;l=2`` for Cu and ``O:l=-3`` or ``O:sp3`` for O

           Would become ``{'kind_name':'Cu','ang_mtm_name':['SP','P','D']}`` for Cu and  ``{'kind_name':'O','ang_mtm_l_list':-3}`` or ``{..., 'ang_mtm_name':['SP3']}`` for O

        #. A single projection onto a PZ orbital orientated in the (1,1,1) direction:

           In Wannier90 ``c=0,0,0:l=1:z=1,1,1`` or ``c=0,0,0:pz:z=1,1,1``

           Would become ``{'position_cart':(0,0,0),'ang_mtm_l_list':1,'zaxis':(1,1,1)}`` or ``{... , 'ang_mtm_name':'PZ',...}``

        #. Project onto S, P, and D (with no radial nodes), and S and P (with one radial node) in silicon:

           In Wannier90 ``Si:l=0;l=1;l=2``, ``Si:l=0;l=1;r=2``

           Would become ``[{'kind_name':'Si','ang_mtm_l_list':[0,1,2]}, {'kind_name':'Si','ang_mtm_l_list':[0,1],'radial_nodes':2}]``

* **settings**, class :py:class:`Dict <aiida.orm.Dict>`
  Additional settings to manage the Wannier90 calculation. 
  It can contain the following file handling options:

    *  **'additional_retrieve_list'**: List of additional filenames to be retrieved.

    *  **'additional_remote_symlink_list'**:  List of custom files to link on the remote.

    *  **'additional_remote_copy_list'**: List of custom files to copy from a source on the remote.

    *  **'additional_local_copy_list'**:  List of custom files to copy from a local source.
  
    *  **'exclude_retrieve_list'**:  List of filename patterns to exclude from retrieving. Does not affect files listed in `additional_retrieve_list`.  

  Besides, the following general options are available:

    *  **'random_projections'**: Enables using random projections if or not enough projections are defined.

    *  **'postproc_setup'**:  Use Wannier90 in preprocessing mode. This affects which input and output files are expected.


.. _my-ref-to-wannier90-filescopy-doc:

Files Copied
------------
All the output files of Wannier90 are retrieved by deafult . #TODO: add and comment onremote/local folder?









