#!/usr/bin/env python2

"""
Manage a RAID volume with the following subcommands:

create: Create an encrypted RAID volume from the given block devices.
tune: Apply optimization settings to increase RAID performance.
start: Start the encrypted RAID volume.
stop: Stop the encrypted RAID volume.

Use `<subcommand> --help` for detailed usage instructions for each subcommand.

Use `--dryrun` to run the script without actually executing any destructive
commands.
Use `--verbose` to print commands as they are run.
"""

from __future__ import print_function
import argparse
import datetime
import os
import subprocess
import time

class DryrunPopen():
    def __init__(self, command):
        self.command = command
        self.returncode = 0
    def poll(self): pass
    def wait(self): pass

RANDOM_SOURCE_RANDOM = "/dev/random"
RANDOM_SOURCE_URANDOM = "/dev/urandom"
ALLOWED_RANDOM_SOURCES = [
    RANDOM_SOURCE_RANDOM,
    RANDOM_SOURCE_URANDOM,
]

OUTPUT_INFO = "INFO"
OUTPUT_WRITE = "WRITE"
OUTPUT_RUN = "RUN"
OUTPUT_SPAWN = "SPAWN"
OUTPUT_NAMES = [
    OUTPUT_INFO,
    OUTPUT_WRITE,
    OUTPUT_RUN,
    OUTPUT_SPAWN,
]

BYTES_PER_SECTOR = 512
BYTES_PER_PAGE = 4096
SECTORS_PER_PAGE = BYTES_PER_PAGE / BYTES_PER_SECTOR

RAID_LEVEL_0 = "0"
RAID_LEVEL_1 = "1"
RAID_LEVEL_5 = "5"
RAID_LEVEL_6 = "6"
ALLOWED_RAID_LEVELS = [
    RAID_LEVEL_0,
    RAID_LEVEL_1,
    RAID_LEVEL_5,
    RAID_LEVEL_6,
]

RAID_SYNC_ACTION_IDLE = "idle"
RAID_SYNC_ACTION_RESYNC = "resync"

DEFAULT_MDADM_CONF_FILE = "/etc/mdadm/mdadm.conf"
DEFAULT_MDADM_CONF_CREATE = "CREATE owner=root group=disk mode=0660 auto=yes"
DEFAULT_MDADM_CONF_DEVICE = "partitions"
DEFAULT_MDADM_CONF_HOMEHOST = "<system>"
DEFAULT_MDADM_CONF_MAILADDR = "root"

CRYPT_KEY_SIZE_256 = "256"
CRYPT_KEY_SIZE_512 = "512"
ALLOWED_CRYPT_KEY_SIZES = [
    CRYPT_KEY_SIZE_256,
    CRYPT_KEY_SIZE_512,
]

CRYPT_HASH_ALGORITHM_SHA_1 = "sha1"
CRYPT_HASH_ALGORITHM_SHA_256 = "sha256"
CRYPT_HASH_ALGORITHM_SHA_512 = "sha512"
ALLOWED_CRYPT_HASH_ALGORITHMS = [
    CRYPT_HASH_ALGORITHM_SHA_1,
    CRYPT_HASH_ALGORITHM_SHA_256,
    CRYPT_HASH_ALGORITHM_SHA_512,
]

FS_TYPE_EXT2 = "ext2"
FS_TYPE_EXT3 = "ext3"
FS_TYPE_EXT4 = "ext4"
ALLOWED_FS_TYPES = [
    FS_TYPE_EXT2,
    FS_TYPE_EXT3,
    FS_TYPE_EXT4,
]

DEFAULT_BLOCK_SIZE = 4
DEFAULT_DRIVE_READAHEAD = 256
DEFAULT_DRIVE_NR_REQUESTS = 128
DEFAULT_RAID_SPEED_LIMIT_MIN = 1000
DEFAULT_RAID_SPEED_LIMIT_MAX = 200000
DEFAULT_CRYPT_ITER_TIME = 5000

MIN_NR_REQUESTS = 1
MAX_NR_REQUESTS = 32

def check_positive_int(value):
    ivalue = int(value)
    if ivalue < 1:
        raise argparse.ArgumentTypeError("%s is not a positive integer" % value)
    return ivalue

