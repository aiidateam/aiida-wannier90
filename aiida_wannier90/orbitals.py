#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Creating OrbitalData instances
==============================
"""
__all__ = ['generate_projections']


def _generate_wannier_orbitals(
    position_cart=None,
    structure=None,
    kind_name=None,
    radial=1,
    ang_mtm_name=None,
    ang_mtm_l=None,
    ang_mtm_mr=None,
    spin=None,
    zona=None,
    zaxis=None,
    xaxis=None,
    spin_axis=None
):
    """
    Use this method to emulate the input style of wannier90,
    when setting the orbitals (see chapter 3 in the user_guide). Position
    can be provided either in cartesian coordiantes using position_cart
    or can be assigned based on an input structure and kind_name.

    :param position_cart: position in cartesian coordinates or list of
                          positions in cartesian coodriantes
    :param structure: input structure for use with kind_names
    :param kind_name: kind_name, for use with the structure
    :param radial: number of radial nodes
    :param ang_mtm_name: orbital name or list of orbital names, cannot
                         be used in conjunction with ang_mtm_l or
                         ang_mtm_mr
    :param ang_mtm_l: angular momentum, if ang_mtm_mr is not specified
                      will return all orbitals associated with it
    :param ang_mtm_mr: magnetic angular momentum number must be specified
                       along with ang_mtm_l
    :param spin: the spin, spin up can be specified with 1,u or U and
                 spin down can be specified using -1,d,D
    :param zona: as specified in user guide, applied to all orbitals
    :param zaxis: the zaxis, list of three floats
                  as described in wannier user guide
    :param xaxis: the xaxis, list of three floats as described in the
                  wannier user guide
    :param spin_axis: the spin alignment axis, as described in the
                      user guide
    """
    from aiida.orm import DataFactory
    from aiida.orm.data.orbital import OrbitalFactory

    def convert_to_list(item):
        """
        internal method, checks if the item is already a list or tuple.
        if not returns a tuple containing only item, otherwise returns
        tuple(item)
        """
        if isinstance(item, (list, tuple)):
            return tuple(item)
        else:
            return tuple([item])

    def combine_dictlists(dict_list1, dict_list2):
        """
        Creates a list of every dict in dict_list1 updated with every
        dict in dict_list2
        """
        out_list = []
        # excpetion handling for the case of empty dicts
        dict_list1_empty = not any([bool(x) for x in dict_list1])
        dict_list2_empty = not any([bool(x) for x in dict_list2])
        if dict_list1_empty and dict_list2_empty:
            raise InputValidationError('One dict must not be empty')
        if dict_list1_empty:
            return dict_list2
        if dict_list2_empty:
            return dict_list2

        for dict_1 in dict_list1:
            for dict_2 in dict_list2:
                temp_1 = dict_1.copy()
                temp_2 = dict_2.copy()
                temp_1.update(temp_2)
                out_list.append(temp_1)
        return out_list

    RealhydrogenOrbital = OrbitalFactory('realhydrogen')

    #########################################################################
    # Validation of inputs                                                  #
    #########################################################################
    if position_cart == None and kind_name == None:
        raise InputValidationError('Must supply a kind_name or position')
    if position_cart != None and kind_name != None:
        raise InputValidationError(
            'Must supply position or kind_name'
            ' not both'
        )

    structure_class = DataFactory('structure')
    if kind_name != None:
        if not isinstance(structure, structure_class):
            raise InputValidationError(
                'Must supply a StructureData as '
                'structure if using kind_name'
            )
        if not isinstance(kind_name, basestring):
            raise InputValidationError('kind_name must be a string')

    if ang_mtm_name == None and ang_mtm_l == None:
        raise InputValidationError("Must supply ang_mtm_name or ang_mtm_l")
    if ang_mtm_name != None and (ang_mtm_l != None or ang_mtm_mr != None):
        raise InputValidationError(
            "Cannot supply ang_mtm_l or ang_mtm_mr"
            " but not both"
        )
    if ang_mtm_l == None and ang_mtm_mr != None:
        raise InputValidationError(
            "Cannot supply ang_mtm_mr without "
            "ang_mtm_l"
        )

    ####################################################################
    #Setting up initial basic parameters
    ####################################################################
    projection_dict = {}
    if radial:
        projection_dict['radial_nodes'] = radial - 1
    if xaxis:
        projection_dict['x_orientation'] = xaxis
    if zaxis:
        projection_dict['z_orientation'] = zaxis
    if kind_name:
        projection_dict['kind_name'] = kind_name
    if spin_axis:
        projection_dict['spin_orientation'] = spin_axis
    if zona:
        projection_dict['diffusivity'] = zona

    projection_dicts = [projection_dict]

    #####################################################################
    # Setting up Positions                                              #
    #####################################################################
    # finds all the positions to append the orbitals to (if applicable)
    position_list = []
    if kind_name:
        for site in structure.sites:
            if site.kind_name == kind_name:
                position_list.append(site.position)
        if len(position_list) == 0:
            raise InputValidationError(
                "No valid positions found in structure "
                "using {}".format(kind_name)
            )
    # otherwise turns position into position_list
    else:
        position_list = [convert_to_list(position_cart)]
    position_dicts = [{"position": v} for v in position_list]
    projection_dicts = combine_dictlists(projection_dicts, position_dicts)

    #######################################################################
    # Setting up angular momentum                                         #
    #######################################################################
    # if ang_mtm_l, ang_mtm_mr provided, setup dicts
    if ang_mtm_l is not None:
        ang_mtm_l = convert_to_list(ang_mtm_l)
        ang_mtm_dicts = []
        for l in ang_mtm_l:
            if l >= 0:
                ang_mtm_dicts += [{
                    'angular_momentum': l,
                    'magnetic_number': i
                } for i in range(2 * l + 1)]
            else:
                ang_mtm_dicts += [{
                    'angular_momentum': l,
                    'magnetic_number': i
                } for i in range(-l + 1)]
        if ang_mtm_mr is not None:
            if len(ang_mtm_l) > 1:
                raise InputValidationError(
                    "If you are giving specific"
                    " magnetic numbers please do"
                    " not supply more than one"
                    " angular number."
                )
            ang_mtm_mr = convert_to_list(ang_mtm_mr)
            ang_mtm_l_num = ang_mtm_l[0]
            ang_mtm_dicts = [{
                'angular_momentum': ang_mtm_l_num,
                'magnetic_number': j - 1
            } for j in ang_mtm_mr]
    if ang_mtm_name is not None:
        ang_mtm_names = convert_to_list(ang_mtm_name)
        ang_mtm_dicts = []
        for name in ang_mtm_names:
            ang_mtm_dicts += RealhydrogenOrbital.get_quantum_numbers_from_name(
                name
            )
    projection_dicts = combine_dictlists(projection_dicts, ang_mtm_dicts)

    #####################################################################
    # Setting up the spin                                               #
    #####################################################################
    if spin:
        spin_dict = {'U': 1, 'u': 1, 1: 1, 'D': -1, 'd': -1, -1: -1}
        if isinstance(spin, (list, tuple)):
            spin = [spin_dict[x] for x in spin]
        else:
            spin = [spin_dict[spin]]
        spin_dicts = [{'spin': v} for v in spin]
        projection_dicts = combine_dictlists(projection_dicts, spin_dicts)

    # generating and returning a list of all corresponding orbitals
    orbital_out = []
    for projection_dict in projection_dicts:
        realh = RealhydrogenOrbital()
        realh.set_orbital_dict(projection_dict)
        orbital_out.append(realh)
    return orbital_out


def generate_projections(list_of_projection_dicts, structure):
    """
    Use this method to emulate the input style of wannier90,
    when setting the orbitals (see chapter 3 in the wannier90 user guide).
    Position can be provided either in cartesian coordiantes using
    position_cart or can be assigned based on an input structure and
    kind_name. Pass a **list of dictionaries**, in which the keys of each
    dictionary correspond to those below. Also that *radial*,
    and *ang_mtm_mr* both use 0 indexing as opposed to 1 indexing,
    effectively meaning that both should be offset by 1. E.g. an orbital
    with 1 radial node would use radial=2 (wannier90 syntax), and then
    be converted to radial_nodes=1 (AiiDa plugin syntax)
    inside the stored orbital.

    .. note:: The key entries used here, may not correspond to the keys used
              internally by the orbital objects, for example, ``ang_mtm_mr``
              will be converted to ``magnetic_number`` in the orbital object
              the value stored in orbital is listed in (braces).

    .. note:: To keep in line with python-indexing as much as possible,
              the values of radial, and ang_mtm_mr our out of sync with
              their radial_nodes, angular_momentum counterparts.
              Specifically, radial and ang_mtm_mr both start at 1 while
              radial_nodes and angular_momentum both start at 0, thus
              making the two off by a factor of 1.

    :param position_cart: position in cartesian coordinates or list of
                          positions in cartesian coordinates (position)
    :param kind_name: kind_name, for use with the structure (kind_name)
    :param radial: number of radial nodes (radial_nodes + 1)
    :param ang_mtm_name: orbital name or list of orbital names, cannot
                         be used in conjunction with ang_mtm_l or
                         ang_mtm_mr (See ang_mtm_l and ang_mtm_mr)
    :param ang_mtm_l: angular momentum, if ang_mtm_mr is not specified
                      will return all orbitals associated with it
                      (angular_momentum)
    :param ang_mtm_mr: magnetic angular momentum number must be specified
                       along with ang_mtm_l (magnetic_number + 1)
    :param spin: the spin, spin up can be specified with 1,u or U and
                 spin down can be specified using -1,d,D (spin)
    :param zona: as specified in user guide, applied to all orbitals
                 (diffusivity)
    :param zaxis: the zaxis, list of three floats
                  as described in wannier user guide (z_orientation)
    :param xaxis: the xaxis, list of three floats as described in the
                  wannier user guide (x_orientation)
    :param spin_axis: the spin alignment axis, as described in the
                      user guide (spin_orientation)
    """
    from aiida.orm import DataFactory

    if not isinstance(list_of_projection_dicts, (list, tuple)):
        list_of_projection_dicts = [list_of_projection_dicts]
    orbitals = []
    for this_dict in list_of_projection_dicts:
        if 'kind_name' in this_dict:
            this_dict.update({'structure': structure})
        orbitals += _generate_wannier_orbitals(**this_dict)
    orbitaldata = DataFactory('orbital')()
    orbitaldata.set_orbitals(orbitals)
    return orbitaldata
