# V1 endpoint: install, use and keep your work

User direction, 2026-10-17: make the installer, configuration, floppy and hard-drive experience solid; use Turbo Pascal as a major acceptance test. Further performance improvements move to after V1. This release checkpoint takes priority over the earlier optimization milestone. The full project plan remains a backlog; deferred work is not reported as completed.

V1 is a release a user can copy onto a C64 Ultimate, install using their own DOS images, launch from a saved home folder, use interactively, and restart with their saved files intact. It uses genuine DOS 3.3, the assembly interpreter, 640 KiB guest memory, a 4 MiB minimum REU and the documented PAL/Manual64 configuration. Runtime operation uses Ultimate DOS/UCI; a development computer or REST connection is not an end-user dependency.

Current checkpoint, 2026-10-17: the public twelve-file candidate builds as one matched package. The model now exercises actual SETUP-created media and configuration through CONFIG in both column modes, generated START, genuine DOS, disk Save/Insert and Finish. The original Turbo Pascal IDE edit/save/disk-compile/run/fresh-launch workflow passes separately on the preceding runtime cohort; it still needs final-candidate and physical acceptance. Full-path error messages, whole-folder relocation, the remaining applicable DOS utilities and final Ultimate/human testing remain open. [Bounded functional evidence](../agentworking/evidence/v1-current-functional-acceptance-root-20261017.json), [candidate guide](V1_CANDIDATE.md).

CONFIG currently creates another launcher sharing the existing media, but rejects an unchanged configuration after the whole installation folder moves. This is a reproduced V1-02 defect, not completed relocation support. The fix must ask before rebasing media below the saved old home to the selected moved folder, preserve external shared paths, recheck the resulting media and publish a new generation without overwriting the original. [Actual native relocation failure and unmoved control](../agentworking/evidence/v1-config-relocation-gap-root-20261017.json).

## What using V1 should feel like

Copy the release and separately obtained DOS images into a folder. Run SETUP, browse to the images and choose a C-drive size; SETUP prepares the disks and launcher directly through Ultimate DOS. Launch START to reach DOS. Use CONFIG to make a new configuration while preserving existing media; after moving the installation, regenerate its folder-aware launcher. Edit the documented same-folder INI for supported startup options.

During emulation, open the native disk controls to select A or B, see the current image and whether it needs saving, and insert/eject/save without guessing which drive will change. A modified disk offers Save, Discard or Cancel. A successful save names the destination and survives a fresh launch. C stays usable across these operations. Exit guest applications to DOS, then use Finish to check completed backing writes and close C before reporting when restarting is safe. Progress and errors must identify the file/operation and available next action; an incomplete operation must never look like success. Exact menu keys and captions will be documented from the implemented UI.

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
5. Complete the supported Finish/close workflow, reset, and launch again through the installed START. Reopen the saved source in Turbo Pascal, run the EXE and verify the text output.
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

Progress after scope definition: the optional public A/B SaveAs+CRC profile has27 actual6510/Peddle tests while default release bytes remain unchanged. The private native hotkey, matched asset loader, menu and Resume now work through genuine DOS with C online in the model. Startup journal validation now runs before normal configuration loading and safely blocks interrupted saves; explicit recovery actions and the complete Save/Swap/Finish workflow remain unfinished. Original Turbo passes edited-source/diskEXE/IDE-and-DOS-run/full20MiB verification/fresh40DOS recovery in the model; independent fresh80 IDE source reopening also passes. Physical acceptance remains separate. [Menu and DOS integration](../agentworking/evidence/native-menu-start-root-20261017.json), [startup recovery gate](../agentworking/evidence/native-start-journal-root-20261017.json). [Media composition](../agentworking/evidence/native-media-panel-composition-root-20261017.json), [Turbo persistence](../agentworking/evidence/v1-turbo-persistence-root-20261017.json), [fresh IDE reopen](../agentworking/evidence/v1-turbo-reopen-root-20261017.json).

