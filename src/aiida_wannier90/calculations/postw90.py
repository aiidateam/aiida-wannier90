"""Calculation class for the postw90.x code of Wannier90."""

import fnmatch
import os

from aiida import orm
from aiida.common import datastructures, exceptions
from aiida.engine import CalcJob

from ..io import write_win
from .wannier90 import _InputFileLists, _InputFileSpec

__all__ = ("Postw90Calculation",)


def validate_inputs(  # pylint: disable=inconsistent-return-statements,unused-argument
    inputs, ctx=None
):
    """Validate the inputs of the entire input namespace."""
    if "settings" in inputs:
        pp_setup = inputs["settings"].get_dict().pop("postproc_setup", False)
    else:
        pp_setup = False
    if pp_setup:
        return "Can not run postw90.x with the 'postproc_setup' option."

    # Check bands_plot and kpoint_path, bands_kpoints
    bands_plot = inputs["parameters"].get_dict().get("bands_plot", False)
    if bands_plot:
        kpoint_path = inputs.get("kpoint_path", None)
        bands_kpoints = inputs.get("bands_kpoints", None)
        if kpoint_path is None and bands_kpoints is None:
            return (
                "`bands_plot` is True but no `kpoint_path` or `bands_kpoints` provided"
            )


class Postw90Calculation(CalcJob):
    """Plugin for Wannier90.

    Wannier90 is a code for computing maximally-localized Wannier functions.
    See http://www.wannier.org/ for more details.
    """

    # The input filename MUST end with .win. This is validated by the prepare_for_submission
    _REQUIRED_INPUT_SUFFIX = ".win"
    _DEFAULT_INPUT_FILE = "aiida.win"
    _DEFAULT_OUTPUT_FILE = "aiida.wpout"

    # The following ones CANNOT be set by the user - in this case an exception will be raised
    # IMPORTANT: define them here in lower-case
    _BLOCKED_PARAMETER_KEYS = (
        "length_unit",
        "unit_cell_cart",
        "atoms_cart",
        "projections",
        "postproc_setup",  # Pass instead a 'postproc_setup' in the input `settings` node
    )

    # By default, retrieve all produced files except .nnkp (which
    # is handled separately) and .chk (checkpoint files are large,
    # and usually not needed).
    _DEFAULT_RETRIEVE_SUFFIXES = (
        ".wpout",
        ".werr",
        ".r2mn",
        "_band.dat",
        "_band.dat",
        "_band.agr",
        "_band.kpt",
        ".bxsf",
        "_r.dat",
        ".bvec",
        "_qc.dat",
        "_dos.dat",
        "_htB.dat",
        "_u.mat",
        "_u_dis.mat",
        ".vdw",
        "_band_proj.dat",
        "_band.labelinfo.dat",
        ".node_*.werr",
    )

    _DEFAULT_RETRIEVE_TEMPORARY_SUFFIXES = (
        # BoltzWann related files
        "_boltzdos.dat",
        "_elcond.dat",
        "_kappa.dat",
        "_seebeck.dat",
        "_sigmas.dat",
        "_tdf.dat",
    )

    @classmethod
    def define(cls, spec):
        """Define the specs."""
        super().define(spec)
        spec.input(
            "structure", valid_type=orm.StructureData, help="input crystal structure"
        )
        spec.input(
            "parameters",
            valid_type=orm.Dict,
            help="Input parameters for the Wannier90 code",
        )
        spec.input(
            "settings",
            valid_type=orm.Dict,
            required=False,
            help="""Additional settings to manage the Wannier90 calculation.""",
        )
        spec.input(
            "projections",
            valid_type=(orm.OrbitalData, orm.Dict, orm.List),
            help="Starting projections for the Wannierisation procedure.",
            required=False,
        )
        spec.input(
            "parent_folder",
            valid_type=orm.RemoteData,
            help=(
                "Get input files (``.amn``, ``.mmn``, ...) from a class "
                "``RemoteData`` possibly stored in a remote computer."
            ),
        )
        spec.input(
            "kpoints",
            valid_type=orm.KpointsData,
            required=False,
            help="k-point mesh used in the NSCF calculation.",
        )
        spec.input(
            "kpoint_path",
            valid_type=orm.Dict,
            required=False,
            help=(
                "Description of the k-points path to be used for bands interpolation; "
                "it should contain two properties: "
                "a list ``path`` of length-2 tuples with the labels of the endpoints of the path; and "
                "a dictionary ``point_coords`` giving the scaled coordinates for each high-symmetry endpoint."
            ),
        )
        spec.input(
            "bands_kpoints",
            valid_type=orm.KpointsData,
            required=False,
            help=(
                "A list of k-points along a path to be used for bands interpolation; "
                "it should contain `labels`. Specify either this or `kpoint_path`."
            ),
        )
        spec.input(
            "clean_workdir",
            valid_type=orm.Bool,
            default=lambda: orm.Bool(False),
            help="If `True`, work directories of all called calculation jobs will be cleaned at the end of execution.",
        )
        spec.inputs.validator = validate_inputs

        spec.output(
            "output_parameters",
            valid_type=orm.Dict,
            help="The ``output_parameters`` output node of the successful calculation.",
        )
        spec.output(
            "interpolated_bands",
            valid_type=orm.BandsData,
            required=False,
            help="The interpolated band structure by Wannier90 (if any).",
        )
        spec.default_output_node = "output_parameters"
        spec.output(
            "boltzwann.boltzdos",
            valid_type=orm.XyData,
            required=False,
            help="The DOS by postw90.x BoltzWann module (if any).",
        )
        spec.output(
            "boltzwann.elcond",
            valid_type=orm.ArrayData,
            required=False,
            help="The elcond by postw90.x BoltzWann module (if any).",
        )
        spec.output(
            "boltzwann.kappa",
            valid_type=orm.ArrayData,
            required=False,
            help="The kappa by postw90.x BoltzWann module (if any).",
        )
        spec.output(
            "boltzwann.seebeck",
            valid_type=orm.ArrayData,
            required=False,
            help="The seebeck by postw90.x BoltzWann module (if any).",
        )
        spec.output(
            "boltzwann.sigmas",
            valid_type=orm.ArrayData,
            required=False,
            help="The sigmas by postw90.x BoltzWann module (if any).",
        )
        spec.output(
            "boltzwann.tdf",
            valid_type=orm.ArrayData,
            required=False,
            help="The tdf by postw90.x BoltzWann module (if any).",
        )

        spec.input(
            "metadata.options.input_filename",
            valid_type=str,
            default=cls._DEFAULT_INPUT_FILE,
        )
        spec.input(
            "metadata.options.output_filename",
            valid_type=str,
            default=cls._DEFAULT_OUTPUT_FILE,
        )
        spec.input(
            "metadata.options.parser_name",
            valid_type=str,
            default="wannier90.postw90",
        )
        spec.input("metadata.options.withmpi", valid_type=bool, default=True)
        spec.exit_code(
            200,
            "ERROR_NO_RETRIEVED_FOLDER",
            message="The retrieved folder data node could not be accessed.",
            invalidates_cache=True,
        )
        spec.exit_code(
            210,
            "ERROR_OUTPUT_STDOUT_MISSING",
            message="The retrieved folder did not contain the required stdout output file.",
            invalidates_cache=True,
        )
        spec.exit_code(
            300,
            "ERROR_WERR_FILE_PRESENT",
            message="A Wannier90 error file (.werr) has been found.",
        )
        spec.exit_code(
            400,
            "ERROR_EXITING_MESSAGE_IN_STDOUT",
            message=(
                'The string "Exiting..." has been found in the Wannier90 output '
                "(some partial output might have been parsed)."
            ),
        )
        spec.exit_code(
            401,
            "ERROR_BVECTORS",
            message="An error related to bvectors has been found in the Wannier90 output.",
        )
        spec.exit_code(
            402,
            "ERROR_DISENTANGLEMENT_NOT_ENOUGH_STATES",
            message="Energy window contains fewer states than number of target WFs.",
        )
        spec.exit_code(
            403,
            "ERROR_PLOT_WF_CUBE",
            message="Error plotting Wanier functions in cube format.",
        )
        spec.exit_code(
            404,
            "ERROR_OUTPUT_STDOUT_INCOMPLETE",
            message="The stdout output file was incomplete probably because the calculation got interrupted.",
        )
        spec.exit_code(
            405,
            "ERROR_OUTPUT_FILE_MISSING",
            message="Some output files were missing probably because the calculation got interrupted.",
        )
        spec.exit_code(
            406,
            "ERROR_NO_RETRIEVED_TEMPORARY_FOLDER",
            message="The retrieved temporary folder could not be accessed.",
        )

    @property
    def _SEEDNAME(self):
        """Return the default seedname, unless a custom one has been set in the calculation settings.

        :raise ValueError: if the input_filename does not end with ``.win``.
        """
        input_filename = self.inputs.metadata.options.input_filename

        if input_filename.endswith(self._REQUIRED_INPUT_SUFFIX):
            return input_filename[: -len(self._REQUIRED_INPUT_SUFFIX)]

        # If we are here, it's an invalid input filename.
        raise ValueError(
            f"The input filename '{input_filename}' does not end with '{self._REQUIRED_INPUT_SUFFIX}', "
            "so I don't know how to get the seedname. "
            "You need to change the `metadata.options.input_filename` in the process inputs."
        )

    def prepare_for_submission(
        self, folder
    ):  # pylint: disable=too-many-locals, too-many-statements # noqa:  disable=MC0001
        """Create the input file of Wannier90.

        :param folder: a aiida.common.folders.Folder subclass where
            the plugin should put all its files.
        """
        self._validate_input_output_names()

        param_dict = self.inputs.parameters.get_dict()
        self._validate_lowercase(param_dict)
        self._validate_input_parameters(param_dict)

        if "settings" in self.inputs:
            settings_dict = self.inputs.settings.get_dict()
        else:
            settings_dict = {}
        self._validate_lowercase(settings_dict)

        ############################################################
        # End basic check on inputs
        ############################################################
        random_projections = settings_dict.pop("random_projections", False)

        write_win(
            filename=folder.get_abs_path(f"{self._SEEDNAME}.win"),
            parameters=param_dict,
            structure=self.inputs.structure,
            kpoints=getattr(self.inputs, "kpoints", None),
            kpoint_path=getattr(self.inputs, "kpoint_path", None),
            bands_kpoints=getattr(self.inputs, "bands_kpoints", None),
            projections=getattr(self.inputs, "projections", None),
            random_projections=random_projections,
        )

        input_file_lists = self._get_input_file_lists()

        #######################################################################

        calcinfo = datastructures.CalcInfo()
        calcinfo.uuid = self.uuid
        calcinfo.local_copy_list = input_file_lists.local_copy_list + settings_dict.pop(
            "additional_local_copy_list", []
        )
        calcinfo.remote_copy_list = (
            input_file_lists.remote_copy_list
            + settings_dict.pop("additional_remote_copy_list", [])
        )
        calcinfo.remote_symlink_list = (
            input_file_lists.remote_symlink_list
            + settings_dict.pop("additional_remote_symlink_list", [])
        )

        codeinfo = datastructures.CodeInfo()
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.cmdline_params = [self._SEEDNAME]

        calcinfo.codes_info = [codeinfo]
        calcinfo.codes_run_mode = datastructures.CodeRunMode.SERIAL

        retrieve_list = [
            self._SEEDNAME + suffix for suffix in self._DEFAULT_RETRIEVE_SUFFIXES
        ]
        exclude_retrieve_list = settings_dict.pop("exclude_retrieve_list", [])
        retrieve_list = [
            filename
            for filename in retrieve_list
            if not any(
                fnmatch.fnmatch(filename, pattern) for pattern in exclude_retrieve_list
            )
        ]
        calcinfo.retrieve_list = retrieve_list
        calcinfo.retrieve_list += settings_dict.pop("additional_retrieve_list", [])

        retrieve_temporary_list = [
            self._SEEDNAME + suffix
            for suffix in self._DEFAULT_RETRIEVE_TEMPORARY_SUFFIXES
        ]
        calcinfo.retrieve_temporary_list = retrieve_temporary_list
        calcinfo.retrieve_temporary_list += settings_dict.pop(
            "additional_retrieve_temporary_list", []
        )

        # pop input keys not used here
        settings_dict.pop("seedname", None)
        if settings_dict:
            raise exceptions.InputValidationError(
                f"The following keys in settings are unrecognized: {list(settings_dict.keys())}"
            )

        return calcinfo

    def _validate_input_output_names(self):
        """Validate the input and output file names given in the settings Dict."""
        # Let's check that the user-specified input filename ends with .win
        if not self.inputs.metadata.options.input_filename.endswith(
            self._REQUIRED_INPUT_SUFFIX
        ):
            raise exceptions.InputValidationError(
                "The input filename for Wannier90 (specified in the metadata.options.input_filename) "
                f"must end with .win, you specified instead '{self.inputs.metadata.options.input_filename}'"
            )

        # The output filename is defined by Wannier90 based on the seedname.
        # In AiiDA, the output_filename needs to be specified as a metadata.option to allow for
        # `verdi calcjob outputcat` to work correctly. Here we check that, if the users manually changed
        # the input_filename, they also changed the output_filename accordingly
        expected_output_filename = self._SEEDNAME + ".wpout"
        if self.inputs.metadata.options.output_filename != expected_output_filename:
            raise exceptions.InputValidationError(
                "The output filename specified is wrong. You probably changed the metadata.options.input_filename "
                "but you forgot to adapt the metadata.options.output_filename accordingly! Currently, you have: "
                f"input_filename: '{self.inputs.metadata.options.input_filename}', "
                f"output_filename: '{self.inputs.metadata.options.output_filename}', "
                f"while I would expect '{expected_output_filename}'"
            )

    @staticmethod
    def _validate_lowercase(dictionary):
        """Get a dictionary and checks that all keys are lower-case.

        :param dict_node: a dictionary
        :raises InputValidationError: if any of the keys is not lower-case
        :return: ``None`` if validation passes
        """
        non_lowercase = []
        for key in dictionary:
            if key != key.lower():
                non_lowercase.append(key)
        if non_lowercase:
            raise exceptions.InputValidationError(
                "input keys to the Wannier90 plugin must be all lower-case, "
                f"but the following aren't : {', '.join(non_lowercase)}"
            )

    def _validate_input_parameters(self, parameters):
        """Get a dictionary with the content of the parameters Dict passed by the user and perform some validation.

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
            raise exceptions.InputValidationError(
                f'The following blocked keys were found in the parameters: {", ".join(existing_blocked_keys)}'
            )

    def _get_input_file_lists(self):
        """Generate the lists of files to copy and link from the 'parent_folder'."""
        input_file_specs = [
            _InputFileSpec(suffix=suffix, required=False, always_copy=False)
            for suffix in [
                ".mmn",
                ".amn",
                ".eig",
                ".chk",
                ".spn",
                ".uHu",
                "_htB.dat",
                "_htL.dat",
                "_htR.dat",
                "_htC.dat",
                "_htLC.dat",
                "_htCR.dat",
                ".unkg",
            ]
        ]

        parent_folder_uuid = self.inputs.parent_folder.computer.uuid
        parent_folder_path = self.inputs.parent_folder.get_remote_path()

        optional_file_globs = []
        remote_copy_list = []
        # We use globbing for optional input files because the 'copy'
        # call in the 'upload' step of the calculation does not fail
        # if a pattern does not match any files. If we were to use the
        # explicit file name, the 'upload' would fail if the file does
        # not exist. See also aiida-core issue #3813.
        remote_symlink_list = [
            (
                parent_folder_uuid,
                os.path.join(parent_folder_path, pattern),
                ".",
            )
            for pattern in optional_file_globs
        ]
        for file_spec in input_file_specs:
            if file_spec.required:
                filename = self._SEEDNAME + file_spec.suffix
                file_info = (
                    parent_folder_uuid,
                    os.path.join(parent_folder_path, filename),
                    filename,
                )
            else:
                # Use globbing for optional files, see comment above.
                file_info = (
                    parent_folder_uuid,
                    os.path.join(parent_folder_path, "*" + file_spec.suffix),
                    ".",
                )
            if file_spec.always_copy:
                remote_copy_list.append(file_info)
            else:
                remote_symlink_list.append(file_info)
        return _InputFileLists(
            local_copy_list=[],
            remote_copy_list=remote_copy_list,
            remote_symlink_list=remote_symlink_list,
        )

    def on_terminated(self):
        """Clean the working directories of all child calculation jobs if `clean_workdir=True` in the inputs."""
        if self.inputs.clean_workdir.value is False:  # type: ignore[union-attr]
            self.report("remote folders will not be cleaned")
        else:
            try:
                # pylint: disable=protected-access
                self.outputs["remote_folder"]._clean()
                self.report("cleaned remote folders of the calculation")
            except (OSError, KeyError):
                pass

        # I need to run the cleanning before this, otherwise the it is not executed.
        super().on_terminated()
