################################################################################
# Copyright (c), AiiDA team and individual contributors.                       #
#  All rights reserved.                                                        #
# This file is part of the AiiDA-wannier90 code.                               #
#                                                                              #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-wannier90 #
# For further information on the license, see the LICENSE.txt file             #
################################################################################
"""Parser for the `Postw90Calculation`."""

from aiida.common import exceptions as exc
from aiida.parsers import Parser

__all__ = ("Postw90Parser",)


class Postw90Parser(Parser):
    """postw90 output parser."""

    def __init__(self, node):
        """Construct the parser."""
        from ..calculations import Postw90Calculation

        # check for valid input
        if not issubclass(node.process_class, Postw90Calculation):
            raise exc.OutputParsingError(
                "Input must calc must be a "
                f"Postw90Calculation, it is instead {type(node.process_class)}"
            )
        super().__init__(node)

    @staticmethod
    def _get_seedname_from_input_filename(input_filename):
        """Return the seedname given the input filename.

        Raises a ValueError if the input filename does not end with .win.
        """
        input_suffix = ".win"
        if input_filename.endswith(input_suffix):
            return input_filename[: -len(input_suffix)]

        raise ValueError(
            f"The input filename '{input_filename}' does not end with '{input_suffix}', "
            "so I don't know how to get the seedname"
        )

    def parse(self, **kwargs):  # pylint: disable=inconsistent-return-statements
        """Parse the datafolder, stores results.

        This parser for this simple code does simply store in the DB a node
        representing the file of forces in real space.
        """
        # pylint: disable=too-many-return-statements,too-many-statements
        import re

        from aiida.orm import Dict

        # None if unset
        # temporary_folder = kwargs.get("retrieved_temporary_folder")

        seedname = self._get_seedname_from_input_filename(
            self.node.get_options()["input_filename"]
        )
        output_file_name = f"{seedname}.wpout"
        error_file_name = f"{seedname}.werr"

        # select the folder object
        # Check that the retrieved folder is there
        try:
            out_folder = self.retrieved
        except exc.NotExistent:
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        exiting_in_stdout = False
        try:
            with out_folder.base.repository.open(output_file_name) as handle:
                out_file = handle.readlines()
            # Wannier90 doesn't always write the .werr file on error
            for line in out_file:
                if "Exiting......" in line:
                    exiting_in_stdout = True
                if "Unable to satisfy B1" in line:
                    return self.exit_codes.ERROR_BVECTORS
                if "kmesh_get_bvector: Not enough bvectors found" in line:
                    return self.exit_codes.ERROR_BVECTORS
                if (
                    "kmesh_get: something wrong, found too many nearest neighbours"
                    in line
                ):
                    return self.exit_codes.ERROR_BVECTORS
                err_msg = (
                    "Energy window contains fewer states than number of target WFs, "
                    "consider reducing dis_proj_min/increasing dis_win_max?"
                )
                if err_msg in line:
                    return self.exit_codes.ERROR_DISENTANGLEMENT_NOT_ENOUGH_STATES
                if "Error plotting WF cube. Try one of the following:" in line:
                    return self.exit_codes.ERROR_PLOT_WF_CUBE
            if len(out_file) == 0:
                return self.exit_codes.ERROR_OUTPUT_STDOUT_INCOMPLETE
            if out_file[-1].strip() not in (
                f"Exiting... {seedname}.nnkp written.",
                "All done: postw90 exiting",
            ):
                return self.exit_codes.ERROR_OUTPUT_STDOUT_INCOMPLETE
        except OSError:
            self.logger.error("Standard output file could not be found.")
            return self.exit_codes.ERROR_OUTPUT_STDOUT_MISSING

        # Checks for error output files
        # This is after the check of stdout, since stdout might give more verbose exit code.
        if error_file_name in out_folder.base.repository.list_object_names():
            self.logger.error(
                "Errors were found please check the retrieved "
                f"{error_file_name} file"
            )
            return self.exit_codes.ERROR_WERR_FILE_PRESENT

        # Some times the error files are aiida.node_00001.werr, ...
        error_file_name = re.compile(seedname + r".+?\.werr")
        for filename in out_folder.base.repository.list_object_names():
            if error_file_name.match(filename):
                self.logger.error(
                    f"Errors were found please check the retrieved {filename} file"
                )
                return self.exit_codes.ERROR_WERR_FILE_PRESENT

        # Parse the stdout an return the parsed data
        wout_dictionary = raw_wpout_parser(out_file)
        output_data = Dict(wout_dictionary)
        self.out("output_parameters", output_data)

        if exiting_in_stdout:
            return self.exit_codes.ERROR_EXITING_MESSAGE_IN_STDOUT


def raw_wpout_parser(
    wann_out_file,
):  # pylint: disable=too-many-locals,too-many-statements
    """Parse a .wpout file and return certain key parameters.

    :param out_file: the .wpout file, as a list of strings
    :return out: a dictionary of parameters that can be stored as parameter data
    """
    import re

    regex = re.compile(
        r"Time for BoltzWann \(Boltzmann transport\) *([+-]?(?:[0-9]*[.])?[0-9]+) \(sec\)"
    )

    out = {}
    out.update({"warnings": []})
    for line in wann_out_file:
        # checks for any warnings
        if "Warning" in line:
            # Certain warnings get a special flag
            out["warnings"].append(line)

        # checks for the time taken for BoltzWann
        match_boltzwann = regex.match(line.strip())
        if match_boltzwann:
            out.update({"wallclock_seconds_boltzwann": float(match_boltzwann.group(1))})

    return out
