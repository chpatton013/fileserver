import os

from marshmallow import Schema, fields, validate

import utility


class UnknownRaidVolume(KeyError):
    pass


class UnknownCryptVolume(KeyError):
    pass


class UnknownFsVolume(KeyError):
    pass


class DiskSchema(Schema):
    class DeviceGroupSchema(Schema):
        class DeviceCommon(object):
            # Device used to iniitialize disk devices with random data.
            randomize_source = fields.Str(
                allow_none=True,
                validate=validate.OneOf([
                    # Cryprographically secure, but very slow.
                    "/dev/random",
                    # Sufficient to obfuscate data occupancy, but slow.
                    "/dev/urandom",
                ]),
            )

            # Readahead parameter in 512-byte sectors.
            readahead_sectors = fields.Int()

            # Number of active I/O requests to pass to device before buffering.
            nr_requests = fields.Int()

        class DeviceDefaultsSchema(Schema, DeviceCommon):
            pass

        class DeviceSchema(Schema, DeviceCommon):
            # Path to block device.
            # This is usually a disk: /dev/sdX
            path = fields.Str(required=True)

        # Defaults for all disk devices in this group.
        # These values will be overridden by values defined in a device.
        defaults = fields.Nested(DeviceDefaultsSchema)

        # Name of the RAID volume this device group belongs to.
        # This is optional.
        raid_volume = fields.Str()

        # Name of the FS volume this device group belongs to.
        # This is optional.
        fs_volume = fields.Str()

        # List of disk devices that compose this group.
        devices = fields.Nested(DeviceSchema, many=True, required=True)

    # List of disk device groups to manage on the system.
    device_groups = fields.Nested(DeviceGroupSchema, many=True, required=True)


class Disk:
    class DeviceGroup:
        class Device:
            def __init__(self, **kwargs):
                self.__dict__.update(**kwargs)

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

        def __init__(self, schema):
            self.raid_volume = schema["raid_volume"]
            self.fs_volume = schema["fs_volume"]
            self.devices = [
                self.Device(**utility.merge(schema["defaults"], d))
                for d in schema["devices"]
            ]

    def __init__(self, schema):
        self.device_groups = [
            self.DeviceGroup(d)
            for d in schema["device_groups"]
        ]


class RaidSchema(Schema):
    class VolumeSchema(Schema):
        class DeviceSchema(Schema):
            # Path to block device.
            # This is usually the only partition on a disk: /dev/sdX1
            path = fields.Str(required=True)

        # Name for RAID volume.
        # This will appear as a symlink at /dev/md/<raid_name>.
        name = fields.Str(required=True)

        # Label for RAID volume.
        # This will appear as a block device at /dev/<raid_label>
        # Labels usually look like `mdN`, where N: [0, 127)
        label = fields.Str(required=True)

        # RAID level for RAID volume.
        # This determines the RAID geometry, reliability, performance, and data
        # recovery strategy.
        raid_level = fields.Int(
            required=True,
            validate=validate.OneOf([
                # Block-level striping.
                0,
                # Full-disk mirroring.
                1,
                # Parity distribution with 1 parity stripe.
                5,
                # Parity distribution with 2 parity stripes.
                6,
            ]),
        )

        # Block devices that compose this RAID volume.
        devices = fields.Nested(DeviceSchema, many=True, required=True)

    class MdadmConfigSchema(Schema):
        device = fields.Str(required=True)
        create = fields.Str(required=True)
        homehost = fields.Str(required=True)
        mailaddr = fields.Str(required=True)

    mdadm_config = fields.Nested(MdadmConfigSchema, required=True)
    speed_limit_min = fields.Int(required=True)
    speed_limit_max = fields.Int(required=True)

    # List of RAID volumes to manage on the system.
    volumes = fields.Nested(VolumeSchema, many=True, required=True)


