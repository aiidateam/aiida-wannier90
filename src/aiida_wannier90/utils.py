################################################################################
# Copyright (c), AiiDA team and individual contributors.                       #
#  All rights reserved.                                                        #
# This file is part of the AiiDA-wannier90 code.                               #
#                                                                              #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-wannier90 #
# For further information on the license, see the LICENSE.txt file             #
################################################################################
"""Utilities."""
import numbers

__all__ = ("plot_centres_xsf", "conv_to_fortran", "conv_to_fortran_withlists")


def plot_centres_xsf(structure, w90_calc, filename="./wannier.xsf"):
    """Plot Wannier function centres in .xsf format."""
    # Disabling the import-error since this is an optional requirement
    import ase  # pylint: disable=import-error,useless-suppression

    a = structure.get_ase()
    new_a = a.copy()
    out = w90_calc.out.output_parameters.get_dict()["wannier_functions_output"]
    coords = [i["wf_centres"] for i in out]
    for c in coords:
        new_a.append(ase.Atom("X", c))
    new_a.write(filename)


def conv_to_fortran(val, quote_strings=True):
    """Convert the input ``val`` to a Fortran-friendly string."""
    # Note that bool should come before integer, because a boolean matches also
    # isinstance(...,int)
    import numpy

    if isinstance(val, (bool, numpy.bool_)):
        if val:
            val_str = ".true."
        else:
            val_str = ".false."
    elif isinstance(val, numbers.Integral):
        val_str = f"{val:d}"
    elif isinstance(val, numbers.Real):
        val_str = (f"{val:18.10e}").replace("e", "d")
    elif isinstance(val, str):
        if quote_strings:
            val_str = f"'{val!s}'"
        else:
            val_str = f"{val!s}"
    else:
        raise ValueError(
            f"Invalid value '{val}' of type '{type(val)}' passed, accepts only bools, ints, floats and strings"
        )

    return val_str


def conv_to_fortran_withlists(val, quote_strings=True):
    """Convert to Fortran, same as conv_to_fortran but with extra logic to handle lists."""
    # pylint: disable=too-many-return-statements

    # Note that bool should come before integer, because a boolean matches also
    # isinstance(...,int)
    if isinstance(val, (list, tuple)):
        val_str = ", ".join(
            conv_to_fortran(thing, quote_strings=quote_strings) for thing in val
        )
        return val_str

    if isinstance(val, bool):
        if val:
            return ".true."

        return ".false."

    if isinstance(val, int):
        return f"{val:d}"

    if isinstance(val, float):
        return f"{val:18.10e}".replace("e", "d")

    if isinstance(val, str):
        if quote_strings:
            return f"'{val!s}'"

        return f"{val!s}"

    raise ValueError(
        "Invalid value passed, accepts only bools, ints, floats and strings"
    )
