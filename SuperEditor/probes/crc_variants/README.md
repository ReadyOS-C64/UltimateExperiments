# CRC16/CCITT implementation comparison

Standalone assembled probe, not a production change. Run from SuperEditor:

```
make -C probes/crc_variants test
```

Input/API: A next byte, 16-bit `crc_value` little endian. `crc_init` setsFFFF;
no reflection/final xor, polynomial1021. All updates preserveY, clobberA/X/flags,
and require no input buffer, ZP, DMA, overlay, font, BOOT or ReadyOS dependency.
Carry is unspecified; both incoming values produce the same CRC. Decimal mode
is irrelevant to these shift/XOR algorithms and remains unchanged. CRC state
is2 bytes for every variant; no additional permanent scratch is allocated.
The routines are foreground/nonreentrant for a shared state, matching production.

| Variant | Update code | Tables | Extra stack | Instructions | CPU cycles incl RTS | Incl caller JSR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Existing tableless baseline |58|0|0|34|96|102|
| Full byte table |20|512|0|8|32|38|
| Nibble decomposition |47|64|1|22|75|81|
| Deliberately unaligned byte table (diagnostic) |20|512|0|8|32–34|38–40|

The512-byte variant reduces the update body to one third of the baseline cycle
cost, and to38/102 including a JSR at each byte. It uses the standard linear
CCITT byte table: X=A xor oldHigh; newHigh=oldLow xor highTable[X];
newLow=lowTable[X]. Its total code+constant cost532 bytes replaces58 bytes,
a net increase474 before alignment padding. Both256-byte arrays must start at
page boundaries. Link-time assertions enforce that constraint. Layout tables in
owned warm RAM/ROM visible to the CPU; never depend on disposable BOOT scratch.

The64-byte option decomposes T[x] into T[x&15] xor T[(x>>4)<<4]. Four16-byte
lo/hi arrays supply those two contributions. It costs111 bytes of code+tables,
net53 over baseline before0–15 bytes alignment padding. Each array needs16-byte
alignment, not a whole page. It uses a single transient PHA/PLA byte to preserve
partial output while reusing the existing CRC state as temporary storage. It
saves21 body cycles (about22%) per byte; 75/96 body-cycle ratio. This is a fallback
if512 bytes plus layout padding cannot fit, and its extra stack depth must be
included in the integrated worst-case-stack audit.

For4096 bytes, update bodies alone cost393216 baseline cycles,131072 full-table,
or307200 nibble cycles. CallerJSR adds24576 cycles equally. These figures exclude
CRC-loop housekeeping, DMA, overlays, interrupts, VIC badlines and emulator speed.
They are not elapsed-time or frame-latency claims. Full-table speedup should be
verified in the integrated normal-clock reload workload after admission.

## Cycle method and alignment proof

The existing Peddle wrapper exposes `regs.cycles`, but calibration of
NOP/NOP/RTS reports zero clock change. Inspection confirms its stepping path does
not advance the exposed clock. No runtime cycle count is invented here.

Instead, the driver audits each executed opcode and addressing mode using exact
NMOS6502/6510 instruction costs. It includes RTS, PHA/PLA and the extra cycle for
an indexed absolute read crossing a page. A callerJSR is separately+6. All
candidate bodies are straight-line code, so there are no unaccounted branch
paths. Actual Peddle instruction-counter differences must equal the audited
instruction count. `traces.json` records representative executed traces.

The selected512-byte arrays start$8100/$8200 in this probe. The64-byte arrays
start$8300/$8310/$8320/$8330. The diagnostic duplicate starts$8401/$8501: index255
crosses a page in both indexed reads, and the audit observes34 rather than32
cycles only for that index. Every possible index is exercised. Probe addresses
are examples, not production memory reservations. Linker alignment padding is
excluded from the comparison table: full table can require0–255 additional
bytes; the nibble table0–15. The complete probe includes all variants/diagnostic
copies at once and is deliberately larger than any proposed production consumer.

## Verification and limits

`tests/test_crc_variants.py` executes emitted6510 code against independent
`binascii.crc_hqx`. It retains the original5376 regression cases per variant,
checks all generated table entries independently, all256Y values, both incoming
carry values, decimal flags, stack entry offsets including wrap, CRC-neighbor
guards, and the published123456789→29B1 vector. Large streams include lengths
255/256/257,4095/4096/4097,65535/65536/65537 and alternate chunk boundaries.

The baseline body is pinned to the exact historical production instruction
sequence/source hash269e946c… rather than following future production edits.
The report separately records the current production source hash/match. This
allows the probe to remain reproducible after root chooses a faster CRC.

`build/crc_variants/result.json` records exact source/probe/wrapper hashes,
per-variant sizes and audited cycles, protected RAM/shim checks and corpus totals.
`probe.map`, labels, generated tables and representative traces are adjacent.
No VICE, D81, physical keyboard, normal-clock timing, or integrated resident-fit
claim is made by this probe. Root owns adoption and all shared source changes.
