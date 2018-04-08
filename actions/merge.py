import argparse
import collections

import yaml

import actions.action
import configuration
import utility


"""
Merge multiple configs into a single output config.

This is useful when incorporating new disks or volumes into an existing system.
"""


def parse_args(argv):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument(
        "--input_files",
        nargs="+",
    )
    parser.add_argument(
        "--output_file",
        required=True,
    )
    return parser.parse_args(args=argv)


class Merge(actions.action.Action):
    def __init__(self, argv):
        self.argv = argv
        self.args = parse_args(self.argv)
        self.configuration = configuration.make_many_raw(self.args.input_files)

    def do(self):
        config = collections.OrderedDict()
        for c in self.configuration:
            config = utility.merge(config, c)
        open(self.args.output_file, "w").write(yaml.dump(config))