class Raid:
    class Volume:
        class Device:
            def __init__(self, **kwargs):
                self.__dict__.update(**kwargs)

        def __init__(self, schema):
            self.name = schema["name"]
            self.label = schema["label"]
            self.raid_level = schema["raid_level"]
            self.devices = [
                self.Device(**d)
                for d in schema["devices"]
            ]

        @property
        def name_path(self):
            return os.path.join("/dev", "md", self.name)

        @property
        def label_path(self):
            return os.path.join("/dev", self.label)

        @property
        def stripe_cache_size_file(self):
            return "/sys/block/{}/md/stripe_cache_size".format(self.label)

    class MdadmConfig:
        def __init__(self, **kwargs):
            self.__dict__.update(**kwargs)

    def __init__(self, schema):
        self.mdadm_config = self.MdadmConfig(**schema["mdadm_config"])
        self.speed_limit_min = schema["speed_limit_min"]
        self.speed_limit_max = schema["speed_limit_max"]
        self.volumes = [
            self.Volume(v)
            for v in schema["volumes"]
        ]

    @property
    def speed_limit_min_file(self):
        return "/proc/sys/dev/raid/speed_limit_min"

    @property
    def speed_limit_max_file(self):
        return "/proc/sys/dev/raid/speed_limit_max"


class CryptSchema(Schema):
    class VolumeCommon(object):
        # Encryption cipher.
        # Choices are limited to what cryptsetup supports.
        cipher = fields.Str()

        # Size of encryption key. Must be a multiple of 8.
        # Actual size options are determined by chosen cipher.
        # 256 or 512 are commonly good options.
        key_size = fields.Int()

        # Encryption hashing algorithm.
        # Must provide at least 160 bytes of output.
        # Choices are limited to what cryptsetup supports.
        hash_algorithm = fields.Str()

        # The number of milliseconds to spend password processing.
        # 0 selects the default compiled into cryptsetup.
        iter_time = fields.Int()

    class VolumeDefaultsSchema(Schema, VolumeCommon):
        pass

    class VolumeSchema(Schema, VolumeCommon):
        # Path to encrypted block device.
        encrypted_path = fields.Str(required=True)

        # Name for decrypted volume.
        # This will appear as a symlink at /dev/mapper/<crypt_name>.
        decrypted_name = fields.Str(required=True)

    # Defaults for all crypt volumes.
    # These values will be overridden by values defined in a volume.
    defaults = fields.Nested(VolumeDefaultsSchema)

    # List of crypt volumes to manage on the system.
    volumes = fields.Nested(VolumeSchema, many=True)


class Crypt:
    class Volume:
        def __init__(self, **kwargs):
            self.__dict__.update(**kwargs)

    def __init__(self, schema):
        self.volumes = [
            self.Volume(**utility.merge(schema["defaults"], v))
            for v in schema["volumes"]
        ]


class FsSchema(Schema):
    class VolumeSchema(Schema):
        # Name of FS volume.
        # This is referenced by disk devices.
        name = fields.Str(required=True)

        # Type of filesystem to use on volume.
        fs_type = fields.Str(
            required=True,
            validate=validate.OneOf([
                "ext2",
                "ext3",
                "ext4",
            ]),
        )

        # Path to block device.
        device_path = fields.Str(required=True)

        # Location to mount filesystem.
        mount_location = fields.Str(required=True)

    # List of FS volumes to manage on the system.
    volumes = fields.Nested(VolumeSchema, many=True)


class Fs:
    class Volume:
        def __init__(self, **kwargs):
            self.__dict__.update(**kwargs)

    def __init__(self, schema):
        self.volumes = [
            self.Volume(**v)
            for v in schema["volumes"]
        ]


class BindSchema(Schema):
    class VolumeSchema(Schema):
        # Path to source directory.
        source = fields.Str(required=True)

        # Path to target directory.
        target = fields.Str(required=True)

    # List of read-only bind mount volumes to manage on the system.
    read_only = fields.Nested(VolumeSchema, many=True)

    # List of read-write bind mount volumes to manage on the system.
    read_write = fields.Nested(VolumeSchema, many=True)


class Bind:
    class Volume:
        def __init__(self, **kwargs):
            self.__dict__.update(**kwargs)

    def __init__(self, schema):
        self.read_only = [
            self.Volume(**v)
            for v in schema["read_only"]
        ]
        self.read_write = [
            self.Volume(**v)
            for v in schema["read_write"]
        ]


