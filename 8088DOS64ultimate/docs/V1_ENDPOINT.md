# V1 endpoint: install, use and keep your work

User direction, 2026-10-17: make the installer, configuration, floppy and hard-drive experience solid; use Turbo Pascal as a major acceptance test. Further performance improvements move to after V1. This release checkpoint takes priority over the earlier optimization milestone. The full project plan remains a backlog; deferred work is not reported as completed.

V1 is a release a user can copy onto a C64 Ultimate, install using their own DOS images, launch from a saved home folder, use interactively, and restart with their saved files intact. It uses genuine DOS 3.3, the assembly interpreter, 640 KiB guest memory, a 4 MiB minimum REU and the documented PAL/Manual64 configuration. Runtime operation uses Ultimate DOS/UCI; a development computer or REST connection is not an end-user dependency.

## What using V1 should feel like

Copy the release and separately obtained DOS images into a folder. Run SETUP, browse to the images and choose a C-drive size; SETUP prepares the disks and launcher directly through Ultimate DOS. Launch START to reach DOS. Use CONFIG to make a new configuration while preserving existing media; after moving the installation, regenerate its folder-aware launcher. Edit the documented same-folder INI for supported startup options.

During emulation, open the native disk controls to select A or B, see the current image and whether it needs saving, and insert/eject/save without guessing which drive will change. A modified disk offers Save, Discard or Cancel. A successful save names the destination and survives a fresh launch. C stays usable across these operations. Finish through an explicit flush/close action that reports when restarting is safe. Progress and errors must identify the file/operation and available next action; an incomplete operation must never look like success. Exact menu keys and captions will be documented from the implemented UI.

## Required release gates

| ID | A user must be able to… | Evidence needed on the final matched release |
| --- | --- | --- |
| V1-01 Install | Browse to the installation folder and three supplied DOS images; prepare independent A/B and a 2 or 20 MiB C image natively, with DOS files copied to C. | Actual SETUP → generated START → genuine DOS on the Ultimate. Source originals unchanged; independent image/FAT checks. No emulated FORMAT/COPY prerequisite, dummy launch D81 or large blank-HD download. |
| V1-02 Configure and launch | Select supported settings with clear current/new choices; launch using the saved absolute home regardless of the browser's current folder; edit same-home INI and see the change next launch. | Real 40/80 launches, missing-file defaults, malformed-file diagnostics, paths with spaces, relocated/reconfigured installation and preserved shared media. Only implemented options are advertised. |
| V1-03 Use A and B | See separate mounted images, paths, writable/readonly and modified/saved/uncertain status; insert/change/eject either disk through the native UI. | Both BIOS drives and all three rotating REU arenas tested. Incoming-image failure retains the old mounted disk. Actual DOS disk-change/revalidation behavior tested. |
| V1-04 Save floppies | Save or Save As while C is mounted; choose Save/Discard/Cancel before replacing a modified disk; restart without losing an acknowledged save. | Complete close/reopen/all-byte/EOF verification; frozen drive/mount/content generation; durable backing-path and CFG CRC update. Failure keeps the working image authoritative and does not silently mark it clean. Readonly originals remain unchanged. |
| V1-05 Trust C | Use a 2 or 20 MiB cached raw HD, add/copy/delete files, run applications and finish a session safely. | Cache eviction, sector/page boundaries, offsets above 16 MiB and final sector; DOS CHKDSK and independent FAT/payload checks; known flush/close and fresh launch after reset. Floppy operations preserve C's handle, position and cache. |
| V1-06 Run DOS tools | Use the applicable supplied DOS commands and utilities, including real two-drive/media workflows. | Resolve the required applicable matrix in TESTING.md, including VER/DIR/TYPE, file/directory operations, pipes/MORE, MODE, CHKDSK and media tools on disposable images. Staged, conditional and excluded utilities retain explicit status. |
| V1-07 Use Turbo Pascal | Launch the original real-mode IDE, edit/save source, compile to disk, run, return to DOS and recover the work after reset. | The complete workflow below in Peddle and on the Ultimate, plus actual keyboard/readability checks. Command-line compiler success alone does not close this gate. |
| V1-08 Read and control it | Use 40/80-column DOS text and an 80-column editor with working cursor, navigation, modifier/function keys and scrolling. | Physical screen captures and human keyboard/readability acceptance. Existing supported CGA modes 4/5/6 retain reference pixel checks and physical test-card checks. Known color/palette compromises are documented. |
| V1-09 Recover and finish | Cancel setup/media work, understand errors, keep existing files on collisions, and finish with an explicit safe-to-restart state. | Failed/short I/O, failed CLOSE, full disk, invalid images/config and cancellation tests. Unknown ownership blocks unsafe resume. Distinguish partial outputs from completion; no unsupported atomic/power-loss recovery claim. |
| V1-10 Install the release | Follow one concise guide with a coherent downloadable build, rather than reconstructing a development fixture. | One matched artifact inventory and hashes; SETUP/CONFIG/launcher/emulator assets checked together; no scratch paths or host developer tools required. Include installation, adding files/apps, image swapping, saving, exit/restart, troubleshooting and known limits. |

