# ReadyFS

ReadyFS aims to provide a full set of command-line tools and a coherent way to work with Ultimate DOS drives, mounted disk images or real C64 drives, SOFTIEC, and SD2IEC. That includes mounting disk images and accessing disk images on the Ultimate **without mounting them**, as if they were folders. A unified path syntax spans these endpoints, with operations such as COPY and MOVE between drive types. It is a standalone Commodore 64 filesystem experiment in Ultimate Experiments, separate from ReadyOS integration.

## What it does

- **Paths and endpoints:** distinguish IEC devices, Ultimate host storage, SoftwareIEC, native SD partitions and contained Ultimate disk-image entries. Aliases name exact locations without changing their capabilities.
- **Navigation and inspection:** `DIR`, `TREE`, `FIND`, `STAT`, `VOLUME`, drive discovery, backend capability reports and native IEC configuration.
- **File work:** typed stream COPY/COMPARE/MOVE, rename, delete, directory creation/removal, content reads, CRC checks, and bounded recursive plans with include/exclude filters and WhatIf previews.
- **Interactive shell:** a wrapped 255-byte editor, editable 32-command REU history, output paging, command shortcuts and compact contextual help.
- **DOS-style scripts:** staged SEQ files, `%0`–`%9`, session/persistent SET variables, arithmetic, IF/GOTO, same-file CALL, result checks and explicit config save/load. [BACKUP.SEQ](docs/examples/BACKUP.SEQ) demonstrates guarded PREVIEW/APPLY and verified copy.
- **SoftwareIEC:** Ultimate logical partitions and mapped folders, with file transfers through existing mappings and firmware-specific mapping limits.
- **Native SD2IEC:** identity/configuration, partitions, hierarchical folders, explicit image mounts, and type-preserving SEQ/PRG/USR transfers.

The application uses native IEC and UCI. REST/FTP and host recording tools are development automation, not runtime dependencies of the C64 program.

## Ten ways to put the path system to work

The interesting part is combining endpoints: **the command stays familiar while the path selects the storage**. These recipes show current syntax and supported routes; choose the ones that match your setup. They assume existing source files, prepared parent folders and writable media you own, with unused destination names. `USB`, `CARD`, `DISK`, `IMAGE` and `SOFT` below are aliases you define, not built-in drive names.