def check_drive_nr_requests(value):
    ivalue = int(value)
    if ivalue < MIN_NR_REQUESTS or ivalue > MAX_NR_REQUESTS:
        raise argparse.ArgumentTypeError(
            "drive_nr_requests must be between %d and %d" % \
            (MIN_NR_REQUESTS, MAX_NR_REQUESTS))
    return ivalue

def check_crypt_iter_time(value):
    ivalue = int(value)
    if ivalue < 0:
        raise argparse.ArgumentTypeError("crypt_iter_time must not be negative")
    return ivalue

post_parse_args = []
rc_commands = []

def arg_default(args, name, function):
    if hasattr(args, name) and not getattr(args, name):
        setattr(args, name, function(args))

def arg_check(args, should_check, check, message):
    if should_check(args) and not check(args):
        raise argparse.ArgumentTypeError(message)

def add_post_parse_default(name, function):
    post_parse_args.append(lambda args: arg_default(args, name, function))

def add_post_parse_check(should_check, check, message):
    post_parse_args.append(
        lambda args: arg_check(args, should_check, check, message))

def block_size_arg(parser):
    parser.add_argument("--block_size",
                        type=check_positive_int,
                        default=DEFAULT_BLOCK_SIZE,
                        help="Device block size in KB")

def raid_level_arg(parser):
    parser.add_argument("--raid_level",
                        choices=ALLOWED_RAID_LEVELS,
                        required=True,
                        help="RAID level")

def raid_chunk_size_arg(parser):
    parser.add_argument("--raid_chunk_size",
                        type=check_positive_int,
                        required=False,
                        help="RAID chunk size in KB")
    add_post_parse_default("raid_chunk_size", optimal_raid_chunk_size_kb)

def md_label_arg(parser):
    parser.add_argument("--md_label",
                        required=True,
                        help="Label for MD device")

def crypt_name_arg(parser):
    parser.add_argument("--crypt_name",
                        required=True,
                        help="Name for crypt device")

def devices_arg(parser):
    parser.add_argument("--devices",
                        nargs="+",
                        required=True,
                        help="List of block devices to use in RAID")

def create_args(parser):
    block_size_arg(parser)
    raid_level_arg(parser)
    raid_chunk_size_arg(parser)
    md_label_arg(parser)
    crypt_name_arg(parser)
    devices_arg(parser)

    parser.add_argument("--randomize",
                        choices=ALLOWED_RANDOM_SOURCES,
                        default=None,
                        help="Random source to initialize drives")

    parser.add_argument("--mdadm_conf_file",
                        default=DEFAULT_MDADM_CONF_FILE,
                        help="MDADM config file location")
    parser.add_argument("--mdadm_conf_create",
                        default=DEFAULT_MDADM_CONF_CREATE,
                        help="Create arguments for MDADM config")
    parser.add_argument("--mdadm_conf_device",
                        default=DEFAULT_MDADM_CONF_DEVICE,
                        help="Device for MDADM config")
    parser.add_argument("--mdadm_conf_homehost",
                        default=DEFAULT_MDADM_CONF_HOMEHOST,
                        help="Host for MDADM config")
    parser.add_argument("--mdadm_conf_mailaddr",
                        default=DEFAULT_MDADM_CONF_MAILADDR,
                        help="Mailaddr for MDADM config")

    parser.add_argument("--crypt_key_size",
                        choices=ALLOWED_CRYPT_KEY_SIZES,
                        default=CRYPT_KEY_SIZE_512,
                        help="Crypt device key size")
    parser.add_argument("--crypt_hash_algorithm",
                        choices=ALLOWED_CRYPT_HASH_ALGORITHMS,
                        default=CRYPT_HASH_ALGORITHM_SHA_512,
                        help="Crypt device hash algorithm")
    parser.add_argument("--crypt_iter_time",
                        type=check_crypt_iter_time,
                        default=DEFAULT_CRYPT_ITER_TIME,
                        help="Crypt device iteration time")

    parser.add_argument("--fs_type",
                        choices=ALLOWED_FS_TYPES,
                        default=FS_TYPE_EXT4,
                        help="Type of filesystem to create")

