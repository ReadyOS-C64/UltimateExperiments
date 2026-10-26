# Plain 60/80-column editing

`syntax plain` now uses the checked grid packets for caret movement and local
typing without first loading semantic parsers. This changes three existing
capsules: C33 `grid`, R25 `geostail`, and R14 `viewsource`. The resident, 54-entry
catalogue, allocations, zero page and ReadyOS reservation are unchanged.

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

Those fallbacks use nine overlay loads. Eliminating redundant capture work and
handling changed geometry efficiently remain open. Full GEOS source repaint is
still 10,151,299 PAL cycles on the diverse fixture. This checkpoint does not meet
the normal-C64 performance targets.

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
