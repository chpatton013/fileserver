import collections


class InconsistentTypeError(TypeError):
    pass


def merge(lhs, rhs):
    if type(lhs) != type(rhs):
        raise InconsistentTypeError()

    arg_type = type(lhs)

    if arg_type == collections.OrderedDict:
        result = collections.OrderedDict()
        for k, v in lhs.items():
            result[k] = v
        for k, v in rhs.items():
            if k in result:
                result[k] = merge(result[k], v)
            else:
                result[k] = v
        return result
    elif arg_type == list:
        return lhs + rhs
    else:
        return rhs