def tune_args(parser):
    block_size_arg(parser)
    raid_level_arg(parser)
    raid_chunk_size_arg(parser)
    md_label_arg(parser)
    crypt_name_arg(parser)
    devices_arg(parser)

    # Drive optimization arguments.
    parser.add_argument("--drive_readahead",
                        type=check_positive_int,
                        default=DEFAULT_DRIVE_READAHEAD,
                        help="Readahead value for each drive in 512B sectors")

    parser.add_argument("--drive_nr_requests",
                        type=check_positive_int,
                        default=DEFAULT_DRIVE_NR_REQUESTS,
                        help="Maximum I/O request queue size. "\
                             "Must be between %d and %d" % \
                             (MIN_NR_REQUESTS, MAX_NR_REQUESTS))

    parser.add_argument("--drive_ncq_depth",
                        type=check_drive_nr_requests,
                        required=False,
                        help="NCQ drive depth")
    add_post_parse_default("drive_ncq_depth", optimal_drive_ncq_depth)

    # RAID optimization arguments.
    parser.add_argument("--raid_readahead",
                        type=check_positive_int,
                        required=False,
                        help="Readahead value for RAID device in 512B sectors")
    add_post_parse_default("raid_readahead", optimal_raid_readahead)

    parser.add_argument("--raid_stripe_cache",
                        type=check_positive_int,
                        required=False,
                        help="Stripe cache for RAID device in 4096B pages")
    add_post_parse_default("raid_stripe_cache", optimal_raid_stripe_cache)

    parser.add_argument("--raid_speed_limit_min",
                        type=check_positive_int,
                        default=DEFAULT_RAID_SPEED_LIMIT_MIN,
                        help="Minimum RAID device speed limit")
    parser.add_argument("--raid_speed_limit_max",
                        type=check_positive_int,
                        default=DEFAULT_RAID_SPEED_LIMIT_MAX,
                        help="Maximum RAID device speed limit")
    add_post_parse_check(
        lambda args: hasattr(args, "raid_speed_limit_min") and \
                     hasattr(args, "raid_speed_limit_max"),
        lambda args: args.raid_speed_limit_min <= args.raid_speed_limit_max,
        "Minimum speed limit must not be less than maximum speed limit")

    # Filesystem optimization arguments.
    parser.add_argument("--fs_stride",
                        type=check_positive_int,
                        required=False,
                        help="Filesystem stride in blocks")
    add_post_parse_default("fs_stride", optimal_fs_stride)

    parser.add_argument("--fs_stripe_width",
                        type=check_positive_int,
                        required=False,
                        help="Filesystem stripe width in blocks")
    add_post_parse_default("fs_stripe_width", optimal_fs_stripe_width)

def start_args(parser):
    md_label_arg(parser)
    crypt_name_arg(parser)

def stop_args(parser):
    md_label_arg(parser)
    crypt_name_arg(parser)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Manage an encrypted RAID volume")

    subparsers = parser.add_subparsers(help="Invoke one of the sub-commands")

    create_parser = subparsers.add_parser(
        "create",
        help="Create an encrypted RAID volume from the given block devices")
    create_args(create_parser)
    create_parser.set_defaults(func=create)

    tune_parser = subparsers.add_parser(
        "tune",
        help="Apply optimization settings to increase RAID performance")
    tune_args(tune_parser)
    tune_parser.set_defaults(func=tune)

    start_parser = subparsers.add_parser("start",
                                         help="Start the encrypted RAID volume")
    start_args(start_parser)
    start_parser.set_defaults(func=start)

    stop_parser = subparsers.add_parser("stop",
                                        help="Stop the encrypted RAID volume")
    stop_args(stop_parser)
    stop_parser.set_defaults(func=stop)

    parser.add_argument("--verbose",
                        dest="verbose",
                        action="store_true",
                        help="Print commands as they are being run")
    parser.add_argument("--dryrun",
                        dest="dryrun",
                        action="store_true",
                        help="Do not run any destructive commands")

    args = parser.parse_args()

    for fn in post_parse_args:
        fn(args)

    return args

def output(args, name, indent, message):
    dryrun_prefix = "DRYRUN " if args.dryrun else ""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    name_centered = name.center(max([len(n) for n in OUTPUT_NAMES]))
    message_indent = " " * indent
    print("%s[%s|%s] %s%s" % (
        dryrun_prefix,
        now,
        name_centered,
        message_indent,
        message,
    ))

