# Native SD2IEC and IEC support

This document tracks the current standalone ReadyFS implementation. It does not
require a Mac relay, HTTP, REST, or a network connection while ReadyFS runs.
Development automation uses the C64 Ultimate's external interfaces to install
and observe test builds; that automation is separate from the C64 program.

## Device, partition, and directory are different things

| Example | Meaning |
| --- | --- |
| `10:` | IEC device 10, as used by configuration commands |
| `10:/folder/file` | A path on device 10; ReadyFS queries and pins its current partition for this operation |
| `10.1:/folder/file` | A path explicitly on partition 1 of device 10 |
| `9:/FILE` | A file on a conventional flat IEC disk/image |
| `s0:/folder/file` | Ultimate SoftwareIEC partition 0, a separate endpoint |
| `u:/usb1/folder/file` | UltimateDOS host storage |

SD2IEC FAT partitions support nested directories. A mounted D64/D71/D81 is a
flat disk filesystem: `10.1:/FILE` refers to its contents while it is mounted.
A DNP has directories, but the firmware's partition-type reply cannot distinguish
it from FAT. **The same text path can refer to different media after a mount.**
An alias shortens a location; it does not remove these device capabilities or
media-state boundaries.

Native components are limited to 16 bytes by this first implementation, even
where FAT itself permits longer names. Wildcards and DOS command separators are
rejected in exact file-operation names. REL files are not ordinary byte streams
and are not supported by the copy pump. SEQ, PRG, and USR retain their CBM type.

## Automatic detection and explicit inspection

The first native file operation queries the drive identity and caches its
classification in the ReadyFS session. SD2IEC operations then query `G-P` to
resolve the current or requested partition and distinguish hierarchical media
from a flat image. A descriptor retains its partition during staging, verified
commit, and MOVE cleanup. Detection does not silently change extension settings,
select a different current partition, or mount an image.

```text
probe iec 10:
profile iec 10:
iec 10: version
iec 10: partitions
iec 10: partition
iec 10: partition 1
```

A cached identity can become stale if hardware is replaced or readdressed outside
ReadyFS. Use `probe iec 10:` again after such changes. ReadyFS's native reset,
address, raw-DOS, and partition-selection paths invalidate affected session data.
Device absence and an unsupported media/path combination are different failures.

## Configuration commands

`help iec` lists the command syntax. These commands run on the C64 over IEC.
SD2IEC-specific operations first check the actual device identity.

### General IEC operations

```text
iec 10: status
iec 10: version
iec 10: initialize
iec 10: reset soft
iec 10: dos "UI"
iec 10: dos --hex "55 49"
```

`status` reads the current DOS reply. `version` sends `UI`. `initialize` sends
`I`; `reset soft` sends `UJ`. Their effect and support depend on the drive's DOS.
Raw `dos` is an expert escape hatch, not a portability layer: the supplied bytes
are sent to that device and its actual status is shown. Hex bytes are needed for
binary parameters; typing decimal digits is not equivalent to a binary byte.

### SD2IEC settings and persistence

```text
iec 10: config
iec 10: extensions 2
iec 10: hide-extensions on
iec 10: images both
iec 10: wildcard 1581
iec 10: partition 1 --select
iec 10: save-config
```

| Setting | Accepted values | Native command |
| --- | --- | --- |
| `extensions` | `0` through `4` | `XE0` through `XE4` |
| `hide-extensions` | `on`, `off` | `XE+`, `XE-` |
| `images` | `files`, `dirs`, `both` | `XI0`, `XI1`, `XI2` |
| `wildcard` | `1541`, `1581` | `X*-`, `X*+` |
| `partition N --select` | Valid partition number | `CPN` |
| `save-config` | No argument | `XW` |

Extension modes on the detected firmware:

| Mode | Normal FAT file creation |
| --- | --- |
| `0` | No X00 wrapper for names representable directly in FAT |
| `1` | X00 for SEQ/USR/REL; ordinary PRG stays raw |
| `2` | X00 for ordinary file types |
| `3` | SEQ/USR/REL filename extensions, without X00 headers |
| `4` | As mode3, including PRG extensions |

