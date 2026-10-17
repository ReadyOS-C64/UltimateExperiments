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

The public twelve-file development candidate builds coherently and has model evidence for actual SETUP → CONFIG in both column modes → generated START → DOS → media controls/Finish. A preceding runtime also passes the full original Turbo Pascal IDE/save/disk-EXE/run/fresh-launch model workflow. These are valuable scoped results; final matched-candidate and Ultimate/human acceptance remain required. [Functional review](../agentworking/evidence/v1-current-functional-acceptance-root-20261017.json), [DOS commands/CHKDSK](../agentworking/evidence/v1-dos-batch-root-review-20261017.json), [candidate guide](V1_CANDIDATE.md).

The current source build includes moved-folder confirmation and complete file-error screens. The final matched installer now passes actual SETUP → unchanged generated START → genuine DOS → native Finish in the model. [Relocation and diagnostics](../agentworking/evidence/v1-config-relocation-diagnostics-root-review-20261017.json), [SETUP errors](../agentworking/evidence/native-installer-all-errors-root-review-20261017.json), [final installer proof](../agentworking/evidence/native-installer-final-positive-root-review-20261017.json).

A private original-8088 trap correctness fix passes 18 focused and 507 base Zig/Peddle tests, including the pinned 5,701-case CPU corpus. Its disk-menu/FORMAT runtime now passes genuine DOS DEBUG tracing, breakpoints, native Finish and fresh-launch persistence in the model. This is required correctness, not renewed performance tuning. [CPU proof](../agentworking/evidence/8088-trap-root-20261017.json), [DEBUG persistence](../agentworking/evidence/v1-debug-trap-root-review-20261017.json).

The public source-built twelve-file package matches the reviewed candidate byte for byte and passes 25 packaging controls. It remains a development candidate. [Package review](../agentworking/evidence/v1-final-public-promotion-root-20261017.json).

Next: close the current-runtime Turbo Pascal and remaining DOS utility proofs, then execute the physical install/media/Turbo Pascal/restart matrix and human checklist. The sole hardware worker owns recovery and device state. Older accepted recovery does not close a later failed staging attempt. Current machine state is recorded in [ACTIVE_HARDWARE_SESSION.json](../agentworking/ACTIVE_HARDWARE_SESSION.json).

Historical scope notes and superseded progress snapshots are preserved in [the endpoint history](../agentworking/research/v1-endpoint-history-20261017.md). Detailed continuity remains in [STATUS](../agentworking/STATUS.md) and [NEXT_SLICE](../agentworking/NEXT_SLICE.md). Historical speed measurements remain workload-specific; V1 does not imply XT speed parity.
