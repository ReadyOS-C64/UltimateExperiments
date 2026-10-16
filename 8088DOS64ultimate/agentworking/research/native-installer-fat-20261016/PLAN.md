# Native installer architecture and staged scope

## Ownership and REU

SETUP runs before the guest starts and exclusively owns native RAM, REU and UCI. It cannot execute inside a running DOS session or silently borrow warm cache/overlay/uncertain-write state. Finish or preserve first failure, close all known handles, then cold-launch the emulator, which reloads every guest/overlay/disk owner. Development hardware retains/restores original machine/REU through the established outer harness.

Current runtime4MiB layout:000000–0FFFFF guest physical arena;100000–17FFFF A slot (loaded360KiB currentlyends159FFF);180000–1FFFFF reserved second floppy slot;200000–2FFFFF HD extent cache;340000–3437FF seven immutable startup slots;350000–3501FF uncertain HD sector;352000–3521FF guest handoff. Other slices are reserved, not automatically free. The production frame cache stays32×512B at native8000–BFFF. Existing HDBIOS has only7B free, so core B/config additions need a real layout solution, not pooled nominal slack.

Proposed installer-only REU map, all below4MiB:

| Range | Exclusive SETUP purpose |
|---|---|
|000000–05FFFF|source disk1 slot,360KiB +guard|
|060000–0BFFFF|source disk2 slot|
|0C0000–11FFFF|source disk3 slot|
|120000–17FFFF|optional derived B,360KiB +guard|
|180000–1FFFFF|derived A,360KiB +guard|
|200000–2FFFFF|1MiB output slab, emitted as bounded32KiB chunks|
|300000–33FFFF|FAT/root/directory/file-plan/validation metadata256KiB|
|340000–3FFFFF|unused/reserved in first installer; no alias with live emulator ownership|

This is a proposed lifetime layout, not an assembled fit. Metadata includes one20KiB FAT (same bytes emitted twice),16KiB fixed root, all generated directories, source root/FAT validation, and bounded descriptors. First scope58DOS inputs/118outputs is small; larger optional trees need explicit file/directory/depth/descriptor limits and measured C struct/stack sizes. Native RAM keeps small sector/UCI buffers; REU adapters split REC transfers before64KiB boundaries and retain00/01/P/IRQ ownership. Keep generated code out of staging/REU aliases; never call ROM while RAM+I/O mapping hides its code.

## Native format/populate algorithm

1. Read source identity/length, load complete three raw360KiB images into disjoint owned slots, validate two FATs, BPB/geometry, every chain/directory, cross-links/cycles/bad clusters, lengths and source checksums. Initially accept the tested MS-DOS3.3/system-pair/360KiB family; IBM OEM names, other geometries, FAT32/LFN/extended partitions require deliberate later support. No silent skip of an unknown boot source.
2. Create a fresh owned output directory and new files (no truncate-existing mode). Compute all allocations first. Generate raw profile MBR partition entry, DOS3.x BPB, both FAT images and short-name directory entries. Calculate offsets with explicit32-bit arithmetic. FAT12 odd/even writes preserve neighboring nibbles and may span sector boundaries. Zero unused entries/padding and final free data.
3. Archive every source payload/attributes/write time under DOS\DISK1..3, retain all variants, generate DOS convenience copies with a recorded resolver. Never copy a source volume-label entry into a subdirectory. Use explicit owned CONFIG/AUTOEXEC and BASIC/game launch text. No arbitrary overwrite or in-place modification of a user disk.
4. Emit C sequentially by slab: metadata regions from the plan, data sectors mapped to source chains/generated text, padding/free sectors as zeros. Because all sources reside in REU, no source/output handle ping-pong is required. Current FILES is a serialized single-open-owner layer even though firmware has target contexts; do not infer concurrent-handle safety.
5. Finish, close, reopen read-only, verify exact byte length+EOF and all output bytes against independent generated expected sector descriptions/checksums. Parse the completed FAT/tree separately; write a closed receipt/config only after every output passes. Failure leaves fresh owned partial files and first error; never present them as installed. No filesystem transaction/power-loss guarantee is inferred from accepted CLOSE.

