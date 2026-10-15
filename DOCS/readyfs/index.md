# ReadyFS

ReadyFS aims to provide a full set of command-line tools and a coherent way to work with Ultimate DOS drives, mounted disk images or real C64 drives, SOFTIEC, and SD2IEC. That includes mounting disk images and accessing disk images on the Ultimate **without mounting them**, as if they were folders. It is a standalone Commodore 64 filesystem experiment in Ultimate Experiments, separate from ReadyOS integration.

## Try the committed disk

Use [readyfs-overlay-lab.d81](../downloads/readyfs-overlay-lab.d81) for normal interactive use. It contains the main program and all 28 sidecars; keep the disk available while loading. Configure at least **1 MiB REU**, mount the image as device 8, then enter:

```basic
LOAD "READYFS-OVERLAY",8,1
RUN
```

Start with `HELP`, `HELP DIR`, `DRIVES`, and `DIR 8:/`. Discovery and directory reads are useful first steps before preparing disposable write tests. On an Ultimate, UCI-dependent endpoints need the Command Interface enabled. Native SD2IEC remains an IEC device with its own address, partition and filesystem view.

[readyfs-lab.d81](../downloads/readyfs-lab.d81) contains the monolithic diagnostic build. It retains a simpler input reader and an earlier command surface; the overlay program is the main shell. Device selection and exact loading behavior are described in the [user guide](READYFS_USER_GUIDE.md).

## What it does

- **Paths and endpoints:** distinguish IEC devices, Ultimate host storage, SoftwareIEC, native SD partitions and contained Ultimate disk-image entries. Aliases name exact locations without changing their capabilities.
- **Navigation and inspection:** `DIR`, `TREE`, `FIND`, `STAT`, `VOLUME`, drive discovery, backend capability reports and native IEC configuration.
- **File work:** typed stream COPY/COMPARE/MOVE, rename, delete, directory creation/removal, content reads, CRC checks, and bounded recursive plans with include/exclude filters and WhatIf previews.
- **Interactive shell:** a wrapped 255-byte editor, editable 32-command REU history, output paging, command shortcuts and compact contextual help.
- **DOS-style scripts:** staged SEQ files, `%0`–`%9`, session/persistent SET variables, arithmetic, IF/GOTO, same-file CALL, result checks and explicit config save/load. [BACKUP.SEQ](examples/BACKUP.SEQ) demonstrates guarded PREVIEW/APPLY and verified copy.
- **Native SD2IEC:** identity/configuration, partitions, hierarchical folders, explicit image mounts, and type-preserving SEQ/PRG/USR transfers.

The application uses native IEC and UCI. REST/FTP and host recording tools are development automation, not runtime dependencies of the C64 program.

## Documentation and screenshot tours

| Read | Purpose |
|---|---|
| [Illustrated user guide](READYFS_USER_GUIDE.md) | Path model, every command, options and worked examples |
| [Portable HTML guide](portable-guide.html) | Self-contained offline/print edition with illustrations |
| [Documentation site](index.html) | HTML references and screenshot walkthroughs without bundled video |
| [Interactive UI](READYFS_INTERACTIVE_UI.md) | Editing, history, paging and display limits |
| [RUN and batch guide](READYFS_RUN_GUIDE.md) | Variables, arguments, flow control, results and complete backup example |
| [SD2IEC walkthrough](READYFS_SD2IEC_TUTORIAL.md) | Folder round trips, image views and intermediate-endpoint workflows |
| [IEC configuration](READYFS_IEC_CONFIGURATION.md) | Read settings, make explicit changes, and understand persistence |
| [Native SD2IEC reference](SD2IEC_NATIVE.md) | Firmware caveats, CBM types, path limits and tested routes |
| [Safety](READYFS_SAFETY.md) | Disposable fixtures and ownership gates |
| [Acceptance summary](READYFS_ACCEPTANCE.md) | Current verified scope and retained-evidence policy |

The external demonstration website is independently maintained. Its Git repository and video files are not included here. The repository's `DOCS/` editions retain screenshots and written walkthroughs.

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

## Layout and local evidence

`src/apps/readyfs/` contains C and 6502 assembly; `cfg/` contains the linker layout; `build_support/` holds tests and automation; `docs/` holds the maintained references. `artifacts/readyfs/` is generated except for the two committed main D81s. Logs and internal working records are ignored.

The 14 October 2026 cleanup keeps `logs/readyfs_c64u/batch-demo-20261013b` and its final `demo-v8-batch-appended-20261013` output. Earlier raw run directories were deleted at the owner's request. Historical design documents retain run identifiers as provenance; those directories are no longer distributed or guaranteed to exist. See [PROJECT_INVENTORY.md](PROJECT_INVENTORY.md) for the source and build map.
