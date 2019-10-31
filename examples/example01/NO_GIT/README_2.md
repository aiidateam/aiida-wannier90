# Steps to run this example, i.e. GaAs wannierization

# Two possibilities are provided:
# A) Run a full calculation from scratch QE+Wannier90 (from step 1 to step 5)
# B) Run only the Wannier90 part (from step 3 to 5 ; needed files from previous steps are saved)

# We use in the following the  verdi command-line interface (CLI). Reminder for simple command in the updated AiiDA version:
# - workon aiida  (to enter the AiiDA cirtual environment)
# - verdi process list -a -p1 (to monitor the state of the calculations done since yesterday)
# - verdi process show <identifier> (once the calculation is finished: more detailed list of properties, inputs and outputs) 
# Since the inputs and outputs are Data nodes, not Process nodes, use verdi node show instead.
# Then we need to distinguish between Dict and CalcjobNode etc.



# Preliminary: 
## We define the starting structure from the verdi shell and we store it in the database:
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
## Definition of the codes and the pesudo family to be used:
your pw code --> <codename_pw> 
your pw2wannier code --> <codename_p2wannier>
your wannier code --> <codename_wannier>
your pseudo potentials family --> <PSEUDO_FAMILY_NAME> 




# Run your simulation (out of the verdi shell):
## 1) Run the SCF
### We specify the pw code to be used, the pk of the structure, the pseudo family, serial/parallel mode, type of pw calculation and the daemon
```
aiida-quantumespresso calculation launch pw -X <codename_pw> --structure=<PK_structure> --pseudo-family=<PSEUDO_FAMILY_NAME> --with-mpi --calculation-mode=scf --daemon
```
### The code prints out on the screen: 

Submitted PwCalculation<PK_calculation> to the daemon 

### Now we can check the status of the calculation and inspect it:
``` 
verdi process list -a -p1
verdi process show <PK_calculation_scf>
```
Output RemoteData: <PK_remotedata_scf>


## 2) Run the NSCF
### We specify the pw code to be used, the pk of the structure, the pseudo family, serial/parallel mode, type of pw calculation, the parent folder from the scf step, the mesh of kpoints to be used and the daemon
```
aiida-quantumespresso calculation launch pw -X <codename_pw> --structure=<PK_structure>  --pseudo-family=<PSEUDO_FAMILY_NAME> --with-mpi --calculation-mode=nscf --parent-folder=<PK_remotedata_scf> --unfolded-kpoints --kpoints-mesh=2 2 2 --daemon
```
Submitted PwCalculation<PK_calculation_nscf> to the daemon

```
 verdi process show <PK_calculation_nscf>
```
Output RemoteData: <PK_remotedata_nscf>


## 3) Run the Wannier90 preprocessing
### We specify only the Wannier code and the preprocessing mode
```
verdi run wannier_gaas.py --send <codename_wannier> preprocess
```
submitted calculation; calc=Calculation(uuid='uuid_wannier-pp') # ID=<PK_calculation_wannier-pp>
``` 
verdi process list -a -p1
verdi process show <PK_calculation_wannier-pp>
```
nnkp_file          <PK_nnkp_file>  SinglefileData


## 4) Run the pw2wannier90 run
### We specify the pw2wannier code, the pk of the remote data from the nscf calculation, the pk of the nnkp file, mpi and daemon
```
aiida-quantumespresso calculation launch pw2wannier90 -X <codename_pw2wannier> -P <PK_remotedata_nscf> -S <PK_nnkp_file> -i -d
```
Submitted Pw2wannier90Calculation<PK_calculation_pw2wannier> to the daemon
...
remote_folder      <PK_remotedata_pw2wannier>  RemoteData
retrieved          <PK_folderdata_pw2wannier>  FolderData


# 5) Run the Wannier90 main run
### Using .mmn, .amn matrices from the AiiDA repository
### Since the pw2wannier90 CLI utility retrieves .eig, .amn and .mmn, we can use files from a FolderData
### We run the example script, we specify the Wannier code, local (or remote) and the pk of the retrieved data from the pw2wannier calculation 

```
verdi run wannier_gaas.py --send <codename_wannier> local <PK_folderdata_pw2wannier> 
```
submitted calculation; calc=Calculation(uuid='uuid_wannier-local') # ID=<PK_calculation_wannier_local>
``` 
verdi process list -a -p1
verdi process show <PK_calculation_wannier_local>
```

verdi calcjob res <PK_calculation_wannier_local>
{
    "Omega_D": 0.008611417,
    "Omega_I": 4.187080332,
    "Omega_OD": 0.484748783,
    ...
}

### Using .mmn, .amn matrices from the remote cluster
### Equivalently, to use the data from the RemoteFolder:
```
verdi run wannier_gaas.py --send <codename_wannier> remote <PK_remotedata_pw2wannier>
```
submitted calculation; calc=Calculation(uuid=''uuid_wannier-remote') # ID=<PK_calculation_wannier_remote>
``` 
verdi process list -a -p1
verdi process show <PK_calculation_wannier_remote>
```

verdi calcjob res <PK_calculation_wannier_remote>
{
    "Omega_D": 0.008611417,
    "Omega_I": 4.187080332,
    "Omega_OD": 0.484748783,
    ...
}

#and one can compare (e.g. via meld) the output (seedname.wout) of the two calculation (local and remote)to check that after 100 iterations we get the same results (convergence!)

