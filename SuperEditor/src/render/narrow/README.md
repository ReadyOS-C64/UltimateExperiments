# Bounded narrow row renderer

This is a CPU-verified building block, separate from the editor. It does not
switch VIC modes, render a document, allocate storage, load overlays, or own
input. The side-view previews currently reuse M1 drawing instead of this module.

`se_narrow_row` takes X/Y = low/high address of a caller-owned 68-byte frame
described in `api.inc`. It returns C clear/A0, or C set/A$90 for an invalid mode,
row, encoding or output base. A/X/Y/P and both loaned pointer pairs are clobbered.
The first 19 frame bytes are immutable input; the rest is scratch. Calls are
foreground-only and nonreentrant. There is no resident BSS or ZP allocation.

The caller supplies the absolute zero-page aliases `se_nr_context` and
`se_nr_pointer` for two existing pairs. Production can alias its foreground
`text_ptr` and `screen_ptr`; the isolated fixture aliases $F0/$F2. Do not allocate
new resident ZP. The caller must exclude competing users during this call.

Input arrays contain native PETSCII bytes, SuperMark role IDs, and flags. Native
input calls the actual shared `se_petscii_screen`; raw-screen encoding accepts
all 256 screen values, treating bit7 as inverse. Explicit inverse and raw inverse
form a union. Selection and caret form a separate union and invert the cell
once, after base ink arbitration. Thus their overlap cannot cancel selection.
Unknown roles map to normal. The caller supplies 14 foreground palette entries
and one background; low color nibbles are used. The palette must offer sufficient
contrast if visible selection is required; the renderer never introduces a
third color into an 8x8 tile.

60 columns have 5-pixel pitch at x10..309, centered in 320 pixels. 80 columns
have 4-pixel pitch at x0..319. Input count is clipped to the selected width.
The row is physical row0..24; it is cleared and recomposed in C64 bitmap layout
`base + row*320 + tile*8 + scanline`. Exactly 320 bitmap bytes and 40 attribute
bytes belong to a successful call. Other rows remain unchanged.

Bitmap bases must be 8KiB aligned from $2000 through $A000; matrix bases must be
1KiB aligned from $0400 through $C000. This excludes shim/I/O/zero-page writes.
The caller must supply accessible RAM, matching VIC bank/layout, nonoverlapping
inputs/frame/output, and valid arrays/fonts/palette. These ownership/mapping
preconditions are not an allocator or a general pointer-validation service.

Each tile counts unselected, clipped base ink for all contributing roles.
Maximum ink wins; ties follow combined > strong > emphasis > keyword/directive >
string > number > label > comment > normal. Same-priority ties choose the lower
semantic ID. Zero-ink tiles use normal. Reverse glyphs count their actual base
ink; selection/caret cannot recolor neighboring glyphs. No source spaces are
inserted to align color boundaries.

`row.s` contains drawing and 768 bytes of popcount/phase tables. `arbitrate.s`
contains the independent tile resolver. `font4.s` and `font5.s` each link exactly
one existing 1024-byte generated font; consumers need not link both. No font is
regenerated or modified. Font provenance is in the existing generated manifest.

Measured linked sizes: row code890 + tables768; resolver code128 + priority14 =
1800 bytes. One font gives2824 bytes, both fonts3848 bytes. The existing shared
converter adds56 bytes only in the isolated fixture (production imports it).
Frame68 bytes, two loaned pairs4 bytes, zero new resident allocation.

Run `python3 tests/test_narrow_rows.py`. The independent oracle checks all256
input values in every column for native and raw-screen inputs at both widths,
all25 rows, role colors, inverse/selection/caret combinations, clipping, majority
and tie cases, complete RAM guards, the1024-byte shim and whole512KiB REU.
It uses actual assembled6510 instructions; a tiny native helper batches the
existing Peddle single-step API without substituting rendering results.

Current worst stress row:62069 instructions (60:60561;80:62069). The wrapper's
exported cycle counter does not advance, so no cycle or real-time claim is made.
This is bounded functional proof, not a production interactive timing gate.
Measure VIC timing and damage/scheduling costs during editor integration.
