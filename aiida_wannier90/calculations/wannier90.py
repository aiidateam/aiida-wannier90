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

__authors__ = "Daniel Marchand, Antimo Marrazzo, Dominik Gresch & The AiiDA team."
__copyright__ = u"Copyright (c), This file is part of the AiiDA platform. For further information please visit http://www.aiida.net/. All rights reserved"
__license__ = "Non-Commercial, End-User Software License Agreement, see LICENSE.txt file."
__version__ = "0.7.0"

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
        if isinstance(list_item, (str,unicode) ):
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

        self._DEFAULT_INPUT_FILE = 'aiida.win'
        self._DEFAULT_INPUT_FILE_GW = 'aiida'
    #    self._DEFAULT_INPUT_FILE_GW_WIN = 'aiida.gw.win'
        self._DEFAULT_OUTPUT_FILE = 'aiida.wout'
    #    self._DEFAULT_OUTPUT_FILE_GW = 'aiida.gw.wout'
        self._ERROR_FILE_NAME = 'aiida.werr'
    #    self._INPUT_PRECODE_FILE_NAME = 'aiida.in'
    #    self._OUTPUT_PRECODE_FILE_NAME = 'aiida.out'
    #    self._OUTPUT_GW_PRECODE_FILE_NAME = 'aiida_GW.out'
    #    self._PREFIX = 'aiida'
    #    self._PREFIX_GW = 'aiida.gw'
        self._SEEDNAME = 'aiida'
        self._default_parser = 'wannier90'
        #self._INPUT_SUBFOLDER = "./out/"
        self._ALWAYS_SYM_FILES = ['UNK*', '*.mmn']
        self._RESTART_SYM_FILES = ['*.amn','*.eig']
        self._CHK_FILE = '*.chk'
        self._DEFAULT_INIT_ONLY = False
        self._DEFAULT_WRITE_UNK = False
        self._blocked_keywords =[['length_unit','ang']]
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
    #        "precode_parameters": {
    #           'valid_types': ParameterData,
    #           'additional_parameter': None,
    #           'linkname': 'precode_parameters',
    #           'docstring': ("Use a node that specifies the input parameters "
    #                         "for the wannier precode"),
    #           },
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
    #        "preprocessing_code": {
    #            'valid_types': Code,
    #            'additional_parameter': None,
    #            'linkname': 'preprocessing_code',
    #            'docstring': ("Use a preprocessing code for "
    #                     "starting wannier90"),
    #            },
    #        "gw_preprocessing_code": {
    #            'valid_types': Code,
    #            'additional_parameter': None,
    #            'linkname': 'gw_preprocessing_code',
    #            'docstring': ("Use a gw pre-processing code for "
    #                     "starting wannier90"),
    #           },
            "kpoints":{
                'valid_types': KpointsData,
                'additional_parameter': None,
                'linkname': 'kpoints',
                'docstring': "Use the node defining the kpoint sampling to use",
                },
            "kpoints_path":{
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
    #    if not isinstance(calc, (PwCalculation, Wannier90Calculation)):
    #        raise ValueError("Parent calculation must be a Pw or Wannier90 "
    #                         "Calculation")
    #    if isinstance(calc, PwCalculation):
    #        # Test to see if parent PwCalculation is nscf
    #        par_type = calc.inp.parameters.dict.CONTROL['calculation'].lower()
    #        if par_type != 'nscf':
    #            raise ValueError("Pw calculation must be nscf")
        try:
            remote_folder = calc.get_outputs_dict()['remote_folder']
        except KeyError:
            raise AttributeError("No remote_folder found in output to the "
                                 "parent calculation set")
        self.use_remote_input_folder(remote_folder)

    def _prepare_for_submission(self,tempfolder, inputdict):
        """
        Routine, which creates the input and prepares for submission

        :param tempfolder: a aiida.common.folders.Folder subclass where
                           the plugin should put all its files.
        :param inputdict: a dictionary with the input nodes, as they would
                be returned by get_inputdata_dict (without the Code!)
        """
        ##################################################################
        # Input validation
        ##################################################################

        # Grabs parent calc information
    #    parent_folder = inputdict.pop(self.get_linkname('parent_folder'),None)
    #    if not isinstance(parent_folder, RemoteData):
    #        raise InputValidationError("parent_folder is not of type "
    #                                   "RemoteData")
        local_input_folder = inputdict.pop(self.get_linkname("local_input_folder",None))
        remote_input_folder = inputdict.pop(self.get_linkname("remote_input_folder", None))
        if not isinstance(local_input_folder, RemoteData):
            raise InputValidationError("local_input_folder is not of type "
                                       "FolderData")
        if not isinstance(remote_input_folder, RemoteData):
            raise InputValidationError("remote_input_folder is not of type "
                                       "RemoteData")

        # Tries to get the input parameters
        try:
            parameters = inputdict.pop(self.get_linkname('parameters'))
        except KeyError:
            raise InputValidationError("No parameters specified for "
                                       "this calculation")
        if not isinstance(parameters, ParameterData):
            raise InputValidationError("parameters is not of "
                                       "type ParameterData")

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

        # Tries to get the precode input paramters
    #    try:
    #        precode_parameters = inputdict.pop(self.get_linkname
    #                                           ('precode_parameters'))
    #    except KeyError:
    #        precode_parameters = ParameterData(dict={})
    #    if not isinstance(precode_parameters,ParameterData):
    #        raise InputValidationError('precode_parameters is not '
    #                                   'of type ParameterData')
    #    precode_param_dict = precode_parameters.get_dict()
    #    precode_param_dict = blocked_keyword_finder(precode_param_dict,
    #                                        self._blocked_precode_keywords)
    #    check_capitals(precode_param_dict)
        # Tries to get the input projections
        try:
            projections = inputdict.pop(self.get_linkname('projections'))
        except KeyError:
            raise InputValidationError("No projections specified for "
                                       "this calculation")
        if not isinstance(projections, OrbitalData):
            raise InputValidationError("projections is not of type "
                                       "OrbitalData")

        # Tries to get the input k-points
        try:
            kpoints = inputdict.pop(self.get_linkname('kpoints'))
        except KeyError:
            raise InputValidationError("No kpoints specified for this"
                                       " calculation")
        if not isinstance(kpoints, KpointsData):
            raise InputValidationError("kpoints is not of type KpointsData")

        # Tries to get the input k-points path, but is not actually mandatory and will
        #  default to None if not found
        kpoints_path = inputdict.pop(self.get_linkname('kpoints_path'), None)
        if not isinstance(kpoints, KpointsData) and kpoints_path is not None:
            raise InputValidationError("kpoints_path is not of type "
                                       "KpointsData")

        # Tries to get the input structure
        try:
            structure = inputdict.pop(self.get_linkname('structure'))
        except KeyError:
            raise InputValidationError("No structure specified for this "
                                       "calculation")
        if not isinstance(structure, StructureData):
            raise InputValidationError("structure is not of type "
                                       "StructureData")

        # Settings can be undefined, and defaults to an empty dictionary
        settings = inputdict.pop(self.get_linkname('settings'),None)
        if settings is None:
            settings_dict = {}
        else:
            if not isinstance(settings,  ParameterData):
                raise InputValidationError("settings, if specified, must be "
                                           "of type ParameterData")
            # Settings converted to uppercase
            settings_dict = _uppercase_dict(settings.get_dict(),
                                            dict_name='settings')

        # This section handles the multicode support
        main_code = inputdict.pop(self.get_linkname('code'),None)
        if main_code is None:
            raise InputValidationError("No input code found!")


    #    preproc_code =  inputdict.pop(self.get_linkname('preprocessing_code')
     #                                 ,None)
     #   if preproc_code is not None:
     #       if not isinstance(preproc_code, Code):
     #           raise InputValidationError("preprocessing_code, if specified,"
     #                                      "must be of type Code")
     #   gw_preproc_code =  inputdict.pop(self.get_linkname('gw_preprocessing_code')
     #                                 ,None)
     #   if gw_preproc_code is not None:
     #       if not isinstance(gw_preproc_code, Code):
     #           raise InputValidationError("GW preprocessing_code, if specified,"
     #                                      "must be of type Code")

        ############################################################
        # End basic check on inputs
        ############################################################

        # Here info from the parent, for file copy settings is found
        parent_info_dict = {}
        parent_calc = remote_input_folder.get_inputs_dict()['remote_folder']
        parent_inputs = parent_calc.get_inputs_dict()
        wannier_parent = isinstance(parent_calc, Wannier90Calculation)
        parent_info_dict.update({'wannier_parent':wannier_parent})
        if parent_info_dict['wannier_parent']:
            # If wannier parent, check if it was INIT_ONY and if precode used
            parent_settings = parent_inputs.pop('settings',{})
            try:
                parent_settings = parent_settings.get_inputs_dict()
            except AttributeError:
                pass
            parent_init_only = parent_settings.pop('INIT_ONLY',
                                                   self._DEFAULT_INIT_ONLY)
            parent_info_dict.update({'parent_init_only':parent_init_only})
    #        parent_precode = parent_inputs.pop(
    #                            self.get_linkname('preprocessing_code'),None)
    #        parent_info_dict.update({'parent_precode':bool(parent_precode)})
        else:
            pass
    #        if preproc_code is None:
    #            raise InputValidationError("You cannot continue from a non"
    #                                       " wannier calculation without a"
    #                                       " preprocess code")


        # Here info from this calculation, for file copy settings is found
        init_only = settings_dict.pop('INIT_ONLY', self._DEFAULT_INIT_ONLY)
    #    if init_only:
    #        if preproc_code is None:
    #            raise InputValidationError ('You cannot have init_only '
    #                                        'mode set, without providing a '
    #                                        'preprocessing code')

        # prepare the main input text
        input_file_lines = []
        from aiida.common.utils import conv_to_fortran_withlists
        for param in param_dict:
            input_file_lines.append(param+' = '+conv_to_fortran_withlists(
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
        atoms_cart = zip(wann_kind_names,wann_positions)
        for atom in atoms_cart:
            input_file_lines.append('{}  {}'.format(atom[0],atom[1]))
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
            path_line = '{} {} {} {} '.format(point1,*coord1)
            path_line += ' {} {} {} {}'.format(point2,*coord2)
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

        # Prints to file the main input
    #    if gw_preproc_code is not None:
    #        input_filename = tempfolder.get_abs_path(self._DEFAULT_INPUT_FILE_GW_WIN)
    #    else:
        input_filename = tempfolder.get_abs_path(self._DEFAULT_INPUT_FILE)
        with open(input_filename, 'w') as file:
            file.write( "\n".join(input_file_lines) )
            file.write( "\n" )

        # Prints the precode input file
    #    if preproc_code is not None:
    #        namelist_dict = {'outdir':PwCalculation._OUTPUT_SUBFOLDER,
    #                         'prefix':PwCalculation._PREFIX,
    #                         'seedname':self._SEEDNAME,
    #                         }
    #        for precode_param in precode_param_dict:
    #            namelist_dict.update({precode_param:
    #                                      precode_param_dict[precode_param]})
            # Manually makes sure that .EIG, .MMN are not rewritten
    #        if  parent_info_dict['wannier_parent']:
    #            user_mmn_setting = namelist_dict.pop('write_mmn',None)
    #            if user_mmn_setting:
    #                raise InputValidationError("You attempt to write_mmn for a "
    #                                           " calculation which inherited"
    #                                           " from a wannier90 calc. This"
    #                                           " is not allowed. Either set"
     #                                          " write_mmn to false, or use a"
     #                                          " non-wannier calc as parent.")
    #            namelist_dict.update({'write_mmn':False})
                # Add write_eig = .false. once this is available
                # namelist_dict.update({})
            # checks and adds UNK file
            # writing UNK as a setting is obsolete
            # write_unk = settings_dict.pop('WRITE_UNK',None)
            # if write_unk:
            #     namelist_dict.update({'write_unk':True})
    #        p2w_input_dict = {'INPUTPP':namelist_dict}

    #        input_precode_filename = tempfolder.get_abs_path(
    #            self._INPUT_PRECODE_FILE_NAME)
    #        with open(input_precode_filename,'w') as infile:
    #            for namelist_name in p2w_input_dict.keys():
    #                infile.write("&{0}\n".format(namelist_name))
    #                # namelist content; set to {} if not present,
    #                #  so that we leave an empty namelist
    #                namelist = p2w_input_dict.pop(namelist_name,{})
    #                for k, v in sorted(namelist.iteritems()):
    #                    infile.write(get_input_data_text(k,v))
    #                infile.write("/\n")

        ############################################################
        #  end of writing text input
        ############################################################

        # set symlinks and copies
        # ensures that the parent /out/ folder is copied correctly
        remote_copy_list = []
        remote_symlink_list = []

        copy_list = []
        sym_list = []
        #parent_uuid = parent_folder.get_computer().uuid
        #parent_path = parent_folder.get_remote_path()
        remote_input_folder_uuid = remote_input_folder.get_computer().uuid
        remote_input_folder_path = remote_input_folder.get_remote_path()
        local_input_folder_uuid = remote_input_folder.get_computer().uuid
        local_input_folder_path = local_input_folder.get_remote_path()

        pw_out = PwCalculation._OUTPUT_SUBFOLDER

        required_files = [self._SEEDNAME + suffix for suffix in ['.mmn','.amn']]
        optional_files = [self._SEEDNAME + suffix for suffix in ['.eig', '.chk', '.spn']]
        input_files = required_files + optional_files
        wavefunctions_files = ['UNK*']
        local_folder_content = local_input_folder.get_folder_list()

        t_dest = get_authinfo(computer=remote_input_folder.get_computer(),
                          aiidauser=remote_input_folder.get_user()).get_transport()
        with t_dest:
            remote_folder_content = t_dest.listdir(path=remote_input_folder_path)

        def files_finder(file_list, exact_patterns, glob_patterns):
            result = [f in exact_patterns if f in file_list]
            import fnmatch
            for glob_p in glob_patterns:
                result += fnmatch.filter(file_list, glob_patterns)
            return result

        found_in_local = files_finder(local_folder_content, input_files, wavefunctions_files)
        found_in_remote = files_finder(remote_folder_content, input_files, wavefunctions_files)
        found_in_remote = [f for f in found_in_remote if f not in found_in_local]
        not_found = [f in required_files if f not in found_in_remote + found_in_local]
        if not len(not_found)!=0:
            raise InputValidationError("{} necessary input files were not found: {} "
                                       .format(len(not_found),''.join(str(nf) for nf in not_found)))


        [sym_list.append((remote_input_folder_uuid,
                          os.path.join(remote_input_folder_path,f),'.'))
                         for f in found_in_remote]
        [copy_list.append((local_input_folder_uuid,
                          os.path.join(local_input_folder_path, f), '.'))
                         for f in found_in_local]
        # #if parent_info_dict['wannier_parent']:
        #     sym_list.append((parent_uuid,os.path.join(parent_path,
        #                           pw_out),self._INPUT_SUBFOLDER))
        #     for f in self._ALWAYS_SYM_FILES:
        #         sym_list.append((parent_uuid, os.path.join(
        #                              parent_path,f),'.'))
        #     if preproc_code is None:
        #         for f in self._RESTART_SYM_FILES:
        #             sym_list.append((parent_uuid, os.path.join(
        #                                  parent_path,f),'.'))
        #         copy_list.append((parent_uuid, os.path.join(
        #                            parent_path,self._CHK_FILE),'.'))
        #     if gw_preproc_code is not None:
        #         copy_list.append((parent_uuid, os.path.join(
        #                            parent_path,'aiida.nnkp'),'.'))

        #else:
        #    copy_list.append((parent_uuid,os.path.join(parent_path,
        #                          pw_out),PwCalculation._OUTPUT_SUBFOLDER))



        if  copy_list:
            remote_copy_list +=  copy_list
        if  sym_list:
            remote_symlink_list += sym_list

        # Add any custom copy/sym links
        remote_symlink_list += settings_dict.pop("ADDITIONAL_SYMLINK_LIST",[])
        remote_copy_list += settings_dict.pop("ADDITIONAL_COPY_LIST",[])
        #######################################################################

        # Calcinfo
        calcinfo = CalcInfo()
        calcinfo.uuid = self.uuid
        calcinfo.local_copy_list = []
        calcinfo.remote_copy_list = remote_copy_list
        calcinfo.remote_symlink_list = remote_symlink_list


        c_pp = CodeInfo()
        c_pp.withmpi = False # No mpi with wannier
        c_pp.cmdline_params = ["-pp",self._DEFAULT_INPUT_FILE]
        c_pp.code_uuid = main_code.uuid
        c_run = CodeInfo()
        c_run.withmpi = False # No mpi with wannier
        c_run.cmdline_params = [self._DEFAULT_INPUT_FILE]
        c_pp.code_uuid = main_code.uuid
        # if preproc_code is not None:
        #     c1 = CodeInfo()
        #     c1.withmpi = False #  No mpi with wannier
        #     c1.cmdline_params = ["-pp",self._DEFAULT_INPUT_FILE]
        #     c1.code_uuid = main_code.uuid
        #     c2 = CodeInfo()
        #     c2.withmpi = True # pw2wannier90 should run in parallel (anyway needed on some slum clusters)
        #     c2.code_uuid = preproc_code.uuid
        #     c2.stdin_name = self._INPUT_PRECODE_FILE_NAME
        #     c2.stdout_name = self._OUTPUT_PRECODE_FILE_NAME
        # if gw_preproc_code is not None:
        #     c_gw = CodeInfo()
        #     c_gw.withmpi = False
        #     c_gw.cmdline_params = [self._DEFAULT_INPUT_FILE_GW]
        #     c_gw.code_uuid = gw_preproc_code.uuid
        #     c_gw.stdout_name = self._OUTPUT_GW_PRECODE_FILE_NAME
        #     c3 = CodeInfo()
        #     c3.withmpi = False # No mpi with wannier
        #     c3.cmdline_params = [self._DEFAULT_INPUT_FILE_GW_WIN]
        #     c3.code_uuid = main_code.uuid
        # else:
        #     c3 = CodeInfo()
        #     c3.withmpi = False # No mpi with wannier
        #     c3.cmdline_params = [self._DEFAULT_INPUT_FILE]
        #     c3.code_uuid = main_code.uuid
        #
        # try:
        #     if gw_preproc_code is not None:
        #         codes_info = [c_gw, c3]
        #     else:
        #         codes_info = [c1, c2, c3]
        # except NameError:
        #     codes_info = [c3]

        # If init_only is set to true, then the last stage of the
        # calculation will be skipped
        if init_only:
            codes_info = [c_pp]
        else:
            codes_info = [c_run]

        calcinfo.codes_info = codes_info
        calcinfo.codes_run_mode = code_run_modes.SERIAL

        # Retrieve files
        calcinfo.retrieve_list = []
        calcinfo.retrieve_list.append(self._DEFAULT_OUTPUT_FILE)
        calcinfo.retrieve_list.append(self._OUTPUT_PRECODE_FILE_NAME)
        calcinfo.retrieve_list.append(self._ERROR_FILE_NAME)

        calcinfo.retrieve_list += ['{}_band.dat'.format(self._PREFIX),
                                   '{}_band.kpt'.format(self._PREFIX),
                                   '{}_wsvec.dat'.format(self._PREFIX)]

        # Retrieves bands automatically, if they are calculated

        calcinfo.retrieve_list += settings_dict.pop("ADDITIONAL_RETRIEVE_LIST"
                                                    ,[])

        if settings_dict:
            raise InputValidationError("Some keys in settings unrecognized")

        return calcinfo

    def _gen_wannier_orbitals(cls, position_cart=None, structure=None,
                             kind_name=None, radial=1,
                             ang_mtm_name=None, ang_mtm_l=None,
                             ang_mtm_mr=None, spin=None,
                             zona=None, zaxis=None,
                             xaxis=None, spin_axis=None):
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
        def convert_to_list(item):
            """
            internal method, checks if the item is already a list or tuple.
            if not returns a tuple containing only item, otherwise returns
            tuple(item)
            """
            if isinstance(item,(list,tuple)):
                return tuple(item)
            else:
                return tuple([item])

        def combine_dictlists(dict_list1, dict_list2):
            """
            Creates a list of every dict in dict_list1 updated with every
            dict in dict_list2
            """
            out_list =  [ ]
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
            raise InputValidationError('Must supply position or kind_name'
                                       ' not both')

        structure_class = DataFactory('structure')
        if kind_name != None:
            if not isinstance(structure, structure_class):
                raise InputValidationError('Must supply a StructureData as '
                                            'structure if using kind_name')
            if not isinstance(kind_name, basestring):
                raise InputValidationError('kind_name must be a string')

        if ang_mtm_name == None and ang_mtm_l == None:
            raise InputValidationError("Must supply ang_mtm_name or ang_mtm_l")
        if ang_mtm_name != None and (ang_mtm_l != None or ang_mtm_mr != None):
            raise InputValidationError("Cannot supply ang_mtm_l or ang_mtm_mr"
                                       " but not both")
        if ang_mtm_l == None and ang_mtm_mr != None:
            raise InputValidationError("Cannot supply ang_mtm_mr without "
                                       "ang_mtm_l")

        ####################################################################
        #Setting up initial basic parameters
        ####################################################################
        projection_dict = {}
        if radial:
            projection_dict['radial_nodes'] = radial-1
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
                raise InputValidationError("No valid positions found in structure "
                                        "using {}".format(kind_name))
        # otherwise turns position into position_list
        else:
            position_list = [convert_to_list(position_cart)]
        position_dicts = [{"position":v} for v in position_list]
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
                    ang_mtm_dicts += [{'angular_momentum':l,'magnetic_number':i}
                                      for i in range(2*l+1)]
                else:
                    ang_mtm_dicts += [{'angular_momentum':l,'magnetic_number':i}
                                      for i in range(-l+1)]
            if ang_mtm_mr is not None:
                if len(ang_mtm_l) > 1:
                    raise InputValidationError("If you are giving specific"
                                               " magnetic numbers please do"
                                               " not supply more than one"
                                               " angular number.")
                ang_mtm_mr = convert_to_list(ang_mtm_mr)
                ang_mtm_l_num = ang_mtm_l[0]
                ang_mtm_dicts = [{'angular_momentum':ang_mtm_l_num,
                                  'magnetic_number':j-1} for j in ang_mtm_mr]
        if ang_mtm_name is not None:
            ang_mtm_names =  convert_to_list(ang_mtm_name)
            ang_mtm_dicts = []
            for name in ang_mtm_names:
                ang_mtm_dicts += RealhydrogenOrbital.get_quantum_numbers_from_name(name)
        projection_dicts = combine_dictlists(projection_dicts, ang_mtm_dicts)

        #####################################################################
        # Setting up the spin                                               #
        #####################################################################
        if spin:
            spin_dict = {'U':1,'u':1,1:1,'D':-1,'d':-1,-1:-1}
            if isinstance(spin, (list,tuple)):
                spin = [spin_dict[x] for x in spin]
            else:
                spin = [spin_dict[spin]]
            spin_dicts = [{'spin':v} for v in spin]
            projection_dicts = combine_dictlists(projection_dicts, spin_dicts)

        # generating and returning a list of all corresponding orbitals
        orbital_out = []
        for projection_dict in projection_dicts:
            realh = RealhydrogenOrbital()
            realh.set_orbital_dict(projection_dict)
            orbital_out.append(realh)
        return orbital_out


    def gen_projections(self, list_of_projection_dicts):
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
        try:
            structure = self.get_inputs_dict()['structure']
        except NameError:
            raise InputValidationError("Must set structure first")
        if not isinstance(list_of_projection_dicts,(list,tuple)):
            list_of_projection_dicts = [list_of_projection_dicts]
        orbitals = []
        for this_dict in list_of_projection_dicts:
            if 'kind_name' in this_dict:
                this_dict.update({'structure':structure})
            orbitals += self._gen_wannier_orbitals(**this_dict)
        orbitaldata = DataFactory('orbital')()
        orbitaldata.set_orbitals(orbitals)
        return orbitaldata


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
    wann_string = "c="+",".join([str(x) for x in position])


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
    wann_string += ",mr={}".format(str(magnetic_number+1))

    # orientations, optional
    # xaxis
    xaxis = orb_dict.pop("x_orientation",None)
    if xaxis:
        wann_string += ":x="+",".join([str(x) for x in xaxis])
    # zaxis
    zaxis = orb_dict.pop("z_orientation",None)
    if zaxis:
        wann_string += ":z="+",".join([str(x) for x in zaxis])

    # radial, optional
    radial = orb_dict.pop("radial_nodes", None)
    if radial:
        wann_string += ":{}".format(str(radial+1))

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
        spin_dict = {-1:"d",1:"u"}
        wann_string += "({})".format(spin_dict[spin])
    spin_orient = orb_dict.pop("spin_orientation",None)
    if spin_orient:
        wann_string += "["+",".join([str(x) for x in spin_orient])+"]"

    return wann_string
