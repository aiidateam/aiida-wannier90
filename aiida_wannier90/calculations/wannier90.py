# -*- coding: utf-8 -*-
import os
import copy

import numpy as np

from aiida.common.utils import classproperty
from aiida.common.exceptions import InputValidationError, ModificationNotAllowed
from aiida.common.datastructures import CalcInfo, CodeInfo, code_run_modes
from aiida.orm import JobCalculation, DataFactory
from aiida.orm.calculation.job.quantumespresso import (
    _uppercase_dict, get_input_data_text)
from aiida.orm.calculation.job.quantumespresso.pw import PwCalculation
from aiida.orm.code import Code
from aiida.orm.data.array.kpoints import KpointsData
from aiida.orm.data.orbital import OrbitalData, OrbitalFactory
from aiida.orm.data.parameter import ParameterData
from aiida.orm.data.remote import RemoteData
from aiida.orm.data.structure import StructureData
from aiida.orm.data.folder import FolderData
try:
    from aiida.backends.utils import get_authinfo
except ImportError:
    from aiida.execmanager import get_authinfo

from ..orbitals import generate_projections as _generate_projections

__authors__ = "Daniel Marchand, Antimo Marrazzo, Dominik Gresch & The AiiDA team."
__copyright__ = u"Copyright (c), This file is part of the AiiDA platform. For further information please visit http://www.aiida.net/. All rights reserved"
__license__ = "Non-Commercial, End-User Software License Agreement, see LICENSE.txt file."


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


