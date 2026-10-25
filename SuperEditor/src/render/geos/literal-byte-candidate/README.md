# R21 literal byte compositor — private release candidate

Production files remain unchanged. This folder contains the operation-sized
replacement R21 implementation, plus R21-private measure/glyph copies. The public
GG implementation in `src/render/geos/{measure,glyph}.s` remains untouched.

## ABI and placement

The sole public rendering entry remains the existing A010 owner4/frame8880 R21
entry. Row704-byte ABI, all descriptors/maps, palettes, majority-role/tie policy,
append behavior, errors and fixed font addresses are unchanged. Packed fontABF3,
widthsAEDB and GEOS_ROW_FASTAF5B stay exact. Actual payload4086 bytes, with8 free
bytes before the fixed font and10 after the helper tail. No new BSS or ZP.

Caller-private offsets P+32..37 are byte_ok, three coverage bytes, fragment index
and popcount subtotal. Old P+16/base is temporarily the third ink byte. These are
within the existing46-byte private suffix. The same two pointer loans are used.
The new helper adds a balanced JSR and a balanced one-byte PHA/PLA popcount
sequence; it makes no overlay calls. Overall stack bounds still require the
parent's actual integrated-byte CFG proof.

## Fast path and preserved fallback

A full-horizontal clip and completely visible nonnegative glyph may use the byte
path. Other horizontal clips, negative origins and right-partial glyphs keep the
original per-pixel compositor. Vertical clipping and intersecting9px lines use
the existing row logic. Generic partial-strip clearing is unchanged.

For each visible scanline, shift the16-bit base ink and advance coverage into up
to3 tile fragments. A16-entry nibble table computes each base fragment's ink
weight; add it to the existing role weight, saturating at255. Only after this vote
apply selection/caret flags2/4 as one coverage XOR, then OR the result into the
bitmap. Explicit inverse is already in base ink and contributes votes. Resolve
still scans14 weights and uses the original stable priority/tie order. This is
not the preview renderer's first-ink policy.

## R21-only GG specialization and guard audit

The validated row's `glyph_setup` writes encoding0 and complete GG clip
`(0,16,0,9)` in the protected fixed GG frame. No legal descriptor/map/source span
can overlap this frame. The private helpers omit only those invariant scalar
checks/branches. They retain the per-glyph style<4 check, exact font header,
width/fallback validation, selected packed-index span/order/width bounds and all
ink/metrics needed by R21. Raw width≤8 plus B/I advances≤3 prove all ink remains
inside advance. The private route therefore omits unused GG_COVERAGE publication
and full-clip masking; R21 never reads that private plane. These helper symbols
must not be exposed as the arbitrary-context public GG API.

The extra style check deliberately also preserves the original rejection when an
illicit map/style-array alias changes a style after the validation pass. Other
caller-array disjointness requirements remain the existing ABI contract.

Actual linked sizes: row CODE1719→1920 and tables202→218; measure340→262,
glyph703→556. Net217-byte compositor/table growth is funded by225 bytes of
R21-only GG specialization, leaving8 bytes before the unchanged font.

## Proof and reproduction

Use `tests/test_geos_literal_byte_candidate.py --variant control|candidate` for
the isolated component matrix. Use `--suite incremental|inline|fold|preview` for
private public-editor R21 SEO substitution, against frozen47 fixture
`build/geos-incremental-editor/20261025T122004452115Z/fixture`. No shared build,
production SEO replacement or native port is used. Control reassembly must match
the exact sealed original before its labels are accepted.

Final component matrix:2570 strips and65 fault cases per variant;6,579,200 bitmap
pixels and102,800 attributes per variant, exact saturating histograms/maps,
full64KiB guards and whole16MiB REU unchanged. Every PETSCII value/style/flag also
checks the genuine ninth row through a second intersecting run. Additional cases
cover signed/right boundaries, arbitrary clips, all14×14 role ties, repeated
saturating append, random two-run data and owner/frame/style/role/font faults.

Actual public gates:15 incremental +19 inline +28 folded +68 preview frames per
variant. All130 PNG files match the control byte-for-byte. Existing independent
pixel, source/bottom/anchor, history, capability, catalog, lease, shim and exact
16MiB guard checks are retained. General public GG tests are unchanged.

CPU instruction improvements are measured separately from native timing. No
native cycle or hardware-input claim is made by this private release.
