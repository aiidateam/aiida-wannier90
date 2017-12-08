#!/usr/bin/env python
# -*- coding: utf-8 -*-


def group_list(values):
    values = sorted(values)
    groups = []
    if len(values) == 0:
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
    else:
        groups.append(sorted(set([current_start, v2])))
    return groups


def groups_to_string(value_groups):
    return ','.join(
        '-'.join([str(g) for g in group]) for group in value_groups
    )


def list_to_grouped_string(values):
    return groups_to_string(group_list(values))
