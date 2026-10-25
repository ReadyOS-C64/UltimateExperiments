# Private SP2 source-grid paragraph reflow

This is a private four-image capsule, not canonical production. It uses no new
asset, resident/BSS/ZP bytes or REU bank. `build-long.py` emits C14 `styler`, R14
`viewsource`, R25 `geostail`, and C33 `grid` against a frozen resident binding.
Earlier SP1/local releases remain immutable.

The actual C14 SuperMark prose event is the authority. SP2 approves all visible
rows belonging to an alphabetic-leading logical paragraph only after the real
complete inline scan finds no `*`, `@`, or native pound escape anywhere. It
handles events and canonical anchors above 64KiB. Uniform role0 is never used
as a substitute for block/parser authority. FE1600..167F keeps the version2,
128-byte CRC-protected source/style/epoch/generation/width/22-anchor record.
R14 ops3/4/5 are BEGIN/EVENT/FINISH; EVENT closes the preceding paragraph and
FINISH closes the last. Opcode6 is free. Successful real source READ2 scans
only bytes before the current event's canonical END.

C33 keeps CAPTURE0/TRY1/PLAN2 and the parent's exact reveal-preparation op3.
R25 keeps original tail0/1 and existing helper2..15. New16 prepares a long
transaction through the same source/object/font/epoch/provider/header guards;
17 writes one shifted packet and its CRC;18 fetches one eight-byte glyph from
the authenticated managed R16/17 backing at its fixed font offset0800. There
is no R-to-R call or unverified retained AC00 font assumption.

Before any pixels/cache publication, the caller verifies every affected old
240-byte packet/CRC, every relevant SP2 paragraph bit, all roles0 and flags0
except the old caret, all40 old attributes16, and the actual new merged source
against the cached source except one interior alphanumeric insertion/BACK.
Only old/new revision+1 and length/hot-length/caret+/-1 qualify. It supports
softwrapped continuations and carry into/off the viewport. It rejects physical
caret edges, selection/folds/pan/manual, inline/code/structural changes, added
or removed physical rows, a deletion exposing CR/EOF at the viewport boundary,
nonwhite attributes and stale/foreign/unready capabilities.

Pixel shifts operate on one eight-scanline VIC row at a time, preserving the
60-column ten-pixel margins. Source positions and packet anchors remain24-bit.
The old caret is removed once, each row shifts4/5 pixels with a genuine narrow
font glyph at the incoming edge, then the new caret is applied once. Metadata,
row packet CRCs, bottom/remaining anchors, unchanged semantic plan and SP2 key
are published only after all rows paint. Source/history/hot/clipboard remain
byte-exact. The sparse-index tags are invalidated before owner4 borrows
8D00..8D7F; source cache8000 is invalidated before pixel scratch uses40 bytes.
The existing FS8EE0 and VIEW8C00 frames are excluded. Runtime pixel core has
caller-proven bounds; the standalone primitive retains its strict public
validation and carry output.

The three cache-valid bytes are cleared before painting. A late transport
failure leaves derived cache invalid so the normal root fallback repaints;
pre-write admission failures are read-only for pixels, source and REU. This is
one bounded22-row synchronous TRY, not a new asynchronous job.

The C33 dynamic status font stores only the exact26 glyphs reachable from six
hex digits and `Modified`/`Clean   `, with a26-byte lookup. Generic native fonts
are unchanged. Packed font is BF00..BFCF; executable tail BFD0..BFFF. C33
additionally authenticates generated exact C14/R14/R25 sizes and CRCs; both
publishers must have actual immutable-backing verification bits. Thus a stale
same-key SP2 record cannot authorize mixed/unexecuted publishers under an
unchanged resident seal. R25's ordinary overlay admission supplies its own
runtime executable validation.

Measured final payloads: C14 4075, R14 3318, R25 4095, C33 4096. The final C33
includes the parent's48-byte op3 and has one prefont byte free. Its tail is full.
Do not insert unrelated code or tables without a new measured link.

Run:

```
python3 tests/test_grid_wrapped_shift.py
python3 tests/test_grid_paragraph_authority.py
python3 tests/test_grid_long_transaction_extended.py
python3 tests/test_grid_long_transaction_vice.py --fixture PATH --run
```

The native wrapper copies a frozen fixture and replaces only these four SEOs
on its disposable D81. Its original product-source ZIP describes the resident
and unchanged assets; the separate private-source ZIP describes replacements.
CPU instruction counts are not native PAL cycles. First publication and settled
idle are reported separately. This does not close general typing performance:
geometry transitions, markup, code, selections, folds and physical edges still
use the normal renderer, and long initial authority scans still cost real work.