def info(args, message):
    output(args, OUTPUT_INFO, 0, message)

def write(args, filepath, content):
    if args.verbose:
        output(args, OUTPUT_WRITE, 2, filepath)
        for line in content.split("\n"):
            print("  %s" % line)

    if not args.dryrun:
        with open(filepath, "w") as filehandle:
            print(content, file=filehandle)

def run(args, command, **kwargs):
    if args.verbose:
        output(args, OUTPUT_RUN, 2, " ".join(map(str, command)))

    if not args.dryrun:
        subprocess.check_call(command)

def spawn(args, command):
    if args.verbose:
        output(args, OUTPUT_SPAWN, 2, " ".join(map(str, command)))

    if args.dryrun:
        return DryrunPopen(command)
    else:
        return subprocess.Popen(command)

def device_partitions(args):
    return ["%s1" % device for device in args.devices]

def md_device_label(args):
    return "/dev/%s" % args.md_label

def crypt_device(args):
    return "/dev/mapper/%s" % args.crypt_name

def num_drives(args):
    """
    Break up the collection of drives into data drives and redundancy drives.
    """
    num_total_drives = len(args.devices)
    if args.raid_level == RAID_LEVEL_0:
        return (num_total_drives, 0)
    elif args.raid_level == RAID_LEVEL_1:
        return (1, num_total_drives - 1)
    elif args.raid_level == RAID_LEVEL_5:
        return (num_total_drives - 1, 1)
    elif args.raid_level == RAID_LEVEL_6:
        return (num_total_drives - 2, 2)
    else:
        return None

def optimal_drive_ncq_depth(args):
    """
    Calculate the highest common NCQ depth value for all devices.
    """
    depths = []
    for device in args.devices:
        output = subprocess.check_output(["hdparm", "-Q", device])
        depth_line = filter(lambda l: "queue_depth" in l, output.split("\n"))
        if len(depth_line):
            depths.append(int(depth_line[0].split()[-1]))
    return min(depths)

def optimal_raid_chunk_size_kb(args):
    """
    These optimal chunk sizes were found in a benchmarking blog post:
    http://louwrentius.com/linux-raid-level-and-chunk-size-the-benchmarks.html
    """
    if args.raid_level == RAID_LEVEL_0: return 512
    elif args.raid_level == RAID_LEVEL_1: return None
    elif args.raid_level == RAID_LEVEL_5: return 64
    elif args.raid_level == RAID_LEVEL_6: return 64
    else: return None

def optimal_raid_readahead(args):
    """
    This optimized readahead formula was found in a RAID tuning forum post:
    https://ubuntuforums.org/showthread.php?t=1494846
    """
    return args.drive_readahead * len(args.devices)

def optimal_raid_stripe_cache(args):
    """
    This optimized stripe cache formula was found in a RAID tuning forum post:
    https://ubuntuforums.org/showthread.php?t=1494846
    """
    return args.drive_readahead / SECTORS_PER_PAGE

def optimal_fs_stride(args):
    """
    This optimized fs stride formula was found in a RAID tuning forum post:
    https://ubuntuforums.org/showthread.php?p=11642898
    """
    return args.raid_chunk_size / args.block_size

def optimal_fs_stripe_width(args):
    """
    This optimized fs stripe width formula was found in a RAID tuning forum post:
    https://ubuntuforums.org/showthread.php?p=11642898
    """
    num_data_drives, _ = num_drives(args)
    return args.fs_stride * num_data_drives

def create(args):
    # Prepare devices for encrypted RAID.
    randomize_drives(args)
    partition_drives(args)
    # Create a RAID volume on the prepared devices.
    create_raid(args)
    configure_raid(args)
    # Add an encrypted volume on top of the RAID volume.
    create_crypt(args)
    start_crypt(args)
    # Add a filesystem to the encrypted volume.
    create_fs(args)

def tune(args):
    # Optimize each drive individually.
    tune_drives(args)
    # Optimize RAID volume.
    start_raid(args)
    tune_raid(args)
    # Optimize filesystem.
    start_crypt(args)
    tune_fs(args)
    # Persist optimization settings in /etc/rc.local.
    tune_persistent(args)

