# REU floppy sector implementation

Updated 2026-10-15. `src/disk.s` provides an actual 6510 assembly INT 13h sector primitive behind the [owned BIOS ROM gate](BIOS_IMPLEMENTATION.md). The primitive moves raw sectors through the [coherent range API](RANGE_IMPLEMENTATION.md). Ultimate/IEC file import, persistent saves, floppy B and hard disks remain unfinished; the complete scope is in [storage design](STORAGE.md).

## Configuration and public behavior

`dos64_disk_init` explicitly configures unloaded floppy A at REU 100000, 720 sectors, 40 cylinders, two heads and nine sectors/track. The caller must load the entire image and then set `dos64_disk_loaded`; initialization never invents loaded media. `dos64_disk_transfer` takes conventional INT 13h guest arguments: AH function, AL count, CH/CL ten-bit cylinder/one-based sector, DH head, DL drive and ES:BX buffer.

| Function | Behavior |
|---|---|
| AH=00 | Reset/status success for drive A, including unloaded media; no bytes transferred |
| AH=02 | Read raw image sectors into guest memory through coherent writes |
| AH=03 | Export coherent guest bytes into the volatile REU image |
| AH=04 | Verify readable REU sectors without guest buffer access/writes |

Only guest AX is modified: AH=status and AL=complete sectors. Guest FLAGS remain unchanged at the primitive boundary; the BIOS wrapper edits saved CF. Host carry reports success/failure and other host P bits are preserved. Last status and fatal host-cache error are separate fields. Status values are 00 success, 01 unsupported command, 04 invalid sector/geometry/count, 09 DMA boundary, 20 controller/transfer and 80 absent drive/media. Their interface meanings were checked against the pinned IBM XT source noted in `src/disk.s`; no BIOS implementation code was copied.

## Validation and transfer policy

Counts must be 1–127, sectors 1–configured sectors/track, head/cylinder in range, and drive zero. Geometry must be nonzero, at most 1,024 cylinders and 63 sectors/track, multiply without overflow and equal the configured sector count. The complete slot must lie outside guest backing and inside minimum 4 MiB REU. Checked 24-bit addition computes `base + LBA*512`; no guest-supplied geometry can overflow into another arena.

CHS uses `LBA=((cylinder*heads)+head)*sectors_per_track+(sector−1)`. This implementation permits a linear multi-sector request across track/head boundaries within the image. It rejects an extent extending beyond its configured image. Guest buffer validation uses the translated physical address: a request may end exactly at a 64 KiB DMA boundary but may not cross it, even if BX itself would not wrap. This is a declared BIOS compatibility policy, independent of CPU segmented word wrapping.

Read/write uses the coherent cache API for every guest byte; REU image chunks split at 64 KiB seams and use the C000–C0FF staging buffer. Reads preserve dirty neighbors in partial guest pages; writes include resident dirty bytes. A disk write changes the volatile REU image only and is not a persistent save. Verify reads bounded chunks into staging; a raw image contains no magnetic CRC metadata, so success proves REU readability rather than physical-media CRC validation.

## Failure and progress

Rejected input performs no DMA/guest writes. Transfer errors report complete 512-byte sectors from the range's committed-byte count. A current failed chunk may have uncertain external DMA bytes; it is never advertised as committed. Host cache errors set `dos64_disk_host_error` and are terminal because guest authority may be compromised. Ordinary source/destination DMA errors are reported as guest disk status 20 through the BIOS frame; earlier complete sectors remain visible. Do not assume rollback or power-fail atomicity.

Tests execute all 720 CHS addresses against independent linear addressing, verify without guest writes, cross track/page/REU seams, export dirty bytes, cover exact/crossing DMA boundaries, validate malformed geometry/count/drive/slot without writes, exercise cylinder high bits and an exact 4 MiB end, and inject failures to check whole-sector progress. The genuine DOS test lets the unchanged bootloader read through this primitive to IO.SYS entry.

No FDC/8237 controller, format implementation, AH=08 geometry/status family, hardware disk controller, file handles, DOS FAT parser or guest DOS API is implemented here. Host FAT12 tooling is an independent fixture/oracle helper, never the runtime sector implementation. The next milestones remain actual Ultimate/IEC media transport and verified persistence, then file-backed approximately 2 MiB and 20 MiB hard disks with forced cache eviction and offsets above 16 MiB.
