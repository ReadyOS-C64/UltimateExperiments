# DOS disk inspection and fixture creation

`build_support/dos_disk_inspect.py` reads FAT12/FAT16 volumes and single-primary-partition raw HD images without writing or repairing them. It checks both FAT copies, BPB/volume bounds, reserved FAT entries, full file and directory chains, dot/parent entries, cross-links, lost allocations, exact lengths and MBR/CHS agreement. Bad clusters are reported separately. It can extract a file to standard output after validating the complete filesystem.

```sh
python3 build_support/dos_disk_inspect.py 'reference/MS-DOS Version 3.3 with GW-BASIC 3.2 (Microsoft) (1988) - 1 of 3.img'
python3 build_support/dos_disk_inspect.py agentworking/runs/my-large-fixture/disk.raw.img --geometry 640,4,16
python3 build_support/dos_disk_inspect.py agentworking/runs/my-large-fixture/disk.raw.img --geometry 640,4,16 --extract BOOTVER.TXT
```

Scope is DOS 3.x: 512-byte sectors, two FAT copies, 16-bit BPB sector counts, short names and FAT12/FAT16. FAT32, long names, extended/multiple partitions and repair are unsupported. Width classification uses cluster counts and the HD partition type must agree; accepted fixtures stay far from historical width-boundary ambiguities. Directory recursion has an explicit depth bound of 64.

`build_support/dos_hd_fixture.py` creates each fixture in a new owned directory inside this project's `agentworking/runs/`. Existing outputs and paths outside that tree are rejected. It requires optional DOSBox-X and NASM tools; neither is needed by the inspector or its unit tests. Tool paths can be supplied through `--dosbox`, `--nasm`, `DOS64_DOSBOX` and `DOS64_NASM`. Python 3.9 or later is required.

```sh
python3 build_support/dos_hd_fixture.py --profile small --output agentworking/runs/my-small-fixture
python3 build_support/dos_hd_fixture.py --profile large --cross16 --output agentworking/runs/my-large-fixture
```

Profiles have fixed original-BIOS geometry:

| Profile | Cylinders/heads/sectors | Raw bytes | Partition | FAT |
|---|---:|---:|---|---|
| small | 128/2/16 | 2,097,152 | active, start LBA 16, length 4,080 | FAT12, type 01h |
| large | 640/4/16 | 20,971,520 | active, start LBA 16, length 40,944 | FAT16, type 04h |

Creation verifies all three supplied source-image hashes, clones disk 1, and runs its unchanged genuine DOS 3.3 FDISK, FORMAT /S, SYS and CHKDSK. The formatted disk then boots alone in a fresh DOSBox-X process; guest VER and completion files must appear, system file contents must match the source, CHKDSK total allocation must match the independent inspector, and all FAT allocations must be valid. No host-mounted drive survives guest boot. Only disposable clones receive CONFIG/AUTOEXEC changes and temporary evidence files.

The FDISK console feeder is a tiny `cpu 8086` TSR in `dos_fixture_assets/keyfeed.asm`. It supplies FDISK's flushed AH=0Ch/AH=08h input and records raw text screens. It does not replace disk/boot/filesystem services. The TSR is absent from the resulting HD. `cross16.asm` is a separate original-8086 guest test using genuine DOS handle calls, not a host-created data file.

The tested DOSBox-X 2026.01.02 classifies raw images no larger than 2,880 KiB as floppies. The small profile therefore uses a temporary **3 MiB zero file with exact advertised 128/2/16 geometry**. After guest execution, every byte in the extra 1 MiB must still be zero before the exact first 2 MiB is extracted. No boot, partition or FAT fields are patched. To reference-boot that 2 MiB raw image with this DOSBox-X version, use a fresh 3 MiB padded copy with the same advertised geometry. Target tests consume the exact 2 MiB image.

`--cross16` is large-only. DOS writes 4,097 blocks of 4,096 bytes to `CROSS16.BIN`, closes, reopens, reads and compares every word, verifies EOF, closes and writes a closed completion marker. Word `j` of block `i` is `0xA55A XOR i XOR j`. The host independently compares every file byte and maps its contiguous chain across raw byte `0x01000000`; seam hashes and 32-bit offsets are retained. No raw HD images are bundled in source control.

Each guest stage has a finite `--timeout` (default 90 seconds; allowed 1–180). Version/assembly tool calls have ten-second bounds. Processes stop after closed guest evidence files or bounded failure. These tests establish reference media contents and semantics; they do not establish power-failure durability, physical C64U storage behavior, 6510 backend correctness or XT performance.

## Manifest interface

Each run keeps `manifest.json` even after failure. Require **all** of `complete`, `original_images_unchanged` and `source_system_files_identical` to be true before consuming an accepted fixture. Verify the actual raw file against `raw_image.bytes` and `raw_image.sha256`.

The interface is `schema_version: 1`, `kind: "dos64-genuine-dos-hd-fixture"`, `profile: "small" | "large"`, and:

```json
{
  "raw_image": {"path": "disk.raw.img", "bytes": 20971520, "sha256": "actual run hash"},
  "geometry": {"cylinders": 640, "heads": 4, "sectors_per_track": 16, "bytes_per_sector": 512}
}
```

Resolve relative `raw_image.path` against the manifest's parent directory. The manifest also records original image identities, actual tool/source hashes, stage commands/configuration hashes, guest transcripts, independent complete inspection and limitations. Optional `cross16` identifies `name`, `file_bytes`, `sha256`, `raw_start`, `raw_end_exclusive`, `contiguous`, seam hashes, and both `guest_write_close_reopen_read_compare_eof_close` and `host_compared_all_generated_bytes`. Long HD acceptance may explicitly require those fields and the `CROSS16.BIN` inspection entry.

Timestamps are set by the guest clock, so re-created images need not have the same whole-image hash. Always pin the actual run's identities. The root image output contains redirected boot logs in AUTOEXEC; booting a disposable writable clone legitimately updates those logs.

## Host verification

The default tests need only Python and the supplied reference images:

```sh
python3 -m unittest discover -s tests/tooling -p 'test_dos_disk_inspect.py' -v
python3 -m unittest discover -s tests/tooling -p 'test_dos_hd_fixture.py' -v
```

Synthetic structural unit images are deliberately nonbootable and are never offered as genuine DOS fixtures. Actual generated HD fixture runs remain opt-in. This tooling does not modify the emulator, inject INT 21h implementations, or provide an alternate native application loader.