The supported Ultimate DOS path is the V1 end-user installation path. The optional VICE/D81/IEC development lane keeps its explicitly tested scope; standalone import is not advertised as complete runtime IEC persistence.

## Turbo Pascal acceptance scenario

Use the selected original real-mode Turbo Pascal 7.01 installation on a disposable 20 MiB C drive. The small 2 MiB profile remains a separate minimal-DOS test; the complete DOS/GW-BASIC/TP collection exceeds it. Vendor files and DOS images are supplied separately from the emulator release.

1. Boot the final folder-aware START into genuine DOS. Confirm VER and A/B/C listings, then create a working directory on C.
2. Start TURBO.EXE in 80 columns. Use the real menus and keyboard mapping to create or edit V1CHECK.PAS, including at least one correction and cursor/navigation operation.
3. Save the source to C and compile an EXE **to disk**. Run it in the IDE, view its output, return to the editor and exit to DOS.
4. TYPE the saved source and generated text output; run the EXE from DOS. Perform an A/B copy-and-save operation while C remains mounted, then use C again.
5. Complete the supported flush/close workflow, reset, and launch again through the installed START. Reopen the saved source in Turbo Pascal, run the EXE and verify the text output.
6. Independently inspect the saved image: expected source/EXE/output and legitimate IDE support-file changes, intact original files, valid FAT chains and free-space accounting. Retain screens, commands, image identities and the exact release hashes.

A suitable small program is:

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

This test exercises CPU, BIOS, keyboard, text/cursor, memory paging, DOS file creation, HD writes and restart persistence together. Physical keyboard input and automated XT-key injection are recorded separately.

## Evidence at scope definition

- Public main666/b9 and matched START79bb/INOeebb are model-qualified. Public CONFIG508d passes four actual SYS/CIA/firmware groups plus two Zig assertions; its actual generated files boot genuine DOS in both modes. [CONFIG evidence](../agentworking/evidence/native-config-public-root-20261017.json), [generated DOS consumers](../agentworking/evidence/native-config-generated-dos-root-20261017.json).
- Native SETUP fresh-install and conflict handling have model evidence; the final current installer/CONFIG/START combination still needs physical qualification. [SETUP evidence](../agentworking/evidence/native-installer-home-preflight-public-root-20261017.json).
- Historical physical4589/a827 ran original TPC, compiled/ran HELLO and verified HD backing writes. Historical original-TURBO model4cc opened an unchanged source and compiled/ran it in memory. Neither proves edited IDE source, disk compilation and fresh-launch persistence on the V1 release. [Physical TPC evidence](../agentworking/evidence/c64u-ac-development-20261016.json), [IDE model evidence](../agentworking/evidence/cga-editor-root-20261016.json).
- Current public SAVE still rejects online C and lacks the end-user disk menu/durable CFG transaction. The new private C-online Save As checkpoint is under test; it is not V1 media completion.
- Following a transport failure before any REU write, a separate documented C64-only reset now passes physical BASIC readiness, advancing clock, resume and unchanged settings/media checks. The Ultimate remains reserved for the next qualification; complete current REU equality and original application restoration are not established. [Cold-state closure](../agentworking/evidence/c64u-coldstate-physical-root-20261017.json), [retained first failure](../agentworking/evidence/c64u-40fe-recovery-failure-root-20261017.json).

Progress after scope definition: the optional public A/B SaveAs+CRC profile now has27 actual6510/Peddle tests while default release bytes remain unchanged. A private native menu/broker composition runs with guarded paused/cache0 ownership, but loader/hotkey/durableSave/CFG/Finish integration is unfinished. Original Turbo now passes edited-source/diskEXE/IDE-and-DOS-run/nativefull20MiBverification/fresh40DOSrecovery in the model; independent fresh80 IDE source reopening now also passes; physical acceptance remains separate. [Media composition](../agentworking/evidence/native-media-panel-composition-root-20261017.json), [Turbo persistence](../agentworking/evidence/v1-turbo-persistence-root-20261017.json), [fresh IDE reopen](../agentworking/evidence/v1-turbo-reopen-root-20261017.json).

All ten release gates remain open until their final-release evidence is checked. Earlier component and hardware successes retain their exact scope; a green model test is not physical acceptance.

Release only with no known reproducible data-loss or blocking installer/media/Turbo Pascal defect in these supported workflows, and with a completed human install/use checklist. Correctness fixes discovered by these tests stay in V1 even when they concern CPU, BIOS or timing. Remaining limitations must be visible in the release guide; they cannot silently waive a required gate.

## Work order and deferred work

In parallel: close the device's cold state; complete C-online floppy ownership and durable A/B/CFG transactions; execute the edited Turbo Pascal workflow on the current interpreter. Then integrate the native media UI and safe session finish, qualify installer/config usability and the matched release package, and run the final physical install/media/Turbo Pascal/restart matrix. Human testing follows a concrete working build and a short checklist.

No further interpreter speed tuning, compiled-code activation or XT percentage target blocks V1. Keep the existing correct interpreter and its timing/IRQ/REP behavior. Archive private performance candidates without promotion; report current speed honestly. The earlier 50% minimum/85% stretch objectives belong to post-V1 work. No new performance result is inferred from passing Turbo Pascal.