Modes3/4 also enable extension hiding. With hiding enabled, a FAT
`README.SEQ` is presented as the logical SEQ file `README`. Disk-image names
have special firmware rules; the raw-image procedure below accounts for
ReadyFS's staging and rename behavior. `images both` lists each image twice,
with its file type and as a directory. `wildcard 1581` makes text after `*`
participate in matching; `1541` ignores that trailing text in native matching.

These settings affect the drive globally, including other C64 software.
`config` shows the native `X` response rather than guessing settings from a
ReadyFS preference. Extension mode and extension hiding are related firmware
settings; inspect `config` after changing either. Image listing as directories
is a presentation setting, not proof that a filesystem entry is an ordinary
FAT directory. On the tested firmware, image files are rejected as intermediate
path components. Recursive planning therefore stops if a listing presents an
image as a directory; it does not silently mount, skip, or recurse into it. Use
`images files` explicitly when you want image containers treated as files.
Running changes and EEPROM persistence are separate: use
`save-config` only when the current drive settings are the ones to retain.

### Device address

```text
iec 8: address 10
iec 8: address 10 --save
iec 10: reset hard
```

The address command sends a **binary** `U0>` address, checks for a conflicting
listener, and verifies the result on the new address. `--save` persists it with
`XW`. Use the old address in the command and the new address afterward. Hard
restart is SD2IEC-specific (`U` followed by `$CA`). If two devices already answer
on the same address, resolve that collision before discovery or readdressing.

`save-config` saves supported current extended settings together, including the
address; it does not save the current folder, selected partition, or mounted
image. On hardware with address jumpers, changing the jumper setting can
override the saved address.

The user's external SD2IEC was found on 8, moved to 10, saved, and verified after
a hard restart. Ultimate A was temporarily disabled during that repair and then
restored to its original image/settings.

## File and folder examples

Replace `demo` with a directory you own. These are ordinary ReadyFS commands;
mutating examples are not requests to run them against existing user files.

```text
dir 10:/demo/
volume 10.1:/demo/
tree 10.1:/demo/
alias card 10.1:/demo
copy @card:/notes u:/usb1/notes.seq
copy u:/usb1/notes.seq @card:/notes2
compare @card:/notes2 u:/usb1/notes.seq
mkdir @card:/work
rename @card:/notes2 @card:/renamed
move @card:/renamed @card:/work/notes
```

`COPY` stages a new destination, closes it, verifies content, and commits it.
`MOVE` removes its source only after successful copy/verification. Empty Ultimate destination folders are valid: the firmware
reply `01,DIRECTORY EMPTY` means the requested file is absent, not that lookup
failed. Failed native
OPEN/CLOSE and DOS statuses are propagated instead of becoming an empty file or
successful operation. The native status reader uses the existing command channel
without closing channel 15, which would discard SD2IEC's other open buffers.

Folder removal uses a partition-qualified parent change followed by a leaf-only
`RD` command: SD2IEC rejects slash paths in `RD`. Consequently removal can change
that partition's native current directory to the removed folder's parent. It
must be empty; recursive deletion is a separate ReadyFS operation.

## Images and boundaries

Explicit native image operations use a partition-qualified path:

```text
probe iec 10:
mount 10.1:/demo/work.d64 --force
dir 10.1:/
copy 10.1:/HELLO u:/usb1/hello.prg
copy u:/usb1/notes.seq 10.1:/NOTES
dismount 10.1:/ --force
```

The mount changes SD2IEC's filesystem context. Subsequent operations query the
new partition type. Native image unmount first goes to the specified partition's
root and then sends its BACK command; it does not use whichever partition happens
to be current. The real-device mount, directory, volume, read/write, MOVE,
DELETE, unmount, and return-to-FAT checks have passed. Independent c1541 inspection of the exported modified image also passed: raw
geometry, bytes, CBM types, and removed MOVE/delete sources were checked.

