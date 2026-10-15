# Sector storage and persistence

## Contracts

PC software sees BIOS disk devices A:/B: and later drive 80h. DOS itself interprets FAT and partitions. Each backend implements bounded byte-range access to a raw image, exact read/write counts, close, and explicit save/export semantics. Device descriptors carry image identity/generation, sector size/count, CHS geometry, read-only flag, backing-file offset, and persistence state.

Use **32-bit file offsets and sector arithmetic** on the host target, implemented as explicit byte operations in assembly. REU addresses remain 24-bit. Do not truncate an HD offset to an REU address; test beyond 0x00FFFFFF. Compute `LBA = ((cylinder * heads) + head) * sectors_per_track + (sector - 1)` with checked bounds. Decode the BIOS cylinder high bits in CL. `offset = LBA * 512` must not overflow before widening.

INT 13h initially needs reset/status/read/write/verify/geometry and the media/format functions actually used by the DOS image. Later HD initialization/type queries and parameter-table behavior support FDISK/FORMAT. Preserve CF/AH, boot drive, transfer counts where defined, BDA disk status, and ES:BX buffer semantics. Test invalid CHS, zero/oversized counts, final sector, 64 KiB buffer crossings, track crossings, missing media, write protection, retries, and change generation. Freeze the selected BIOS behavior for partial transfers rather than assuming every BIOS agrees. [BIOS reference](https://msarchive.pcjs.org/mspl13/msdos/encyclopedia/appendix-o/).

## Floppies

The supplied images are 368,640 bytes: 40 cylinders × 2 heads × 9 sectors × 512 bytes. Whole-image loading into a reserved REU slot is required. Use a descriptor's exact length; do not save the unused tail of a 1 MiB slot. Guest sector writes update that slot through coherent transfer routines, then mark the image dirty.

Floppy writes initially have **session persistence**: they survive within the emulated session, but require **Save image** to become host files. Show a dirty indicator, and require save/discard/cancel on eject or normal quit. A host crash/power loss can lose unsaved REU data. Save means pause guest disk activity, write a new output file, close, reopen, verify length and contents, and only then mark the image clean. Keep the previous file until the new file is verified. A rename sequence is not advertised as a power-fail-atomic filesystem transaction.

Normal reference images are immutable; work disks are explicitly derived copies. BIOS write-protection and save/export behavior are distinct. Do not silently write back to the user's source image. Disk swap tests must invalidate both the BIOS media state and any image cache identity; stale DOS buffers require the normal DOS/BIOS media-change behavior too.

## Hard disk: small first, then 20 MiB

Use a whole raw disk image with MBR, primary partition, volume boot sector, FATs and data. A partition-only image is a different fixture kind and must never be autodetected from an arbitrary filename. Prefer the included FDISK/FORMAT/SYS to construct the guest filesystem so its own expectations are tested.

Proposed experimental geometries (subject to the included tools' acceptance):

| Profile | C/H/S | Sectors | Exact bytes |
|---|---|---:|---:|
| Small | 128 / 2 / 16 | 4,096 | 2,097,152 |
| Large | 640 / 4 / 16 | 40,960 | 20,971,520 |

Both fit traditional CHS fields and the DOS 3.3 small-partition size range. If its FDISK insists on different geometry/reservations, select a conventional 17-sector geometry and record actual capacity; do not patch DOS merely to meet a round number. Account for MBR/hidden sectors and any reserved diagnostic cylinder consistently in INT 13h, tables, file size, and partition bounds.

A small fixed disk may legitimately format as FAT12 (partition type 01h); do not force FAT16 based on the word “hard disk.” The larger small FAT16 partition should use type 04h, not later type 06h. DOSBox-X documents that its default IMGMAKE FAT16 format is unsuitable for this old DOS workflow; create blank/unformatted media and let the guest partition and format it. [DOSBox-X guide](https://dosbox-x.com/wiki/Guide:Installing-DOS-2.x-3.x).

Use a bounded REU extent cache, starting with 4 or 16 KiB extents under measurement. Guest page size and disk extent size are separate choices. Keep tags/descriptors for active extents in host RAM; a 2 MiB cache with 16 KiB extents has 128 entries. Include this metadata in the memory budget; shrink cache size or move cold metadata to REU if needed.

Begin with read caching and **write-through image updates**: guest write → coherent source bytes → update backing range → check transferred count/status → complete BIOS operation. Only mark cached bytes synchronized after success. Force the M8 cache to 64–256 KiB so a 2 MiB fixture actually tests eviction. Reads crossing extents split and preserve exact offsets; do not read an entire 20 MiB image.

Write-through reduces application-level dirty-cache complexity; it does not prove power-loss durability inside the Ultimate/filesystem. Define clean close/export and verify by reopen. Add write-back only after failure semantics are tested, with dirty-sector maps, flush ordering, bounded memory, and recovery behavior. An unsuccessful/uncertain write or close must retain “uncertain/dirty” state and refuse destructive source replacement. Initial failure testing may guarantee detected inconsistency and retained recovery files, not transactional DOS crash recovery.

## Ultimate DOS backend

Use native UCI, not runtime REST or host-side file sharing. The documented targets 01h and 02h each own their current file/directory. With resident floppies, reserve an active file target for HD access and another for import/export where possible; otherwise reopen by absolute path and explicitly seek each operation. Guest handles do not consume Ultimate handles.

Implement identify/open/seek/file-info/read/write/close plus REU load/save. Full floppy transfer uses file→REU or REU→file. Partial HD extents use absolute file seek plus bounded REU load/save. Validate returned **actual byte count**, not only `00,OK`; source code permits a short transfer to be reported separately in the reply. Distinguish status text/wire ASCII from PETSCII strings.

The documentation says REU transfer arguments are 32-bit little endian with restricted upper bits and a 16 MiB assumption. Inspected upstream `dos.cc` instead masks addresses to 24 bits and lengths to 25 bits, permitting a full 16 MiB operation. Pin the firmware/version and test boundary behavior; use modest bounded chunks so correctness does not depend on this documentation discrepancy. Sources: [Ultimate DOS](https://1541u-documentation.readthedocs.io/en/master/uci/ultimate_dos_target.html), [inspected implementation](https://github.com/GideonZ/1541ultimate/blob/125da1fec3e3b50d31f6409ec217d80693ed674d/software/filemanager/dos.cc).

Port ReadyFS's proven protocol contract, with attribution and this project's tests: synchronize quiet IDLE; queue command; PUSH once; wait for MORE/LAST; drain data and status; accept; observe transition; return to quiet IDLE. Handle delayed initial busy state, oversized replies, empty results, late errors, and asynchronous ABORT. A fast polling loop at 64 MHz must not turn an old iteration limit into an unrealistically short timeout. [UCI protocol](https://1541u-documentation.readthedocs.io/en/latest/uci/core_uci_architecture.html).

## IEC/D81 development backend

Store the **PC IMG as binary contents of a CBM SEQ file** inside a D81, not as a replacement D81 filesystem. A 360 KiB image needs `ceil(368640/254) = 1452` CBM data blocks. Two copies need 2904 blocks before bootstrap/program files, leaving limited headroom in a 3160-free-block D81. Prefer separate boot/source and output D81s for verified-save scenarios. Do not assume a PRG LOAD/SAVE can transfer a 360 KiB file through one 64 KiB C64 buffer.

Planning proof: c1541 successfully placed disk 1 into a fresh 819,200-byte D81 as a 1452-block SEQ file, leaving 1708 blocks free, and extracted all 368,640 bytes identically. [Evidence](../agentworking/research/d81-container-proof.json). This proves container capacity and byte preservation only; it does not prove the future target's IEC stream code.

Use KERNAL OPEN/CHKIN/CHRIN/READST streaming through small RAM buffers and REU DMA; save with CHKOUT/CHROUT/CLOSE, preserving binary 00/1A/FF bytes and final-byte/EOF handling. Stream whole floppies once, then guest sector access is REU-local. This deliberately avoids random-seek support for ordinary CBM sequential files. The IEC lane initially covers floppy persistence only; HD extent I/O stays in mocked/Ultimate lanes until a separately tested chunk-file/random-access adapter is justified.

Run VICE with a 1581 image, REU, virtual-device traps, true-drive emulation disabled, and warp for fast integration. Resolve installed option names from its help/version. Repeat a smaller true-drive 1581/KERNAL test for real serial behavior; traps skip physical protocol details. Reuse the sibling .NET binary-monitor harness. Extract the SEQ image with c1541 and independently verify guest sectors/FAT/files. [VICE quick setup](https://vice-emu.sourceforge.io/vice_5.html), [resources](https://vice-emu.sourceforge.io/vice_6.html).
