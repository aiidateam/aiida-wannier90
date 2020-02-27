#!/usr/bin/env runaiida
from __future__ import absolute_import
from __future__ import print_function

import os
from six.moves import input

from aiida.plugins import DataFactory

# Get path of 'inputdata' folder in the same folder as this script.
files_folder = os.path.join(
    os.path.split(os.path.abspath(__file__))[0], "inputdata"
)


def get_unstored_folder_data(seedname='aiida'):
    """Return a folder data (unstored) containing the .amn and .mmn files for GaAs."""
    # Create empty FolderData node
    folder_node = DataFactory('folder')()
    for local_file_name, file_name_in_aiida in [
        ('gaas.amn', '{}.amn'.format(seedname)),
        ('gaas.mmn', '{}.mmn'.format(seedname))
    ]:
        folder_node.put_object_from_file(
            path=os.path.join(files_folder, local_file_name),
            key=file_name_in_aiida,
            encoding=None
        )
    return folder_node


if __name__ == "__main__":
    folder_node = get_unstored_folder_data()
    print("Do you want to store the FolderData node? [CTRL+C to stop]")
    input()
    folder_node.store()
    print("Stored FolderData node pk={}".format(folder_node.pk))
    print("You can now run:")
    print(
        "verdi run wannier_gaas.py --send <WANNIER_CODE_NAME> main {}".format(
            folder_node.pk
        )
    )
