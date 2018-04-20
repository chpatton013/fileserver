import collections
from functools import reduce


class InconsistentTypeError(TypeError):
    pass


def _merge_dict_items(lhs, rhs, result):
    """
    Recursively merge two dictionary-like arguments (lhs, rhs) into a
    dictionary-like argument (result).
    """
    # Initialize result with contents of lhs.
    for k, v in lhs.items():
        result[k] = v

    # Iteratively apply contents of rhs.
    for k, v in rhs.items():
        # If an rhs-key is already in result, attempt to merge.
        if k in result:
            result[k] = merge(result[k], v)
        # If an rhs-key is not present in result, insert it.
        else:
            result[k] = v

    return result


def merge(lhs, rhs):
    """
    Recursively merge two arguments of identical type.

    This has similar semantics to dict.update, but does not modify lhs and
    applies to all types.

    If lhs and rhs are not the same type, InconsistentTypeError is raised.
    If lhs and rhs are dict's or collections.OrderedDict's, they are recursively
    merged.
    If lhs and rhs are list's, lhs and rhs are appended.
    If lhs and rhs are any other type, lhs is replaced by rhs.
    """
    if type(lhs) != type(rhs):
        raise InconsistentTypeError()

    arg_type = type(lhs)

    if arg_type == collections.OrderedDict:
        return _merge_dict_items(lhs, rhs, collections.OrderedDict())
    if arg_type == dict:
        return _merge_dict_items(lhs, rhs, dict())
    elif arg_type == list:
        return lhs + rhs
    else:
        return rhs


def merge_r(lhs, *rhs):
    """
    Recursively merge any number of arguments of identical type.

    See merge() for information about merging semantics.
    """
    return reduce(merge, rhs, initializer=lhs)


def greatest_common_denominator(a, b):
    """
    Find the greatest common denominator between two integers.
    """
    while b:
        modulo = a % b
        a = b
        b = modulo
    return a


def least_common_multiple(a, b):
    """
    Find the least common multiple between two integers.
    """
    return a * b // greatest_common_denominator(a, b)
