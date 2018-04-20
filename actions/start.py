"""
Start existing RAID, crypt, filesystem, bind, and export volumes.
"""


import argparse

import actions.action
import configuration
import executor


def parse_args(argv):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument(
        "--config_file",
        required=True,
    )
    parser.add_argument(
        "--dryrun",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
    )
    return parser.parse_args(args=argv)


class Start(actions.action.Action):
    def __init__(self, argv):
        self.argv = argv
        self.args = parse_args(self.argv)
        self.executor = executor.Executor(
            dryrun=self.args.dryrun,
            verbose=self.args.verbose,
        )
        self.configuration = configuration.make(self.args.config_file)

    def do(self):
        self._start_raid()
        self._start_crypt()
        self._start_fs()
        self._start_bind()
        self._start_export()

    def _start_raid(self):
        pass

    def _start_crypt(self):
        pass

    def _start_fs(self):
        pass

    def _start_bind(self):
        pass

    def _start_export(self):
        pass

    def _start_raid_volume(self, volume):
        pass

    def _start_crypt_volume(self, volume):
        pass

    def _start_fs_volume(self, volume):
        pass

    def _start_bind_volume(self, volume):
        pass
