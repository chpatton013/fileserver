import collections

import yaml

import schema
import utility


def _represent_ordereddict(dumper, data):
    value = [
        (
            dumper.represent_data(item_key),
            dumper.represent_data(item_value),
        )
        for item_key, item_value in data.items()
    ]

    return yaml.nodes.MappingNode(u'tag:yaml.org,2002:map', value)


yaml.add_representer(collections.OrderedDict, _represent_ordereddict)


class UnknownRaidVolume(KeyError):
    pass


class UnknownCryptVolume(KeyError):
    pass


class UnknownFsVolume(KeyError):
    pass


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

        @property
        def active(self):
            pass # TODO

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


class Crypt:
    class Volume:
        def __init__(self, **kwargs):
            self.__dict__.update(**kwargs)

        @property
        def active(self):
            pass # TODO

    def __init__(self, schema):
        self.volumes = [
            self.Volume(**utility.merge(schema["defaults"], v))
            for v in schema["volumes"]
        ]


class Fs:
    class Volume:
        def __init__(self, **kwargs):
            self.__dict__.update(**kwargs)

        @property
        def active(self):
            pass # TODO

    def __init__(self, schema):
        self.volumes = [
            self.Volume(**v)
            for v in schema["volumes"]
        ]


class Bind:
    class Volume:
        def __init__(self, **kwargs):
            self.__dict__.update(**kwargs)

        @property
        def active(self):
            pass # TODO

    def __init__(self, schema):
        self.read_only = [
            self.Volume(**v)
            for v in schema["read_only"]
        ]
        self.read_write = [
            self.Volume(**v)
            for v in schema["read_write"]
        ]


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


def make_raw(config_file):
    return schema.ConfigurationSchema().load(
        yaml.load(open(config_file, "r").read()),
    )


def make_many_raw(config_files):
    return [make_raw(f) for f in config_files]


def make(config_file):
    return Configuration(make_raw(config_file))
