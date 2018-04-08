#!/usr/bin/env python3

"""
Fileserver management utility.
"""

import argparse
import sys

import actions


class InvalidAction(ValueError):
    pass


def parse_args(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument(
        "action",
        choices=[
            "create",
            "tune",
            "merge",
            "start",
            "stop",
        ],
    )
    return parser.parse_known_args(args=argv)


def main(argv=None):
    namespace, extra_args = parse_args(argv=argv)

    if namespace.action == "create":
        action = actions.Create(extra_args)
    elif namespace.action == "merge":
        action = actions.Merge(extra_args)
    elif namespace.action == "tune":
        action = actions.Tune(extra_args)
    elif namespace.action == "start":
        action = actions.Start(extra_args)
    elif namespace.action == "stop":
        action = actions.Stop(extra_args)
    else:
        raise InvalidAction(namespace.action)

    action.do()


if __name__ == "__main__":
    main(argv=sys.argv[1:])
