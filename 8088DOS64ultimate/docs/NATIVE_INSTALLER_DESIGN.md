# Native Ultimate installer and folder launcher — research proposal

User direction2026-10-16: no dummy launcher D81; require Ultimate DOS/UCI, use a native C setup program with REU, create images on the Ultimate, and never run installation copying through the8088 emulator. Users supply the three supported DOS floppy images themselves; do not bundle DOS images or binaries. A verified archive.org source link remains a packaging requirement. This document is research/design, not an implemented installer or physical benchmark.

## What exists today

Current complete C is a fully allocated20,971,520-byte raw image (20MiB/approximately20.97decimalMB). The alternative supported profile is2,097,152bytes. There is no sparse/compressed/container mapping in the current HD backend: raw sectorLBA maps to512*LBA. The complete fixture has13,977,600free DOSbytes, but those free clusters need not contain zeros: the builder deleted the CROSS16 test allocation without clearing old payload bytes. Both measured raw files occupy their full logical size on the current host. See agentworking/research/native-installer-20261016/CURRENT_IMAGES.json.

For20MiB, geometry640/4/16, partition startsLBA16; twoFAT16 copies each20,480bytes, root512entries/16KiB, clusters2048bytes/10,207total. MBRgap+allfilesystemmetadata occupies66,048bytes before data. These structures can be generated from constants and allocation plans, with no large blank image/template shipped. The three360KiB source images total1,105,920bytes, fitting comfortably in a4MiB setup session alongside metadata and transfer buffers. See CURRENT_GEOMETRY.json and the existing independent dos_disk_inspect.py oracle.

## Recommended disk builder

1. Self-contained SETUP browses to home, validates prerequisites and the supported source image contents/geometry, and plans new owned output names. It must not need an external overlay before discovering home.
2. Read source floppies through Ultimate DOS into REU. Derive working A from the user's actual boot floppy, preserving its bootstrap/system-file placement. Create independent B from a selected source or a native blank FAT12 data floppy. No D81 or emptyDOSfloppy template is required. Initially support the tested360KiB profile. Boot-A/data-onlyC can omit redundantrootIO.SYS/MSDOS.SYS/COMMAND.COM copies: nativeFAT research plans118files and176,128free bytes in2MiB, versus90,112bytes with those3extra rootcopies; the fullTP collection requires20MiB.
3. Enumerate selected source files and optional loose application directories; validate8.3 names/duplicates and capacity, assign clusters and build both FATs/directories in REU. Archive all original DOS files under separate DISK1..3 trees; preserve deterministic convenience-copy policy.
4. Create C as a fresh raw file with the supported2/20MiB geometry. Plan output before writing, then emit MBR/BPB/FAT/root, allocated file payload+slack, and zero runs sequentially. This avoids a full zero-fill followed by rewriting every imported byte. First version boots from A and treats C as a data volume; C bootability/system placement is a separate explicit extension.
5. Use random seek for subsequent metadata/extent updates and later imports. Firmware targets1/2 have independent file state and can support source/destination streaming, but the existing DOS64 FILES API has one serialized open owner: a nativeC setup needs a separate reviewed two-context adapter for this. Preloading the threefloppies in REU avoids that requirement for initialDOS installation. The20MiB HD never needs to reside wholly in REU.
6. Close/reopen, require exact length and transfer counts, verify filesystem ownership and written bytes, then commit configuration/launcher last. Preserve originals and failed partial outputs; never reinterpret incomplete installation as ready.

The Python Populate implementation is a useful oracle/reference but currently rejects existing subdirectories in an input base. It is not already a general importer into a populated C. A native importer for later application additions needs its own validated existing-tree parser and explicit replacement policy.

## Bulk creation, quick allocation, and sparse files

Prefer DOS target01/02 explicit OPEN, SAVE_REU22 and LOAD_REU21, with caller-owned capacity and exact-count checks. The pinned DOS implementation passes large direct REU buffers to File::write/read. At32KiB per command,20MiB needs640data-write commands instead of81,920split256writes:128times fewer commands, not a measured128times speedup. Fill a zero buffer once for long zero runs; gather metadata/file payload runs into a transfer buffer. Reopen/readback can use another bounded REU buffer. See pinned dos.cc and ReadyOS UZIP's explicit transferred-count parser; do not substitute the unrelated control-target preload commands.

The public API assumes a16MiB cap and does not enforce the configured4MiB capacity. Every address/length must be constrained to a proven4MiB-owned arena, and the fastpath needs physical4MiB qualification. CRC/compare CPU cost, firmware storage speed and media fragmentation remain unmeasured for this installer.

Seeking past EOF is not sparse, zero-filled storage: FatFs expands its cluster allocation with undefined gap contents. A quick-format raw file could legally initialize all metadata and allocated payload/slack while leaving free DOS clusters unspecified, but that is not a deterministic zeroed image. Recommend actual bulk zero initialization for the first predictable release. A custom sparse container could grow only with written blocks, but requires new emulator address translation, allocation/recovery, tools and raw export. It is not necessary to eliminate a large download.

