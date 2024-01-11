################################################################################
# Copyright (c), AiiDA team and individual contributors.                       #
#  All rights reserved.                                                        #
# This file is part of the AiiDA-wannier90 code.                               #
#                                                                              #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-wannier90 #
# For further information on the license, see the LICENSE.txt file             #
################################################################################
"""Parser for the `Postw90Calculation`."""
from pathlib import Path
import typing as ty

import numpy as np

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

        from aiida.orm import ArrayData, Dict, XyData

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

        # Some times the error files are aiida.node_XXXXX.werr, ...
        # The XXXXX are 5-digit index of processor
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

        params = self.node.inputs.parameters.get_dict()
        retrieve_temporary_list = self.node.base.attributes.get(
            "retrieve_temporary_list", None
        )
        retrieved_tmp_filenames = None
        # If temporary files were specified, check that we have them
        if retrieve_temporary_list:
            try:
                retrieved_temporary_folder = Path(kwargs["retrieved_temporary_folder"])
            except KeyError:
                return self.exit_codes.ERROR_NO_RETRIEVED_TEMPORARY_FOLDER
            retrieved_tmp_filenames = [
                _.name for _ in retrieved_temporary_folder.iterdir()
            ]

        if params.get("boltzwann", False):
            if retrieved_tmp_filenames is None:
                return self.exit_codes.ERROR_NO_RETRIEVED_TEMPORARY_FOLDER

            if params.get("boltz_calc_also_dos", False):
                filename = retrieved_temporary_folder / f"{seedname}_boltzdos.dat"
                if filename.name in retrieved_tmp_filenames:
                    with open(filename, encoding="utf-8") as handle:
                        energy_dos, attrs = raw_boltzdos_dat_parser(handle)
                    boltzdos_dat = XyData()
                    boltzdos_dat.set_x(energy_dos[:, 0], "Energy", "eV")
                    boltzdos_dat.set_y(energy_dos[:, 1], "Dos", "states/eV")
                    boltzdos_dat.base.attributes.set_many(attrs)
                    self.out("boltzwann.boltzdos", boltzdos_dat)
                else:
                    self.logger.error(
                        f"Did not find {filename} in temporary retrieved files"
                    )
                    return self.exit_codes.ERROR_OUTPUT_FILE_MISSING

            filename = retrieved_temporary_folder / f"{seedname}_elcond.dat"
            if filename.name in retrieved_tmp_filenames:
                with open(filename, encoding="utf-8") as handle:
                    elcond, column_names, attrs = raw_elcond_dat_parser(handle)
                elcond_dat = ArrayData()
                for i, name in enumerate(column_names):
                    col = elcond[:, i]
                    elcond_dat.set_array(name, np.array(col))
                elcond_dat.base.attributes.set_many(attrs)
                self.out("boltzwann.elcond", elcond_dat)
            else:
                self.logger.error(
                    f"Did not find {filename} in temporary retrieved files"
                )
                return self.exit_codes.ERROR_OUTPUT_FILE_MISSING

            filename = retrieved_temporary_folder / f"{seedname}_kappa.dat"
            if filename.name in retrieved_tmp_filenames:
                with open(filename, encoding="utf-8") as handle:
                    kappa, column_names, attrs = raw_kappa_dat_parser(handle)
                kappa_dat = ArrayData()
                for i, name in enumerate(column_names):
                    col = kappa[:, i]
                    kappa_dat.set_array(name, np.array(col))
                kappa_dat.base.attributes.set_many(attrs)
                self.out("boltzwann.kappa", kappa_dat)
            else:
                self.logger.error(
                    f"Did not find {filename} in temporary retrieved files"
                )
                return self.exit_codes.ERROR_OUTPUT_FILE_MISSING

            filename = retrieved_temporary_folder / f"{seedname}_seebeck.dat"
            if filename.name in retrieved_tmp_filenames:
                with open(filename, encoding="utf-8") as handle:
                    seebeck, column_names, attrs = raw_seebeck_dat_parser(handle)
                seebeck_dat = ArrayData()
                for i, name in enumerate(column_names):
                    col = seebeck[:, i]
                    seebeck_dat.set_array(name, np.array(col))
                seebeck_dat.base.attributes.set_many(attrs)
                self.out("boltzwann.seebeck", seebeck_dat)
            else:
                self.logger.error(
                    f"Did not find {filename} in temporary retrieved files"
                )
                return self.exit_codes.ERROR_OUTPUT_FILE_MISSING

            filename = retrieved_temporary_folder / f"{seedname}_sigmas.dat"
            if filename.name in retrieved_tmp_filenames:
                with open(filename, encoding="utf-8") as handle:
                    sigmas, column_names, attrs = raw_sigmas_dat_parser(handle)
                sigmas_dat = ArrayData()
                for i, name in enumerate(column_names):
                    col = sigmas[:, i]
                    sigmas_dat.set_array(name, np.array(col))
                sigmas_dat.base.attributes.set_many(attrs)
                self.out("boltzwann.sigmas", sigmas_dat)
            else:
                self.logger.error(
                    f"Did not find {filename} in temporary retrieved files"
                )
                return self.exit_codes.ERROR_OUTPUT_FILE_MISSING

            filename = retrieved_temporary_folder / f"{seedname}_tdf.dat"
            if filename.name in retrieved_tmp_filenames:
                with open(filename, encoding="utf-8") as handle:
                    tdf, column_names, attrs = raw_tdf_dat_parser(handle)
                tdf_dat = ArrayData()
                for i, name in enumerate(column_names):
                    col = tdf[:, i]
                    tdf_dat.set_array(name, np.array(col))
                tdf_dat.base.attributes.set_many(attrs)
                self.out("boltzwann.tdf", tdf_dat)
            else:
                self.logger.error(
                    f"Did not find {filename} in temporary retrieved files"
                )
                return self.exit_codes.ERROR_OUTPUT_FILE_MISSING


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
    regex_boltzwann_grid = re.compile(
        r"k-grid used for band interpolation in BoltzWann: *([0-9]+)x([0-9]+)x([0-9]+)"
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

        # checks for the k-grid used for band interpolation in BoltzWann
        match = regex_boltzwann_grid.match(line.strip())
        if match:
            out.update(
                {
                    "kmesh_boltzwann": [
                        int(match.group(1)),
                        int(match.group(2)),
                        int(match.group(3)),
                    ]
                }
            )

    return out


def raw_boltzdos_dat_parser(handle: ty.TextIO) -> ty.Union[np.ndarray, dict]:
    """Parse boltzdos.dat file."""
    # useless header
    # Written by the BoltzWann module of the Wannier90 code.
    handle.readline()
    # The first column.
    handle.readline()
    # The second column is the DOS for a fixed smearing of   0.300000E-01 eV.
    line = handle.readline()
    adpt_smr = False
    if "# The second column is the unsmeared DOS." in line:
        smr_width = 0.0
    elif "# The second column is the adaptively-smeared DOS" in line:
        adpt_smr = True
        # (see Yates et al., PRB 75, 195121 (2007)
        handle.readline()
        # Smearing coefficient:    0.100000
        line = handle.readline()
        adpt_smr_fac = float(line.split("Smearing coefficient:")[1].strip())
        # Number of points refined: 1394 out of 8120601
        line = handle.readline()
        line = line.split("Number of points refined:")[1].strip()
        number_of_points_total = int(line.split("out of")[1].strip())
        number_of_points_refined = int(line.split("out of")[0].strip())
        # (Min spacing:   0.1568860590E-06, max spacing:   0.1691778553    )
        line = handle.readline()
        adpt_smr_min_spacing = float(
            line.split("Min spacing:")[1].split(",")[0].strip()
        )
        adpt_smr_max_spacing = float(
            line.split("max spacing:")[1].split(")")[0].strip()
        )
    else:
        smr_width = float(line.split("fixed smearing of")[1].split("eV")[0].strip())
    # Cell volume (ang^3):     16.8700
    line = handle.readline()
    volume = float(line.split("(ang^3):")[1].strip())
    # Energy(eV) DOS [DOS DOS ...]
    handle.readline()

    attrs = {
        "adaptive_smearing": adpt_smr,
        "cell_volume": volume,
        "cell_volume_unit": "ang^3",
    }
    if adpt_smr:
        attrs.update(
            {
                "adaptive_smearing_factor": adpt_smr_fac,
                "adaptive_smearing_number_of_points_total": number_of_points_total,
                "adaptive_smearing_number_of_points_refined": number_of_points_refined,
                "adaptive_smearing_min_spacing": adpt_smr_min_spacing,
                "adaptive_smearing_max_spacing": adpt_smr_max_spacing,
            }
        )
    else:
        attrs.update(
            {
                "fixed_smearing_width": smr_width,
                "fixed_smearing_width_unit": "eV",
            }
        )
    energy_dos = np.loadtxt(handle)
    return energy_dos, attrs


def raw_elcond_dat_parser(handle: ty.TextIO) -> ty.Union[np.ndarray, list, dict]:
    """Parse elcond.dat file."""
    # useless header
    # Written by the BoltzWann module of the Wannier90 code.
    handle.readline()
    # [Electrical conductivity in SI units, i.e. in 1/Ohm/m]
    line = handle.readline()
    assert (
        line.strip() == "# [Electrical conductivity in SI units, i.e. in 1/Ohm/m]"
    ), line
    # Mu(eV) Temp(K) ElCond_xx ElCond_xy ElCond_yy ElCond_xz ElCond_yz ElCond_zz
    handle.readline()

    attrs = {
        "Mu_unit": "eV",
        "Temp_unit": "K",
        "ElCond_unit": "1/Ohm/m",
    }
    elcond = np.loadtxt(handle)
    column_names = [
        "Mu",
        "Temp",
        "ElCond_xx",
        "ElCond_xy",
        "ElCond_yy",
        "ElCond_xz",
        "ElCond_yz",
        "ElCond_zz",
    ]
    return elcond, column_names, attrs


def raw_kappa_dat_parser(handle: ty.TextIO) -> ty.Union[np.ndarray, list, dict]:
    """Parse kappa.dat file."""
    # useless header
    # Written by the BoltzWann module of the Wannier90 code.
    handle.readline()
    # [K coefficient in SI units, i.e. in W/m/K]
    line = handle.readline()
    assert line.strip() == "# [K coefficient in SI units, i.e. in W/m/K]"
    # [the K coefficient is defined in the documentation, and is an ingredient of
    #  the thermal conductivity. See the docs for further information.]
    handle.readline()
    handle.readline()
    # Mu(eV) Temp(K) Kappa_xx Kappa_xy Kappa_yy Kappa_xz Kappa_yz Kappa_zz
    handle.readline()

    attrs = {
        "Mu_unit": "eV",
        "Temp_unit": "K",
        "ElCond_unit": "W/m/K",
    }
    kappa = np.loadtxt(handle)
    column_names = [
        "Mu",
        "Temp",
        "Kappa_xx",
        "Kappa_xy",
        "Kappa_yy",
        "Kappa_xz",
        "Kappa_yz",
        "Kappa_zz",
    ]
    return kappa, column_names, attrs


def raw_seebeck_dat_parser(handle: ty.TextIO) -> ty.Union[np.ndarray, list, dict]:
    """Parse seebeck.dat file."""
    # useless header
    # Written by the BoltzWann module of the Wannier90 code.
    handle.readline()
    # [Seebeck coefficient in SI units, i.e. in V/K]
    line = handle.readline()
    assert line.strip() == "# [Seebeck coefficient in SI units, i.e. in V/K]"
    # Mu(eV) Temp(K) Seebeck_xx Seebeck_xy Seebeck_xz Seebeck_yx Seebeck_yy Seebeck_yz Seebeck_zx Seebeck_zy Seebeck_zz
    handle.readline()

    attrs = {
        "Mu_unit": "eV",
        "Temp_unit": "K",
        "Seebeck_unit": "V/K",
    }
    seebeck = np.loadtxt(handle)
    column_names = [
        "Mu",
        "Temp",
        "Seebeck_xx",
        "Seebeck_xy",
        "Seebeck_xz",
        "Seebeck_yx",
        "Seebeck_yy",
        "Seebeck_yz",
        "Seebeck_zx",
        "Seebeck_zy",
        "Seebeck_zz",
    ]
    return seebeck, column_names, attrs


def raw_sigmas_dat_parser(handle: ty.TextIO) -> ty.Union[np.ndarray, list, dict]:
    """Parse sigmas.dat file."""
    # useless header
    # Written by the BoltzWann module of the Wannier90 code.
    handle.readline()
    # [(Electrical conductivity * Seebeck coefficient) in SI units, i.e. in Ampere/m/K]
    line = handle.readline()
    assert (
        line.strip()
        == "# [(Electrical conductivity * Seebeck coefficient) in SI units, i.e. in Ampere/m/K]"
    )
    # Mu(eV) Temp(K) (Sigma*S)_xx (Sigma*S)_xy (Sigma*S)_yy (Sigma*S)_xz (Sigma*S)_yz (Sigma*S)_zz
    handle.readline()

    attrs = {
        "Mu_unit": "eV",
        "Temp_unit": "K",
        # I cannot use "(Sigma*S)_unit" as name, since ArrayData will complain
        # "(Sigma*S)_unit": "V/K",
        "SigmaS_unit": "V/K",
    }
    sigmas = np.loadtxt(handle)
    column_names = [
        "Mu",
        "Temp",
        "SigmaS_xx",  # "(Sigma*S)_xx",
        "SigmaS_xy",  # "(Sigma*S)_xy",
        "SigmaS_yy",  # "(Sigma*S)_yy",
        "SigmaS_xz",  # "(Sigma*S)_xz",
        "SigmaS_yz",  # "(Sigma*S)_yz",
        "SigmaS_zz",  # "(Sigma*S)_zz",
    ]
    return sigmas, column_names, attrs


def raw_tdf_dat_parser(handle: ty.TextIO) -> ty.Union[np.ndarray, list, dict]:
    """Parse tdf.dat file."""
    # useless header
    # Written by the BoltzWann module of the Wannier90 code.
    handle.readline()
    # Transport distribution function (in units of 1/hbar^2 * eV * fs / angstrom) vs energy in eV
    line = handle.readline()
    assert (
        line.strip()
        == "# Transport distribution function (in units of 1/hbar^2 * eV * fs / angstrom) vs energy in eV"
    )
    # Content of the columns:
    # Energy TDF_xx TDF_xy TDF_yy TDF_xz TDF_yz TDF_zz
    #   (if spin decomposition is required, 12 further columns are provided, with the 6
    #    components of the TDF for the spin up, followed by those for the spin down)
    for _ in range(4):
        handle.readline()

    attrs = {
        "Energy_unit": "eV",
        "TDF_unit": "1/hbar^2 * eV * fs / angstrom",
    }
    tdf = np.loadtxt(handle)
    column_names = [
        "Energy",
        "TDF_xx",
        "TDF_xy",
        "TDF_yy",
        "TDF_xz",
        "TDF_yz",
        "TDF_zz",
    ]
    return tdf, column_names, attrs
