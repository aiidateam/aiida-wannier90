# -*- coding: utf-8 -*-
################################################################################
# Copyright (c), AiiDA team and individual contributors.                       #
#  All rights reserved.                                                        #
# This file is part of the AiiDA-wannier90 code.                               #
#                                                                              #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-wannier90 #
# For further information on the license, see the LICENSE.txt file             #
################################################################################

__all__ = ('group_list', 'groups_to_string', 'list_to_grouped_string')


def group_list(values):  # pylint: disable=missing-function-docstring
    values = sorted(values)
    groups = []
    if not values:
        return groups
    if len(values) == 1:
        return [values]
    current_start = values[0]
    for val1, val2 in zip(values, values[1:]):
        # contiguous range
        if val2 - 1 <= val1:
            continue
        # break in the range
        groups.append(sorted(set([current_start, val1])))
        current_start = val2
        # final group
    groups.append(sorted(set([current_start, val2])))  # pylint: disable=undefined-loop-variable
    return groups


def groups_to_string(value_groups):
    return ','.join(
        '-'.join([str(g) for g in group]) for group in value_groups
    )


def list_to_grouped_string(values):
    return groups_to_string(group_list(values))
