#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import copy

from aiida.common.utils import conv_to_fortran_withlists
from aiida.common.exceptions import InputValidationError, ModificationNotAllowed

from ._group_list import list_to_grouped_string

__all__ = ['write_win']


def write_win(
    filename,
    parameters,
    kpoints=None,
    structure=None,
    kpoint_path=None,
    projections=None,
    random_projections=False,
):
    """
    Write input to a ``.win`` file.

    :param filename: Path of the file where the input is written.
    :type filename: str

    :param parameters: Additional input parameters, as specified in the Wannier90 user guide.
    :type parameters: dict, aiida.orm.data.parameter.ParameterData

    :param structure: Structure of the calculated material.
    :type structure: aiida.orm.data.structure.StructureData

    :param kpoints: Mesh of k-points used for the Wannierization procedure.
    :type kpoints: aiida.orm.data.array.kpoints.KpointsData

    :param kpoint_path: List of k-points used for band interpolation.
    :type kpoint_path: aiida.orm.data.parameter.ParameterData

    :param projections: Orbitals used for the projections. Can be specified either as AiiDA OrbitalData, or as a list of strings specifying the projections in Wannier90's format.
    :type projections: aiida.orm.data.orbital.OrbitalData, aiida.orm.data.base.List[str]

    :param random_projections: If OrbitalData is used for projections, enables random projections completion
    :type random_projections: aiida.orm.data.base.Bool
    """
    with open(filename, 'w') as file:
        file.write(
            _create_win_string(
                parameters=parameters,
                structure=structure,
                kpoints=kpoints,
                kpoint_path=kpoint_path,
                projections=projections,
                random_projections=random_projections,
            )
        )


def _create_win_string(
    parameters,
    kpoints,
    structure=None,
    kpoint_path=None,
    projections=None,
    random_projections=False,
):
    from aiida.orm import DataFactory
    from aiida.orm.data.base import List

    # prepare the main input text
    input_file_lines = []
    if isinstance(parameters, DataFactory('parameter')):
        parameters = parameters.get_dict()
    try:
        parameters.setdefault('mp_grid', kpoints.get_kpoints_mesh()[0])
    except AttributeError:
        pass
    input_file_lines += _format_parameters(parameters)

    block_inputs = {}
    if projections is None:
        # If no projections are specified, random projections is used (Dangerous!)
        if random_projections:
            block_inputs['projections'] = ['random']
        else:
            block_inputs['projections'] = []
    elif isinstance(projections, (tuple, list)):
        if random_projections:
            raise InputValidationError(
                'random_projections cannot be True with (tuple,list) projections.'
                'Instead, use "random" string as first element of the list.'
            )
        block_inputs['projections'] = projections
    elif isinstance(projections, List):
        if random_projections:
            raise InputValidationError(
                'random_projections cannot be True if with List-type projections.'
                'Instead, use "random" string as first element of the List.'
            )
        block_inputs['projections'] = projections.get_attr('list')
    else:
        block_inputs['projections'] = _format_all_projections(
            projections, random_projections=True
        )

    if structure is not None:
        block_inputs['unit_cell_cart'] = _format_unit_cell(structure)
        block_inputs['atoms_cart'] = _format_atoms_cart(structure)
    if kpoints is not None:
        block_inputs['kpoints'] = _format_kpoints(kpoints)
    if kpoint_path is not None:
        block_inputs['kpoint_path'] = _format_kpoint_path(kpoint_path)
    input_file_lines += _format_block_inputs(block_inputs)

    return '\n'.join(input_file_lines) + '\n'


def _format_parameters(parameters_dict):
    """
    Join key / value pairs of the parameters dictionary into formatted strings, returning a list of lines for the .win file.
    """
    lines = []
    for key, value in sorted(
        _format_parameter_values(parameters_dict).items()
    ):
        lines.append(key + ' = ' + value)
    return lines


def _format_parameter_values(parameters_dict):
    """
    Turn the values of the parameters dictionary into the appropriate string.
    """
    result_dict = {}
    for key, value in parameters_dict.items():
        key = key.lower()
        if key == 'exclude_bands':
            result_dict[key] = list_to_grouped_string(value)
        else:
            result_dict[key] = conv_to_fortran_withlists(
                value, quote_strings=False
            )
    return result_dict


def _format_all_projections(projections, random_projections=False):
    """
    Return a list of strings, they are the lines to insert into
    Wannier90 projections block.

    :param projections: OrbitalData object with projections info
    :param random_projections: if True, add the 'random' keyword on top.
        It asks the code to fill missing projections with random orbitals (see Wannier90 docs)
    """
    projection_list = projections.get_orbitals()
    # TODO: Check if spinor_projections actually needs to be used.
    # spin_use = any([bool(projection.get_orbital_dict()['spin'])
    #                 for projection in projection_list])
    # projector_type = "spinor_projections" if spin_use else "projections"
    projection_lines = [
        _format_single_projection(projection) for projection in projection_list
    ]
    if random_projections:
        projection_lines = ['random'] + projection_lines
    return projection_lines


