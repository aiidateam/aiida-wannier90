Documentation of the parsed outputs of the aiida-wannier90 plugin
==================================================================

This is the list of output parsed nodes.

``output_parameters``
---------------------
A :py:class:`~aiida.orm.Dict` node (accessed by ``calculation.res``).
Contains a number of parsed properties. Currently it includes:

* ``number_wfs``: the number of Wannier functions.

* ``Omega_D``, ``Omega_I``, ``Omega_OD``, ``Omega_total``: the components
  of the spread. They contain, respectively,
  the diagonal part :math:`\Omega_D`, the gauge-invariant part
  :math:`\Omega_I`, the off-diagonal part :math:`\Omega_{OD}`, and the
  total spread :math:`\Omega_{total}`. Units are always :math:`\mathring{A}^2`.

* ``wannier_functions_output``: a list of dictionaries containing:

  - ``wf_ids``: integer index of the Wannier functions
  - ``wf_centres``: the centre of the Wannier functions,
    in :math:`\mathring{A}`.
  - ``wf_spreads``: the spread of the wannier functions,
    in :math:`\mathring{A}^2`.
  - ``im_re_ratio``: if available, the Imaginary/Real ratio of the Wannier
    functions.

* ``warnings``: parsed list of warnings (see section
  :ref:`my-ref-parsed_warnings`).

* ``length_units``: units used to express the lengths.
  If these are not :math:`\mathring{A}`, a warning will be added to the
  ``warnings`` list.

* ``output_verbosity``: the output verbosity. A warning is thrown if any
  value other than the default is used.

* ``preprocess_only``: whether the calculation only performed the
  preprocessing step (``wannier90 -pp``).

* ``r2mn_writeout``: whether the :math:`r^2_{mn}` file was written.

* ``convergence_tolerance``: the tolerance for convergence on the spread, in
  units of :math:`\mathring{A}^2`.

* ``xyz_writeout``: whether `the `xyz_wf_centre`` file was explicitly written.

* Other parameters, if present, should match those described in the user guide.

``interpolated_bands``
----------------------
A :py:class:`BandsData <aiida.orm.BandsData>` node. If a band structure is
required, it will contain the bands interpolated using Wannier functions.


.. _my-ref-parsed_warnings:

Warnings
--------
Currently some errors are parsed but mostly are handled as human-readable
strings instead of using error codes.

Parsing errors are reported in the log of the calculation
(accessible with the ``verdi process logshow`` command).
Moreover, they are stored in the ``output_parameters`` output
:py:class:`~aiida.orm.Dict` node, under the key ``warnings``,
and are accessible with ``calc.res.warnings``.

Here we report the warnings produced by the parser:

- Check in what units the inputs are given. If not :math:`\mathring{A}`,
  the code prints out: ``Units not Ang, be sure this is OK!``.

- Check the output verbosity. If different than 1, the parser cannot work
  as expected, and the code prints out: ``Parsing is only supported if
  output verbosity is set to 1``.

- If the Wannierisation procedure stops after reaching the ``num_iter`` set
  in the input, the code prints out: ``Wannierisation finished because
  num_iter was reached.``. This typically means that the convergence has
  not been reached.

- When the number of items in each line of ``_band.labelinfo.dat`` is not
  equal to 6, the code warns: ``Wrong number of items in line XXX of the
  labelinfo file - I will not assign that label``

- When the second column (i.e. the index) of each line in
  ``_band.labelinfo.dat`` is not an integer, then the code warns:
  ``Invalid value for the index in line XXX of the labelinfo file,
  it's not an integer - I will not assign that label``.

- If you use a Wannier90 version before v3.0, the file ``_band.labelinfo.dat``
  is not generated. Thus, the old version of the parser
  (i.e. ``band_parser_legacy``) will be used, but it needs to guess the
  exact position of the high-symmetry points. Therefore it will output the
  following warning: ``Note: no file named SEEDNAME_band.labelinfo.dat found.
  You are probably using a version of Wannier90 before 3.0.
  There, the labels associated with each k-points were not printed in output
  and there were also cases in which points were not calculated
  (see issue #195 on the Wannier90 GitHub page).
  I will anyway try to do my best to assign labels,
  but the assignment might be wrong
  (especially if there are path discontinuities)``.
