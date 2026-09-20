import collections
import os

import schema

import lib.utility
import models.model
import models.validation


def _validate_mdadm_auto(data):
    if not (data.startswith("+") or data.startswith("-")):
        return False
    return data[1:] in ("all", "homehost") or _validate_mdadm_metadata(data[1:])


def _validate_mdadm_metadata(data):
    str_data = str(data)

    if str_data in ("ddf", "imsm", "0.9"):
        return True

    if "." not in str_data:
        return False

    major, _, minor = str_data.partition(".")
    return (int(major) == 1) and (int(minor) >= 0)


def make_schema():
    return schema.Schema({
        # Config values for MDADM config file.
        # See `man mdadm.conf` for detailed information.
        schema.Optional("mdadm_config"): schema.Schema({
            schema.Optional("device"): schema.And(
                models.validation.is_list,
                models.validation.not_empty,
                schema.Schema([
                    schema.And(
                        models.validation.is_string,
                        models.validation.not_empty,
                    ),
                ]),
            ),
            schema.Optional("mailaddr"): schema.And(
                models.validation.is_string,
                models.validation.not_empty,
            ),
            schema.Optional("mailfrom"): schema.And(
                models.validation.is_string,
                models.validation.not_empty,
            ),
            schema.Optional("program"): schema.And(
                models.validation.is_string,
                models.validation.not_empty,
            ),
            schema.Optional("create"): schema.Schema({
                schema.Optional("owner"): schema.And(
                    models.validation.is_string,
                    models.validation.not_empty,
                ),
                schema.Optional("group"): schema.And(
                    models.validation.is_string,
                    models.validation.not_empty,
                ),
                schema.Optional("mode"): schema.And(
                    models.validation.is_octal,
                    models.validation.length_eq(4),
                ),
                schema.Optional("auto"): schema.And(
                    models.validation.is_string,
                    models.validation.matches("^(yes|md|mdp|part|p)\d{0,2}$"),
                ),
                schema.Optional("metadata"): _validate_mdadm_metadata,
                schema.Optional("symlinks"): models.validation.equals("no"),
                schema.Optional("names"): models.validation.one_of("yes", "no"),
                schema.Optional("bbl"): models.validation.equals("no"),
            }),
            schema.Optional("homehost"): schema.And(
                models.validation.is_string,
                models.validation.not_empty,
            ),
            schema.Optional("auto"): schema.And(
                models.validation.is_list,
                models.validation.not_empty,
                schema.Schema([
                    schema.And(
                        models.validation.is_string,
                        _validate_mdadm_auto,
                    ),
                ]),
            ),
            schema.Optional("policy"): schema.Schema([{
                schema.Optional("domain"): schema.And(
                    models.validation.is_string,
                    models.validation.not_empty,
                ),
                schema.Optional("metadata"): _validate_mdadm_metadata,
                schema.Optional("path"): schema.And(
                    models.validation.is_string,
                    models.validation.not_empty,
                ),
                schema.Optional("type"): models.validation.one_of(
                    "disk",
                    "part",
                ),
                schema.Optional("action"): models.validation.one_of(
                    "include",
                    "re-add",
                    "spare",
                    "spare-same-slot",
                    "force-spare",
                ),
                schema.Optional("auto"): models.validation.one_of(
                    "yes",
                    "no",
                    "homehost",
                ),
            }]),
        }),
        # Target RAID rebuild speed while the RAID has non-rebuild-related IO
        # activity in KB/s.
        "speed_limit_min": schema.And(
            models.validation.is_int,
            models.validation.is_positive,
        ),
        # Target RAID rebuild speed while the RAID has does not have any
        # non-rebuild-related IO activity in KB/s.
        "speed_limit_max": schema.And(
            models.validation.is_int,
            models.validation.is_positive,
        ),
        # List of RAID volumes to manage on the system.
        "volumes": schema.And(
            models.validation.is_list,
            models.validation.not_empty,
            schema.Schema([{
                # Name for RAID volume.
                # This will appear as a symlink at /dev/md/<raid_name>.
                "name": schema.And(
                    models.validation.is_string,
                    models.validation.not_empty,
                ),
                # Label for RAID volume.
                # This will appear as a block device at /dev/<raid_label>
                # Labels usually look like `mdN`, where N: [0, 127)
                # `md127` is sometimes used by MDADM to indicate a
                # misconfiguration.
                "label": schema.And(
                    models.validation.is_string,
                    models.validation.not_empty,
                ),
                # RAID level for RAID volume.
                # This determines the RAID geometry, reliability, performance,
                # and data recovery strategy.
                "raid_level": models.validation.one_of(
                    # Full-device block-level striping.
                    0,
                    # Full-device mirroring.
                    1,
                    # Parity distribution with 1 parity stripe.
                    5,
                    # Parity distribution with 2 parity stripes.
                    6,
                ),
                # Block devices that compose this RAID volume.
                "devices": schema.And(
                    models.validation.is_list,
                    models.validation.not_empty,
                    schema.Schema([{
                        # Path to block device.
                        # This is usually the only partition on a storage drive:
                        # /dev/sdX1
                        "path": schema.And(
                            models.validation.is_string,
                            models.validation.not_empty,
                        ),
                    }]),
                ),
            }]),
        ),
    })


def validate(data):
    raid = make_schema().validate(data)
    if raid["speed_limit_min"] > raid["speed_limit_max"]:
        raise schema.SchemaError(
            "'speed_limit_min' cannot be greater than 'speed_limit_max'",
        )
    return raid


def from_dict(data):
    return Raid.from_dict(validate(data))


class Raid(models.model.Model):
    def __init__(self, mdadm_config, speed_limit_min, speed_limit_max, volumes):
        self.mdadm_config = mdadm_config
        self.speed_limit_min = speed_limit_min
        self.speed_limit_max = speed_limit_max
        self.volumes = volumes

    @staticmethod
    def from_dict(raid):
        return Raid(
            MdadmConfig.from_dict(raid.get("mdadm_config", {})),
            raid["speed_limit_min"],
            raid["speed_limit_max"],
            [Volume.from_dict(volume) for volume in raid["volumes"]],
        )

    @property
    def speed_limit_min_file(self):
        return "/proc/sys/dev/raid/speed_limit_min"

    @property
    def speed_limit_max_file(self):
        return "/proc/sys/dev/raid/speed_limit_max"


class MdadmConfig(models.model.Model):
    def __init__(self, device, create, homehost, mailaddr):
        self.device = device
        self.create = create
        self.homehost = homehost
        self.mailaddr = mailaddr

    @staticmethod
    def from_dict(config):
        return MdadmConfig(
            config.get("device"),
            config.get("create"),
            config.get("homehost"),
            config.get("mailaddr"),
        )


class Volume(models.model.Model):
    def __init__(self, name, label, raid_level, devices):
        self.name = name
        self.label = label
        self.raid_level = raid_level
        self.devices = devices

    @staticmethod
    def from_dict(volume):
        return Volume(
            volume["name"],
            volume["label"],
            volume["raid_level"],
            [Device.from_dict(device) for device in volume["devices"]],
        )


class Device(models.model.Model):
    def __init__(self, path):
        self.path = path

    @staticmethod
    def from_dict(device):
        return Device(device["path"])