**Jump to:** [Aliases](#2-give-locations-names-then-mix-aliases-and-relative-paths) · [Unmounted images](#5-open-an-ultimate-image-like-a-folder-without-mounting-it) · [Image-to-image transfers](#8-bridge-a-mounted-sd-image-and-an-unmounted-ultimate-image) · [Batch scripting](#10-turn-the-transfer-into-a-reusable-batch-job)

### 1. Address different kinds of storage directly

```text
DRIVES
DIR u:/usb1/demo
STAT u:/usb1/other.d64/HELLO.prg
STAT u:/usb1/demo/work.d81/README.seq
DIR 9:/
```

| Path | What it addresses |
|---|---|
| `u:/usb1/demo` | An Ultimate host folder, without going through an emulated floppy |
| `u:/usb1/other.d64/HELLO.prg` | The PRG entry `HELLO` inside an unmounted D64 on the Ultimate |
| `u:/usb1/demo/work.d81/README.seq` | The SEQ entry `README` inside an unmounted D81 on the Ultimate |
| `9:/` | The disk in IEC device 9: a physical drive or a mounted image |
| `s0:/demo` | A folder in SoftwareIEC logical partition 0, using its existing mapping |
| `10.1:/demo` | Native IEC device 10, explicitly selecting partition 1 |

The image paths use an ordinary **`/` after the image filename**, treating its contents like a folder without mounting it. Use existing images and entry names, and keep those images unmounted while accessing them this way.

#### SoftwareIEC: an Ultimate logical mapping

```text
PROBE SOFTIEC
DIR s0:/demo
```

`s0:` addresses SoftwareIEC logical partition 0, not device 0 or an SD2IEC partition. Its root comes from the SoftwareIEC mapping. See the separate [SoftwareIEC guide](docs/READYFS_SOFTWAREIEC_GUIDE.md) for discovery, mapped folders and firmware limits.

#### Native SD2IEC: an IEC device and its partitions

```text
PROBE IEC 10:
DIR 10.1:/demo
```

**Read `10.1:` as device 10, partition 1.** `10.2:/games` addresses partition 2 on that same SD2IEC, if it exists; ReadyFS is not limited to partition 1. `10:/games` uses the device's current partition, which ReadyFS queries and pins for each operation. List the available partitions first:

```text
IEC 10: PARTITIONS
IEC 10: PARTITION
IEC 10: PARTITION 2
```

These inspect the partition list, current partition and partition 2 respectively; they do not select a partition. Explicit file paths select their own partition without changing the drive's current selection. Path numbers are decimal, even when the partition listing shows hexadecimal numbers with `$`. See the [partition reference](docs/SD2IEC_NATIVE.md#more-than-one-partition-on-the-same-device).

Available native partitions depend on your SD2IEC, card and firmware. See the separate [SD2IEC walkthrough](docs/READYFS_SD2IEC_TUTORIAL.md) for native folders and image mounts.

### 2. Give locations names, then mix aliases and relative paths

```text
ALIAS USB u:/usb1/demo
ALIAS CARD 10.1:/demo
ALIAS DISK 9:/
ALIAS IMAGE u:/usb1/other.d64
ALIAS
CD @usb:/source
DIR
HEAD readme.seq 3
CD ..
PWD
DIR @card:/
```

`@usb:/source` expands to an absolute location; `readme.seq` resolves against the current directory. `CD ..` goes up one level. An alias is a bookmark, so it neither creates the folder nor changes the endpoint's capabilities. Aliases do not chain, and `..` is not permitted inside an alias suffix. See the [path rules](docs/READYFS_USER_GUIDE.md#2-the-path-system) for normalization and limits.

### 3. Copy a program onto a mounted disk, then bring it back

With your own writable disk or image already in device 9:

```text
COPY @usb:/HELLO.prg @disk:/HELLO --WHATIF
COPY @usb:/HELLO.prg @disk:/HELLO
COMPARE @usb:/HELLO.prg @disk:/HELLO
COPY @disk:/HELLO @usb:/returned.prg
```

The host filename and the CBM directory entry can have different spellings. Single-file destinations name the **file**, not just its parent folder. The same IEC path works whether device 9 is a suitable real drive or an Ultimate drive with mounted media.

### 4. Mount an Ultimate image explicitly

```text
MOUNT @usb:/work.d81 9: --WHATIF
MOUNT @usb:/work.d81 9:
DRIVES
DIR 9:/
DISMOUNT 9:
```

Mounting changes the drive's media; `CD` only changes ReadyFS's current path. The overlay shell remembers its own accepted mounts for the session, which `DRIVES` displays as a historical hint. This recipe uses device 9 so the program's sidecar disk can stay in device 8. Choose an available drive and a valid image; do not access this same container through a direct Ultimate image path while it is mounted.

### 5. Open an Ultimate image like a folder, without mounting it

Use the separate `other.d64` named by `IMAGE`, left unmounted:

```text
DIR @image:/
COPY @image:/HELLO.prg @usb:/extracted.prg
COPY @usb:/extracted.prg @image:/HELLO2.prg
COMPARE @image:/HELLO.prg @image:/HELLO2.prg
```

`@image:/HELLO.prg` expands to **`u:/usb1/other.d64/HELLO.prg`**: the image is traversed using an ordinary slash. Current direct operations reject the modeled `!/` spelling. Supported contained streams are SEQ, PRG and USR; the physical contained-image matrix covered D64. Copying `u:/usb1/other.d64` itself would copy the whole image file instead of one entry.

### 6. Take a filtered folder tree from USB to native SD2IEC

```text
MKDIR @card:/seqtree
COPY @usb:/source @card:/seqtree -R -I "**/*.seq" -X "scratch/**" -W
COPY @usb:/source @card:/seqtree -R -I "**/*.seq" -X "scratch/**"
TREE @card:/seqtree
```

`**/*.seq` selects matching names at the root and below it; `scratch/**` excludes that subtree. `-R` recurses and `-W` previews. The destination is a container created first: the source's selected descendants go inside `seqtree`, without an extra `source` folder. Native SD path components are limited to 16 bytes. In the tested extension mode, a host `one.seq` becomes logical SEQ name `ONE` on SD; use the names shown by `DIR` when reading it back.

### 7. Work through a SoftwareIEC mapping

With an existing writable `demo` folder in SoftwareIEC logical partition 0:

```text
ALIAS SOFT s0:/demo
DIR @soft:/
COPY @usb:/source/readme.seq @soft:/README
COMPARE @usb:/source/readme.seq @soft:/README
COPY @soft:/README @usb:/fromsoft.seq
```

This uses the Ultimate's SoftwareIEC filesystem, with its own logical mapping and discovered IEC bus. Its filename handling and folder operations depend on the mapping and firmware. For transfers between SoftwareIEC and native SD2IEC, see the [interoperability section](docs/READYFS_SOFTWAREIEC_GUIDE.md#interoperability-softwareiec-and-native-sd2iec).

### 8. Bridge a mounted SD image and an unmounted Ultimate image

With `work.d64` already present and mountable in the native SD folder:

```text
MOUNT @card:/work.d64 --FORCE
DIR 10.1:/
COPY @image:/HELLO.prg 10.1:/DEMO-PRG
COPY 10.1:/DEMO-PRG @image:/FROM-SD.prg
COMPARE 10.1:/DEMO-PRG @image:/FROM-SD.prg
COPY 10.1:/DEMO-PRG @usb:/fromimg.prg
DISMOUNT 10.1:/ --FORCE
COPY @usb:/fromimg.prg @card:/fromimg.prg
```

There are two different image models here: **SD2IEC must mount its image; UltimateDOS can access a separate unmounted image directly.** While mounted, `10.1:/` exposes the SD image's directory, and `@card:/` no longer reaches the earlier FAT folder. The final three commands stage a file on USB, dismount, then copy it into that SD folder. The intermediate endpoint makes the same-device transition possible. Automatic native `10.1:/work.d64/FILE` traversal is not implemented. [See the illustrated image walkthrough](docs/READYFS_SD2IEC_TUTORIAL.md#5-work-inside-an-image-stored-on-sd2iec).

### 9. Move a file across drive types

With SD2IEC back in its folder view and a disposable SEQ file `NOTES` in `@card:/`, move it to a new host filename:

```text
MOVE @card:/NOTES @usb:/moved.seq --WHATIF
MOVE @card:/NOTES @usb:/moved.seq
DIR @card:/
STAT @usb:/moved.seq
```

Cross-drive MOVE copies and normally verifies the destination, then removes the source. It is not an atomic rename: a failure can leave partial progress, so inspect both locations. COPY keeps the original. Both commands can operate between the supported host, IEC, SoftwareIEC and native SD endpoints; the [acceptance summary](docs/READYFS_ACCEPTANCE.md) records the tested routes.

### 10. Turn the transfer into a reusable batch job

The shell has a **DOS-style batch language**: arguments, named variables, arithmetic, conditions, labels, local subroutines and error handling. The same paths and aliases work inside scripts. Here is a complete, small example; save it as `TRANSFER.SEQ`, or [download the ready-to-use script](docs/examples/TRANSFER.SEQ):

```text
ONERROR STOP
IF "%1"=="" GOTO USAGE
IF "%2"=="" GOTO USAGE
IF "%3"=="PREVIEW" GOTO PREVIEW
IF NOT "%3"=="APPLY" GOTO USAGE
COPY "%1" "%2"
COMPARE "%1" "%2"
EXIT /B 0
:PREVIEW
COPY "%1" "%2" --WHATIF
EXIT /B 0
:USAGE
ECHO USE SOURCE DEST AND PREVIEW OR APPLY
EXIT /B 4
```

Put the script in `@usb:/`, then **pass the source, destination and mode as parameters**:

```text
RUN @usb:/TRANSFER.SEQ @disk:/HELLO @usb:/saved.prg PREVIEW
RUN @usb:/TRANSFER.SEQ @disk:/HELLO @usb:/saved.prg APPLY
```

| Script parameter | Value in these RUN commands |
|---|---|
| `%1` | `@disk:/HELLO` — the source on IEC device 9 |
| `%2` | `@usb:/saved.prg` — the destination on Ultimate host storage |
| `%3` | `PREVIEW` or `APPLY` — the selected branch |

`IF` checks the arguments and mode; `GOTO` jumps to a label in this file. `PREVIEW` performs COPY with `--WHATIF`, then exits without writing. `APPLY` copies and compares, with normal destination-conflict checks. Missing path arguments or an invalid mode go to `USAGE` and return 4. Keep the source disk from example 3 available, choose an unused destination name, or substitute another supported pair of endpoints. Quote any RUN argument containing spaces; the script quotes `%1` and `%2` when using them.

`ONERROR STOP` ends the run on a failed command; it does not undo completed work. ReadyFS stages the script before executing it, so the script stream is closed during transfers. Host-created scripts need uppercase option bytes and real line breaks; the download already has both. For explicit existence guards, a local `CALL` subroutine and a session counter, see the demonstrated [BACKUP.SEQ](docs/examples/BACKUP.SEQ) and the [full batch guide](docs/READYFS_RUN_GUIDE.md).

## Try the committed disk

Use [readyfs-overlay-lab.d81](artifacts/readyfs/readyfs-overlay-lab.d81) for normal interactive use. It contains the main program and all 28 sidecars; keep the disk available while loading. Configure at least **1 MiB REU**, mount the image as device 8, then enter:

```basic
LOAD "READYFS-OVERLAY",8,1
RUN
```

Start with `HELP`, `HELP DIR`, `DRIVES`, and `DIR 8:/`. Discovery and directory reads are useful first steps before preparing disposable write tests. On an Ultimate, UCI-dependent endpoints need the Command Interface enabled. Native SD2IEC remains an IEC device with its own address, partition and filesystem view.

[readyfs-lab.d81](artifacts/readyfs/readyfs-lab.d81) contains the monolithic diagnostic build. It retains a simpler input reader and an earlier command surface; the overlay program is the main shell. Device selection and exact loading behavior are described in the [user guide](docs/READYFS_USER_GUIDE.md).

## Documentation and screenshot tours

| Read | Purpose |
|---|---|
| [Illustrated user guide](docs/READYFS_USER_GUIDE.md) | Path model, every command, options and worked examples |
| [Portable HTML guide](docs/READYFS_USER_GUIDE.html) | Self-contained offline/print edition with illustrations |
| [Documentation site](../DOCS/readyfs/index.html) | HTML references and screenshot walkthroughs without bundled video |
| [Interactive UI](docs/READYFS_INTERACTIVE_UI.md) | Editing, history, paging and display limits |
| [RUN and batch guide](docs/READYFS_RUN_GUIDE.md) | Variables, arguments, flow control, results and complete backup example |
| [SoftwareIEC guide](docs/READYFS_SOFTWAREIEC_GUIDE.md) | Logical partitions, mapped folders, transfers and firmware limits |
| [SD2IEC walkthrough](docs/READYFS_SD2IEC_TUTORIAL.md) | Folder round trips, image views and intermediate-endpoint workflows |
| [IEC configuration](docs/READYFS_IEC_CONFIGURATION.md) | Read settings, make explicit changes, and understand persistence |
| [Native SD2IEC reference](docs/SD2IEC_NATIVE.md) | Firmware caveats, CBM types, path limits and tested routes |
| [Safety](docs/READYFS_SAFETY.md) | Disposable fixtures and ownership gates |
| [Acceptance summary](docs/READYFS_ACCEPTANCE.md) | Supported routes and current limitations |

## Current scope and boundaries

The attached SD2IEC/C64 Ultimate acceptance covered the twelve directed COPY and MOVE routes between Ultimate host storage, mounted IEC9, SoftwareIEC and native SD FAT, recursive folder round trips, and an expanded image matrix with SEQ/PRG/USR type checks. Native reads/configuration were exercised at 1, 16 and 64 MHz. This does not establish compatibility with every firmware, drive, partition or physical tape device.

The current build uses 28 cached sidecars. Its retained build report places resident code at `$B536`, leaving 117 safe bytes before KERNAL scratch; the monolithic end is `$C5F7`. These are build-specific measurements, not spare capacity guarantees.

Important limits:

- Native SD components are limited to 16 bytes. REL is not a supported native SD byte stream.
- SD image transitions require explicit MOUNT/DISMOUNT. Automatic native `image.d64!/FILE` traversal is not implemented. SD FAT↔an image mounted on that same device requires an intermediate endpoint.
- SoftwareIEC partition map/unmap remains provisional on firmware without the required commands. Broader backend/recursive coverage and legacy typed-result conversion remain incomplete.
- Scripts are bounded to 16 KiB, 255-byte expanded lines, 16 variables, nine positional inputs, eight local calls and 10,000 executed lines. External-script CALL, nested RUN, SHIFT, FOR, pipes and redirection are unavailable.
- Host-created batch option bytes must be uppercase, such as `--WHATIF`. Preview and verification do not provide transaction rollback for an entire script.

## Build and verify

Requirements: cc65 (`cl65`), VICE tools (`c1541`, `x64sc`), Python 3, Clang, and .NET for the external VICE harness. From this folder:

```sh
make readyfs
make readyfs-host-tests
make readyfs-build-report
make readyfs-vice-smoke
```

`make readyfs` builds the monolithic and overlay programs, all 28 sidecars, disks and tape fixtures, host tests, UCI source-contract checks, and memory/REU reports. VICE launchers resolve `VICE_TASKS_REPO` or the sibling `../../agenticdevharness` checkout.

Run `node build_support/build_readyfs_user_guide.mjs` to rebuild the portable guide. Install the root documentation dependencies with `npm ci`, or supply `READYFS_MARKED_PATH` for its Markdown renderer. Rebuild the public documentation with `npm run build:docs` from the repository root.

## Physical automation and safety

Use `build_support/start_readyfs_*_terminal.sh` wrappers for Terminal-owned REST/FTP automation. Read [AGENTS.md](AGENTS.md) and the safety guide before hardware work. Mutation suites create fresh marker-owned run roots under `/usb1/READYFS_TEST/<run-id>` or `/sdcard/READYFS_TEST/<run-id>`, with separate native SD ownership gates. They preserve original files and restore touched hardware settings.

## Project layout

`src/apps/readyfs/` contains C and 6502 assembly; `cfg/` contains the linker layout; `build_support/` holds tests and automation; `docs/` holds the maintained references. `artifacts/readyfs/` is generated except for the two committed main D81s. Logs and internal working records are ignored.

See [PROJECT_INVENTORY.md](PROJECT_INVENTORY.md) for the source and build map.
