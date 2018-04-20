from functools import reduce
import subprocess

import lib.utility


BYTES_PER_SECTOR = 512
BYTES_PER_PAGE = 4096
SECTORS_PER_PAGE = BYTES_PER_PAGE / BYTES_PER_SECTOR


class InvalidRaidLevel(ValueError):
    pass


def _num_data_devices(media_devices, raid_level):
    """
    Determine how many of the provided media devices contribute to total data
    capacity according to the provided raid level.
    """
    if raid_level == 0:
        return len(media_devices)
    elif raid_level == 1:
        return 1
    elif raid_level == 5:
        return len(media_devices) - 1
    elif raid_level == 6:
        return len(media_devices) - 2
    else:
        raise InvalidRaidLevel(raid_level)


def device_ncq_depth(devices):
    """
    Calculate the least common NCQ depth value for all devices.
    """
    depths = []
    for device in devices:
        output = subprocess.check_output(["hdparm", "-Q", device.path])
        depth_line = [l for l in output.splitlines() if b"queue_depth" in l]
        if len(depth_line):
            depths.append(int(depth_line[0].split()[-1]))
    return int(min(depths))


def raid_chunk_size_kb(raid_level):
    """
    These were found in a benchmarking blog post:
    http://louwrentius.com/linux-raid-level-and-chunk-size-the-benchmarks.html
    """
    if raid_level == 0:
        return 512
    elif raid_level == 1:
        return None
    elif raid_level == 5:
        return 64
    elif raid_level == 6:
        return 64
    else:
        raise InvalidRaidLevel(raid_level)


def raid_readahead_sectors(media_devices):
    """
    This formula was found in a RAID tuning forum post:
    https://ubuntuforums.org/showthread.php?t=1494846
    """
    return int(sum(d.readahead_sectors for d in media_devices))


def raid_stripe_cache_pages(media_devices):
    """
    This formula was found in a RAID tuning forum post:
    https://ubuntuforums.org/showthread.php?t=1494846
    """
    sum_media_readahead_sectors = sum(
        d.readahead_sectors for d in media_devices
    )
    average_media_readahead_sectors = \
        sum_media_readahead_sectors / len(media_devices)
    return int(average_media_readahead_sectors / SECTORS_PER_PAGE)


def fs_block_size_kb(media_devices):
    block_sizes = [
        int(subprocess.check_output(["blockdev", "--getbsz", d.path]).strip())
        for d in media_devices
    ]
    return int(reduce(lib.utility.least_common_multiple, block_sizes) / 1024)


def fs_stride(media_devices, raid_level):
    """
    This formula was found in a RAID tuning forum post:
    https://ubuntuforums.org/showthread.php?p=11642898
    """
    return int(
        raid_chunk_size_kb(raid_level) / fs_block_size_kb(media_devices)
    )


def fs_stripe_width(media_devices, raid_level):
    """
    This formula was found in a RAID tuning forum post:
    https://ubuntuforums.org/showthread.php?p=11642898
    """
    num_data_devices = _num_data_devices(media_devices, raid_level)
    return int(fs_stride(media_devices, raid_level) * num_data_devices)