def _format_single_projection(orbital):
    """
    Creates an appropriate wannier line from input orbitaldata,
    will raise an exception if the orbital does not contain enough
    information, or the information is badly formated
    """
    from aiida.common.orbital import OrbitalFactory
    RealhydrogenOrbital = OrbitalFactory("realhydrogen")

    if not isinstance(orbital, RealhydrogenOrbital):
        raise InputValidationError(
            "Only realhydrogen orbitals are currently supported for Wannier90 input."
        )
    orb_dict = copy.deepcopy(orbital.get_orbital_dict())

    def _get_attribute(name, required=True):
        res = orb_dict.get(name, None)
        if res is None and required:
            raise InputValidationError(
                "Orbital is missing attribute '{}'.".format(name)
            )
        return res

    def _format_projection_values(name, value):
        if value is None:
            return ''
        if not isinstance(value, (tuple, list)):
            value = [value]
        return '{}={}'.format(name, ','.join(str(x) for x in value))

    # required arguments
    position = _get_attribute("position")
    angular_momentum = _get_attribute("angular_momentum")
    magnetic_number = _get_attribute("magnetic_number")
    wann_string = (
        _format_projection_values('c', position) + ':' +
        _format_projection_values('l', angular_momentum) + ',' +
        _format_projection_values('mr', magnetic_number + 1)
    )

    # optional, colon-separated arguments
    zaxis = _get_attribute("z_orientation", required=False)
    xaxis = _get_attribute("x_orientation", required=False)
    radial = _get_attribute("radial_nodes", required=False)
    zona = _get_attribute("diffusivity", required=False)
    if any(arg is not None for arg in [zaxis, xaxis, radial, zona]):
        zaxis_string = _format_projection_values('z', zaxis)
        xaxis_string = _format_projection_values('x', xaxis)
        radial_string = _format_projection_values('r', radial + 1)
        zona_string = _format_projection_values('zona', zona)
        wann_string += ':{}:{}:{}:{}'.format(
            zaxis_string, xaxis_string, radial_string, zona_string
        )

    # spin, optional
    # Careful with spin, it is insufficient to set the spin the projection
    # line alone. You must, in addition, apply the appropriate settings:
    # either set spinors=.true. or use spinor_projections, see user guide
    spin = _get_attribute("spin", required=False)
    if spin is not None:
        spin_dict = {-1: "d", 1: "u"}
        wann_string += "({})".format(spin_dict[spin])
    spin_orient = _get_attribute("spin_orientation", required=False)
    if spin_orient is not None:
        wann_string += "[" + ",".join([str(x) for x in spin_orient]) + "]"

    return wann_string


def _format_unit_cell(structure):
    return ['ang'] + [
        "{0:18.10f} {1:18.10f} {2:18.10f}".format(*vector)
        for vector in structure.cell
    ]


def _format_atoms_cart(structure):
    """
    Generates site locations and cell dimensions
    in a manner that can be used by the wannier90 input script
    """

    def list2str(list_item):
        '''
        Converts an input list item into a str
        '''
        list_item = copy.deepcopy(list_item)
        if isinstance(list_item, (str, unicode)):
            return list_item
        else:
            return ' ' + ' '.join([str(_) for _ in list_item]) + ' '

    return ['ang'] + [
        '{}  {}'.format(site.kind_name, list2str(site.position))
        for site in structure.sites
    ]


def _format_kpoints(kpoints):
    # KpointsData was set with set_kpoints_mesh
    try:
        all_kpoints = kpoints.get_kpoints_mesh(print_list=True)
    # KpointsData was set with set_kpoints
    except AttributeError:
        all_kpoints = kpoints.get_kpoints()
    return ["{:18.10f} {:18.10f} {:18.10f}".format(*k) for k in all_kpoints]


def _format_kpoint_path(kpoint_path):
    """
    Prepare the lines for the Wannier90 input file related to
    the kpoint_path.

    :param kpoint_path_info: a ParameterData containing two entries:
        a 'path' list with the labels of the endpoints of each
        path segment, and a dictionary called "point_coords" that gives the
        three (fractional) coordinates for each label.
    :return: a list of strings to be added to the input file, within the
        kpoint_info block
    """
    kinfo = kpoint_path.get_dict()
    path = kinfo.pop('path')
    point_coords = kinfo.pop('point_coords')
    if kinfo:
        raise InputValidationError(
            'kpoint_path_info must be contain only a '
            'list called "path" with the labels of the endpoints of each '
            'path segment, and a dictionary called "point_coords". It contains '
            'instead also other keys: {}'.format(", ".join(kinfo.keys()))
        )

    # In Wannier90 (from the user guide): Values are in
    # fractional coordinates with respect to the primitive
    # reciprocal lattice vectors.
    res = []
    for (point1, point2) in path:
        coord1 = point_coords[point1]
        coord2 = point_coords[point2]
        path_line = '{} {} {} {} '.format(point1, *coord1)
        path_line += ' {} {} {} {}'.format(point2, *coord2)
        res.append(path_line)
    return res


def _format_block_inputs(block_inputs):
    res = []
    for name, lines in sorted(block_inputs.items()):
        res.append('')
        res.append('begin {}'.format(name))
        res.extend(lines)
        res.append('end {}'.format(name))
    return res
