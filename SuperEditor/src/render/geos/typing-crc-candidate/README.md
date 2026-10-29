# Private sealed glyph CRC typing candidate

Frozen parent: `build/geos-incremental-editor/20261025T093421198503Z/fixture`.
No production files, shared builds, resident state or zero-page allocation change.

The complete 128-entry CRC16 low/high tables fit inside R30. `worker.s` replaces
five whole-font reads and their 1280-byte CRC with CRC16 of the C6-prefetched
nine scanlines plus advance. It derives the screen-code index again from the
actual GEC byte through the resident PETSCII converter. The expected CRC is
entirely sealed in R30; no checksum byte is relayed through the certificate.
The existing 32-byte READY/font/binding metadata check remains exact. An unused
font glyph has no authority until used; corruption of that glyph is rejected
when its prefetched plane/advance is checked. Parent C30 cache-repair work is
separate from this candidate.

Full-table placement initially exceeded R30 by31 bytes. `status-normal.s` shares
the Modified/Clean print setup and uses a stack temporary for hex output.
`transfer.s` uses short branches to its existing identical bad-span handler.
Those two changes preserve behavior and recover enough bytes: R30=4091,
C6=3897. No certificate, geometry, source, map, epoch or owner validation is
removed. All other copied modules are unchanged from the frozen product.

Integration is only the three files `worker.s`, `status-normal.s`, `transfer.s`
over the corresponding production typing modules. The worker defines
`GTF_INCLUDE_GLYPH_CRC=1` before the existing `font-witness.inc`; C6 receives no
new table/relay. Existing root op3, actual 47-byte certificate, source-provider
contracts and fallback protocol remain the same.

Run `python3 tests/test_geos_typing_crc.py`. This privately builds/binds the two
actual sidecars, replaces them inside an immutable real editor fixture, and
executes the real packaged root render path. Ten A/B frames compare every VIC
pixel/attribute against both the baseline and an independent source/font model,
the entire FE bank byte-for-byte, source/history and all other 16MiB REU banks.
All128 table entries are checked against the frozen normal face. Eight fault
cases and all80 individual prefetched glyph/advance bit flips prove refusal
before derived/source/pixel writes; readonly misses retain GCC/GEC for fallback.

Measured warm render instructions fall28.88–31.05% with zero overlay loads;
first renders include one ordinary sidecar load. These are CPU instruction
counts, not PAL cycles or native latency. Native production acceptance belongs
to the parent integration lane.