All ten release gates remain open until their final-release evidence is checked. Earlier component and hardware successes retain their exact scope; a green model test is not physical acceptance.

Release only with no known reproducible data-loss or blocking installer/media/Turbo Pascal defect in these supported workflows, and with a completed human install/use checklist. Correctness fixes discovered by these tests stay in V1 even when they concern CPU, BIOS or timing. Remaining limitations must be visible in the release guide; they cannot silently waive a required gate.

## Work order and deferred work

In parallel: close the device's cold state; complete C-online floppy ownership and durable A/B/CFG transactions; execute the edited Turbo Pascal workflow on the current interpreter. Then integrate the native media UI and safe session finish, qualify installer/config usability and the matched release package, and run the final physical install/media/Turbo Pascal/restart matrix. Human testing follows a concrete working build and a short checklist.

No further interpreter speed tuning, compiled-code activation or XT percentage target blocks V1. Keep the existing correct interpreter and its timing/IRQ/REP behavior. Archive private performance candidates without promotion; report current speed honestly. The earlier 50% minimum/85% stretch objectives belong to post-V1 work. No new performance result is inferred from passing Turbo Pascal.

The latest device recovery qualification now passes: independent checks of both complete4MiB snapshots match the original backup, one native file restore finishes with its CRC checked and file closed, and original settings/media and responding BASIC are verified. This qualifies the development recovery path; current-product installation and Turbo Pascal acceptance remain open. It began with unchanged original bytes and adopted a historically verified backup file, so it is not a new changed-all-banks recovery test. The earlier31-pair recovery failure remains failed. [Current recovery evidence](../agentworking/evidence/c64u-fast-put-physical-root-20261017.json), [retained earlier failure](../agentworking/evidence/c64u-whole4m-original-failure-root-20261017.json).

The full private Save As controller now passes seven actual native model groups, including both A/B/C-target combinations, phase-file corruption and output collision. Its result is not a released disk workflow: actual CUI orchestration, the final coupled cold assets, remaining media actions, recovery controls and physical acceptance stay open. A reproduced postcommit Resume-capability defect is retained and fixed; native release is now denied on those failures. [Controller evidence](../agentworking/evidence/native-media-action-controller-root-20261017.json).

The actual private disk-menu Save As path now passes9 native model groups and8 independent focused controls, including private intent/cancellation/partial-transfer refusal. This connects the menu to durable saving but remains UNIT-role with synthetic media; repeat-save sequence selection, actual runtime/cold coupling, other media actions/Finish and final physical V1 gates remain open. [Menu save evidence](../agentworking/evidence/native-media-ui-saveas-root-20261017.json).

The subsequent current9 staging attempt failed during its initial readonly snapshot, before staging files or writing REU. Original settings restoration passed; current completeREU/BASIC closure is not inferred from the older accepted recovery. This failure does not change the final-product hardware gates. [Retained attempt](../agentworking/evidence/c64u-current9-staging-failure-root-20261017.json).

Private cold-start recovery now requires confirmation, completes verified saves and freshly rechecks no journal before launch. Root10 unique outcomes and11 independent model checks pass; final native20KiB publishing, runtime coupling and physical acceptance remain separate. [Recovery evidence](../agentworking/evidence/native-cold-recovery-ui-root-20261017.json).


Private runtime Finish now passes8 actual menu/native model groups plus a SaveAs regression with UNIT products absent. It requires final confirmation and a real mounted C, obtains Safe only from known native CLOSE, and permanently blocks guest Resume. Ordinary versioned Save and the20KiB native template publisher pass separate component tests; runtime composition, remaining floppy actions and final Ultimate acceptance stay open. A genuine cold SaveAs integration test exposed an initial binding-order defect; its blocked failure is retained and being repaired. [Finish evidence](../agentworking/evidence/native-runtime-finish-ui-root-20261017.json).


