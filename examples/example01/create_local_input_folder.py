#!/usr/bin/env runaiida
from __future__ import absolute_import
from __future__ import print_function
import os
from six.moves import input

files_folder = os.path.join(
    os.path.split(os.path.abspath(__file__))[0], "inputdata"
)

folder_node = DataFactory('folder')()
folder_node.replace_with_folder(files_folder)

print("Do you want to store the FolderData node? [CTRL+C to stop]")
input()
folder_node.store()
print(("Stored FolderData node pk={}".format(folder_node.pk)))
print("You can now run:")
print(("verdi run wannier_gaas.py --dont-send local {} <WANNIER_CODE_NAME>".format(
    folder_node.pk
)))
