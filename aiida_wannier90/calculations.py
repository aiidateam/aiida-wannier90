# -*- coding: utf-8 -*-
import os
from collections import Counter

import numpy as np

#NOTE: below is a rather unsightly import should discuss
from aiida.common import (classproperty, InputValidationError,
                          ModificationNotAllowed, CalcInfo,
                          CodeInfo, code_run_modes)
from aiida.engine import CalcJob
from aiida.orm import Code
from aiida.orm.nodes.base import List
from aiida.orm import (KpointsData, OrbitalData,
                       OrbitalFactory, Dict,
                       RemoteData, StructureData,
                       FolderData, SinglefileData)

try:
    from aiida.backends.utils import get_authinfo
except ImportError:
    from aiida.execmanager import get_authinfo

from .io import write_win


class Wannier90Calculation(CalcJob):
    """
    Plugin for Wannier90, a code for producing maximally localized Wannier
    functions. See http://www.wannier.org/ for more details
    """
    #NOTE: consider altering the names of these defaults
    self._DEFAULT_SEEDNAME = 'aiida'
    self._default_parser = 'wannier90.wannier90'
    self._blocked_parameter_keys = [
        'length_unit', 'unit_cell_cart', 'atoms_cart', 'projections'
    ]

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
        except (KeyError, AttributeError):
            return self._DEFAULT_SEEDNAME

    _INPUT_FILE = _property_helper('.win')
    _OUTPUT_FILE = _property_helper('.wout')
    _DEFAULT_INPUT_FILE = _INPUT_FILE
    _DEFAULT_OUTPUT_FILE = _OUTPUT_FILE
    _ERROR_FILE = _property_helper('.werr')
    _CHK_FILE = _property_helper('.chk')
    _NNKP_FILE = _property_helper('.nnkp')

    @classproperty
    def define(cls, spec):
        super(Wannier90Calculation, class).define(spec)
        spec.input("structure", valid_type=StructureData, help="Choose the input structure to use")
        spec.input("settings", valid_type=Dict, help="Use an additional node for special settings")
        spec.input("parameters", valid_type=Dict, help="")
        spec.input("projections", valid_types=(OrbitalData, Dict),
                   help="Starting projections of class OrbitalData")
        spec.input("local_input_folder", valid_type=FolderData,
                   help="Use a local folder as parent folder for restarts and similar")
        spec.input("remote_input_folder", valid_type=RemoteData,
                   help="Use a remote folder as parent folder")
        spec.input("kpoints", valid_type=KpointsData,
                   help="Use the node defining the kpoint sampling to use")
        spec.input("kpoints_path", valid_type=Dict,
                   help="Use the node defining the k-points path for bands interpolation")

    def use_parent_calculation(self, calc):
        """
        Set the parent calculation, from which it will inherit the output subfolder as remote_input_folder.
        """
        try:
            remote_folder = calc.get_outputs_dict()['remote_folder']
        except KeyError:
            raise AttributeError(
                "No remote_folder found in output to the "
                "parent calculation set"
            )
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

        parameters = input_validator(
            name='parameters', valid_types=Dict
        )
        param_dict = self._get_validated_parameters_dict(parameters)

        projections = input_validator(
            name='projections',
            valid_types=(OrbitalData, List),
            required=False
        )
        kpoints = input_validator(name='kpoints', valid_types=KpointsData)
        kpoint_path = input_validator(
            name='kpoint_path', valid_types=Dict, required=False
        )
        structure = input_validator(
            name='structure', valid_types=StructureData
        )

        settings = input_validator(
            name='settings', valid_types=Dict, required=False
        )
        if settings is None:
            settings_dict = {}
        else:
            settings_dict_raw = settings.get_dict()
            settings_dict = {
                key.lower(): val
                for key, val in settings_dict_raw.items()
            }
            if len(settings_dict_raw) != len(settings_dict):
                raise InputValidationError(
                    'Input settings contain duplicate keys.'
                )
        pp_setup = settings_dict.pop('postproc_setup', False)
        if pp_setup:
            param_dict.update({'postproc_setup': True})

        if local_input_folder is None and remote_input_folder is None and pp_setup is False:
            raise InputValidationError(
                'Either local_input_folder or remote_input_folder must be set.'
            )

        code = input_validator(name='code', valid_types=Code)

        ############################################################
        # End basic check on inputs
        ############################################################
        random_projections = settings_dict.pop('random_projections', False)

        write_win(
            filename=tempfolder.get_abs_path(self._INPUT_FILE),
            parameters=param_dict,
            structure=structure,
            kpoints=kpoints,
            kpoint_path=kpoint_path,
            projections=projections,
            random_projections=random_projections,
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
                    path=remote_input_folder_path
                )

        if local_input_folder is not None:
            local_folder_content = local_input_folder.get_folder_list()
        if pp_setup:
            required_files = []
        else:
            required_files = [
                self._SEEDNAME + suffix for suffix in ['.mmn', '.amn']
            ]
        optional_files = [
            self._SEEDNAME + suffix for suffix in ['.eig', '.chk', '.spn']
        ]
        input_files = required_files + optional_files
        wavefunctions_files = ['UNK*']

        def files_finder(file_list, exact_patterns, glob_patterns):
            result = [f for f in exact_patterns if (f in file_list)]
            import fnmatch
            for glob_p in glob_patterns:
                result += fnmatch.filter(file_list, glob_p)
            return result

        # Local FolderData has precedence over RemoteData
        if local_input_folder is not None:
            found_in_local = files_finder(
                local_folder_content, input_files, wavefunctions_files
            )
        else:
            found_in_local = []
        if remote_input_folder is not None:
            found_in_remote = files_finder(
                remote_folder_content, input_files, wavefunctions_files
            )
            found_in_remote = [
                f for f in found_in_remote if f not in found_in_local
            ]
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
        #Here we enforce that everything except checkpoints are symlinked
        #because in W90 you never modify input files on the run
        ALWAYS_COPY_FILES = [self._CHK_FILE]
        for f in found_in_remote:
            file_info = (
                remote_input_folder_uuid,
                os.path.join(remote_input_folder_path, f), os.path.basename(f)
            )
            if f in ALWAYS_COPY_FILES:
                remote_copy_list.append(file_info)
            else:
                remote_symlink_list.append(file_info)
        for f in found_in_local:
            local_copy_list.append(
                (local_input_folder.get_abs_path(f), os.path.basename(f))
            )

        # Add any custom copy/sym links
        remote_symlink_list += settings_dict.pop(
            "additional_remote_symlink_list", []
        )
        remote_copy_list += settings_dict.pop(
            "additional_remote_copy_list", []
        )
        local_copy_list += settings_dict.pop("additional_local_copy_list", [])

        #######################################################################

        calcinfo = CalcInfo()
        calcinfo.uuid = self.uuid
        calcinfo.local_copy_list = local_copy_list
        calcinfo.remote_copy_list = remote_copy_list
        calcinfo.remote_symlink_list = remote_symlink_list

        codeinfo = CodeInfo()
        codeinfo.code_uuid = code.uuid
        #codeinfo.withmpi = True  # Current version of W90 can be run in parallel
        codeinfo.cmdline_params = [self._INPUT_FILE]

        calcinfo.codes_info = [codeinfo]
        calcinfo.codes_run_mode = code_run_modes.SERIAL

        # Retrieve files
        calcinfo.retrieve_list = []
        calcinfo.retrieve_list.append(self._OUTPUT_FILE)
        calcinfo.retrieve_list.append(self._ERROR_FILE)
        if pp_setup:
            calcinfo.retrieve_list.append(self._NNKP_FILE)
            calcinfo.retrieve_singlefile_list = [
                ('output_nnkp', 'singlefile', self._NNKP_FILE)
            ]

        calcinfo.retrieve_list += [
            '{}_band.dat'.format(self._SEEDNAME),
            '{}_band.kpt'.format(self._SEEDNAME)
        ]

        if settings_dict.pop('retrieve_hoppings', False):
            calcinfo.retrieve_list += [
                '{}_wsvec.dat'.format(self._SEEDNAME),
                '{}_hr.dat'.format(self._SEEDNAME),
                '{}_centres.xyz'.format(self._SEEDNAME),
            ]

        # Retrieves bands automatically, if they are calculated

        calcinfo.retrieve_list += settings_dict.pop(
            "additional_retrieve_list", []
        )

        # pop input keys not used here
        settings_dict.pop('seedname', None)
        if settings_dict:
            raise InputValidationError(
                "The following keys in settings are unrecognized: {}".format(
                    settings_dict.keys()
                )
            )

        return calcinfo

    @staticmethod
    def _get_input_validator(inputdict):
        def _validate_input(name, valid_types, required=True, default=None):
            try:
                value = inputdict.pop(name)
            except KeyError:
                if required:
                    raise InputValidationError(
                        "Missing required input parameter '{}'".format(name)
                    )
                else:
                    value = default

            if not isinstance(valid_types, (list, tuple)):
                valid_types = [valid_types]
            if not required:
                valid_types = list(valid_types) + [type(default)]
            valid_types = tuple(valid_types)

            if not isinstance(value, valid_types):
                raise InputValidationError(
                    "Input parameter '{}' is of type '{}', but should be of type(s) '{}'".
                    format(name, type(value), valid_types)
                )
            return value

        return _validate_input

    def _get_validated_parameters_dict(self, parameters):
        param_dict_raw = parameters.get_dict()

        # keys to lowercase, check for duplicates
        param_dict = {
            key.lower(): value
            for key, value in param_dict_raw.items()
        }
        if len(param_dict) != len(param_dict_raw):
            counter = Counter([k.lower() for k in param_dict_raw])
            counter = {key: val for key, val in counter if val > 1}
            raise InputValidationError(
                'The following keys were found more than once in the parameters: {}. Check for duplicates written in upper- / lowercase.'.
                format(counter)
            )

        # check for blocked keywords
        existing_blocked_keys = []
        for key in self._blocked_parameter_keys:
            if key in param_dict:
                existing_blocked_keys.append(key)
        if existing_blocked_keys:
            raise InputValidationError(
                'The following blocked keys were found in the parameters: {}'.
                format(existing_blocked_keys)
            )

        return param_dict
