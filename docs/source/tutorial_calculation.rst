Running a Wannier90 calculation
===============================

GaAs wannierization
+++++++++++++++++++

You can check the folder ``examples/example01`` in the source repository
for an actual script (``wannier_gaas.py``) that you can run.
In this example, two possibilities are provided:

A) Run a full calculation from scratch QE+Wannier90 (from step 1 to step 5)
B) Run only the Wannier90 part (step 5 only)

We use the ``verdi`` command-line interface (CLI). A
small reminder of some simple commands:

- Activate your virtual environment, e.g. with ``workon aiida``
- ``verdi process list -a -p<N>`` (to monitor the state of the
  calculations done in the last ``<N>`` days)
- ``verdi process show <identifier>`` (once the calculation is finished:
  more detailed list of properties, inputs and outputs).

If following strategy (B), you can directly jump to Section 5 of the documentation.

Preliminary
-----------
We define the starting  input structure from the verdi shell and we store it in
the database in the form of a ``StructureData`` by typing:

.. code:: python

   from aiida.plugins import DataFactory
   StructureData = DataFactory('core.structure')
   a = 5.68018817933178
   structure = StructureData(cell = [[-a/2., 0, a/2.], [0, a/2., a/2.], [-a/2., a/2., 0]])
   structure.append_atom(symbols=['Ga'], position=(0., 0., 0.))
   structure.append_atom(symbols=['As'], position=(-a/4., a/4., a/4.))
   structure.store()
   print ( 'Structure stored with pk %d' %structure.pk)

In the example  file we also define the kpoints mesh to be used :

.. code:: python

   KpointsData = DataFactory('core.array.kpoints')
   kpoints = KpointsData()
   kpoints.set_kpoints_mesh([2, 2, 2])

and the kpoints path:

.. code:: python

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
         'path': [('G', 'X'), ('X', 'W'), ('W', 'K'), ('K',
                                                         'G'), ('G', 'L'),
                  ('L', 'U'), ('U', 'W'), ('W', 'L'), ('L',
                                                         'K'), ('U', 'X')]
      }
   )

Eventually, we provide the projections in the following format:

.. code:: python

   from aiida_wannier90.orbitals import generate_projections
   projections = generate_projections(
      dict(
         position_cart=(1, 2, 0.5),
         radial=2,
         ang_mtm_l_list=2,
         ang_mtm_mr_list=5,
         spin=None,
         #zona=1.1,
         zaxis=(0, 1, 0),
         xaxis=(0, 0, 1),
         spin_axis=None
      ),
      structure=structure
   )



In the following, we will use this definition for the codes and the pseudo family
to be used:

1. your pw code –> ``<codename_pw>``
2. your pw2wannier code –> ``<codename_pw2wannier>``
3. your wannier code –> ``<codename_wannier>``
4. your pseudo potentials family –> ``<PSEUDO_FAMILY_NAME>``

Run your simulation
-------------------

1) Run the SCF
**************

We specify the pw code to be used, the PK of the structure, the pseudo
family, serial/parallel mode, type of pw calculation and the daemon:

::

   aiida-quantumespresso calculation launch pw -X <codename_pw> --structure=<PK_structure> --pseudo-family=<PSEUDO_FAMILY_NAME> --with-mpi --calculation-mode=scf --daemon

The code prints out on the screen:

::

   Submitted PwCalculation<PK_calculation> to the daemon

and we can check the status of the calculation:

::

   verdi process list -a -p1
   verdi process show <PK_calculation_scf>

By typing the latter command we get among the output text:

::

   ...
   remote_folder <PK_remotedata_scf> RemoteData
   ...

2) Run the NSCF
***************

We specify the pw code to be used, the PK of the structure, the pseudo
family, serial/parallel mode, type of pw calculation, the parent folder
from the scf step, the mesh of kpoints to be used and the daemon:

::

   aiida-quantumespresso calculation launch pw -X <codename_pw> --structure=<PK_structure>  --pseudo-family=<PSEUDO_FAMILY_NAME> --with-mpi --calculation-mode=nscf --parent-folder=<PK_remotedata_scf> --unfolded-kpoints --kpoints-mesh=2 2 2 --daemon

Submission is confirmed by the following message:

::

   Submitted PwCalculation<PK_calculation_nscf> to the daemon

We can check the progress and the outputs with:

::

    verdi process show <PK_calculation_nscf>

we finally get in the output text:

::

   ...
   remote_folder <PK_remotedata_nscf> RemoteData
   ...

3) Run the Wannier90 preprocessing
**********************************

We specify only the Wannier code and select the ``preprocess`` mode:

::

   verdi run wannier_gaas.py --send <codename_wannier> preprocess

The output tells us the PK of the calculation just submitted:

::

   submitted calculation; calc=Calculation(uuid='uuid_wannier-pp') # ID=<PK_calculation_wannier-pp>

By typing the usual commands we check the status of the calculation

::

   verdi process list -a -p1
   verdi process show <PK_calculation_wannier-pp>

and we get among the outputs the PK of the node containing the ``.nnkp``
file:

::

   ...
   nnkp_file  <PK_nnkp_file>  SinglefileData
   ...

4) Run the pw2wannier90 step
****************************

We specify the pw2wannier code, the PK of the remote data from the NSCF
calculation, the PK of the ``nnkp_file`` node, and the options to indicate
we want to run using MPI and via the daemon:

::

   aiida-quantumespresso calculation launch pw2wannier90 -X <codename_pw2wannier> -P <PK_remotedata_nscf> -S <PK_nnkp_file> -i -d

As usual, in the output:

::

   Submitted Pw2wannier90Calculation<PK_calculation_pw2wannier> to the daemon

and by typing ``verdi process show``, we obtain:

::

   ...
   remote_folder      <PK_remotedata_pw2wannier>  RemoteData
   retrieved          <PK_folderdata_pw2wannier>  FolderData
   ...

5) Run the Wannier90 main step
******************************

We eventually can run the main Wannier90 calculation, where we need to
specify the Wannier code, the mode (``main``, for the main run) and the
PL of the ``FolderData`` containing the ``.amn`` and ``.mmn`` files.
This ``FolderData``, if following strategy (A), is the one retrieved
from the pw2wannier calculation. If instead you are following strategy
(B), you will need to create this FolderData by running the script
``create_local_input_folder.py`` via

::

   verdi run create_local_input_folder.py

The script will ask you if you want to store the ``FolderData`` on a
node. Once you confirm, you will obtain the corresponding PK and the
command to run the following Wannier90 calculation.

The command, in both cases, is the following:

::

   verdi run wannier_gaas.py --send <codename_wannier> main <PK_inputfolder>

where ``<PK_inputfolder>`` is either ``<PK_remotedata_pw2wannier>``
(strategy A) or the output of the ``create_local_input_folder.py``
script (strategy B).

Get the PK from the output:

::

   submitted calculation; calc=Calculation(uuid='uuid_wannier-local') # ID=<PK_calculation_wannier_local>

And inspect the status of the job:

::

   verdi process list -a -p1
   verdi process show <PK_calculation_wannier_local>

Finally, we can inspect the parsed outputs with:

::

   verdi calcjob res <PK_calculation_wannier_local>

that will output something like:

::

   {
       "Omega_D": 0.008611417,
       "Omega_I": 4.187080332,
       "Omega_OD": 0.484748783,
       ...
   }
