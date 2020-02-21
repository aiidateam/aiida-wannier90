# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division
import os
import six

from aiida.common import datastructures

from aiida.common import exceptions as exc
from aiida.engine import CalcJob
from aiida.orm import (
    AuthInfo, BandsData, Dict, FolderData, KpointsData, List, OrbitalData,
    RemoteData, SinglefileData, StructureData
)

from .io import write_win

__all__ = ('Wannier90Calculation', )


class Wannier90Calculation(CalcJob):
    """
    Plugin for Wannier90, a code for computing maximally-localized Wannier
    functions. See http://www.wannier.org/ for more details
    """
    _DEFAULT_SEEDNAME = 'aiida'
    # The following ones CANNOT be set by the user - in this case an exception will be raised
    # IMPORTANT: define them here in lower-case
    _BLOCKED_PARAMETER_KEYS = [
        'length_unit',
        'unit_cell_cart',
        'atoms_cart',
        'projections',
        'postproc_setup'  # Pass instead a 'postproc_setup' in the input `settings` node
    ]

    @classmethod
    def define(cls, spec):  # pylint: disable=no-self-argument
        super(Wannier90Calculation, cls).define(spec)
        spec.input(
            "structure",
            valid_type=StructureData,
            help="input crystal structure"
        )
        spec.input(
            "parameters",
            valid_type=Dict,
            help="Input parameters for the Wannier90 code"
        )
        spec.input(
            "settings",
            valid_type=Dict,
            required=False,
            help="Additional settings to manage the Wannier90 calculation"
        )
        spec.input(
            "projections",
            valid_type=(OrbitalData, Dict, List),
            help="Starting projections for the Wannierisation procedure",
            required=False
        )
        spec.input(
            "local_input_folder",
            valid_type=FolderData,
            required=False,
            help=
            "Get input files (.amn, .mmn, ...) from a FolderData stored in the AiiDA repository"
        )
        spec.input(
            "remote_input_folder",
            valid_type=RemoteData,
            required=False,
            help=
            "Get input files (.amn, .mmn, ...) from a RemoteData possibly stored in a remote computer"
        )
        spec.input(
            "kpoints",
            valid_type=KpointsData,
            help="k-point mesh used in the NSCF calculation"
        )
        spec.input(
            "kpoint_path",
            valid_type=Dict,
            required=False,
            help=
            "Description of the kpoints-path to be used for bands interpolation; "
            "it should contain two properties: "
            "a list 'path' of length-2 tuples with the labels of the endpoints of the path; and "
            "a dictionary 'point_coords' giving the scaled coordinates for each high-symmetry endpoint"
        )

        spec.output(
            'output_parameters',
            valid_type=Dict,
            help=
            'The `output_parameters` output node of the successful calculation.'
        )
        spec.output(
            'interpolated_bands',
            valid_type=BandsData,
            required=False,
            help='The interpolated band structure by Wannier90 (if any).'
        )
        spec.output(
            'nnkp_file',
            valid_type=SinglefileData,
            required=False,
            help='The SEEDAME.nnkp file, produced only in -pp (postproc) mode.'
        )
        spec.default_output_node = 'output_parameters'

        # This is used to allow the user to choose the input and output filenames
        spec.input(
            'metadata.options.seedname',
            valid_type=six.string_types,
            default=cls._DEFAULT_SEEDNAME
        )
        spec.input(
            'metadata.options.parser_name',
            valid_type=six.string_types,
            default='wannier90.wannier90'
        )
        # withmpi defaults to "False" in aiida-core 1.0. Below, we override to default to withmpi=True
        spec.input('metadata.options.withmpi', valid_type=bool, default=True)
        spec.exit_code(
            200,
            'ERROR_NO_RETRIEVED_FOLDER',
            message='The retrieved folder data node could not be accessed.'
        )
        spec.exit_code(
            210,
            'ERROR_OUTPUT_STDOUT_MISSING',
            message=
            'The retrieved folder did not contain the required stdout output file.'
        )
        spec.exit_code(
            300,
            'ERROR_WERR_FILE_PRESENT',
            message='A Wannier90 error file (.werr) has been found.'
        )
        spec.exit_code(
            400,
            'ERROR_EXITING_MESSAGE_IN_STDOUT',
            message=
            'The string "Exiting..." has been found in the Wannier90 output (some partial output might have been '
            'parsed).'
        )

    @property
    def _SEEDNAME(self):
        """
        Return the default seedname, unless a custom one has been set in the
        calculation settings
        """
        return self.inputs.metadata.options.seedname

    def prepare_for_submission(self, folder):  #pylint: disable=too-many-locals, too-many-statements # noqa:  disable=MC0001
        """
        Routine which creates the input file of Wannier90
        :param folder: a aiida.common.folders.Folder subclass where
            the plugin should put all its files.
        """
        param_dict = self.inputs.parameters.get_dict()
        self._validate_lowercase(param_dict)
        self._validate_input_parameters(param_dict)

        if 'settings' in self.inputs:
            settings_dict = self.inputs.settings.get_dict()
        else:
            settings_dict = {}
        self._validate_lowercase(settings_dict)

        pp_setup = settings_dict.pop('postproc_setup', False)
        if pp_setup:
            param_dict.update({'postproc_setup': True})

        if 'local_input_folder' not in self.inputs and 'remote_input_folder' not in self.inputs and not pp_setup:
            raise exc.InputValidationError(
                'Either local_input_folder or remote_input_folder must be set.'
            )

        ############################################################
        # End basic check on inputs
        ############################################################
        random_projections = settings_dict.pop('random_projections', False)

        write_win(
            filename=folder.get_abs_path('{}.win'.format(self._SEEDNAME)),
            parameters=param_dict,
            structure=self.inputs.structure,
            kpoints=self.inputs.kpoints,
            kpoint_path=getattr(self.inputs, 'kpoint_path', None),
            projections=getattr(self.inputs, 'projections', None),
            random_projections=random_projections,
        )

        #NOTE: remote_input_folder -> parent_calc_folder (for consistency)
        if 'remote_input_folder' in self.inputs:
            remote_input_folder_uuid = self.inputs.remote_input_folder.computer.uuid
            remote_input_folder_path = self.inputs.remote_input_folder.get_remote_path(
            )

            t_dest = AuthInfo.objects.get(
                dbcomputer_id=self.inputs.remote_input_folder.computer.pk,
                aiidauser_id=self.inputs.remote_input_folder.user.pk
            ).get_transport()
            with t_dest:
                remote_folder_content = t_dest.listdir(
                    path=remote_input_folder_path
                )

        if 'local_input_folder' in self.inputs:
            local_folder_content = self.inputs.local_input_folder.list_object_names(
            )
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
        if 'local_input_folder' in self.inputs:
            found_in_local = files_finder(
                local_folder_content, input_files, wavefunctions_files
            )
        else:
            found_in_local = []
        if 'remote_input_folder' in self.inputs:
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
        if not_found:
            raise exc.InputValidationError(
                "{} necessary input files were not found: {} (NOTE: if you "
                "wanted to run a preprocess step, remember to pass "
                "postproc_setup=True in the input settings node)".format(
                    len(not_found), ', '.join(str(nf) for nf in not_found)
                )
            )

        remote_copy_list = []
        remote_symlink_list = []
        local_copy_list = []
        #Here we enforce that everything except checkpoints are symlinked
        #because in W90 you never modify input files on the run
        ALWAYS_COPY_FILES = ['{}.chk'.format(self._SEEDNAME)]
        for f in found_in_remote:
            #NOTE: for symlinks this appears wrong (comp_uuid, remote_path, default_calc_fldr)
            #NOTE: what is self._DEFAULT_PARENT_CALC_FLDR_NAME equivalent to here?
            file_info = (
                remote_input_folder_uuid,
                os.path.join(remote_input_folder_path, f), os.path.basename(f)
            )
            if f in ALWAYS_COPY_FILES:
                remote_copy_list.append(file_info)
            else:
                remote_symlink_list.append(file_info)
        for f in found_in_local:
            local_copy_list.append((self.inputs.local_input_folder.uuid, f, f))

        # Add any custom copy/sym links
        remote_symlink_list += settings_dict.pop(
            "additional_remote_symlink_list", []
        )
        remote_copy_list += settings_dict.pop(
            "additional_remote_copy_list", []
        )
        local_copy_list += settings_dict.pop("additional_local_copy_list", [])

        #######################################################################

        calcinfo = datastructures.CalcInfo()
        calcinfo.uuid = self.uuid
        calcinfo.local_copy_list = local_copy_list
        calcinfo.remote_copy_list = remote_copy_list
        calcinfo.remote_symlink_list = remote_symlink_list

        codeinfo = datastructures.CodeInfo()
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.cmdline_params = [self._SEEDNAME]

        calcinfo.codes_info = [codeinfo]
        calcinfo.codes_run_mode = datastructures.CodeRunMode.SERIAL

        # Retrieve files
        calcinfo.retrieve_list = []
        calcinfo.retrieve_temporary_list = []
        calcinfo.retrieve_list.append('{}.wout'.format(self._SEEDNAME))
        calcinfo.retrieve_list.append('{}.werr'.format(self._SEEDNAME))
        if pp_setup:
            # The parser will then put this in a SinglefileData (if present)
            calcinfo.retrieve_temporary_list.append(
                '{}.nnkp'.format(self._SEEDNAME)
            )

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
            raise exc.InputValidationError(
                "The following keys in settings are unrecognized: {}".format(
                    list(settings_dict.keys())
                )
            )

        return calcinfo

    @staticmethod
    def _validate_lowercase(dictionary):
        """
        This function gets a dictionary and checks that all keys are lower-case.

        :param dict_node: a dictionary
        :raises InputValidationError: if any of the keys is not lower-case
        :return: ``None`` if validation passes
        """
        non_lowercase = []
        for key in dictionary:
            if key != key.lower():
                non_lowercase.append(key)
        if non_lowercase:
            raise exc.InputValidationError(
                "input keys to the Wannier90 plugin must be all lower-case, but the following aren't : {}"
                .format(", ".join(non_lowercase))
            )

    def _validate_input_parameters(self, parameters):
        """
        This function gets a dictionary with the content of the parameters Dict passed by the user
        and performs some validation.

        In particular, it checks that there are no blocked parameters keys passed.

        :param dict_node: a dictionary
        :raises InputValidationError: if any of the validation fails
        :return: ``None`` if validation passes
        """
        existing_blocked_keys = []
        for key in self._BLOCKED_PARAMETER_KEYS:
            if key in parameters:
                existing_blocked_keys.append(key)
        if existing_blocked_keys:
            raise exc.InputValidationError(
                'The following blocked keys were found in the parameters: {}'.
                format(", ".join(existing_blocked_keys))
            )
