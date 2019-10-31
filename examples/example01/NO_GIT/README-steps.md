# Steps to run this example, i.e. GaAs wannierization
#Two possibilities are provided:
# A) Runa  a full calculation from scratch QE+Wannier90 (from step 1 to step 5)
# B) Run only the Wannier90 part (from step 3 to 5 ; needed files from previous steps are saved)

# We use in the following the  verdi command-line interface (CLI). Reminder for simple command in the updated AiiDA version:
# - verdi process list -a -p1 (list all the processes that have been launched since yesterday)
#- verdi process show <identifier> (more detailed list of properties, inputs and outputs) 
#Since the inputs and outputs are Data nodes, not Process nodes, use verdi node show instead.
# Then we need to distinguish between Dict and CalcjobNode etc.


## 1) Run the SCF`
``
aiida-quantumespresso calculation launch pw -X pw-6.4-release@localhost --structure=132632 --pseudo-family=SSSP_efficiency_pseudos --with-mpi --calculation-mode=scf --daemon
```
Submitted PwCalculation<132651> to the daemon

``` 
verdi process list -a -p1
verdi process show 132651
```
Output RemoteData: 132652


## 2) Run the NSCF
```
aiida-quantumespresso calculation launch pw -X pw-6.4-release@localhost --structure=132632 --pseudo-family=SSSP_efficiency_pseudos --with-mpi --calculation-mode=nscf --parent-folder=132652 --unfolded-kpoints --kpoints-mesh=2 2 2 --daemon
```
Submitted PwCalculation<132659> to the daemon

``` verdi process show 132659
```
Output RemoteData: 132660


## 3) Run the Wannier90 preprocessing
```
verdi run wannier_gaas.py --send wannier90-3-desktop@localhost preprocess
```
submitted calculation; calc=Calculation(uuid='85226bb7-268a-47d4-91d1-8a6b99b1ed56') # ID=132718
``` 
verdi process list -a -p1
verdi process show 132718
```
nnkp_file          132721  SinglefileData


## 4) Run the pw2wannier90 run
```
aiida-quantumespresso calculation launch pw2wannier90 -X pw2wannier90-6.4-release@localhost -P 132660 -S 132721 -i -d
```
Submitted Pw2wannier90Calculation<132725> to the daemon
``` 
verdi process list -a -p1
verdi process show 132725
```
remote_folder      132726  RemoteData
retrieved          132727  FolderData


# 5) Run the Wannier90 main run
### Using .mmn, .amn matrices from the AiiDA repository
Since the pw2wannier90 CLI utility retrieves .eig, .amn and .mmn, we can use
files from a FolderData

```
verdi run wannier_gaas.py --send wannier90-3-desktop@localhost local 132727
```
submitted calculation; calc=Calculation(uuid='61c20a6f-a32b-48e4-aac6-a0aa4d26e9d4') # ID=132762
``` 
verdi process list -a -p1
verdi process show 132762
```

verdi calcjob res 132762
{
    "Omega_D": 0.008611417,
    "Omega_I": 4.187080332,
    "Omega_OD": 0.484748783,
    ...
}

### Using .mmn, .amn matrices from the remote cluster
Equivalently, to use the data from the RemoteFolder:
```
verdi run wannier_gaas.py --send wannier90-3-desktop@localhost remote 132726
```
submitted calculation; calc=Calculation(uuid='f0473297-d117-4964-a05e-88ff940fcbae') # ID=132770
``` 
verdi process list -a -p1
verdi process show 132770
```

verdi calcjob res 132770
{
    "Omega_D": 0.008611417,
    "Omega_I": 4.187080332,
    "Omega_OD": 0.484748783,
    ...
}

#and one can compare (e.g. via meld) the output of the two calculation to check that after around 100 iterations we get the same results (convergence!)

