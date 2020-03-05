Documentation of the inputs of the aiida-wannier90 plugin
=========================================================

Input description
^^^^^^^^^^^^^^^^^

.. _my-ref-to-wannier90-doc:

Wannier90
+++++++++

Supported codes
---------------
The plugin supports all the Wannier90 versions released from v1.0 to v3.0. It has been tested on v3.0 and v2.0, however it should work also for v1.0. We strongly suggest version v3.0 if interested in bands structure and new features in general.

.. _my-ref-to-wannier90-inputs-doc:

Inputs
------
* **remote_input_folder**, The remote input folder is a  class :py:class:`RemoteData <aiida.orm.RemoteData>` containing input files (**.amn**, **.mmn**, ...) stored in a remote computer. See :ref:`my-ref-to-wannier90-filescopy-doc` for more details.

* **local_input_folder**, The local input folder it is a   class :py:class:`FolderData <aiida.orm.FolderData>` containing input files (**.amn**, **.mmn**, ...) stored in the AiiDA repository. See :ref:`my-ref-to-wannier90-filescopy-doc` for more details.

* **kpoints**, class :py:class:`KpointsData <aiida.orm.KpointsData>`
  Reciprocal space points on which to build the Wannier functions. Note that this must be an evenly spaced grid and must be constructed using an ``mp_grid`` kpoint mesh, with `{'FORCE_KPOINTS_LIST': True}` setting in the PW nscf calculation. It is a requirement of Wannier90, though not of this plugin, that symmetry not be used in the parent calculation, that is the setting card ``['SYSTEM'].update({'nosym': True})`` be applied in the parent calculation.

* **kpoints_path**, class :py:class:`KpointsData <aiida.orm.KpointsData>` (optional).
  A set of kpoints which indicate the path to be plotted by wannier90 band plot feature.

* **parameters**, class :py:class:`Dict <aiida.orm.Dict>`.
  Input parameters that defines the calculations to be performed, and their parameters. Unlike the wannier90 code, which does not check capitilization, this plugin is case sensitive. All keys must be lowercase e.g. ``num_wann`` is acceptable but ``NUM_WANN`` is not. See the Wannier90 documentation for more details.

* **structure**, class :py:class:`StructureData <aiida.orm.StructureData>`.
  Input structure mandatory for execution of the code.

* **projections**, class :py:class:`OrbitalData <aiida.orm.OrbitalData>`.
  An OrbitalData object containing it it a list of orbitals.


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

           Would become::
           
           [{'kind_name':'Si','ang_mtm_l_list':[0,1,2]}, {'kind_name':'Si','ang_mtm_l_list':[0,1],'radial_nodes':2}]

* **settings**, class :py:class:`Dict <aiida.orm.Dict>`
  Additional settings to manage the Wannier90 calculation. 
  It can contain the following file handling options:

    *  **'additional_retrieve_list'**: List of additional filenames to be retrieved.

    *  **'additional_remote_symlink_list'**:  List of custom files to link on the remote.

    *  **'additional_remote_copy_list'**: List of custom files to copy from a source on the remote.

    *  **'additional_local_copy_list'**:  List of custom files to copy from a local source.
  
    *  **'exclude_retrieve_list'**:  List of filename patterns to exclude from retrieving. Does not affect files listed in ``additional_retrieve_list``.  

  Besides, the following general options are available:

    *  **'random_projections'**: Enables using random projections if or not enough projections are defined.

    *  **'postproc_setup'**:  Use Wannier90 in preprocessing mode. This affects which input and output files are expected.

.. _my-ref-to-wannier90-filescopy-doc:



Files Copied
------------

Files upload
############
Depending on the startup settings used, and what the parent calculation was, will alter which files are copied, which are symlinked. The goal being to copy the minimum number of files, and to not symlink to files that will be rewritten (e.g. ``.chk``).  The list of files to copy an link is generated from the ``local_input_folder`` and ``remote_input-folder``, the two being mutually exclusive.
The following operations will be performed on the files:

* *copy*: the file, if present, is copied from the parent
* *sym*: the file, if present, will be symlinked to the parent
* *none*: the file will neither be copied or symlinked

For example, the files ``.amn`` and ``.mmn`` are always required but by default  are not copied unless specified. At variance, the file ``.chk`` is not required but when present is always copied by default.
Evetually, there exist the possibility of non required files that even if present are still not copied by default: ``.eig``, ``.spn``, ``.uHu``, ``_htB.dat``, ``_htL.dat``, ``_htR.dat``,
``_htC.dat``, ``_htLC.dat``, ``_htCR.dat``, ``.unkg``. To change the default values, the user can modify the corresponding files list in the settings: ``additional_remote_symlink_list``, ``additional_remote_copy_list`` and ``additional_local_copy_list``.

Files retrieve
##############

All the output files of Wannier90 are retrieved by deafult  except the ``.nnkp`` (which is handled separately and stored as a class :py:class:`SinglefileData <aiida.orm.SinglefileData>`) and the ``.chk`` (checkpoint files are large and usually not needed, by default they are not retrieved but can optionally be selected for restart option).
Here it follows a complete list of retrieved suffices: (``.wout``, ``.werr``, ``.r2mn``, ``_band.dat``, ``_band.agr``, ``_band.kpt``, ``.bxsf``, ``_w.xsf``, ``_w.cube``, ``_centres.xyz``, ``_hr.dat``, ``_tb.dat``, ``_r.dat``, ``.bvec``, ``_wsvec.dat``, ``_qc.dat``, ``_dos.dat``, ``_htB.dat``, ``_u.mat``, ``_u_dis.mat``, ``.vdw``, ``_band_proj.dat``, ``_band.labelinfo.dat``).
To exclude or include specific files from the retrieved list one can respectively use the ``exclude_retrieve_list`` and ``additional_retrieve_list`` settings introduced above in the documentation.








