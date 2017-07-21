#!/usr/bin/env python
# -*- coding: utf-8 -*-

def write_win(filename, ):
    # prepare the main input text
    input_file_lines = []
    from aiida.common.utils import conv_to_fortran_withlists
    for param in param_dict:
        input_file_lines.append(param + ' = ' + conv_to_fortran_withlists(
            param_dict[param]))

    # take projections dict and write to file
    # checks if spins are used, and modifies the opening line
    projection_list = projections.get_orbitals()
    spin_use = any([bool(projection.get_orbital_dict()['spin'])
                    for projection in projection_list])
    if spin_use:
        raise InputValidationError("Spinors are implemented but not tested"
                                   "disable this error if you know what "
                                   "you are doing!")
        projector_type = "spinor_projections"
    else:
        projector_type = "projections"
    input_file_lines.append('Begin {}'.format(projector_type))
    for projection in projection_list:
        orbit_line = _print_wann_line_from_orbital(projection)
        input_file_lines.append(orbit_line)
    input_file_lines.append('End {}'.format(projector_type))

    # convert the structure data
    input_file_lines.append("Begin unit_cell_cart")
    input_file_lines.append('ang')
    for vector in structure.cell:
        input_file_lines.append("{0:18.10f} {1:18.10f} {2:18.10f}".format
                                (*vector))
    input_file_lines.append('End unit_cell_cart')

    input_file_lines.append('Begin atoms_cart')
    input_file_lines.append('ang')
    wann_positions, wann_kind_names = _wann_site_format(structure.sites)
    atoms_cart = zip(wann_kind_names, wann_positions)
    for atom in atoms_cart:
        input_file_lines.append('{}  {}'.format(atom[0], atom[1]))
    input_file_lines.append('End atoms_cart')

    # convert the kpoints_path
    try:
        special_points = kpoints_path.get_special_points()
    except ModificationNotAllowed:
        raise InputValidationError('kpoints_path must be kpoints with '
                                   'a special kpoint path already set!')

    input_file_lines.append('Begin Kpoint_Path')
    for (point1, point2) in special_points[1]:
        coord1 = special_points[0][point1]
        coord2 = special_points[0][point2]
        path_line = '{} {} {} {} '.format(point1, *coord1)
        path_line += ' {} {} {} {}'.format(point2, *coord2)
        input_file_lines.append(path_line)
    input_file_lines.append('End Kpoint_Path')

    # convert the kmesh
    try:
        kmesh = kpoints.get_kpoints_mesh()[0]
    except AttributeError:
        raise InputValidationError('kpoints should be set with '
                                   'set_kpoints_mesh, '
                                   'and not set_kpoints... ')

    mp_line = 'mp_grid = {},{},{}'.format(*kmesh)
    input_file_lines.append(mp_line)

    input_file_lines.append('Begin kpoints')
    for vector in kpoints.get_kpoints_mesh(print_list=True):
        input_file_lines.append("{0:18.10f} {1:18.10f} {2:18.10f}"
                                .format(*vector))
    input_file_lines.append('End kpoints')

    input_filename = tempfolder.get_abs_path(self._DEFAULT_INPUT_FILE)
    with open(input_filename, 'w') as file:
        file.write("\n".join(input_file_lines))
        file.write("\n")

def _wann_site_format(structure_sites):
    '''
    Generates site locations and cell dimensions
    in a manner that can be used by the wannier90 input script
    '''
    def list2str(list_item):
        '''
        Converts an input list item into a str
        '''
        list_item = copy.deepcopy(list_item)
        if isinstance(list_item, (str, unicode)):
            return list_item
        else:
            return ' ' + ' '.join([str(_) for _ in list_item]) + ' '

    calc_positions = []
    calc_kind_names = []
    for i in range(len(structure_sites)):
        calc_positions.append(list2str(structure_sites[i].position))
        calc_kind_names.append(structure_sites[i].kind_name)
    return calc_positions, calc_kind_names
