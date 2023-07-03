#!/usr/bin/env runaiida
################################################################################
# Copyright (c), AiiDA team and individual contributors.                       #
#  All rights reserved.                                                        #
# This file is part of the AiiDA-wannier90 code.                               #
#                                                                              #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-wannier90 #
# For further information on the license, see the LICENSE.txt file             #
################################################################################
"""Example to create a local input folder for a Wannier90Calculation."""
import os

from aiida.plugins import DataFactory

# Get path of 'inputdata' folder in the same folder as this script.
files_folder = os.path.join(os.path.split(os.path.abspath(__file__))[0], "inputdata")


def get_unstored_folder_data(seedname="aiida"):
    """Return a folder data (unstored) containing the .amn and .mmn files for GaAs."""
    # Create empty FolderData node
    folder_node = DataFactory("core.folder")()  # pylint: disable=redefined-outer-name
    for local_file_name, file_name_in_aiida in [
        ("gaas.amn", f"{seedname}.amn"),
        ("gaas.mmn", f"{seedname}.mmn"),
    ]:
        folder_node.base.repository.put_object_from_file(
            filepath=os.path.join(files_folder, local_file_name),
            path=file_name_in_aiida,
        )
    return folder_node


if __name__ == "__main__":
    folder_node = get_unstored_folder_data()
    print("Do you want to store the FolderData node? [CTRL+C to stop]")
    input()
    folder_node.store()
    print(f"Stored FolderData node pk={folder_node.pk}")
    print("You can now run:")
    print(f"verdi run wannier_gaas.py --send <WANNIER_CODE_NAME> main {folder_node.pk}")
