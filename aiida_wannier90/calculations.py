# -*- coding: utf-8 -*-
import os

import numpy as np

from aiida.common.utils import classproperty
from aiida.common.exceptions import InputValidationError, ModificationNotAllowed
from aiida.common.datastructures import CalcInfo, CodeInfo, code_run_modes
from aiida.orm import JobCalculation
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

from .io import write_win

class Wannier90Calculation(JobCalculation):
    """
    Plugin for Wannier90, a code for producing maximally localized Wannier
    functions. See http://www.wannier.org/ for more details
    """

    def _init_internal_params(self):
        super(Wannier90Calculation, self)._init_internal_params()

        self._DEFAULT_SEEDNAME = 'aiida'
        self._default_parser = 'wannier90.wannier90'
        self._blocked_keywords = [['length_unit', 'ang']]

    # Needed because the super() call tries to set the properties to None
    def _property_helper(suffix):
        def getter(self):
            return self._SEEDNAME + suffix
        def setter(self, value):
            if value is None:
                pass
            else:
                raise AttributeError('Cannot set attribute')
        return property(fget=getter, fset=setter)

    @property
    def _SEEDNAME(self):
        try:
            return self.get_inputs_dict()['settings'].get_attr('seedname')
        except KeyError:
            return self._DEFAULT_SEEDNAME

    _DEFAULT_INPUT_FILE = _property_helper('.win')
    _DEFAULT_OUTPUT_FILE = _property_helper('.wout')
    _ERROR_FILE_NAME = _property_helper('.werr')
    _CHK_FILE = _property_helper('.chk')

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
            "kpoint_path": {
                'valid_types': KpointsData,
                'additional_parameter': None,
                'linkname': 'kpoint_path',
                'docstring': "Use the node defining the k-points path to use for bands interpolation",
            },
        })

        return retdict

    def use_parent_calculation(self, calc):
        """
        Set the parent calculation, from which it will inherit the output subfolder as remote_input_folder.
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
            name='projections', valid_types=OrbitalData, required=False
        )
        kpoints = input_validator(
            name='kpoints', valid_types=KpointsData
        )
        kpoint_path = input_validator(
            name='kpoint_path', valid_types=KpointsData, required=False
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
        write_win(
            filename=tempfolder.get_abs_path(
                self._DEFAULT_INPUT_FILE
            ),
            parameters=param_dict,
            structure=structure,
            kpoints=kpoints,
            kpoint_path=kpoint_path,
            projections=projections,
        )

        if remote_input_folder is not None:
            remote_input_folder_uuid = remote_input_folder.get_computer().uuid
            remote_input_folder_path = remote_input_folder.get_remote_path()

            t_dest = get_authinfo(
                computer=remote_input_folder.get_computer(),
                aiidauser=remote_input_folder.get_user()
            ).get_transport()
            with t_dest:
                remote_folder_content = t_dest.listdir(
                    path=remote_input_folder_path)

        if local_input_folder is not None:
            local_folder_content = local_input_folder.get_folder_list()

        required_files = [self._SEEDNAME +
                          suffix for suffix in ['.mmn', '.amn']]
        optional_files = [self._SEEDNAME +
                          suffix for suffix in ['.eig', '.chk', '.spn']]
        input_files = required_files + optional_files
        wavefunctions_files = ['UNK*']

        def files_finder(file_list, exact_patterns, glob_patterns):
            result = [f for f in exact_patterns if (f in file_list)]
            import fnmatch
            for glob_p in glob_patterns:
                result += fnmatch.filter(file_list, glob_p)
            return result

        if local_input_folder is not None:
            found_in_local = files_finder(
                local_folder_content, input_files, wavefunctions_files)
        else:
            found_in_local = []
        if remote_input_folder is not None:
            found_in_remote = files_finder(
                remote_folder_content, input_files, wavefunctions_files)
            found_in_remote = [
                f for f in found_in_remote if f not in found_in_local]
        else:
            found_in_remote = []

        not_found = [
            f for f in required_files
            if f not in found_in_remote + found_in_local
        ]
        if len(not_found) != 0:
            raise InputValidationError(
                "{} necessary input files were not found: {} ".format(
                    len(not_found), ', '.join(str(nf) for nf in not_found)
                )
            )

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
                (local_input_folder.get_abs_path(f), '.')
            )

        # Add any custom copy/sym links
        remote_symlink_list += settings_dict.pop("additional_remote_symlink_list", [])
        remote_copy_list += settings_dict.pop("additional_remote_copy_list", [])
        local_copy_list += settings_dict.pop("additional_local_copy_list", [])

        #######################################################################

        calcinfo = CalcInfo()
        calcinfo.uuid = self.uuid
        calcinfo.local_copy_list = local_copy_list
        calcinfo.remote_copy_list = remote_copy_list
        calcinfo.remote_symlink_list = remote_symlink_list

        codeinfo = CodeInfo()
        codeinfo.code_uuid = code.uuid
        codeinfo.withmpi = False  # No mpi with wannier
        codeinfo.cmdline_params = [self._DEFAULT_INPUT_FILE]

        calcinfo.codes_info = [codeinfo]
        calcinfo.codes_run_mode = code_run_modes.SERIAL

        # Retrieve files
        calcinfo.retrieve_list = []
        calcinfo.retrieve_list.append(self._DEFAULT_OUTPUT_FILE)
        calcinfo.retrieve_list.append(self._ERROR_FILE_NAME)

        calcinfo.retrieve_list += ['{}_band.dat'.format(self._SEEDNAME),
                                   '{}_band.kpt'.format(self._SEEDNAME)]

        if settings_dict.pop('retrieve_hoppings', False):
            calcinfo.retrieve_list += ['{}_wsvec.dat'.format(self._SEEDNAME),
                                       '{}_hr.dat'.format(self._SEEDNAME)]

        # Retrieves bands automatically, if they are calculated

        calcinfo.retrieve_list += settings_dict.pop(
            "additional_retrieve_list", [])

        # pop input keys not used here
        settings_dict.pop('seedname', None)
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
