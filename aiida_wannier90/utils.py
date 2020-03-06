# -*- coding: utf-8 -*-
################################################################################
# Copyright (c), AiiDA team and individual contributors.                       #
#  All rights reserved.                                                        #
# This file is part of the AiiDA-wannier90 code.                               #
#                                                                              #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-wannier90 #
# For further information on the license, see the LICENSE.txt file             #
################################################################################
from __future__ import absolute_import
import numbers

import six

__all__ = ('plot_centres_xsf', 'conv_to_fortran', 'conv_to_fortran_withlists')


def plot_centres_xsf(structure, w90_calc, filename='./wannier.xsf'):
    """
    Plots Wannier function centres in .xsf format
    """
    # Disabling the import-error since this is an optional requirement
    import ase  # pylint: disable=import-error

    a = structure.get_ase()
    new_a = a.copy()
    out = w90_calc.out.output_parameters.get_dict()['wannier_functions_output']
    coords = [i['wf_centres'] for i in out]
    for c in coords:
        new_a.append(ase.Atom('X', c))
    new_a.write(filename)


def conv_to_fortran(val, quote_strings=True):
    """
    :param val: the value to be read and converted to a Fortran-friendly string.
    """
    # Note that bool should come before integer, because a boolean matches also
    # isinstance(...,int)
    import numpy

    if isinstance(val, (bool, numpy.bool_)):
        if val:
            val_str = '.true.'
        else:
            val_str = '.false.'
    elif isinstance(val, numbers.Integral):
        val_str = "{:d}".format(val)
    elif isinstance(val, numbers.Real):
        val_str = ("{:18.10e}".format(val)).replace('e', 'd')
    elif isinstance(val, six.string_types):
        if quote_strings:
            val_str = "'{!s}'".format(val)
        else:
            val_str = "{!s}".format(val)
    else:
        raise ValueError(
            "Invalid value '{}' of type '{}' passed, accepts only bools, ints, floats and strings"
            .format(val, type(val))
        )

    return val_str


def conv_to_fortran_withlists(val, quote_strings=True):
    """
    Same as conv_to_fortran but with extra logic to handle lists
    :param val: the value to be read and converted to a Fortran-friendly string.
    """
    # pylint: disable=too-many-return-statements

    # Note that bool should come before integer, because a boolean matches also
    # isinstance(...,int)
    if isinstance(val, (list, tuple)):
        val_str = ", ".join(
            conv_to_fortran(thing, quote_strings=quote_strings)
            for thing in val
        )
        return val_str

    if isinstance(val, bool):
        if val:
            return '.true.'

        return '.false.'

    if isinstance(val, six.integer_types):
        return "{:d}".format(val)

    if isinstance(val, float):
        return "{:18.10e}".format(val).replace('e', 'd')

    if isinstance(val, six.string_types):
        if quote_strings:
            return "'{!s}'".format(val)

        return "{!s}".format(val)

    raise ValueError(
        "Invalid value passed, accepts only bools, ints, floats and strings"
    )
