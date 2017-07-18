#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

def test_local_input(sample, configure_with_daemon):
    from aiida.orm import DataFactory, CalculationFactory
    FolderData = DataFactory('folder')
    local_input_folder = FolderData()
    sample_folder = sample('gaas')
    exclude_list = ['gaas.win']
    for path in os.listdir(sample_folder):
        if path in exclude_list:
            continue
        abs_path = os.path.join(sample_folder, path)
        local_input_folder.add_path(abs_path, path.replace('gaas', 'aiida'))
