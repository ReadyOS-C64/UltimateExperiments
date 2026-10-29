# Plain 60/80-column editing

`syntax plain` now uses the checked grid packets for caret movement and local
typing without first loading semantic parsers. This changes three existing
capsules: C33 `grid`, R25 `geostail`, and R14 `viewsource`. That checkpoint kept
the resident, allocations, zero page and ReadyOS reservation unchanged. The
subsequent lexical-cache registration brings the catalogue to59 entries.

NC header byte253 records the exact presentation preset under the existing
CCITT checksum. Every consumer compares it. Plain typing checks source objects,
window/revision/caret deltas, exact old-to-new bytes, packet CRCs, row ownership,
fonts and REU capabilities. It never manufactures an SP2 semantic certificate,
publishes a semantic descriptor or marks parsing valid. Markdown and Full retain
their semantic checks and exact helper witnesses.

Short edits require both old and new row lengths below the column width. Wrapped
edits can carry pixels across existing rows only after validating the complete
affected source and packets. Before writing pixels, a real checked R14 admission
authenticates its pixel worker. Its owner4 operation6 is a no-op used to complete
that admission; operation7 performs the existing pixel carry. Four assembler-
checked short branches fund the new entry without removing validation.

The short-row old-length check is essential: inserting into a width-minus-one
line can create a separate CR row. Deleting the inserted byte must remove that
physical row. An earlier candidate checked only the new length and left stale
following pixels. The native test reproduces this sequence in both widths; the
corrected build uses the full renderer for this geometry change.

## Measured PAL work

These are VICE CPU cycles through settled foreground idle, with IRQ/VIC/REU
stalls included. Setup uses real ROM File/Open and IRQ commands. The stopwatch
uses an explicit PC/SP/public-input entry seam, so these are not measurements
of physical keyboard latency. Warp and drive traps are enabled for development.

| Plain operation | Previous | Current | Current overlay loads |
|---|---:|---:|---:|
| 60-column Right | 871,683 | 133,289 | 2 |
| 80-column Right | 792,692 | 137,911 | 2 |
| 60-column short-space insertion | 997,820 | 371,328 | 4 |
| 80-column short-space insertion | 931,728 | 255,659 | 4 |
| 60-column first wrapped-quote insertion | 1,435,327 | 692,236 | 4 |
| 80-column first wrapped-quote insertion | 1,029,577 | 364,769 | 4 |

Structural edits still have a material regression because their completed full
paint is followed by the 22-packet capture:

| Plain fallback | Previous settled | Current first publication | Current settled |
|---|---:|---:|---:|
| 60-column insertion adding a row | 1,428,082 | 1,523,967 | 2,046,346 |
| 80-column insertion adding a row | 1,125,862 | 1,221,684 | 1,740,134 |
| 60-column CR insertion | 2,094,539 | 2,243,720 | 2,760,409 |
| 80-column CR insertion | 1,538,007 | 1,691,286 | 2,205,244 |

The current capture implementation reduces the extra settled work from roughly
0.52 million to0.30 million PAL cycles. It expands full CRC lookup tables once
and reuses the already admitted R25 during one exclusive capture. Every helper
still checks its actual owner/operation; no executable image is patched. Both
pending redraw and drawbusy refuse before any borrowed scratch is initialized.

The lookup tables alias retained line-index storage. Capture now revokes all
three index/cache authority fields before writing there. The first native
mode60→80/GOTO2 test exposed a `$7B` error when that invalidation was missing.
Both mode directions, real File/Open, and GOTO above64KiB now pass.

| Current fallback | First publication | Settled PAL cycles | Loads |
|---|---:|---:|---:|
| 60-column insertion adding a row | 1,524,117 | 1,828,709 |9|
| 80-column insertion adding a row | 1,221,519 | 1,525,607 |9|
| 60-column CR insertion | 2,243,693 | 2,546,706 |9|
| 80-column CR insertion | 1,691,372 | 1,994,023 |9|

Handling changed geometry efficiently remains open. Full GEOS source repaint is
still10,155,510 PAL cycles on the diverse fixture. This does not meet the
normal-C64 performance targets.

## Qualification

