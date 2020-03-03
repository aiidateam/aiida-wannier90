#!/usr/bin/env python
# -*- coding: utf-8 -*-
################################################################################
# Copyright (c), AiiDA team and individual contributors.                       #
#  All rights reserved.                                                        #
# This file is part of the AiiDA-wannier90 code.                               #
#                                                                              #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-wannier90 #
# For further information on the license, see the LICENSE.txt file             #
################################################################################

from __future__ import absolute_import
from six.moves import zip

__all__ = ('group_list', 'groups_to_string', 'list_to_grouped_string')


def group_list(values):
    values = sorted(values)
    groups = []
    if not values:
        return groups
    current_start = values[0]
    for v1, v2 in zip(values, values[1:]):
        # contiguous range
        if v2 - 1 <= v1:
            continue
        # break in the range
        else:
            groups.append(sorted(set([current_start, v1])))
            current_start = v2
        # final group
    groups.append(sorted(set([current_start, v2])))  # pylint: disable=undefined-loop-variable
    return groups


def groups_to_string(value_groups):
    return ','.join(
        '-'.join([str(g) for g in group]) for group in value_groups
    )


def list_to_grouped_string(values):
    return groups_to_string(group_list(values))
