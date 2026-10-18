# V1 endpoint: install, use and keep your work

User direction, 2026-10-17: prioritize a dependable installer, configuration and floppy/hard-drive experience. Turbo Pascal is the main application acceptance test. Further performance improvement and compiled-code activation move to after V1. The earlier 50% minimum / 85% stretch speed targets do not block this release.

**V1 is ready when a user can install from their own DOS images on a C64 Ultimate, work in DOS and Turbo Pascal, save to A/B/C, finish safely, and recover that work after restarting.** The same final release must pass the model and actual Ultimate tests below. A component test or an older successful build does not close a final-release gate.

## Supported V1 system

- Original 8088 / IBM PC XT compatibility, genuine DOS 3.3, 640 KiB guest memory and the 6502/6510 assembly interpreter.
- C64 Ultimate, documented PAL / Manual64 configuration, at least 4 MiB REU. Ultimate DOS/UCI is required for installation and normal file access.
- 40/80-column text, keyboard/cursor/navigation, and the existing supported CGA modes 4/5/6 with documented display compromises.
- Raw floppy images loaded into REU, independent A and B controls, and cached 2 or 20 MiB C images. SETUP creates C directly; users need no large blank hard-drive download or dummy launch D81.
- A self-contained emulator release with SETUP, CONFIG, matching runtime/launcher assets, checksums and a concise guide. Users supply DOS and application files separately. A development computer, REST service and host build tools are not runtime dependencies.

## Installation and everyday use

Copy the release and separately obtained DOS images into a folder. Run SETUP, browse to the three images, choose the destination and C-drive size, and let native code prepare A/B/C and copy the DOS files. Launch the generated START to reach DOS.

CONFIG must clearly show current and new settings, preserve existing media, and create a replacement launcher. After moving an installation, it must ask before rebasing image paths below the old home; external/shared paths stay unchanged. Use the newly generated START. Supported startup options live in a documented same-folder INI, read on each launch.

In the native disk controls, users must see which drive and image they are changing, whether it is writable and whether it needs saving. Changing a modified disk offers Save, Discard or Cancel. Incoming-image failure retains the mounted disk. Successful saves name their destination and survive a fresh launch. Floppy operations preserve C and its file/cache state. Finish reports safe-to-restart only after a known successful flush and close.

Errors must name the file and operation, preserve the first cause, distinguish partial outputs from success, and explain the next safe action. Existing files are not silently overwritten. Unknown file ownership must block unsafe continuation. V1 makes no unsupported atomic-write or power-loss-recovery promise.

## Release gates

| Gate | Required final-release proof |
|---|---|
| V1-01 Install | Actual SETUP → generated START → genuine DOS on the Ultimate, using separately supplied originals. Native preparation of independent A/B and 2/20 MiB C; originals unchanged and complete output/FAT inspection. |
| V1-02 Configure | Real 40/80 launches, same-folder INI defaults/errors, paths with spaces, moved-folder confirmation and launcher regeneration, preserved external/shared media. Advertise only implemented options. |
| V1-03 Change floppies | Both BIOS drives and all three rotating REU arenas; insert/change/eject, readonly state, DOS disk-change revalidation and retained old mount after a failed incoming image. |
| V1-04 Save floppies | Save/Save As and Save/Discard/Cancel while C is mounted; complete close/reopen/all-byte/EOF verification, stable drive/content generation, durable path/CFG update, fresh-launch persistence and failure that keeps the working image authoritative. |
| V1-05 Trust C | File creation/copy/deletion, cache eviction and page boundaries, offsets above 16 MiB and the final sector; CHKDSK plus independent FAT/payload checks, known close and fresh launch after reset. |
| V1-06 DOS tools | Resolve the applicable matrix in TESTING.md, including directory/file commands, batch/pipes/MORE, MODE, CHKDSK, DEBUG and disposable-image FORMAT/SYS/media workflows. Conditional/excluded utilities remain explicit. |
| V1-07 Turbo Pascal | Complete original IDE edit/save/compile-to-disk/IDE-run/DOS-run/Finish/restart/reopen workflow below, on the final build in Peddle and on the Ultimate. |
| V1-08 Display/input | Physical 40/80 captures and human readability/keyboard acceptance, including modifiers/function keys, navigation and scrolling. Supported CGA pixel references and physical test cards. |
| V1-09 Recover/finish | Cancellation, failed/short I/O, failed CLOSE, full disk, invalid images/config and filename collisions; honest partial-output reporting and no unsafe resume after uncertain ownership. |
| V1-10 Deliver | One matched downloadable package, hashes and guide covering install, adding applications/files, image swapping/saving, finish/restart, troubleshooting and visible limits. No development scratch paths or vendor media in the release. |

