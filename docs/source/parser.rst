Documentation of the parsed outputs of the aiida-wannier90 plugin
==================================================================

Outputs
-------
* output_parameters :py:class:`Dict <aiida.orm.Dict>` (accessed by ``calculation.res``). Contains the scalar properties. Currently parsed parameters include:

  * ``number_wfs``: the number of Wannier functions
  * ``Omega_D``, ``Omega_I``, ``Omega_OD``, ``Omega_total`` which are: the diagonal :math:`\Omega_D`,
     gauge-invariant  :math:`\Omega_I`, off-diagonal :math:`\Omega_{OD}`, and total spread :math:`\Omega_{total}`. Units are always Ang^2
  * ``wannier_functions_output`` a list of dictionaries containing:

    - wf_centres: the center of the wannier function
    - wf_spreads: the spread of the wannier function. Units are always Ang^2
    - wf_ids: numerical index of the wannier function
    - im_re_ratio: if available, the Imaginary/Real ratio of the wannier function

  * ``warnings``: parsed list of warnings
  * ``length_units``: Units used to express the lengths, if not Ang we will have an additional warning in the list warnings
  * ``output_verbosity``: the output verbosity, throws a warning if any value other than default is used
  * ``preprocess_only``: whether the calc only did the preprocessing step ``wannier90 -pp``
  * ``r2mn_writeout``: whether :math:`r^2_{mn}` file was written
  * ``convergence_tolerence``: the tolerance for convergence, units of Ang^2
  * ``xyz_writeout``: whether xyz_wf_center file was explicitly and independently written
  * Other parameters, should match those described in the user guide
    
* interpolated_bands :py:class:`BandsData <aiida.orm.BandsData>`
  If available, will parse the interpolated bands and store them.


Errors
------
Errors of the parsing are reported in the log of the calculation (accessible with the ``verdi calculation logshow`` command). Moreover, they are stored in the Dict under the key ``warnings``, and are accessible with ``calc.res.warnings``.
Here we report the warnings currently produced by the parser:

    - 'Units not Ang, be sure this is OK!': check the units given in input.
    - 'Parsing is only supported directly supported if output verbosity is set to 1': if output verbosity is not 1 the parser complains informing the user that it is disabled.
    - 'The r^2_nm file has been selected to be written, but this is not yet supported!': it complains because the parsing of this file is not yet supported.
    - 'The xyz_WF_center file has been selected to be written, but this is not yet supported!': same as above.
    - 'Wannierisation finished because num_iter was reached.': the wannierization procedure has stopped due tu maximum number of iterations set reached.
    - 'Wrong number of items in line {} of the labelinfo file -I will not assign that label'
    - 'Invalid value for the index in line {} of the labelinfo file, it's not an integer - I will not assign that label'
    - 'Note: no file named SEEDNAME_band.labelinfo.dat found. You are probably using a version of Wannier90 before 3.0. There, the labels associated with each k-points were not printed in output  and there were also cases in which points were not calculated (see issue #195 on the Wannier90 GitHub page). I will anyway try to do my best to assign labels, but the assignment might be wrong (especially if there are path discontinuities).'