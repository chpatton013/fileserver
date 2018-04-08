import collections

import yaml

import schema


__all__ = [
    "Configuration",
    "make_many_raw",
    "make",
]


class Configuration(object):
    def __init__(self, raw):
        self.__dict__.update(**dict(raw))


def represent_ordereddict(dumper, data):
    value = [
        (
            dumper.represent_data(item_key),
            dumper.represent_data(item_value),
        )
        for item_key, item_value in data.items()
    ]

    return yaml.nodes.MappingNode(u'tag:yaml.org,2002:map', value)


yaml.add_representer(collections.OrderedDict, represent_ordereddict)


def make_raw(config_file):
    return schema.ConfigurationSchema().load(
        yaml.load(open(config_file, "r").read()),
    )


def make_many_raw(config_files):
    return [make_raw(f) for f in config_files]


def make(config_file):
    return schema.Configuration(make_raw(config_file))