Release with no known reproducible data-loss or blocking installer/media/Turbo Pascal defect in the supported workflows, and a completed human install/use checklist. Correctness fixes found by these tests remain V1 work even when they involve CPU, BIOS or timing. All ten gates remain open until their final-release evidence is checked.

The optional VICE/D81/IEC development lane retains its separately tested scope. It does not substitute for Ultimate DOS persistence or physical acceptance.

## Turbo Pascal acceptance scenario

Use the selected original real-mode Turbo Pascal 7.01 installation on a disposable 20 MiB C drive. The complete DOS/GW-BASIC/TP collection exceeds the separate minimal-DOS 2 MiB profile.

1. Boot through installed START. Confirm VER and A/B/C listings; create a work directory on C.
2. Open TURBO.EXE in 80 columns. Create/edit V1CHECK.PAS using real menus, including a correction and cursor/navigation operation.
3. Save source and compile an EXE **to disk**. Run it inside the IDE, inspect output, return to the editor and exit to DOS.
4. TYPE the source/output and run the EXE from DOS. Copy/save through A and B while C remains mounted, then use C again.
5. Finish safely, reset and relaunch START. Reopen the saved source in the IDE, run the EXE and verify its output.
6. Independently inspect the complete saved image: expected source/EXE/output, legitimate IDE support-file changes, preserved original files, valid FAT chains and free-space accounting. Retain screens, commands and exact release identities. Record automated XT injection separately from physical human input.

```pascal
program V1Check;
var F: Text;
begin
  Assign(F, 'V1TEST.TXT');
  Rewrite(F);
  Writeln(F, 'C64U DOS V1');
  Close(F);
  Writeln('Saved V1TEST.TXT');
end.
```

## Current evidence and remaining work

The public twelve-file development candidate builds coherently and has model evidence for actual SETUP → CONFIG in both column modes → generated START → DOS → media controls/Finish. The same final runtime passes the full original Turbo Pascal IDE/save/disk-EXE/run/fresh-launch model workflow. These are valuable scoped results; final matched-candidate and Ultimate/human acceptance remain required. [Functional review](../agentworking/evidence/v1-current-functional-acceptance-root-20261017.json), [DOS commands/CHKDSK](../agentworking/evidence/v1-dos-batch-root-review-20261017.json), [candidate guide](V1_CANDIDATE.md).

The current source build includes moved-folder confirmation and complete file-error screens. The final matched installer now passes actual SETUP → unchanged generated START → genuine DOS → native Finish in the model. [Relocation and diagnostics](../agentworking/evidence/v1-config-relocation-diagnostics-root-review-20261017.json), [SETUP errors](../agentworking/evidence/native-installer-all-errors-root-review-20261017.json), [final installer proof](../agentworking/evidence/native-installer-final-positive-root-review-20261017.json).

The integrated original-8088 trap correctness fix passes 18 focused and 507 base Zig/Peddle tests, including the pinned 5,701-case CPU corpus. Its disk-menu/FORMAT runtime now passes genuine DOS DEBUG tracing, breakpoints, native Finish and fresh-launch persistence in the model. This is required correctness, not renewed performance tuning. [CPU proof](../agentworking/evidence/8088-trap-root-20261017.json), [DEBUG persistence](../agentworking/evidence/v1-debug-trap-root-review-20261017.json).

The public source-built twelve-file package matches the reviewed candidate byte for byte and passes 25 packaging controls. It remains a development candidate. [Package review](../agentworking/evidence/v1-final-public-promotion-root-20261017.json).

The final CONFIG passes nine native and two Zig checks using actual SETUP-produced media. Original Turbo Pascal passes edit/save/compile-to-disk/IDE-run/DOS-run, native Finish, fresh 40-column execution and fresh 80-column source reopening on the final runtime; a native diagnostic then reads back the entire 20 MiB image. These model tests bypass physical keyboard input. [CONFIG proof](../agentworking/evidence/v1-current-config-root-20261017.json), [final Turbo Pascal proof](../agentworking/evidence/v1-turbo-final-root-review-20261017.json).