| Transfer | Implementation boundary |
| --- | --- |
| SD FAT ↔ UltimateDOS | Normal verified byte-stream transfer |
| SD FAT ↔ another IEC image | Normal verified byte-stream transfer |
| SD FAT ↔ SoftwareIEC | Normal verified byte-stream transfer |
| Mounted SD image ↔ a different device/endpoint | Read/write/MOVE with UltimateDOS passed; IEC9/SoftwareIEC matrix pending |
| SD FAT ↔ image mounted on the **same SD device** | Use an intermediate file on another endpoint and explicit mount/unmount |
| `10.1:/work.d64!/FILE` | Not yet implemented as an automatic media transition |
| `u:/usb1/work.d81/FILE` | UltimateDOS embedded-filesystem traversal; contained-file mutation has type/lookup limits described below |

### UltimateDOS contained-file paths

The Ultimate firmware can enter an unmounted image through an ordinary slash
path such as `u:/usb1/work.d81/HELLO`. That is separate from native SD image
mounting. It can also open a typed contained-file name such as `HELLO.prg` or
`NOTES.seq`.

General mutation through this route is **not yet a supported substitute for
mounting the image on an IEC device**. Its directory reply omits generated type
suffixes, so ReadyFS lookup cannot reliably match a typed access name. Its
extensionless staging and backup names can also convert SEQ/USR entries to PRG.
Content comparison checks bytes, not the CBM directory type. In particular, do
not infer safe replacement, rollback, or MOVE cleanup from a successful direct
OPEN or COMPARE. Use an explicitly mounted IEC image for those general transfers.
A narrow physical acceptance using unique bare PRG names in a separately owned,
unmounted image is being prepared; it does not cover the SEQ/USR limitations.

Mount/unmount can close all buffers on an SD2IEC device, including buffers on
other partitions. It cannot safely occur in the middle of ordinary simultaneous
source/destination streaming. A future automatic media controller needs whole
file spooling (with capacity checks), closed-channel transitions, and verified
source cleanup. The current implementation does not claim that capability.

ReadyFS remembers mounts it performs as session hints where implemented. An
unknown previous native image/current directory cannot be reconstructed from
`G-P`. Never interpret a remembered path as proof that another program or the
Ultimate menu has not since changed the media.

## Evidence and current work

- Exact detected firmware: `SD2IEC V1.0.0ATENTDEAD0-36`.
- Config CLI, partition queries, and temporary configuration restoration passed
  on the real C64U at 1, 16, and 64 MHz.
- Existing UltimateDOS/IEC-image/SoftwareIEC directed COPY/MOVE baseline passed
  with the SD2IEC present.
- A fresh marked native SD root and a 1,025-byte binary fixture were created and
  reread byte-for-byte. Existing user files were preserved.
- The expanded four-endpoint matrix passed all 12 directed COPY/COMPARE and
  12 MOVE/COMPARE pairs. SD destinations were exported and host-hashed; the
  persisted IEC image was independently checked for bytes, types, and removed
  MOVE sources. Machine settings were restored.
- Automatic directory/tree and VOLUME overlay changes pass the full host build;
  their physical acceptance is running.

Detailed chronological evidence, retained failed probes, firmware findings, and
run paths are in `agentworking/readyFS/SD2IEC_2026-10-12.md` at repository root.

### Copying a disk-image container onto SD FAT

SD2IEC's normal extension modes may create X00 wrappers. ReadyFS reads the
logical bytes inside those wrappers, so a successful `COMPARE` alone does not
prove that the underlying FAT file is a mountable disk image. In particular,
renaming an X00 file changes its internal CBM name, not its outer FAT container.

The current explicit procedure is to inspect `iec 10: config`, temporarily use
`iec 10: extensions 0`, copy to an unused owned `.d64`/`.d71`/`.d81` filename,
and restore the exact previous extension mode and hiding flag. Restore the mode
first, then hiding, because modes 3 and 4 enable hiding. Do not save this temporary
setting to EEPROM. ReadyFS now uses FAT-safe stage names so XE0 can produce a raw
file. Mounting the resulting image is an additional required check. This procedure
has passed copying, logical comparison, and actual D64 mounting. The modified
image export passed independent geometry, byte, and type checks; automatic raw-image creation across all
five extension modes is not claimed.