The canonical build passes the five editor/cache cases, the exact public
insert/delete sequence in Plain and Full at both widths, the existing wrapped
and prewrite-fault suites, and the unchanged 68-byte staged stack bound. The
paired private proofs also retain CRC, foreign-owner, stale-capability,
mixed-helper-generation, NUL and source positions above64KiB coverage.

Native qualification includes20 typing/fallback frames,16 Plain/Full caret
frames,11 source/settings/preview frames and6 controlled lifecycle frames.
All53 were directly reviewed and independently checked against VIC pixels.
All20 corrected typing screenshots are byte-identical to the previous control.
Lifecycle testing includes resumed editing, Undo, SaveAs and reopen through the
existing standalone adapter; it is not ReadyOS suspend/resume integration.

The59-overlay integration repeats the20 typing,16 caret and11 presentation
frames; all47 were inspected. The20 typing screenshots remain byte-identical to
the earlier54-overlay control. Additional tests cover partially visible GEOS
carets, native lexical reuse, the phase/index regression, all256 CRC table words,
132 packet checks and a70,002-byte document on a1MiB REU. The unchanged68-byte
stack bound includes the new finite lexical dispatch tables and admitted R25
capture calls. None of these checks closes the remaining structural-edit cost.

## Normal-role80-column raster

R16 now proves an all-normal effective-role row before skipping tile color
arbitration. Original glyph/flag conversion and mixed-role arbitration remain.
NativePAL short insert/BACK improve about11.4% with identical pixels and the
same four overlay loads; the separate wrapped shift route is unchanged.
No resident/BSS/ZP/font growth occurs; R25/C33 are rebuilt against the actual
new R16 CRC. See [the proof and limitations](https://github.com/ReadyOS-C64/UltimateExperiments/blob/main/SuperEditor/src/render/grid/probes/normal-row80/README.md).

## Empty-CR physical-row insertion/removal

Plain60/80 ordinary insertion/BACK can now move a validated body suffix when
wrapping adds/removes an empty CR physical row. Existing R24 operations preserve
source/header/packet/provider authority, complete packets/anchors/CRbits and
final R25 publication. NativePAL cases improve43.9–57.5% with identical images.
Unknown offscreen exposure still falls back. Return-key split/merge now has
the separate checked R29 path described below. See the
[geometry contract and measured limits](https://github.com/ReadyOS-C64/UltimateExperiments/blob/main/SuperEditor/src/render/grid/geometry/README.md).

## Return at a short line's end

The long-row validator now authenticates an inserted byte before testing the
old row's terminal bound. Previously a Return exactly at that bound could be
mistaken for the original CR: source bytes were correct, but the following rows
stayed at their old screen positions. The terminal CR now reaches the existing
structural-edit admission; ordinary terminal glyphs still use the validated path.
Deletion checks its old-byte bound before reading. No CRC, provider or source
guard is removed. See the [isolated regression](https://github.com/ReadyOS-C64/UltimateExperiments/blob/main/SuperEditor/src/render/grid/probes/row-geometry-extend/cr/TERMINAL.md).

## Native-row input setup

C33 initializes the complete19-byte native-row input descriptor from a constant
template, then sets the current width/count and physical row. It leaves the
renderer-owned49-byte scratch area to the worker. This recovers40 code/data
bytes without extra overlay calls or changing either native renderer. Both
widths pass544 glyph/role/flag vectors (1088 calls) with zero versus nonzero
scratch, identical independent pixels/attributes and instruction counts.
Registered edit/fault, stack and native60/80 typing checks also pass. This is
space recovery for further rendering work, not a structural-edit speed claim.

## Plain Return splits and BACK merges

R29 now validates the complete visible logical paragraph against the genuine
pending source, stages candidate rows, and paints only rows whose full240-byte
packets differ. It copies/authenticates the real narrow font once and uses a
local role0 blitter, reducing loads9→4. R25 still performs the final source/
revision/CRC VALID-last commit. Selected, folded, styled, panned and incomplete
offscreen scopes retain the existing renderer. See the [phase, authority and
build contract](https://github.com/ReadyOS-C64/UltimateExperiments/blob/main/SuperEditor/src/render/grid/cr/README.md) and [paired native timings](PERFORMANCE.md).
