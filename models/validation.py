import re
import os

import schema


def validate_missing_keys(data, required_keys):
    missing_keys = [key for key in required_keys if key not in data]
    if len(missing_keys):
        s_missing_keys = ', '.join(
            repr(k) for k in sorted(missing_keys, key=repr),
        )
        raise schema.SchemaMissingKeyError(
            "Missing keys: " + s_missing_keys,
        )


def is_int(data):
    return type(data) is int


def is_float(data):
    return type(data) is float


def is_string(data):
    return type(data) is str


def is_list(data):
    return type(data) is list


def is_octal(data):
    return is_string(data) and all(0 <= int(c) < 8 for c in data)


def is_positive(data):
    return data > 0


def is_negative(data):
    return data < 0


def not_positive(data):
    return not is_positive(data)


def not_negative(data):
    return not is_negative(data)


def not_empty(data):
    return len(data) > 0


def length_eq(length):
    return lambda data: len(data) == length


def equals(value):
    return lambda data: data == value


def one_of(*options):
    return lambda data: data in options


def matches(regex):
    return lambda data: re.compile(regex).match(data)
