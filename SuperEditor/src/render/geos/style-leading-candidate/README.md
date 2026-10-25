# C6 leading-star local styled typing

Private production-ready delta in `certify.s`: the existing alphabetic opener
rule also accepts a literal leading `*` when the old GPR_INLINE is nonzero and
the following source byte is not space. This permits whole-line `**bold**`,
`*italic*` and `***both***` interior edits. It does not admit star-space bullets.

All other C6 checks are unchanged: actual typed FE ownership/epoch/full source
key and geometry, all row styles≤3, all row/neighbor-band roles0, exact deletion
byte and glyph prefetch/CRC. Existing C32 independently proves the edited byte
and adjacent bytes are alphanumeric with equal styles, no delimiter/escape
adjacency, and actual transformed bounds. Old GPR_INLINE means *possible* inline
syntax; it is not by itself a claim that a pair is closed. Locality is still the
consumer's proof. No parser or generic style API is changed.

Actual original C6 reassembles byte-identically against immutable47 fixture
`build/geos-incremental-editor/20261025T122004452115Z/fixture`. Candidate is4084
bytes versus4060 (+24), leaving12. No new BSS/ZP, phase fields or namespace ABI.
Only `typing/certify.s` would change in an eventual parent promotion. The private
builder and new test never alter production files, shared builds or a D81.

`tests/test_geos_style_leading.py --variant control|candidate` builds both exact
SEOs and privately substitutes only C6 into a copied fixture. Both variants pass
35 real public-editor frames, all bitmap/attributes/source/history/font guards,
whole16MiB REU outside exact FE header/row/body spans and the1KiB OS shim. Every
PNG matches byte-for-byte. Tests include all three whole-line styles, repeated
insert/backspace and undo/redo, marker/space/open/close adjacency fallback,
star-space bullet, heading, neighboring colored glyphs and an actual checked FE
DMA fault clearing only old INLINE. Namespace42→41→42 is exercised with real
GOTO/edit/paint through C32/C31, never by changing a load counter or stage bytes.

Example actual input+render CPU work: bold insert1,264,762→143,086 instructions;
bold backspace1,226,466→42,396. This is not native VIC/IRQ cycle timing or a
physical keyboard claim. Parent coherent integration/stack/native gates remain
separate. An initial verifier error incorrectly required the prose certificate
for the existing code worker; that failed run is retained, corrected code path
requires its existing GEC rather than GTC proof.
