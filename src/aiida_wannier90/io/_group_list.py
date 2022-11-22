################################################################################
# Copyright (c), AiiDA team and individual contributors.                       #
#  All rights reserved.                                                        #
# This file is part of the AiiDA-wannier90 code.                               #
#                                                                              #
# The code is hosted on GitHub at https://github.com/aiidateam/aiida-wannier90 #
# For further information on the license, see the LICENSE.txt file             #
################################################################################
"""Functions for converting list of integers."""

__all__ = ("group_list", "groups_to_string", "list_to_grouped_string")


def group_list(values):
    """Group a list of values into a list of groups of consecutive values.

    For W90 input parameters, e.g. exclude_bands.
    """
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
        groups.append(sorted({current_start, val1}))
        current_start = val2
        # final group
    groups.append(
        sorted({current_start, val2})  # pylint: disable=undefined-loop-variable
    )
    return groups


def groups_to_string(value_groups):
    """Convert a list of groups of values to a string."""
    return ",".join("-".join([str(g) for g in group]) for group in value_groups)


def list_to_grouped_string(values):
    """Convert a list of values to a string, grouping consecutive values."""
    return groups_to_string(group_list(values))