def start(args):
    start_raid(args)
    start_crypt(args)

def stop(args):
    stop_crypt(args)
    stop_raid(args)

def randomize_drives(args):
    if args.randomize is None:
        return

    info(args, "Randomizing devices in parallel")

    get_sectors = lambda d: subprocess.check_output(["blockdev", "--getsz", d])
    processes = [
        spawn(args, [
            "dd",
            "if=%s" % args.randomize,
            "of=%s" % d,
            "bs=512", # Sector size
            "count=%d" % int(count),
        ])
        for d, count in [(d, get_sectors(d)) for d in args.devices]
    ]

    while len(processes) > 0:
        time.sleep(0.1)
        for p in processes:
            p.poll()
        processes = [p for p in processes if p.returncode is None]

def partition_drives(args):
    def wait_for_partitions(present):
        if args.dryrun:
            return
        for partition in device_partitions(args):
            part_base = os.path.basename(partition)
            part_dir = os.path.dirname(partition)
            while (part_base in os.listdir(part_dir)) == present:
                time.sleep(0.1)

    info(args, "Partitioning devices")

    parted_command_prefix = ["parted", "--script", "--align", "optimal"]

    for device in args.devices:
        run(args, parted_command_prefix + [device, "mklabel", "gpt"])
    # Wait for partitions to be removed.
    wait_for_partitions(True)

    for device in args.devices:
        run(args,
            parted_command_prefix + [device, "mkpart", "primary", "0%", "100%"])
    # Wait for new partitions to be visisble.
    wait_for_partitions(False)

def create_raid(args):
    info(args, "Creating new RAID volume")

    run(args, ["mdadm", "--zero-superblock"] + device_partitions(args))

    command = [
        "mdadm",
        "--create",
        "--verbose",
        md_device_label(args),
        "--level=%s" % args.raid_level,
    ]
    if args.raid_chunk_size:
        command += ["--chunk=%d" % args.raid_chunk_size]
    command += ["--raid-devices=%d" % len(args.devices)]
    command += device_partitions(args)

    run(args, command)

    md_sys_directory = os.path.join("/sys/class/block", args.md_label, "md")

    sync_action_file_path = os.path.join(md_sys_directory, "sync_action")
    def _sync_action():
        with open(sync_action_file_path, "r") as sync_action_file:
            return sync_action_file.read().strip()

    sync_completed_file_path = os.path.join(md_sys_directory, "sync_completed")
    def _sync_completed():
        with open(sync_completed_file_path, "r") as completed_file:
            completed = completed_file.read().split("/")
            current = int(completed[0].strip())
            total = int(completed[1].strip())
            return int((current * 100 / total) / 10) * 10

    last_sync_completed = None
    def _print_sync_status():
        current_sync_completed = _sync_completed()
        if last_sync_completed is None:
            info(args, "RAID resync in progress")
        elif last_sync_completed < current_sync_completed:
            info(args, "RAID resync %d%% complete" % current_sync_progress)
        last_sync_completed = current_sync_completed

    while True:
        sync_action = _sync_action(sync_action_file_path)
        if sync_action == RAID_SYNC_ACTION_RESYNC:
            _print_sync_status()
        elif sync_action == RAID_SYNC_ACTION_IDLE:
            info(args, "RAID resync complete")
            break
        else:
            info(args, "Unknown sync action '%s'. Exiting." % sync_action)
            quit(1)
        time.sleep(5)

def configure_raid(args):
    info(args, "Configuring MDADM")

    mdadm_conf_file_content = "\n".join([
        "DEVICE %s" % args.mdadm_conf_device,
        "CREATE %s" % args.mdadm_conf_create,
        "HOMEHOST %s" % args.mdadm_conf_homehost,
        "MAILADDR %s" % args.mdadm_conf_mailaddr,
        subprocess.check_output(["mdadm", "--detail", "--scan"]),
    ])

    write(args, args.mdadm_conf_file, mdadm_conf_file_content)

def create_crypt(args):
    # The cipher is not customizable because none of the alternatives are
    # anywhere near as secure.
    run(args, [
        "cryptsetup",
        "--cipher=aes-xts-plain64",
        "--key-size=%s" % args.crypt_key_size,
        "--hash=%s" % args.crypt_hash_algorithm,
        "--iter-time=%d" % args.crypt_iter_time,
        "--use-random",
        "luksFormat",
        md_device_label(args),
    ])