## A boot versus optional C boot

For initial A, clone the entire user-owned boot floppy in REU and preserve its boot sector, IO/MSDOS payloads, first root entries and original chains. Change owned startup text with FAT allocation that cannot move those system files. Set PATH/C switch only when the configured C image has been verified. Source original CONFIG files remain in C archives. B is a clone of a chosen user disk initially; do not require it to be bootable.

Initial C is a data volume. Its metadata template contains no proprietary loader or system binaries; ordinary DOS mounts it after booting the unchanged user A loader. A fresh non-DOS error bootstrap can mark C boot unsupported. MBR-active does not itself make C bootable. Keep boot_drive00 in the installed runtime configuration.

Optional boot C is a later explicitly verified SYS-equivalent native operation. Microsoft KBQ66530 says DOS3.3 still requires the two system files as first root entries and the first three IO.SYS sectors at the start of data; COMMAND.COM must be copied separately. We can conservatively allocate both system files fully contiguous from cluster2. A Microsoft/IBM OEM pair is not interchangeable; validate the exact family and preserve original bytes. An independently authored8088 MBR/VBR or a separately reviewed derivation from that user's loader must implement geometry/hidden sectors/drive80/load contract. Merely patching the A BPB and copying files is not boot-C acceptance. Existing genuine FORMAT/SYS reference fixtures remain test oracles, never distributed templates. [Microsoft original KB,archived](https://jeffpar.github.io/kbarchive/kb/066/Q66530/).

Do not write a modern extended BPB over DOS3.x loader bytes: our existing sectors use an older layout. The new data-only formatter can author its own complete structure; preserving A means preserving the user's complete original boot sector. Later boot-C needs exact loader-specific analysis.

## Runtime changes for B and custom install paths

Existing D64N already supports an A ASCII path<=127chars plus NUL, expected imageCRC32, target and REU capacity. D64H supports a separate HD path/profile/readonly/boot/slot count; seek offsets are32-bit. First A+C install can configure these cold blocks in an owned copy of the shipped emulator, streaming the base PRG through REU with a version-bound patch descriptor. No executable byte outside the exact configuration fields may change. A future sidecar loader is cleaner but is a new runtime ABI, not present today. Development proof/registration remains purpose-specific; dynamic user media does not widen old hardware allowlists.

B requires: versioned startup descriptor per drive; complete import and CRC/length/EOF/CLOSE to180000; per-drive loaded/geometry/base/status/dirty/path state; BIOS DL01 routing; BDA equipment/floppy count (current410h says one); applicable INT13 reset/status/read/write/verify/parameters semantics; correct boot drive and no accidental third floppy; per-drive SAVE/export and remount/dirty/uncertain ownership. Current disk.s rejects every DL except00, and its importer is hardwired720sectors at100000. TestB cannot pass by relabeling A. Existing HD80 dispatch/async/PIC/guest context must remain intact.

Cold dual-import must finish before bitmap takeover, retaining all7 overlay sources and HDBIOS copy; normal32-frame cache ownership/cadence remains. Additive state/code must actually link within each window or use a separately reviewed cold/overlay redesign. Installed A/B default write policy and save/discard behavior must be explicit and retained; a created image path is not yet persistence support.

## Delivery stages

A. Host-independent generated metadata/allocator reference and known DOS source fixture semantics; no distributed DOS bytes. Native C unit logic compiled on host, then actual cc65 code through Peddle.
B. Standalone native SETUP A+C,360KiB sources and2/20MiB raw profiles, conservative bounded transport then exact-count bulk adapter. Full output verification; genuine DOS boot/DIR/CHKDSK/BASIC/reopen and physical C64U proof.
C. Real dual-floppy runtime/descriptor/SAVE changes with same independent gates; optional user-supplied unpacked app tree/Turbo install. ZIP support only as an explicit new codec/decompression stage.
D. Optional C boot and optional sparse extent container after raw installation is accepted. No UI should suggest these are implemented during A/B stages.
