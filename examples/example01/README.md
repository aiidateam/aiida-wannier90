# Steps to run this example, i.e. GaAs wannierization

 Two possibilities are provided:\
 A) Run a full calculation from scratch QE+Wannier90 (from step 1 to step 5)\
 B) Run only the Wannier90 part (step 5 only)

 We use in the following the  verdi command-line interface (CLI). Reminder for simple command in the updated AiiDA version:
1. workon aiida  (to enter the AiiDA cirtual environment)
2. verdi process list -a -pn (to monitor the state of the calculations done in the last n days)
3. verdi process show \<identifier> (once the calculation is finished: more detailed list of properties, inputs and outputs) 

If following strategy (B) you can directly jump to Section 5 of this README file.


## Preliminary: 
 We define the starting structure from the verdi shell and we store it in the database:
```
from aiida.plugins import DataFactory
StructureData = DataFactory('structure')
a = 5.68018817933178
structure = StructureData(cell = [[-a/2., 0, a/2.], [0, a/2., a/2.], [-a/2., a/2., 0]])
structure.append_atom(symbols=['Ga'], position=(0., 0., 0.))
structure.append_atom(symbols=['As'], position=(-a/4., a/4., a/4.))
structure.store()
print ( 'Structure stored with pk %d' %structure.pk)  
```
 Definition of the codes and the pesudo family to be used:
1. your pw code --> <codename_pw> 
2. your pw2wannier code --> <codename_p2wannier>
3. your wannier code --> <codename_wannier>
your pseudo potentials family --> <PSEUDO_FAMILY_NAME> 




# Run your simulation (out of the verdi shell):
## 1) Run the SCF
We specify the pw code to be used, the PK of the structure, the pseudo family, serial/parallel mode, type of pw calculation and the daemon:
```
aiida-quantumespresso calculation launch pw -X <codename_pw> --structure=<PK_structure> --pseudo-family=<PSEUDO_FAMILY_NAME> --with-mpi --calculation-mode=scf --daemon
```
The code prints out on the screen: 

```
Submitted PwCalculation<PK_calculation> to the daemon 
```
and we can check the status of the calculation:
``` 
verdi process list -a -p1
verdi process show <PK_calculation_scf>
```
by typing the latter command we get in `Outputs`:
```
...
remote_folder <PK_remotedata_scf> RemoteData
```

## 2) Run the NSCF
 We specify the pw code to be used, the pk of the structure, the pseudo family, serial/parallel mode, type of pw calculation, the parent folder from the scf step, the mesh of kpoints to be used and the daemon:
```
aiida-quantumespresso calculation launch pw -X <codename_pw> --structure=<PK_structure>  --pseudo-family=<PSEUDO_FAMILY_NAME> --with-mpi --calculation-mode=nscf --parent-folder=<PK_remotedata_scf> --unfolded-kpoints --kpoints-mesh=2 2 2 --daemon
```
it follows:
```
Submitted PwCalculation<PK_calculation_nscf> to the daemon

```
```
 verdi process show <PK_calculation_nscf>
 ```
In `Outputs`:
```
remote_folder <PK_remotedata_nscf> RemoteData
```

## 3) Run the Wannier90 preprocessing
We specify only the Wannier code and the preprocessing mode:
```
verdi run wannier_gaas.py --send <codename_wannier> preprocess
```
On the screen:
```
submitted calculation; calc=Calculation(uuid='uuid_wannier-pp') # ID=<PK_calculation_wannier-pp>
``` 
By typing the usual commands we check the status of the calculation
```
verdi process list -a -p1
verdi process show <PK_calculation_wannier-pp>
```
and we get the pk of the nnkp file 
```
nnkp_file  <PK_nnkp_file>  SinglefileData
```

## 4) Run the pw2wannier90 run
We specify the pw2wannier code, the pk of the remote data from the nscf calculation, the pk of the nnkp file, mpi and daemon:
```
aiida-quantumespresso calculation launch pw2wannier90 -X <codename_pw2wannier> -P <PK_remotedata_nscf> -S <PK_nnkp_file> -i -d
```
On the screen:
```
Submitted Pw2wannier90Calculation<PK_calculation_pw2wannier> to the daemon
...
remote_folder      <PK_remotedata_pw2wannier>  RemoteData
retrieved          <PK_folderdata_pw2wannier>  FolderData
```

# 5) Run the Wannier90 main run

We eventually run the main Wannier90 calculation, where  we need to specify the Wannier code, the mode (preprocess or main)
and the pk of the FolderData containing the .amn and .mmn files. This FolderData, if following strategy (A) is the one retrieved
from the pw2wannier calculation.
If instead you are following strategy (B), you will need to create this FolderData by running teh script `create_local_input_folder'.
The script will ask you if you want to store the FolderData on a node, say yes and you will get the corresponding PK and the 
command to run the following Wannier90 calculation. The command, in both cases, is the following:

```
verdi run wannier_gaas.py --send <codename_wannier> main <PK_folderdata_pw2wannier> 
```
```
submitted calculation; calc=Calculation(uuid='uuid_wannier-local') # ID=<PK_calculation_wannier_local>
``` 
We type:
```
verdi process list -a -p1
verdi process show <PK_calculation_wannier_local>
```
and we  inspect the output file:
```
verdi calcjob res <PK_calculation_wannier_local>
{
    "Omega_D": 0.008611417,
    "Omega_I": 4.187080332,
    "Omega_OD": 0.484748783,
    ...
}
```