class Wannier90Calculation(JobCalculation):
    """
    Plugin for Wannier90, a code for producing maximally localized Wannier
    functions. See http://www.wannier.org/ for more details
    """

    def _init_internal_params(self):
        super(Wannier90Calculation, self)._init_internal_params()

        self._SEEDNAME = 'aiida'
        self._DEFAULT_INPUT_FILE = self._SEEDNAME + '.win'
        self._DEFAULT_OUTPUT_FILE = self._SEEDNAME + '.wout'
        self._ERROR_FILE_NAME = self._SEEDNAME + '.werr'
        self._default_parser = 'wannier90.wannier90'
        self._CHK_FILE = self._SEEDNAME + '.chk'
        self._blocked_keywords = [['length_unit', 'ang']]
        self._blocked_precode_keywords = []

    @classproperty
    def _use_methods(cls):
        """
        Additional use_* methods for the Wannier90 calculation class.
        """
        retdict = JobCalculation._use_methods
        retdict.update({
            "structure": {
                'valid_types': StructureData,
                'additional_parameter': None,
                'linkname': 'structure',
                'docstring': "Choose the input structure to use",
            },
            "settings": {
                'valid_types': ParameterData,
                'additional_parameter': None,
                'linkname': 'settings',
                'docstring': "Use an additional node for special settings",
            },
            "parameters": {
                'valid_types': ParameterData,
                'additional_parameter': None,
                'linkname': 'parameters',
                'docstring': ("Use a node that specifies the input parameters "
                              "for the wannier code"),
            },
            "projections": {
                'valid_types': OrbitalData,
                'additional_parameter': None,
                'linkname': 'projections',
                'docstring': ("Starting projections of class OrbitalData"),
            },
            "local_input_folder": {
                'valid_types': FolderData,
                'additional_parameter': None,
                'linkname': 'local_input_folder',
                'docstring': ("Use a local folder as parent folder (for "
                              "restarts and similar"),
            },
            "remote_input_folder": {
                'valid_types': RemoteData,
                'additional_parameter': None,
                'linkname': 'remote_input_folder',
                'docstring': ("Use a remote folder as parent folder"),
            },
            "kpoints": {
                'valid_types': KpointsData,
                'additional_parameter': None,
                'linkname': 'kpoints',
                'docstring': "Use the node defining the kpoint sampling to use",
            },
            "kpoints_path": {
                'valid_types': KpointsData,
                'additional_parameter': None,
                'linkname': 'kpoints_path',
                'docstring': "Use the node defining the k-points path to use for bands interpolation",
            },
        })

        return retdict

    def use_parent_calculation(self, calc):
        """
        Set the parent calculation,
        from which it will inherit the output subfolder as remote_input_folder.
        """
        try:
            remote_folder = calc.get_outputs_dict()['remote_folder']
        except KeyError:
            raise AttributeError("No remote_folder found in output to the "
                                 "parent calculation set")
        self.use_remote_input_folder(remote_folder)

    def _prepare_for_submission(self, tempfolder, inputdict):
        """
        Routine, which creates the input and prepares for submission

        :param tempfolder: a aiida.common.folders.Folder subclass where
                           the plugin should put all its files.
        :param inputdict: a dictionary with the input nodes, as they would
                be returned by get_inputdata_dict (without the Code!)
        """
        input_validator = self._get_input_validator(inputdict=inputdict)
        local_input_folder = input_validator(
            name='local_input_folder', valid_types=FolderData, required=False
        )
        remote_input_folder = input_validator(
            name='remote_input_folder', valid_types=RemoteData, required=False
        )
        if local_input_folder is None and remote_input_folder is None:
            raise InputValidationError('Either local_input_folder or remote_input_folder must be set.')

        parameters = input_validator(
            name='parameters', valid_types=ParameterData
        )

        def blocked_keyword_finder(input_params, blocked_keywords):
            """
            Searches through the input_params for any blocked_keywords and
            forces the default, returns the modified input_params
            """
            import re
            for blocked in blocked_keywords:
                nl = blocked[0]
                flag = blocked[1]
                defaultvalue = None
                if len(blocked) >= 3:
                    defaultvalue = blocked[2]
                if nl in input_params:
                    # The following lines is meant to avoid putting in input the
                    # parameters like celldm(*)
                    stripped_inparams = [re.sub("[(0-9)]", "", _)
                                         for _ in input_params[nl].keys()]
                    if flag in stripped_inparams:
                        raise InputValidationError(
                            "You cannot specify explicitly the '{}' flag in "
                            "the '{}' input.".format(flag, nl))
                    if defaultvalue is not None:
                        if nl not in input_params:
                            input_params[nl] = {}
                        input_params[nl][flag] = defaultvalue
            return input_params

        def check_capitals(input_params):
            """
            Goes through the input_params (which much be a dictionary) and
            raises an InputValidationError if any of the keys are not capitalized
            """
            for k in input_params:
                if k != k.lower():
                    raise InputValidationError("Please make sure all keys"
                                               "are lower case, {} was not!"
                                               "".format(k))
        param_dict = parameters.get_dict()
        param_dict = blocked_keyword_finder(param_dict, self._blocked_keywords)
        check_capitals(param_dict)

        projections = input_validator(
            name='projections', valid_types=OrbitalData
        )
        kpoints = input_validator(
            name='kpoints', valid_types=KpointsData
        )
        kpoints_path = input_validator(
            name='kpoints_path', valid_types=KpointsData, required=False
        )
        structure = input_validator(
            name='structure', valid_types=StructureData
        )

        settings = input_validator(
            name='settings', valid_types=ParameterData, required=False
        )
        if settings is None:
            settings_dict = {}
        else:
        #    # removed _uppercase_dict
            settings_dict_raw = settings.get_dict()
            settings_dict = {key.lower(): val for key, val in settings_dict_raw.items()}
            if len(settings_dict_raw) != len(settings_dict):
                raise InputValidationError('Input settings contain duplicate keys.')

        code = input_validator(
            name='code', valid_types=Code
        )

        ############################################################
        # End basic check on inputs
        ############################################################

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

        # set symlinks and copies
        # ensures that the parent /out/ folder is copied correctly

        #parent_uuid = parent_folder.get_computer().uuid
        #parent_path = parent_folder.get_remote_path()
        remote_input_folder_uuid = remote_input_folder.get_computer().uuid
        remote_input_folder_path = remote_input_folder.get_remote_path()
        local_input_folder_uuid = local_input_folder.get_computer().uuid
        local_input_folder_path = local_input_folder.get_remote_path()

        required_files = [self._SEEDNAME +
                          suffix for suffix in ['.mmn', '.amn']]
        optional_files = [self._SEEDNAME +
                          suffix for suffix in ['.eig', '.chk', '.spn']]
        input_files = required_files + optional_files
        wavefunctions_files = ['UNK*']
        local_folder_content = local_input_folder.get_folder_list()

        t_dest = get_authinfo(computer=remote_input_folder.get_computer(),
                              aiidauser=remote_input_folder.get_user()).get_transport()
        with t_dest:
            remote_folder_content = t_dest.listdir(
                path=remote_input_folder_path)

        def files_finder(file_list, exact_patterns, glob_patterns):
            result = [f for f in exact_patterns if (f in file_list)]
            import fnmatch
            for glob_p in glob_patterns:
                result += fnmatch.filter(file_list, glob_patterns)
            return result

        found_in_local = files_finder(
            local_folder_content, input_files, wavefunctions_files)
        found_in_remote = files_finder(
            remote_folder_content, input_files, wavefunctions_files)
        found_in_remote = [
            f for f in found_in_remote if f not in found_in_local]
        not_found = [
            f for f in required_files
            if f not in found_in_remote + found_in_local
        ]
        if not len(not_found) != 0:
            raise InputValidationError("{} necessary input files were not found: {} "
                                       .format(len(not_found), ''.join(str(nf) for nf in not_found)))

        remote_copy_list = []
        remote_symlink_list = []
        local_copy_list = []

        ALWAYS_COPY_FILES = [self._CHK_FILE]
        for f in found_in_remote:
            file_info = (
                remote_input_folder_uuid,
                os.path.join(remote_input_folder_path, f),
                '.'
            )
            if f in ALWAYS_COPY_FILES:
                remote_copy_list.append(file_info)
            else:
                sym_list.append(file_info)
        for f in found_in_local:
            local_copy_list.append(
                (local_input_folder_uuid, os.path.join(local_input_folder_path, f), '.')
            )

        #if copy_list:
        #    local_copy_list += copy_list
        #if sym_list:
        #    remote_symlink_list += sym_list

        # Add any custom copy/sym links
        remote_symlink_list += settings_dict.pop("additional_remote_symlink_list", [])
        remote_copy_list += settings_dict.pop("additional_remote_copy_list", [])
        local_copy_list += settings_dict.pop("additional_local_copy_list", [])

        #######################################################################

        # Calcinfo
        calcinfo = CalcInfo()
        calcinfo.uuid = self.uuid
        calcinfo.local_copy_list = local_copy_list
        calcinfo.remote_copy_list = remote_copy_list
        calcinfo.remote_symlink_list = remote_symlink_list

        codeinfo = CodeInfo()
        codeinfo.withmpi = False  # No mpi with wannier
        codeinfo.cmdline_params = [self._DEFAULT_INPUT_FILE]

        calcinfo.codes_info = [codeinfo]
        calcinfo.codes_run_mode = code_run_modes.SERIAL

        # Retrieve files
        calcinfo.retrieve_list = []
        calcinfo.retrieve_list.append(self._DEFAULT_OUTPUT_FILE)
        #calcinfo.retrieve_list.append(self._OUTPUT_PRECODE_FILE_NAME)
        calcinfo.retrieve_list.append(self._ERROR_FILE_NAME)

        calcinfo.retrieve_list += ['{}_band.dat'.format(self._PREFIX),
                                   '{}_band.kpt'.format(self._PREFIX)]

        if settings.pop('retrieve_hoppings',False):
            calcinfo.retrieve_list += ['{}_wsvec.dat'.format(self._PREFIX),
                                       '{}_hr.dat'.format(self._PREFIX)]

        # Retrieves bands automatically, if they are calculated

        calcinfo.retrieve_list += settings_dict.pop(
            "additional_retrieve_list", [])

        if settings_dict:
            raise InputValidationError("Some keys in settings unrecognized")

        return calcinfo

    @staticmethod
    def _get_input_validator(inputdict):
        def _validate_input(name, valid_types, required=True, default=None):
            try:
                value = inputdict.pop(name)
            except KeyError:
                if required:
                    raise InputValidationError("Missing required input parameter '{}'".format(name))
                else:
                    value = default

            if not isinstance(valid_types, (list, tuple)):
                valid_types = [valid_types]
            if not required:
                valid_types = list(valid_types) + [type(default)]
            valid_types = tuple(valid_types)

            if not isinstance(value, valid_types):
                raise InputValidationError("Input parameter '{}' is of type '{}', but should be of type(s) '{}'".format(name, type(value), valid_types))
            return value

        return _validate_input

    def generate_projections(self, list_of_projection_dicts):
        return _generate_projections(
            list_of_projection_dicts,
            self.get_inputs_dict()['structure']
        )


