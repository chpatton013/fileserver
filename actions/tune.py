"""
Tune performance parameters for disk devices, raid volumes, and filesystem
volumes.
"""


import argparse
import datetime

import actions.action
import configuration
import executor
import parameters


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


class Tune(actions.action.Action):
    def __init__(self, argv):
        self.argv = argv
        self.args = parse_args(self.argv)
        self.executor = executor.Executor(
            dryrun=self.args.dryrun,
            verbose=self.args.verbose,
        )
        self.configuration = configuration.make(self.args.config_file)

    def do(self):
        # TODO: assert everything is started before proceeding

        rc_commands = []
        rc_commands += self._tune_disk()
        rc_commands += self._tune_raid()

        self._tune_fs()

        self._tune_persist(rc_commands)

    def _tune_disk_device(self, device, max_sectors_kb, ncq_depth):
        rc_commands = []

        rc_commands.append(self.executor.info(
            "Tuning disk device '{}'".format(device.path),
        ))

        rc_commands.append(self.executor.run([
            "blockdev",
            "--setra",
            str(device.readahead_sectors),
            device.path,
        ]))

        rc_commands.append(self.executor.write(
            device.max_sectors_kb_file,
            str(max_sectors_kb),
        ))

        rc_commands.append(self.executor.write(
            device.nr_requests_file,
            str(device.nr_requests),
        ))

        rc_commands.append(self.executor.write(
            device.queue_depth_file,
            str(ncq_depth),
        ))

        return rc_commands

    def _tune_disk(self):
        rc_commands = []

        rc_commands.append(self.executor.info("Tuning disk parameters"))

        for device_group in self.configuration.disk.device_groups:
            raid_volume = self.configuration.find_raid_volume(
                device_group.raid_volume,
            )
            max_sectors_kb = parameters.raid_chunk_size_kb(
                raid_volume.raid_level,
            )

            disk_devices = \
                self.configuration.find_disk_devices_with_raid_volume(
                    device_group.raid_volume,
                )
            ncq_depth = parameters.disk_ncq_depth(disk_devices)

            for device in device_group.devices:
                rc_commands += self._tune_disk_device(
                    device,
                    max_sectors_kb,
                    ncq_depth,
                )

        return rc_commands

    def _tune_raid_volume(self, volume):
        rc_commands = []

        rc_commands.append(self.executor.info(
            "Tuning RAID volume '{}' ('{}')".format(volume.name, volume.label),
        ))

        disk_devices = self.configuration.find_disk_devices_with_raid_volume(
            volume.name,
        )

        raid_readahead_sectors = parameters.raid_readahead_sectors(disk_devices)
        rc_commands.append(self.executor.run([
            "blockdev",
            "--setra",
            str(raid_readahead_sectors),
            volume.label_path,
        ]))

        raid_stripe_cache_pages = parameters.raid_stripe_cache_pages(
            disk_devices,
        )
        rc_commands.append(self.executor.write(
            volume.stripe_cache_size_file,
            str(raid_stripe_cache_pages),
        ))

        return rc_commands

    def _tune_raid(self):
        rc_commands = []

        rc_commands.append(self.executor.info("Tuning RAID parameters"))

        rc_commands.append(self.executor.write(
            self.configuration.raid.speed_limit_min_file,
            str(self.configuration.raid.speed_limit_min),
        ))

        rc_commands.append(self.executor.write(
            self.configuration.raid.speed_limit_max_file,
            str(self.configuration.raid.speed_limit_max),
        ))

        for volume in self.configuration.raid.volumes:
            rc_commands += self._tune_raid_volume(volume)

        return rc_commands

    def _tune_fs_volume(self, volume):
        self.executor.info(
            "Tuning FS volume '{}' ({}:{})",
            volume.name,
            volume.device_path,
            volume.mount_location,
        )

        disk_device_group = \
            self.configuration.find_disk_device_group_with_fs_volume(
                volume.name,
            )
        raid_volume = self.configuration.find_raid_volume(
            disk_device_group.raid_volume,
        )

        self.executor.run([
            "tune2fs",
            "-E",
            "stride={},stripe-width={}".format(
                parameters.fs_stride(
                    disk_device_group.devices,
                    raid_volume.raid_level,
                ),
                parameters.fs_stripe_width(
                    disk_device_group.devices,
                    raid_volume.raid_level,
                ),
            ),
            volume.device_path,
        ])

    def _tune_fs(self):
        self.executor.info("Tuning FS parameters")

        for v in self.configuration.fs.volumes:
            self._tune_fs_volume(v)

    def _tune_persist(self, rc_commands):
        self.executor.info("Persisting tuning parameters")

        rc_file = "/etc/rc.local"
        backup_rc_file = "{}.bak.{}".format(
            rc_file,
            datetime.datetime.now().strftime("%Y%m%dT%H%M%S"),
        )
        self.executor.run(["cp", rc_file, backup_rc_file])

        rc_file_contents = "\n".join(rc_commands + ["exit 0"])
        self.executor.write(rc_file, rc_file_contents)