def create_fs(args):
    run(args, [
        "mke2fs",
        "-t", args.fs_type,
        "-b", str(args.block_size * 1024),
        crypt_device(args),
    ])

def tune_drives(args):
    # Align to RAID chunk size instead of default value of 1280.
    max_sectors_kb = args.raid_chunk_size
    for device in args.devices:
        drive = device.lstrip("/dev/")

        rc_commands.append("# Tune drive %s" % device)

        run(args, [
            "blockdev",
            "--setra",
            str(args.drive_readahead),
            device,
        ])
        rc_commands.append("blockdev --setra '%d' '%s'" % \
                           (args.drive_readahead, device))

        max_sectors_kb_file = "/sys/block/%s/queue/max_sectors_kb" % drive
        write(args,
              max_sectors_kb_file,
              str(max_sectors_kb))
        rc_commands.append("echo '%d' > '%s'" % \
                           (max_sectors_kb, max_sectors_kb_file))

        nr_requests_file = "/sys/block/%s/queue/nr_requests" % drive
        write(args,
              nr_requests_file,
              str(args.drive_nr_requests))
        rc_commands.append("echo '%d' > '%s'" % \
                           (args.drive_nr_requests, nr_requests_file))

        queue_depth_file = "/sys/block/%s/device/queue_depth" % drive
        write(args,
              queue_depth_file,
              str(args.drive_ncq_depth))
        rc_commands.append("echo '%d' > '%s'" % \
                           (args.drive_ncq_depth, queue_depth_file))

def tune_raid(args):
    rc_commands.append("# Tune RAID device %s" % md_device_label(args))

    run(args, [
        "blockdev",
        "--setra",
        str(args.raid_readahead),
        md_device_label(args),
    ])
    rc_commands.append("blockdev --setra '%d' '%s'" % \
                       (args.raid_readahead, md_device_label(args)))

    stripe_cache_size_file = "/sys/block/%s/md/stripe_cache_size" % \
                             args.md_label
    write(args,
          stripe_cache_size_file,
          str(args.raid_stripe_cache))
    rc_commands.append("echo '%d' > '%s'" % \
                       (args.raid_stripe_cache, stripe_cache_size_file))

    speed_limit_min_file = "/proc/sys/dev/raid/speed_limit_min"
    write(args,
          speed_limit_min_file,
          str(args.raid_speed_limit_min))
    rc_commands.append("echo '%d' > '%s'" % \
                       (args.raid_speed_limit_min, speed_limit_min_file))

    speed_limit_max_file = "/proc/sys/dev/raid/speed_limit_max"
    write(args,
          speed_limit_max_file,
          str(args.raid_speed_limit_max))
    rc_commands.append("echo '%d' > '%s'" % \
                       (args.raid_speed_limit_max, speed_limit_max_file))

def tune_fs(args):
    options = [
        "stride=%d" % args.fs_stride,
        "stripe-width=%d" % args.fs_stripe_width,
    ]
    run(args, [
        "tune2fs",
        "-E", ",".join(options),
        crypt_device(args),
    ])

def tune_persistent(args):
    info(args, "Persisting tuning parameters")

    now = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")

    rc_file = "/etc/rc.local"
    backup_rc_file = "%s.bak.%s" % (rc_file, now)

    rc_file_contents = "\n".join(rc_commands + ["exit 0"])

    run(args, ["cp", rc_file, backup_rc_file])
    write(args, rc_file, rc_file_contents)

def start_raid(args):
    run(args, [
        "mdadm",
        "--assemble",
        md_device_label(args),
    ])

def start_crypt(args):
    run(args, [
        "cryptsetup",
        "luksOpen",
        md_device_label(args),
        args.crypt_name
    ])

def stop_raid(args):
    run(args, [
        "mdadm",
        "--stop",
        md_device_label(args),
    ])

def stop_crypt(args):
    run(args, [
        "cryptsetup",
        "luksClose",
        args.crypt_name,
    ])

if __name__ == "__main__":
    args = parse_args()
    args.func(args)