[Ultimate DOS API](https://1541u-documentation.readthedocs.io/en/master/uci/ultimate_dos_target.html), [pinned DOS source](https://github.com/GideonZ/1541ultimate/blob/830665cd9b41bc34b868f5c1a1179c5baa4989af/software/filemanager/dos.cc), [FatFs seek semantics](https://elm-chan.org/fsw/ff/doc/lseek.html). Read source-version and installed-binary qualifications in the firmware research handoff before implementation.

## Persistent launcher and volatile handoff

SETUP creates a small START.PRG containing the absolute installation home plus configuration schema/build compatibility information. DOS64.CFG in that home contains editable drive filenames/options. Moving the folder requires rerunning SETUP to regenerate START; there is no assumption that Ultimate exposes the launching program's path.

START reads CFG through Ultimate DOS, validates paths/media and the mainPRG header/size/compatibility, writes a checked magic/version/length/checksum handoff to a reserved REU record, loads the emulator payload to separate REU staging, closes its file, and executes a safe DMA trampoline outside the overwritten payload. The emulator consumes the record before initialization can reuse memory. START invalidates the previous ready marker before loading and publishes ready last after full record validation. REU is volatile; START's embedded home is the persistent bootstrap anchor. Startup must reject stale/incompatible/corrupt records, preserve the reserved region, and consume one-shot validity explicitly.

Candidate layout only (not yet reserved): handoff3FF000..3FFFFF, reserve the complete3E0000..3EFFFF staging bank (payload3E0000..3EAFFE for current45,055bytes). Current PRG is45,057bytes including0801loadheader, payload loads0801..B7FF. A low-RAM0200 or other proven nonoverlapping trampoline can perform final DMA, but bank/IRQ/NMI/stack setup and native entry must be tested. No C call frame may survive transfer of control.

Two implementation routes: patch the staged release-specific existing D64N/D64H cold configuration after validating a build descriptor, or add a small cold handoff reader/new entry before existing configuration validation. The latter gives a cleaner stable contract. Reject joined media paths exceeding the current128-byte native envelopes, regardless of the larger browser buffer. Check the full staged release CRC before permitted envelope edits and configured CRC afterward; validate final DMA identity. The current native ENTRY changes banking to37 before CIA takeover, so a35 trampoline and SEI alone do not establish NMI safety; inject NMI/RESTORE across DMA/entry in tests. Both need actual startup and independentB integration; existing configurable A/C blocks reduce scope but do not make the proposed launcher implemented. Home enables SETUP overlays only after discovery; emulator overlays are currently embedded in its45KiB package.

## Product and verification work

- NativeC SETUP may reuse focused ReadyOS UI/UCI/UZIP code and assembly DMA gateways; main emulator remains6502assembly. Measure the setup linker map before requiring overlays. Setup has a different memory lifetime from the emulator and can use REU for FATs, source images, plans and buffers.
- Implement actual independent B startup/BIOS/save; a reservedREUslot alone does not establish B support.
- Product configuration validates user media geometry/structure and declared identities, while development purpose-specific fixture allowlists stay strict and separate. Legitimate saved A/B images need refreshed CRC/configuration or explicit SETUP revalidation; do not permanently hardcode pristine fixture checksums in a user launcher.
- Peddle tests run assembledC/assembly file builder and loader with mockedUCI/REU; host FAT/sector/CRC oracles remain independent. Include partial transfers, disk full, final-byte/64KiB/16MiB boundaries, malformed paths/records, stalehandshake, overwrite refusal and interrupted commits.
- First physical experiment: owned32KiB/128KiB/2MiB directSAVE_REU+LOAD_REU with independent whole-file retrieval and restoration, including configured4MiB. Then20MiB creation/import, exactoriginalpreservation, reset and START-only boot, real A/B distinction, DOSDIR/CHKDSK/application use, normalclose/persistence, and moved-folder recovery.

Installation timing is unmeasured. Write20MiB+readback20MiB is40MiB I/O: at256KiB/s160seconds;1MiB/s40seconds;4MiB/s10seconds, plus metadata/import/verification/UI costs. Those are conditional arithmetic, not measured Ultimate speeds. Previous5–15minute estimate described the conservative small-WRITE path, not this proposed bulkDMA design.


## Research handoffs

- [Firmware findings](../agentworking/research/native-installer-firmware-20261016/HANDOFF.md), manifest4b5db009: source-version comparison, seek/allocation behavior, DOS21/22 directREU path, configured-capacity limits and physicalprobe checklist.
- [Bootstrap findings](../agentworking/research/native-installer-bootstrap-20261016/BOOTSTRAP.md), manifestbd9cd7ca: exact staging/anchor fit, self-contained firststage, UZIP versus older browser bounds, CRC/count checks and CPUhandoff tests.
- [Native FAT research](../agentworking/research/native-installer-fat-20261016/README.md), actualprofile/metadata/sourcecapacity analysis and testplan.

No production code, media, firmware or hardware state changed during this research. No installer speed is measured.