The file/text utility lane also proves genuine XCOPY, FC, REPLACE, SORT, FIND, COMP, TREE, LABEL and VOL outputs, plus EDLIN editing and fresh-launch persistence. A real LABEL result exposed a host inspection bug; its narrow repair has eleven focused tests and retains duplicate-file and malformed-label rejection. [Utility and parser review](../agentworking/evidence/v1-utilities-parser-root-review-20261017.json).

Genuine FORMAT B:, DISKCOPY A:B and DISKCOMP also pass on the current runtime, followed by native Save As, C-drive use, Finish and a fresh launch of the saved B image. All 720 sectors and 37 files match the source. This covers two-drive operation; same-drive swaps and physical persistence remain separate. [Disk-copy review](../agentworking/evidence/v1-diskcopy-root-review-20261017.json).

A separate restart-history test now preserves the complete set of active files, saved images and backup/journal archives across a fresh machine. A second native save allocates version 2 and leaves every version-1 artifact intact. This tests a clean mounted B image; dirty guest edits and physical behavior retain their separate acceptance requirements. [Restart-history proof](../agentworking/evidence/v1-save-history-root-review-20261017.json).

The current development source accepts FDISK's speaker writes silently, handles ANSI.SYS's bounded text clear, and restores finalized interrupt vectors through guest ROM instructions on a warm reset. The newly source-built package1506210a reproduces the reviewed matching assets and passes all518 base tests plus25 packaging and15 native-media builder controls. Genuine FDISK partition/restart/FORMAT/SYS/COPY/persistence and the full Turbo Pascal workflow have passed in the model; their sealed reviews preserve source/media identities and first failures. [FDISK workflow](../agentworking/evidence/v1-reset-fdisk-root-20261017.json), [Turbo Pascal workflow](../agentworking/evidence/v1-reset-turbo-root-20261017.json). Final Ultimate and human release gates remain open. [Current public build](../agentworking/evidence/v1-reset-public-promotion-root-20261017.json).

The final same-drive DISKCOPY A:A → native Insert blank → Save As → C use → Finish → fresh launch workflow now passes the model with all720sectors and original media checked. Its retained host-input/oracle failures are qualified. [Same-drive proof](../agentworking/evidence/v1-same-drive-final-root-20261017.json).

Actual .NET-driven native SETUP now creates2MiB C/all58 original DOS payloads, bootable A, separate empty B and the folder-aware START on the Ultimate. Generated START cold readback/bootstrap and continued genuineDOS VER/DIR C/MODE40/80 pass atPAL/Manual64.32 complete cursor-aware guest/native RAM display comparisons pass. This is partial physical install/display evidence;20MiB installer, physical CONFIG/media/Turbo/persistence/human gates remain open. [Current aggregate](../agentworking/evidence/dotnet-native-dos-root-20261017.json).

Next: complete physical CONFIG/media/Turbo Pascal/restart and human checks. All agents finished; main thread owns remaining work. The Ultimate remains at80-column DOS C> with native C backing channel open and no host worker. Native Finish/proven closure precedes any reset or baseline restoration. [ACTIVE state](../agentworking/ACTIVE_HARDWARE_SESSION.json).

Historical scope notes and superseded progress snapshots are preserved in [the endpoint history](../agentworking/research/v1-endpoint-history-20261017.md). Detailed continuity remains in [STATUS](../agentworking/STATUS.md) and [NEXT_SLICE](../agentworking/NEXT_SLICE.md). Historical speed measurements remain workload-specific; V1 does not imply XT speed parity.

## Physical runtime follow-up — 2026-10-17

Original Turbo7.01 now passes real IDE edit/backspace/save/DestinationDisk/compile/run, DOS execution and a cold restart with40-column source/EXE use and80-column source reopening. The actual native CLOSE/full20MiB readback preserves302 baseline payloads plus exactly the source66B/EXE2208B/output17B; all three are byte-for-byte equal to independent Peddle results.46 actual VIC captures pass complete native memory/cursor/pixel checks. [Evidence](../agentworking/evidence/physical-screenshot-campaign-root-20261017.json), [screenshots](screenshots/physical-20261017/README.md).

This is scoped runtime evidence using host-prepared CFG/START and earlier native-generated A/B. It does not close V1-07's actual native UI Finish or final-release composition requirements. Native20MiB SETUP still fails WRITE_NEW/UCI03 after65536 produced bytes; preserve its partial output and investigate the measured path. CONFIG/media/human acceptance and all final release gates remain open. The machine is left RUNNING at80-column C> with native C open; no reset before proven closure.
