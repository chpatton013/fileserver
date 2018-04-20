# TODO

* Rename disk to media.
  * A disk is just an implementation of storage media.

* Add sync schema.
  * List of source-to-target tuples to feed to lsyncd.
  * Multi-lsyncd tool:
    * `msyncd`?
    * SystemD unit file to start daemon
    * Command line interface to add, remove, and query syncs.

* Change disk device path to disk device id (`/dev/disk/by-id`).
  * Drive names (`/dev/sdX`) are not persistent.
  * UUID's are only available for partitions, not disks.

* Change raid device path to raid device id (`/dev/disk/by-id`).
  * UUID's are persistent across all hardware configurations, but only exist
    after a partition has been created. A pre-configuration identifier is
    necessary, so hardware id must be used.
  * A partition-UUID can be added as an integrity check to ensure the hardware
    id has not changed since last setup.

* Investigate alternate schema library that will combine schema and property
  classes.
  * Currently doing this manually with `schema.py` and `configuration.py`.
  * Some meta-programming might do the trick.

* Combine Fs and Bind schemas
  * Rename to Mount
  * Add `bind` and `rbind` to `fs_type`
  * Rename `mount_location` to `volume_path`
  * Add list of mount options (just like export options)
  * Mount volumes in root-only location, apply options, then move to destination
    ```
    mkdir --parents /root/private/<tmpdir>
    chown root: /root/private
    chmod 700 /root/private
    mount --bind /some/where /root/private/mnt
    mount -o remount,ro,bind /root/private/mnt
    mount --move /root/private/mnt /mnt/readonly
    ```

* Start action
  * Implement idempotent volume startup
    * Dependency graph of volumes; start in descendant-first DFS order.
      * Export after FS or Bind startup
  * MDADM config: remove `name=*` portions to fix `/dev/md127` issue.
  * S.M.A.R.T. tests
    * Perform conveyance-test upon startup (assume movement or physical
      interation) (should complete in ~5 minutes)
    * Schedule hourly short-tests (should complete in ~2 minutes)
    * Schedule daily long-tests (should complete in ~90 minutes)

* Stop action
  * Implement idempotent volume shutdown
    * Dependency graph of volumes; stop in ancestor-first DFS order.
      * Export after FS or Bind shutdown

* Glossary
  * Device: A physical component exposed on the filesystem. Devices are managed
    by the kernel at the time the component is detected by attached hardware.
    Devices are intrinsically present due to the state of the hardware.
    * Examples:
      * IDE- or ATA-connected hardware (`/dev/hda`, `/dev/sda`)
      * Disk partitions (`/dev/sda1`)
  * Volume: A logical filesystem construct backed by Devices or other Volumes.
    Volumes are started by kernel modules at the time that user-space software
    is invoked. Volumes are only present after some action has been taken.
    * Examples:
      * RAID or Device Mapper devices (`/dev/md0`, `/dev/md/array`,
        `/dev/mapper/volume`)
      * Mounted filesystems or binds (variations on the command `mount`)
      * Exported NFS locations