class ExportSchema(Schema):
    class HostGroupSchema(Schema):
        # Name of this group of hosts.
        name = fields.Str(required=True)

        # List of host addresses (IPs, CIDRs, domains, etc).
        # Wildcards (*) can be used for IP blocks or subdomain components.
        hosts = fields.List(fields.Str(), required=True)

    class OptionsSchema(Schema):
        # Name for this option description.
        name = fields.Str(required=True)

        # Comma-delimited set of export options.
        value = fields.Str(required=True)

    class VolumeSchema(Schema):
        class HostGroupOptionsSchema(Schema):
            # Name of host group.
            host_group = fields.Str(required=True)

            # Name of option set.
            option = fields.Str(required=True)

        # Filesystem path to export.
        path = fields.Str(required=True)

        # List of host-group, option pairings to apply to this volume.
        host_group_options = fields.Nested(HostGroupOptionsSchema, many=True)

    # List of named host groups to reference in volumes.
    host_groups = fields.Nested(HostGroupSchema, many=True)

    # List of named option sets to reference in volumes.
    options = fields.Nested(OptionsSchema, many=True)

    # List of export volumes to manage on the system.
    volumes = fields.Nested(VolumeSchema, many=True)


class Export:
    class HostGroup:
        def __init__(self, **kwargs):
            self.__dict__.update(**kwargs)

    class Options:
        def __init__(self, **kwargs):
            self.__dict__.update(**kwargs)

    class Volume:
        class HostGroupOptions:
            def __init__(self, **kwargs):
                self.__dict__.update(**kwargs)

        def __init__(self, schema):
            self.path = schema["path"]
            self.host_group_options = [
                self.HostGroupOptions(**h)
                for h in schema["host_group_options"]
            ]

    def __init__(self, schema):
        self.host_groups = [
            self.HostGroup(**h)
            for h in schema["host_groups"]
        ]
        self.options = [
            self.Options(**o)
            for o in schema["options"]
        ]
        self.volumes = [
            self.Volume(v)
            for v in schema["volumes"]
        ]


class ConfigurationSchema(Schema):
    class Meta:
        # Preserve order when dumping to YAML. This recursively applies to all
        # nested schema.
        ordered = True
        strict = True

    disk = fields.Nested(DiskSchema)
    raid = fields.Nested(RaidSchema)
    crypt = fields.Nested(CryptSchema)
    fs = fields.Nested(FsSchema)
    bind = fields.Nested(BindSchema)
    export = fields.Nested(ExportSchema)


class Configuration:
    def __init__(self, schema):
        self.disk = Disk(schema["disk"])
        self.raid = Raid(schema["raid"])
        self.crypt = Crypt(schema["crypt"])
        self.fs = Fs(schema["fs"])
        self.bind = Bind(schema["bind"])
        self.export = Export(schema["export"])

    def find_raid_volume(self, raid_volume_name):
        for v in self.raid.volumes:
            if v.name == raid_volume_name:
                return v
        raise UnknownRaidVolume(raid_volume_name)

    def find_crypt_volume(self, crypt_volume_name):
        for v in self.crypt.volumes:
            if v.decrypted_name == crypt_volume_name:
                return v
        raise UnknownCryptVolume(crypt_volume_name)

    def find_fs_volume(self, fs_volume_name):
        for v in self.fs.volumes:
            if v.name == fs_volume_name:
                return v
        raise UnknownFsVolume(fs_volume_name)

    def find_disk_device_group_with_raid_volume(self, raid_volume_name):
        for dg in self.disk.device_groups:
            if dg.raid_volume == raid_volume_name:
                return dg
        raise UnknownRaidVolume(raid_volume_name)

    def find_disk_device_group_with_fs_volume(self, fs_volume_name):
        for dg in self.disk.device_groups:
            if dg.fs_volume == fs_volume_name:
                return dg
        raise UnknownFsVolume(fs_volume_name)

    def find_disk_devices_with_raid_volume(self, raid_volume_name):
        device_groups = [
            dg
            for dg in self.disk.device_groups
            if dg.raid_volume == raid_volume_name
        ]
        return sum((dg.devices for dg in device_groups), [])

    def find_disk_devices_with_fs_volume(self, fs_volume_name):
        device_groups = [
            dg
            for dg in self.disk.device_groups
            if dg.fs_volume == fs_volume_name
        ]
        return sum((dg.devices for dg in device_groups), [])