Private Eject/Write Protect now pass12 actual menu/core model groups plus2 Finish regressions. Their explicit session-only policy preserves saved startup media for next launch; Save-first failure prevents Eject, and the other drive remains savable. Genuine cold DOS→SaveAs→Resume→C-read passes separately after correcting initial binding capture. These proofs remain separate from final combined package and physical acceptance; incoming-file/durable Insert is still in progress. [Controls](../agentworking/evidence/native-runtime-controls-root-20261017.json), [cold fix pin review](../agentworking/evidence/native-cold-binding-pin-review-root-20261017.json).

The concrete final-release checklist is now [the V1 usability and release-gap audit](../agentworking/research/v1-release-gap-ux-audit-20261017/AUDIT.md). It keeps all ten gates open, identifies the matched package/Insert/physical Turbo work, and explicitly retains guest FORMAT as required: the current floppy BIOS rejects AH05. Native SETUP's FAT creation does not close that DOS utility gate. No further performance target blocks V1.

Private incoming-image verification now passes24 native groups, and Insert PLAN/cold journal recovery passes15 source-closed native groups, including emptyB/ejectedmedia/CRC0 and refusal controls. These remain component proofs; the final controller, DOS disk revalidation, coherent installer/package and Ultimate/human acceptance are still required. [Insert planning/recovery evidence](../agentworking/evidence/native-insert-plan-journal-root-20261017.json).


The complete runtime Insert composition now passes21 actual model groups, and the normal source-only `make runtime-media` build produces the enabled menu without private dependencies. Root verifies three additional actual CIA smoke groups from the public build. The final matched cold installer/configuration package, genuine DOS workflows, physical Turbo Pascal and human acceptance remain open. A current80-column installer consumer saving refusal is being diagnosed; passing40-column/model component results do not waive it. [Runtime media checkpoint](../agentworking/research/native-runtime-media-checkpoint-20261017).


The combined source-built runtime now includes optional XT floppy FORMAT and corrected media clock handling.27 actual CPU and28 host checks pass; default binaries remain exact. The earlier CONFIG80 Save/Insert failure is resolved in the model by bounded admission and scan-held CIA input, with the first failures retained. Current matched cold/installer packaging, complete20MiB Turbo Pascal persistence and physical/human gates remain open. [Combined runtime evidence](../agentworking/evidence/native-format-media-composition-root-20261017.json).


The source-only matched cold START builder is now public and passes11host groups plus3default-template checks. It emits the eight-file runtime/recovery bundle from verified public sources; the default launcher remains exact. This closes a development build dependency, not any final V1 gate. Current installer composition, complete Turbo/media persistence and actual Ultimate/human acceptance remain separate. [Builder evidence](../agentworking/evidence/native-cold-public-builder-root-20261017.json), [build instructions](../tools/cold/README.md).


The clean public `make test-floppy-format` command now passes12actual-runtime Python and2directZig groups with fresh source-built models. This makes the FORMAT component tests reproducible without vendor media; genuineDOS FORMAT/SYS/boot, saving and finalUltimate acceptance keep their own gates. [Test evidence](../agentworking/evidence/public-format-tests-root-20261017.json).


The current public cold56 SETUP/CONFIG source profile now builds against the matched eight assets; actual BASIC37 startup/error components and checkedmetadata intake pass. Defaults remain byteexact. FullnewSETUP/CONFIG-generatedDOS/media, remainingfilename/CONFIGpublication clarity and finalUltimate/human gates remainopen. [Installer integration evidence](../agentworking/evidence/native-installer-public-integration-root-20261017.json).


A coherent public twelve-file candidate now builds through runtime/cold/SETUP/CONFIG, with21Root host packaging checks and exact intake bytes. Its smallZIP includes installation/media/Finish instructions but no vendor media or configured disks. This is a development delivery checkpoint; finalUltimate/human and remainingerrorUX gates stayopen. [Candidate evidence](../agentworking/evidence/v1-runtime-candidate-public-root-20261017.json), [instructions](V1_CANDIDATE.md).
