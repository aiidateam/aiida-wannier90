# GaAs wannierization workchain

This Aiida workchain run a full calculation from scratch ( i.e.Quantum ESPRESSO and Wannier90) to wannierize  the GaAs material without SCDM.
The workflows provide the parsed information from the standard Wannier90 output (i.e. centres, spreads etc.) and the intrepolated bands.

 We use in the following the  verdi command-line interface (CLI). Reminder for simple command in the updated AiiDA version:
1. workon aiida  (to enter the AiiDA cirtual environment)
2. verdi process list -a -pn (to monitor the state of the calculations done in the last n days)
3. verdi process show \<identifier> (once the calculation is finished: more detailed list of properties, inputs and outputs) 

## Run your simulation

- Open a terminal (click on the 'Terminal' icon on the left bar, represented  by a black screen with a '>_' symbol inside) and type:
``` 
     workon AiiDA
``` 

  to enter the "virtual environment" where AiiDA is installed.

  - In the workflow folder, run the following script (i.e. the launcher):

```    
     verdi run ./workflows/launch_w90_minimal.py 
``` 
- Notes: in this example we use as starting guess for projections atomic orbitals (sp3 centred on As atoms). For more 
  details about the inputs of QE and Wannier90 calculations you can inspect both the launcher and the workchain script.


## Check the results

- When you run the *launch_w90_minimal.py* script it will execute the *../example01/minimal.py* script. On screen you will get a output line for each step running (i.e. in order: pw-scf, pw-nscf, pp wannier, pw2wannier, final wannier), reporting the identifier pk of each calculation. You can ispect each calculation node by typing:

``` 
     verdi process show <PK>
``` 
  or

```   
     verdi node show <PK>

``` 
  for the specific inputs and outputs node of each calculation, and 
``` 
     verdi data dict show <PK>
``` 
 to inspect the dictionaries such as the *output_parameters* one containing the parsed information from the standard Wannier output.

- As final results you get all the information parsed in AiiDA and saved as outputs, as documented online (https://aiida-core.readthedocs.io/en/v0.7.0/plugins/wannier90/wannier90.html#my-ref-to-wannier90-filescopy-doc).

### Band structure

- Something useful is be able to export and/or visualize the resulting interpolated bands using maximally-localised Wannier functions (MLWFs).
Once the workflow is finished, you can find the ID of the band structure using the command:
```
     verdi node show <PK>
```
and then getting the PK for the row corresponding to the link label "MLWF_interpolated_bands".     
With this PK, you can show the bands with xmgrace using:
```
    verdi data bands show -F agr <PK> 
```
or export to file using:
```
   verdi data bands export -F agr <PK> -o file_name.agr
```
where *file_name.agr* is the name chosen for the file containing the bands to be plotted.

### Compare with DFT bands

- If you want to compare the interpolated band structure with the bands obtained directly from DFT (Quantum ESPRESSO),  you can plot together the two executing the following command:
```
xmgrace DFT-bands.agr file_name.agr 
```
where the *DFT-bands.agr* has been already provided in this folder.



## Visualizing Aiida Provenance Graphs

- Data provenance is tracked automatically and stored in the form of a directed acyclic graph.  
Each  calculation is represented by a node, that is linked to its input and output data nodes.
The provenance graph is stored  in a local database that can be queried typing:
```
   verdi node graph generate <PK>
```   
where the PK is the one identifying teh calculation of interest. Finally, one can easily 
convert the graph into a pdf format for visualization:
```
   evince pk.dot.pdf .
```