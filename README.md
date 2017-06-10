# Fileserver management tools

Perform a variety of operations on an encrypted software RAID.

Each operation is invoked by a different subcommand. Options `--verbose` and
`--dryrun` can be specified *BEFORE* any subcommand.

## Create

Create a new encrypted RAID volume.

Specify the RAID geometry, MDADM config options, LUKS properties, and FS type.
```
usage: manage.py create [-h] [--block_size BLOCK_SIZE] --raid_level {0,1,5,6}
                        [--raid_chunk_size RAID_CHUNK_SIZE] --md_label
                        MD_LABEL --crypt_name CRYPT_NAME --devices DEVICES
                        [DEVICES ...] [--randomize {/dev/random,/dev/urandom}]
                        [--mdadm_conf_file MDADM_CONF_FILE]
                        [--mdadm_conf_create MDADM_CONF_CREATE]
                        [--mdadm_conf_device MDADM_CONF_DEVICE]
                        [--mdadm_conf_homehost MDADM_CONF_HOMEHOST]
                        [--mdadm_conf_mailaddr MDADM_CONF_MAILADDR]
                        [--crypt_key_size {256,512}]
                        [--crypt_hash_algorithm {sha1,sha256,sha512}]
                        [--crypt_iter_time CRYPT_ITER_TIME]
                        [--fs_type {ext2,ext3,ext4}]
```

Example:
```
manage.py --verbose --dryrun \
  create --raid_level 6 \
         --md_label md0 \
         --crypt_name vault \
         --devices /dev/sd{b..j} \
         --randomize /dev/urandom
```

## Tune

Tune an existing encrypted RAID volume.

Specify the RAID geometry, optimization parameters, and FS properties.
```
usage: manage.py tune [-h] [--block_size BLOCK_SIZE] --raid_level {0,1,5,6}
                      [--raid_chunk_size RAID_CHUNK_SIZE] --md_label MD_LABEL
                      --crypt_name CRYPT_NAME --devices DEVICES [DEVICES ...]
                      [--drive_readahead DRIVE_READAHEAD]
                      [--drive_nr_requests DRIVE_NR_REQUESTS]
                      [--drive_ncq_depth DRIVE_NCQ_DEPTH]
                      [--raid_readahead RAID_READAHEAD]
                      [--raid_stripe_cache RAID_STRIPE_CACHE]
                      [--raid_speed_limit_min RAID_SPEED_LIMIT_MIN]
                      [--raid_speed_limit_max RAID_SPEED_LIMIT_MAX]
                      [--fs_stride FS_STRIDE]
                      [--fs_stripe_width FS_STRIPE_WIDTH]
```

Example:
```
manage.py --verbose --dryrun \
  tune --raid_level 6 \
       --md_label md0 \
       --crypt_name vault \
       --devices /dev/sd{b..j}
```

## Start

Start a stopped encrypted RAID volume.

Specify the RAID label and LUKS name.
```
usage: manage.py start [-h] --md_label MD_LABEL --crypt_name CRYPT_NAME
```

Example:
```
manage.py --verbose --dryrun \
  start --md_label md0 \
        --crypt_name vault
```

## Stop

Stop a running encrypted RAID volume.

Specify the RAID label and LUKS name.
```
usage: manage.py stop [-h] --md_label MD_LABEL --crypt_name CRYPT_NAME
```

Example:
```
manage.py --verbose --dryrun \
  stop --md_label md0 \
       --crypt_name vault
```