def _print_wann_line_from_orbital(orbital):
    """
    Prints an appropriate wannier line from input orbitaldata,
    will raise an exception if the orbital does not contain enough
    information, or the information is badly formated
    """
    from aiida.common.orbital import OrbitalFactory
    realh = OrbitalFactory("realhydrogen")

    if not isinstance(orbital, realh):
        raise InputValidationError("Only realhydrogen oribtals supported"
                                   " for wannier input currently")
    import copy
    orb_dict = copy.deepcopy(orbital.get_orbital_dict())

    # setup position
    try:
        position = orb_dict["position"]
        if position is None:
            raise KeyError
    except KeyError:
        raise InputValidationError("orbital must have position!")
    wann_string = "c=" + ",".join([str(x) for x in position])

    # setup angular and magnetic number
    # angular_momentum
    try:
        angular_momentum = orb_dict["angular_momentum"]
        if angular_momentum is None:
            raise KeyError
    except KeyError:
        raise InputValidationError("orbital must have angular momentum, l")
    wann_string += ":l={}".format(str(angular_momentum))
    # magnetic_number
    try:
        magnetic_number = orb_dict["magnetic_number"]
        if angular_momentum is None:
            raise KeyError
    except KeyError:
        raise InputValidationError("orbital must have magnetic number, m")
    wann_string += ",mr={}".format(str(magnetic_number + 1))

    # orientations, optional
    # xaxis
    xaxis = orb_dict.pop("x_orientation", None)
    if xaxis:
        wann_string += ":x=" + ",".join([str(x) for x in xaxis])
    # zaxis
    zaxis = orb_dict.pop("z_orientation", None)
    if zaxis:
        wann_string += ":z=" + ",".join([str(x) for x in zaxis])

    # radial, optional
    radial = orb_dict.pop("radial_nodes", None)
    if radial:
        wann_string += ":{}".format(str(radial + 1))

    # zona, optional
    zona = orb_dict.pop("diffusivity", None)
    if zona:
        wann_string += ":{}".format(str(zona))

    # spin, optional
    # Careful with spin, it is insufficient to set the spin the projection
    # line alone. You must, in addition, apply the appropriate settings:
    # either set spinors=.true. or use spinor_projections, see user guide

    spin = orb_dict.pop("spin", None)
    if spin:
        spin_dict = {-1: "d", 1: "u"}
        wann_string += "({})".format(spin_dict[spin])
    spin_orient = orb_dict.pop("spin_orientation", None)
    if spin_orient:
        wann_string += "[" + ",".join([str(x) for x in spin_orient]) + "]"

    return wann_string
