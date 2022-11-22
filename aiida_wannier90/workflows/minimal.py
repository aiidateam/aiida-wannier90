################################################################################
# Copyright (c), AiiDA team and individual contributors.                       #
#  All rights reserved.                                                        #
# This file is part of the AiiDA-wannier90 code.                               #
#                                                                              #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-wannier90 #
# For further information on the license, see the LICENSE.txt file             #
################################################################################
"""A minimal WorkChain to run Wannier90."""
from aiida import orm
from aiida.engine import ToContext, WorkChain, calcfunction
from aiida.orm import Dict
from aiida.orm.nodes.data.upf import get_pseudos_from_structure
from aiida.plugins import CalculationFactory


class MinimalW90WorkChain(WorkChain):
    """Workchain to run a full stack of Quantum ESPRESSO + Wannier90 for GaAs.

    Note that this is mostly to be used as an example, as there is no
    error checking and runs directly Quantum ESPRESSO calculations rather
    than the base workflows.
    """

    @classmethod
    def define(cls, spec):
        """Define the process specification."""
        super().define(spec)
        spec.input(
            "pw_code",
            valid_type=orm.Code,
            help="The `pw.x` code to use for the `PwCalculation`s.",
        )
        spec.input(
            "pw2wannier90_code",
            valid_type=orm.Code,
            help="The `pw2wannier90.x` code to use for the `Pw2Wannier90Calculation`s.",
        )
        spec.input(
            "wannier_code",
            valid_type=orm.Code,
            help="The `wannier90.x` code to use for the `Wannier90Calculation`s.",
        )
        spec.input(
            "structure", valid_type=orm.StructureData, help="The input structure."
        )
        spec.input(
            "pseudo_family",
            valid_type=orm.Str,
            help="The name of a pseudopotential family to use.",
        )
        spec.input(
            "num_machines",
            valid_type=orm.Int,
            help="The number of machines (nodes) to use",
            required=False,
            default=lambda: orm.Int(1),
        )
        spec.input(
            "max_wallclock_seconds",
            valid_type=orm.Int,
            help="Maximum wallclock time in seconds",
            required=False,
            default=lambda: orm.Int(30 * 60),
        )
        spec.input(
            "kpoints_scf",
            valid_type=orm.KpointsData,
            help="The kpoints for the SCF run.",
        )
        spec.input(
            "kpoints_nscf",
            valid_type=orm.KpointsData,
            help="The kpoints for the NSCF run and Wannierisation.",
        )
        spec.input(
            "kpoint_path",
            valid_type=orm.Dict,
            help="The kpoints path for the NSCF run and Wannierisation.",
        )
        spec.input(
            "projections",
            valid_type=orm.OrbitalData,
            help="The projections for the Wannierisation.",
        )

        spec.outline(
            cls.run_pw_scf,
            cls.run_pw_nscf,
            cls.run_w90_pp,
            cls.run_pw2wan,
            cls.run_w90,
            cls.results,
        )
        spec.output("scf_output", valid_type=orm.Dict)
        spec.output("nscf_output", valid_type=orm.Dict)
        spec.output("nnkp_file", valid_type=orm.SinglefileData)
        spec.output("p2wannier_output", valid_type=orm.Dict)
        spec.output("matrices_folder", valid_type=orm.FolderData)
        spec.output("pw2wan_remote_folder", valid_type=orm.RemoteData)
        spec.output("wannier_bands", valid_type=orm.BandsData)

    def run_pw_scf(self):
        """Run the SCF with pw.x."""

        # A fixed value, for testing
        ecutwfc = 30.0

        self.ctx.scf_parameters = {
            "CONTROL": {
                "calculation": "scf",
            },
            "SYSTEM": {
                "ecutwfc": ecutwfc,
                "ecutrho": ecutwfc * 8.0,
            },
        }

        inputs = {
            "code": self.inputs.pw_code,
            "structure": self.inputs.structure,
            "pseudos": get_pseudos_from_structure(
                self.inputs.structure, self.inputs.pseudo_family.value
            ),
            "parameters": orm.Dict(self.ctx.scf_parameters),
            "kpoints": self.inputs.kpoints_scf,
            "metadata": {
                "options": {
                    # int is used to convert from AiiDA nodes to python ints
                    "resources": {"num_machines": int(self.inputs.num_machines)},
                    "max_wallclock_seconds": int(self.inputs.max_wallclock_seconds),
                    "withmpi": True,
                }
            },
        }

        running = self.submit(CalculationFactory("quantumespresso.pw"), **inputs)
        self.report(f"launching PwCalculation<{running.pk}> (SCF step)")

        return ToContext(pw_scf=running)

    def run_pw_nscf(self):
        """Run the NSCF step with ``pw.x``."""

        self.out("scf_output", self.ctx.pw_scf.outputs.output_parameters)

        try:
            # Check if it's an explicit list of kpoints; this raises AttributeError if it's a mesh
            self.inputs.kpoints_nscf.get_kpoints()
            # If I am here, this an explicit grid, I stop
            raise ValueError(
                "You should pass an MP grid; we'll take care of converting to an explicit one"
            )
        except AttributeError:
            # Check that the one provided is an unshifted mesh
            assert self.inputs.kpoints_nscf.get_kpoints_mesh()[1] == [
                0,
                0,
                0,
            ], "You should pass an unshifted mesh"
            self.ctx.kpoints_nscf_explicit = get_explicit_kpoints(
                self.inputs.kpoints_nscf
            )

        nscf_parameters = self.ctx.scf_parameters.copy()
        nscf_parameters["CONTROL"]["calculation"] = "nscf"

        inputs = {
            "code": self.inputs.pw_code,
            "structure": self.inputs.structure,
            "pseudos": get_pseudos_from_structure(
                self.inputs.structure, self.inputs.pseudo_family.value
            ),
            "parameters": orm.Dict(nscf_parameters),
            "kpoints": self.ctx.kpoints_nscf_explicit,
            "parent_folder": self.ctx.pw_scf.outputs.remote_folder,
            "metadata": {
                "options": {
                    "resources": {"num_machines": int(self.inputs.num_machines)},
                    "max_wallclock_seconds": int(self.inputs.max_wallclock_seconds),
                    "withmpi": True,
                }
            },
        }

        running = self.submit(CalculationFactory("quantumespresso.pw"), **inputs)
        self.report(f"launching PwCalculation<{running.pk}> (NSCF step)")

        return ToContext(pw_nscf=running)

    def run_w90_pp(self):
        """Run the Wannier90 pre-processing with -pp wannier90.x."""

        self.out("nscf_output", self.ctx.pw_nscf.outputs.output_parameters)

        # A fixed value, for testing
        self.ctx.exclude_bands = [1, 2, 3, 4, 5]

        self.ctx.w90_pp_parameters = {
            "mp_grid": self.inputs.kpoints_nscf.get_kpoints_mesh()[0],
            "write_hr": False,
            "write_xyz": False,
            "use_ws_distance": True,
            "bands_plot": True,
            "num_iter": 200,
            "guiding_centres": False,
            "num_wann": 4,
            "exclude_bands": self.ctx.exclude_bands,
        }

        inputs = {
            "code": self.inputs.wannier_code,
            "structure": self.inputs.structure,
            "parameters": orm.Dict(self.ctx.w90_pp_parameters),
            "kpoints": self.ctx.kpoints_nscf_explicit,
            "kpoint_path": self.inputs.kpoint_path,
            "projections": self.inputs.projections,
            "settings": Dict({"postproc_setup": True}),
            "metadata": {
                "options": {
                    "resources": {"num_machines": int(self.inputs.num_machines)},
                    "max_wallclock_seconds": int(self.inputs.max_wallclock_seconds),
                    "withmpi": False,  # serial run
                }
            },
        }

        running = self.submit(CalculationFactory("wannier90.wannier90"), **inputs)
        self.report(f"launching Wannier90<{running.pk}> (pp step)")

        return ToContext(w90_pp=running)

    def run_pw2wan(self):
        """Run pw2wannier90.x."""
        self.out("nnkp_file", self.ctx.w90_pp.outputs.nnkp_file)

        self.ctx.pw2wannier_parameters = {
            "inputpp": {
                "write_amn": True,
                "write_unk": True,
                "write_mmn": True,
            }
        }
        settings = {"ADDITIONAL_RETRIEVE_LIST": ["*.amn", "*.mmn", "*.eig"]}
        inputs = {
            "code": self.inputs.pw2wannier90_code,
            "parameters": orm.Dict(self.ctx.pw2wannier_parameters),
            "parent_folder": self.ctx.pw_nscf.outputs.remote_folder,
            "nnkp_file": self.ctx.w90_pp.outputs.nnkp_file,
            "settings": Dict(settings),
            "metadata": {
                "options": {
                    "resources": {"num_machines": int(self.inputs.num_machines)},
                    "max_wallclock_seconds": int(self.inputs.max_wallclock_seconds),
                    "withmpi": True,
                }
            },
        }
        running = self.submit(
            CalculationFactory("quantumespresso.pw2wannier90"), **inputs
        )
        self.report(f"launching pw2wannier90<{running.pk}>(pw2wannier90 step)")
        return ToContext(pw2wannier=running)

    def run_w90(self):
        """Run the Wannier90 main run with wannier90.x."""
        self.out("matrices_folder", self.ctx.pw2wannier.outputs.retrieved)
        self.out("pw2wan_remote_folder", self.ctx.pw2wannier.outputs.remote_folder)
        self.out("p2wannier_output", self.ctx.pw2wannier.outputs.output_parameters)

        inputs = {
            "code": self.inputs.wannier_code,
            "structure": self.inputs.structure,
            "parameters": orm.Dict(self.ctx.w90_pp_parameters),
            "kpoints": self.ctx.kpoints_nscf_explicit,
            "kpoint_path": self.inputs.kpoint_path,
            "remote_input_folder": self.ctx.pw2wannier.outputs.remote_folder,
            "projections": self.inputs.projections,
            "metadata": {
                "options": {
                    "resources": {"num_machines": int(self.inputs.num_machines)},
                    "max_wallclock_seconds": int(self.inputs.max_wallclock_seconds),
                    "withmpi": False,
                }
            },
        }

        running = self.submit(CalculationFactory("wannier90.wannier90"), **inputs)
        self.report(f"launching Wannier90<{running.pk}> (main run)")

        return ToContext(w90=running)

    def results(self):
        """Output the final results obtained in the previous step."""
        self.out("wannier_bands", self.ctx.w90.outputs.interpolated_bands)


@calcfunction
def get_explicit_kpoints(kpoints):
    """Convert from a mesh to an explicit list."""
    from aiida.orm import KpointsData

    kpt = KpointsData()
    kpt.set_kpoints(kpoints.get_kpoints_mesh(print_list=True))
    return kpt
