import collections
import os

import schema

import lib.utility
import models.model
import models.validation


def make_schema():
    device_common_schema = {
        # Device used to initialize media devices with random data.
        # TODO: add `shred` and `openssl` options:
        #   https://serverfault.com/a/415962
        # TODO: add write speed stats:
        #   /dev/random: unknown
        #   /dev/urandom: ~10MB/s
        #   openssl: ~300MB/s
        #   shred: unknown
        schema.Optional("randomize_method"): models.validation.one_of(
            # Cryprographically secure, but very slow.
            "/dev/random",
            # Sufficient to obfuscate data occupancy, but slow.
            "/dev/urandom",
        ),
        # Readahead parameter in 512-byte sectors.
        schema.Optional("readahead_sectors"): schema.And(
            models.validation.is_int,
            models.validation.is_positive,
        ),
        # Number of active I/O requests to pass to device before buffering.
        schema.Optional("nr_requests"): schema.And(
            models.validation.is_int,
            models.validation.is_positive,
        ),
    }

    device_specific_schema = {
        # Path to block device.
        # This is usually a storage drive: /dev/sdX
        "path": schema.And(
            models.validation.is_string,
            models.validation.not_empty,
        ),
    }

    return schema.Schema({
        # Defaults for all media devices.
        # These values will be overridden by values defined in a device group.
        schema.Optional("device_defaults"): schema.Schema(
            device_common_schema,
        ),
        # List of media device groups to manage on the system.
        "device_groups": schema.And(
            models.validation.is_list,
            models.validation.not_empty,
            schema.Schema([{
                # Name of the RAID volume this device group belongs to.
                # This is optional.
                schema.Optional("raid_volume"): schema.And(
                    models.validation.is_string,
                    models.validation.not_empty,
                ),
                # Name of the mount volume this device group belongs to.
                # This is optional.
                schema.Optional("mount_volume"): schema.And(
                    models.validation.is_string,
                    models.validation.not_empty,
                ),
                # Defaults for all media devices in this group.
                # These values will be overridden by values defined in a device.
                schema.Optional("device_defaults"): schema.Schema(
                    device_common_schema,
                ),
                # List of media devices that compose this group.
                "devices": schema.And(
                    models.validation.is_list,
                    models.validation.not_empty,
                    schema.Schema([{
                        **device_common_schema,
                        **device_specific_schema,
                    }]),
                ),
            }]),
        ),
    })


def validate(data):
    media = make_schema().validate(data)
    for device_group in media["device_groups"]:
        for device in device_group["devices"]:
            data = lib.utility.merge(
                media.get("device_defaults", {}),
                device_group.get("device_defaults", {}),
                device,
            )
            models.validation.validate_missing_keys(data, (
                "randomize_method",
                "readahead_sectors",
                "nr_requests",
                "path",
            ))
    return media


def from_dict(data):
    return Media.from_dict(validate(data))


class Media(models.model.Model):
    def __init__(self, device_defaults, device_groups=[]):
        self.device_defaults = device_defaults
        self.device_groups = device_groups

    def to_dict(self):
        data = collections.OrderedDict()
        if self.device_defaults:
            data["device_defaults"] = device_defaults
        data["device_groups"] = [dg.to_dict() for dg in self.device_groups]
        return data

    @staticmethod
    def from_dict(data):
        media = Media(data.get("device_defaults", {}))
        media.device_groups = [
            DeviceGroup.from_dict(device_group, media)
            for device_group in data["device_groups"]
        ]
        return media


class DeviceGroup(models.model.Model):
    def __init__(self, device_defaults, raid_volume, mount_volume, devices=[]):
        self.device_defaults = device_defaults
        self.raid_volume = raid_volume
        self.mount_volume = mount_volume
        self.devices = devices

    def to_dict(self):
        data = collections.OrderedDict()
        if self.device_defaults:
            data["device_defaults"] = device_defaults
        if self.raid_volume:
            data["raid_volume"] = self.raid_volume
        if self.mount_volume:
            data["mount_volume"] = self.mount_volume
        data["devices"] = [d.to_dict() for d in self.devices]
        return data

    @staticmethod
    def from_dict(data, media):
        device_group = DeviceGroup(
            data.get("device_defaults", {}),
            data.get("raid_volume"),
            data.get("mount_volume"),
        )
        device_group.devices = [
            Device.from_dict(device, device_group, media)
            for device in data["devices"]
        ]
        return device_group


class Device(models.model.Model):
    def __init__(
        self,
        media,
        device_group,
        randomize_method,
        readahead_sectors,
        nr_requests,
        path,
    ):
        self._media = media
        self._device_group = device_group
        self._randomize_method = randomize_method
        self._readahead_sectors = readahead_sectors
        self._nr_requests = nr_requests
        self.path = path

    def __default_value(self, device_attr, device_group_attr, media_attr):
        return self.__dict__.get(
            device_attr,
            self._device_group.device_defaults.get(
                device_group_attr,
                self._media.device_defaults.get(media_attr),
            ),
        )

    def to_dict(self):
        data = collections.OrderedDict()
        if self._randomize_method:
            data["randomize_method"] = self._randomize_method
        if self._readahead_sectors:
            data["readahead_sectors"] = self._readahead_sectors
        if self._nr_requests:
            data["nr_requests"] = self._nr_requests
        data["path"] = self.path
        return data

    @staticmethod
    def from_dict(data, device_group, media):
        return Device(
            media,
            device_group,
            data.get("randomize_method"),
            data.get("readahead_sectors"),
            data.get("nr_requests"),
            data["path"],
        )

    @property
    def randomize_method(self):
        return self.__default_value(
            "_randomize_method",
            "randomize_method",
            "randomize_method",
        )

    @property
    def readahead_sectors(self):
        return self.__default_value(
            "_readahead_sectors",
            "readahead_sectors",
            "readahead_sectors",
        )

    @property
    def nr_requests(self):
        return self.__default_value(
            "_nr_requests",
            "nr_requests",
            "nr_requests",
        )

    @property
    def basename(self):
        return os.path.basename(self.path)

    @property
    def max_sectors_kb_file(self):
        return "/sys/block/{}/queue/max_sectors_kb".format(self.basename)

    @property
    def nr_requests_file(self):
        return "/sys/block/{}/queue/nr_requests".format(self.basename)

    @property
    def queue_depth_file(self):
        return "/sys/block/{}/device/queue_depth".format(self.basename)
