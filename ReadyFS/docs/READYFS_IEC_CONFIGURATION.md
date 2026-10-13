# Native IEC and SD2IEC configuration

Implementation status: the commands below are built into the overlay version,
with host protocol tests. Physical acceptance of this new command family is
still pending. The monolithic diagnostic retains its earlier command set.
The existing `native` translation preview is unchanged.

## Read first, change explicitly

These commands run directly on the C64 using its IEC bus. They need no network,
REST service or Mac relay. They run as standalone commands with no transfer
channels open. Use a device designator such as `10:`, without a file path.

```text
iec 10: status
iec 10: version
iec 10: config
iec 10: partitions
iec 10: partition
iec 10: partition 1
```

`status` reads the current DOS status without first issuing a reset or version
command. Reading consumes that status. `version` sends UI; its effect depends
on the drive firmware. On SD2IEC it reports the version. The SD2IEC-specific
commands identify SD2IEC/uIEC before sending their device-specific operation.

`config` sends X, a query. Bare XE and XI are not queries and are never used
for inspection. `partitions` reads the native partition directory; the numbers
shown with `$` are hexadecimal. `partition` queries the selected partition;
`partition 0` queries SYSTEM, while `partition 1` queries partition 1. G-P type
1 can mean FAT or a mounted DNP, so ReadyFS labels that ambiguity. A missing
partition is an error. These queries do not select partitions or change images.

## Change the running settings

| Command | Effect |
|---|---|
| `iec 10: partition 1 --select` | Select partition 1; SD2IEC also clears its autoswap list. |
| `iec 10: extensions 0` | No x00 headers or automatic typed extensions. |
| `iec 10: extensions 1` | x00 headers for non-PRG files; raw PRG. |
| `iec 10: extensions 2` | x00 headers for all supported types. |
| `iec 10: extensions 3` | Typed filename extensions for non-PRG files. |
| `iec 10: extensions 4` | Typed filename extensions for all types. |
| `iec 10: hide-extensions on` | Hide typed extensions in the logical directory view. |
| `iec 10: hide-extensions off` | Show typed extensions. |
| `iec 10: images files` | Present images as files. |
| `iec 10: images dirs` | Present images as directories. |
| `iec 10: images both` | Present both views. |
| `iec 10: wildcard 1541` | 1541 wildcard suffix matching. |
| `iec 10: wildcard 1581` | 1581 wildcard suffix matching. |

Modes 3 and 4 also enable extension hiding in the firmware. Returning to mode
0, 1 or 2 does not automatically turn hiding off. ReadyFS does not normalize
these settings on probe or copy. Settings can affect the host filename, CBM
logical name and file format seen by future operations.

```text
iec 10: config
iec 10: extensions 2
iec 10: config
iec 10: save-config
```

`save-config` sends XW and saves **all current SD2IEC settings**, not just the
last command. Setters do not save automatically.

## Address and reset

```text
iec 10: address 13
iec 13: status
iec 13: address 10 --save
iec 10: initialize
iec 10: reset soft
iec 10: reset hard
```

Address changes accept 8 through 30, reject occupied/ambiguous listener checks,
and verify SD2IEC at the new address. `--save` sends XW only after verification.
It still saves every running setting. Address 13 is sent as a binary byte with
an extra command terminator, preserving it through the firmware CR handling.

Initialize cleans device buffers. Soft reset sends UJ; on SD2IEC it preserves
cwd, mounted image and autoswap state. Hard reset sends U plus binary $CA;
saved settings, including the saved address, then apply. ReadyFS reports that
the restart was sent, rather than claiming that the device has returned at the
old address. These commands invalidate ReadyFS cached profile/mount hints for
the affected address, and an address change also invalidates its destination.

## Explicit DOS commands

```text
iec 10: dos "x?"
iec 10: dos --hex "55 CA"
```

The text form transmits its quoted command. The hex form accepts separated,
complete byte pairs, including zero bytes. Both forms are limited to 119 bytes.
These are real commands, not previews; their meaning and side effects come from
the device firmware. Raw commands invalidate all cached IEC profile/mount hints
because their effect cannot be inferred. DOS status 09 is accepted as SD2IEC's
long-version information, alongside success/information codes 00–03 and 73.
Other DOS errors are red and set the shell's typed error result.

## Implementation and test boundaries

Policy lives in cached overlay 17; native standalone I/O and media reporting
live in overlay 18. Stream preparation retains overlay 16 for filesystem policy. The resident gateway enters them sequentially. Neither
loads a sidecar from disk at runtime. All returned data stays in resident
buffers, and existing file transfer loops keep their current implementation.

On SD2IEC, **CLOSE 15 closes all user data channels on that device**. The new
standalone configuration transaction must not be reused for status checks
inside a copy. Native filesystem support needs command-channel lifetime handling
that preserves live source/destination channels.

Host tests exercise exact binary commands, current versus SYSTEM partition,
partition/address 13, occupied-address refusal, verify-before-save sequencing,
short writes, unavailable partitions, the special partition-directory EOF,
operation-specific status codes, bounded raw commands and cache invalidation.
They do not prove physical timing or persistent-device behavior.

Protocol reference: [official source for the attached -36 firmware](https://www.sd2iec.de/nightlies/sd2iec-1.0.0atentdead0-36-g7e7be29.tar.gz),
particularly `src/doscmd.c`, `src/iec.c` and `src/fileops.c`.
