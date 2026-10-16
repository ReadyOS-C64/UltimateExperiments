# Native SETUP: recommended implementation scope

Research only,2026-10-16. No native installer code, emulator change, guest installation run, hardware/LAN operation or pushed commit was performed. `analyze.py` is a read-only host sizing experiment; it writes research JSON, never a disk image.25 source/image inputs stayed byte-identical. IDE driver review4777 remains a separate outstanding cleanup/capture blocker.

Build a standalone **native C/6510 SETUP.PRG** which reads user-owned DOS3.3 floppies through Ultimate DOS, validates them in REU, clones a boot A, optionally clones B, creates a new raw2MiB or20MiB C directly, and writes the configured emulator/manifest. No emulated DOS COPY/FDISK/FORMAT installation, dummyD81 launcher, bundled DOS file or bundled DOS boot sector is needed. Native C can use installed cc65/cl65V2.18 plus existing ca65 assembly adapters; actual installer linker/code/stack budgets remain unmeasured.

Start with **boot A plus data-only C**. Clone A's user-owned boot sector and system-file allocation unchanged; replace only owned CONFIG/AUTOEXEC in the derived image. Generate C's MBR/BPB/FAT/directory fields from scalar format definitions, with an independently authored nonbooting/error bootstrap if needed. This avoids prematurely implementing SYS/boot-C compatibility. Keep 2/20MiB geometry exactly aligned with current emulator profiles. B requires real startup/BIOS/persistence changes; writing a B file alone does not implement driveB.

## Measured layout and capacity

These are byte/operation counts from the current tools/images, not native elapsed-time benchmarks.

| Property | 2MiB | 20MiB |
|---|---:|---:|
| Raw bytes / sectors |2,097,152 /4,096|20,971,520 /40,960|
| CHS |128/2/16|640/4/16|
| Partition start / sectors / type |16 /4,080 /01h|16 /40,944 /04h|
| Cluster bytes / count |4,096 /505|2,048 /10,207|
| FAT type / one FAT |FAT12 /1,024B|FAT16 /20,480B|
| Two FATs + fixed root + VBR |18,944B|57,856B|
| Plus MBR and prepartition gap |27,136B /53sectors|66,048B /129sectors|
| Initial DOS-only data-C files |118|118|
| DOS-only free bytes |176,128|19,163,136|

The data-C budget retains all58 original file payloads in DOS\DISK1..3, all54 convenient DOS names, GWBASIC/Hangman and native-generated launch/startup text. It excludes redundant root IO.SYS/MSDOS.SYS/COMMAND.COM because boot remains A. Keeping those three root files as well gives121files and90,112B/19,083,264B free. Original volume labels are metadata, not files; retain their raw label/source identity in the installer receipt instead of manufacturing invalid subdirectory volume labels.

All three source images total1,105,920B. The58 file payloads total801,588B; archives plus54 convenient copies total1,525,308B before games/root support/cluster padding. Identical duplicate system files and differing CONFIG.SYS variants are all preserved in the archives; lowest numbered input wins convenience resolution, recorded explicitly.

The accepted full TP collection has360files/6,495,364B payload; original TP tree alone has233files/4,809,137B. It requires20MiB. Native ZIP installation is a separate scope: initially accept a verified unpacked short-name tree supplied by the user; do not silently bundle vendor files or promise decompression already exists.

## Write-pass budget

Allocate FAT/chains/directories **before writing C**, then emit metadata, payload, padding and zero free space in ascending raw offset, once. A metadata-only template is field definitions and generated structures, not a20MiB image. In particular, never presume a writable seek gap contains zeros.

| Complete C pass |2MiB|20MiB|
|---|---:|---:|
| Conservative WRITE256 calls |8,192|81,920|
| Reviewed future32KiB SAVE_REU chunks |64|640|
| Full reopen verification with READ512 |4,096|40,960|
| Or32KiB LOAD_REU verification chunks |64|640|

Bulk counts assume a validated native adapter around firmware21h/22h, exact transferred-count parsing and bank/range/ownership limits; the current DOS64 FILES layer does not expose these operations. Firmware peer research establishes the protocol opportunity, not physical installer speed. A/B each need12×32KiB chunks (last8KiB), or1,440 WRITE256 calls and720 READ512 calls. Loading all three sources needs36bulk chunks or2,160 READ512 calls, plus exact-length/EOF checks.

Avoid zero-C-then-populate. The conservative121-file sizing experiment would require16,026 versus8,192 WRITE256 calls at2MiB, or89,290 versus81,920 at20MiB. One composed pass removes those avoidable rewrite calls. Control messages, open/close/seek, count parsing, CRC/verification and UI costs remain additional; no wall-clock estimate follows from these counts.

See PLAN.md for REU ownership/boot/core changes and TEST_PLAN.md for acceptance gates. OBSERVED_LAYOUTS.json and DOS_ONLY_BUDGET.json hold reproducible numbers; `python3 -B analyze.py` regenerates them from read-only user/project inputs.
