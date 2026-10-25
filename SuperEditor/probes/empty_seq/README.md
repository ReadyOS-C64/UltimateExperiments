# Empty SEQ investigation and isolated workaround

This is a throwaway M4 probe. Existing `src/fileio/` and its `$98` writer guard
are unchanged. The probe deliberately bypasses that guard only for its freshly
created owned candidate, uses no CHROUT for that candidate, and later promotes
it by exact rename. No editor or shared D81 build is involved.

```sh
make -f probes/empty_seq/Makefile test
# Requires the root's exclusive VICE monitor window:
python3 tests/test_empty_seq.py --vice
```

All probe build outputs stay under `probes/empty_seq/build/`. Native evidence
uses a newly formatted writable D81, copied as `initial.d81` before VICE starts.
The normal .NET harness uses warp and trapped1581 access. No hardware, global
configuration, TDE setting, neighboring project or existing disk was changed.

## Correction to the earlier diagnosis

The retained prior EMPTY sector begins `00 01`: a terminal sector with **zero
logical payload bytes**. Its unused254-byte tail exactly matches what the older
native sequential reader and c1541 extracted. The earlier conclusion that the
writer had created254 logical bytes was incorrect; using c1541 as a second
oracle repeated the same reader implementation.

Installed VICE is3.10. The matching [official3.10 release source](https://downloads.sourceforge.net/project/vice-emu/releases/vice-3.10.tar.gz)
was inspected. Its sequential reader begins at buffer index2 and takes the last
sector's byte1 as its endpoint. For an empty endpoint1, its equality test misses
EOF and emits the unused tail until the index wraps. The writer's endpoint for
zero data is correctly1. This explains the exact old disk/output pair.

`vdrive-iec-3.10.c.txt` is the unmodified GPL reference source with its original
license header, extracted read-only from that release, SHA256
`5a13de2d32da96d09d5c499965a796cf9dd8e51648d7531af74cb3bc324d41ba`.
`homebrew-vice.json` records installed/release metadata and the declared tarball
checksum; the complete tarball hash was not independently computed. Relevant
release-source lines: sequential-read initialization131/135; final-sector count
795; read comparison933; later-sector endpoint reload956. The source and retained
disk jointly support the diagnosis; no physical-drive behavior is inferred.

## Concrete D81 provider proposal

`reader.s` implements read-only, bounded first-block metadata preflight for an
**unpartitioned1581/D81** provider. The caller freezes its validated native name
and device8/9 through this operation. No active provider data channel is allowed.

- `empty_begin` opens private LFN7/SA3 as a DOS direct buffer and queues the D81
  header40/0. It returns carry clear/A2 pending. It does not mutate disk data.
- Each `empty_step` performs one U1 read of exactly256 bytes into8000, then parses
  the header or at most eight directory entries, or classifies the file's first
  block. Directory links must remain on track40/sectors3..39; a40-sector budget
  prevents corrupt loops. Data track/sector values are bounded1..80/0..39.
- Exact native filename bytes and closed SEQ type select the file. `00 01` in its
  first block means empty. A different valid endpoint or a next block means
  nonempty. Terminal count0 is malformed, never an empty-success shortcut.
- A2 means pending; A0 means completed and `empty_result`0/1 classifies the file.
  The result may be consumed only after successful completion. Errors propagate
  argument/busy/ROM/DOS/format status and close LFN7. `empty_cancel` is resident
  cleanup in a production placement and must not depend on a loaded asset.
- Detection writes no disk sector, performs no scratch, and opens no document
  source object. U1 is the only raw-disk command used; no U2/block-write exists.

After successful preflight, perform the normal SEQ open/status operation. If
metadata proved empty, set the provider EOF flag before its first read-chunk.
Existing `se_io_read_chunk` then returns zero transferred bytes without calling
CHRIN, and ordinary close/status still closes the real opened file. Nonempty
files follow the existing normal streaming path, including a one-byte NUL file.
The probe's `safe_open` demonstrates this concrete sequence; a product coordinator
must yield between preflight steps rather than use its probe-only blocking loop.

This permits an eventual production change to remove the conservative `$98`
zero-write guard **together with** this verified empty readback path. Do not
remove the guard alone, skip save readback, or save a NUL to stand in for empty.
For failed close/status or uncertain name promotion, keep the current owned-temp
recovery policy. Never touch an original file merely to normalize unused bytes.

Before integration, freeze/copy name/device into an owned request frame, map
metadata-not-found diagnostics consistently with DOS status text, validate disk
identity around removable-media changes, and place cancellation/frame ownership
according to the overlay ABI. D81 geometry is explicitly part of this adapter;
future UltimateDOS should provide its own exact-length metadata rather than
inherit raw tracks. Partitioned1581, device9 native, real-drive and TDE cases
remain separate gates. No general portable-IEC claim is made.

## Exact evidence

`build/offline-result.json` passes raw retained-disk verification, a reproduction
of the3.10 endpoint arithmetic, and actual emitted preflight code with modeled
ROM/DOS: empty, one-NUL and multi-block classification, missing name, competing
begin, cancellation and OPEN/CHKIN/CHRIN failure cleanup. Every call checks shim.

Native `agentsworking/evidence/M4/20261024T200911775765Z-empty-seq/` passes:

- Zero-CHROUT create/close produces an owned `00 01` empty file; preflight plus
  real SEQ OPEN/read/close returns done0/EOF64 and leaves buffer markerA7 intact.
- The owned empty candidate is promoted to EMPTYFINAL and has zero logical bytes
  by independent raw-chain decoding. An existing host-imported empty file also
  reads zero bytes through the same sequence.
- A true one-NUL file remains one byte; a64-byte CONTROL remains byte-exact.
  All original fixture data-sector contents/links are unchanged, including
  imported empty and NUL. KERNAL channel table is empty, shim1024 intact.
- Original384×272 PNG inspected: EMPTY SEQ NATIVE PASSED on a clean BASIC screen.
  PRG SHA256`05a749ec2d99fad8e0f2748807636b8537bea4c62020d658ed0f730dc69f913c`.

Prior failed runs200731/200843 retained a probe packaging collision: boot PRG
was named EMPTYPROBE, the intended candidate name. Create correctly refused
DOS63 and preserved it. Renaming the boot program EMPTYTEST fixed the probe.
The initial packaging-only200723 attempt hit UTF-8 decoding of c1541's PETSCII
diagnostic output; logs now decode with replacement without changing file bytes.
These are probe harness mistakes, not additional file-provider failures.
