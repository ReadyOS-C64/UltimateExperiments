# Private plain-row typing primitive

`entry.s` + `patch.s` are an actual sealed R30 probe, not an editor typing
fastpath. The unchanged production editor supplies no inputs to it. The caller
explicitly supplies a trusted caret-free9x40 bitmap and a trusted plain9-byte
left-aligned glyph. All source/font/FE publication authority remains future
integration work.

The image is844B (patch CODE748/RODATA57, entry39B including16-byte binding), with
zero added resident BSS/ZP/REU. It loans existing `text_ptr` and `screen_ptr`.
`api.inc` specifies the96B caller frame at8B40,360B source at8200 and40B temporary
scanline at8380. Only42 frame bytes are currently used; the96B caller reservation
leaves room for an integrated controller.

Owner4 is checked before frame access. Inputs reject nonplain flags, top outside
16..183, advance/caret widths outside1..8, invalid320-pixel bounds and ink outside
the supplied advance. Both whole40-cell attribute bands must already match the
supplied plain foreground/background attribute. This conservative neighbor-color
restriction avoids changing a color shared by another logical line. Rejections
preserve bitmap, attributes, source and shim.

For each of nine scanlines, adjacent source bytes rotate by the advance, original
prefix and shifted suffix masks merge, the inserted glyph ORs into at most two
bytes, the vacated tail clears, and the new caret XORs into at most two bytes. It
writes exactly40 bitmap bytes per scanline in real VIC tile layout. The previous
live caret is irrelevant because the explicit source is caret-free. Attributes
are already correct and remain unchanged. No other pixels are written.

```sh
python3 tests/test_geos_typing_candidate.py \
  --base build/geos-incremental-editor/20261025T081538083121Z/fixture
```

Final proof: `agentsworking/evidence/M8/20261025T083310336943Z-geos-typing-candidate`.
It passed5227 pixel cases/30 refusals, including every valid x for both edit
operations and all advances1..8, every body scanline alignment, short/empty rows,
clipped end caret, all128 actual BSW9 glyph bitplanes and actual foreign source
leases1/7. The packed source font is checked against the frozen R21 image. Each
call has a whole64KiB expected-memory guard; the whole16MiB REU is unchanged.
Canonical source/history/hot state, ReadyOS shim and all foreign memory persist.
Earlier5097-case synthetic-only evidence remains separately retained.

Warm sealed-call instruction counts at x63 are approximately19401..29518 for
insert and18692..28745 for delete, across advances1..8. These are CPU instructions,
not PAL cycles or a claim of <0.15s typing. Font/cache initialization, FE transfers,
source certification, metadata updates and UI publication are not included.

## Proposed integrated C6/R30 contract

Keep C6 and R30 in separate overlay slots so the same two verified images remain
active across successive keys. Existing GEC20B is the mutation certificate:
`old revision/length + epochs + published sequence + exact canonical position and
old/new byte`. It is necessary but insufficient alone. R30 must independently
check the full source graph and typed FE ownership, page/header/GCC sequence and
key, exactly one revision/length/caret delta, and the plain complete CR/EOF row.
Missing/corrupt/stale/wrap/inline/fold/selection/pan/pixel overflow/neighbor colors
must fall back before pixel mutation. Source/history are never flushed by R30.

Use FE tail data exactly as requested:

| Offset | Bytes | Meaning |
|---|---:|---|
| E568..E9E7 |1152|128 normal glyphs,9 bytes each|
| E9E8..EA67 |128|screen-code widths|
| EA68..EA87 |32|magic/version/ready, exact build binding and font CRC witness|

A new one-time C30 builder can link existing measure/glyph/packed assets plus
warm checked cache transfers. It runs only after a complete paint, with owner4,
no source lease and the9px normal face/native8 fallback restored at4800. BEGIN
checks the metadata; each STEP constructs one actual glyph and writes9 bytes plus
its width; a final bounded readback CRC pass checks all1280 bytes before READY.
No source or overlay bank is used for this cache. Header validity is cleared
before an incomplete initialization can be observed. A compact trusted256B
per-glyph CRC table in R30 would let each edited glyph verify its fetched9+width
bytes without a full1280-byte CRC every key; this is additional protection beyond
the typed epoch/owner and full build/font witness.

R30 must refresh the row prefix/chars/styles/roles/X boundaries, following-row
canonical prefixes, page key/bottom/caret fields, caret-free GCC bitmap cache,
current caret rectangle/key/sequence, GEC consumption and the real status row
before the root publishes the new sequence. It cannot invoke R27/R21 from inside
its R slot. Any interrupted/failed transaction leaves derived validity clear;
normal rendering must recover from canonical source. A subsequent C6 edit may
issue a new GEC only after the preceding new page/GCC sequence is fully published.

### Version2 cost and a precise version3 migration

Current C21 `canonical` emits LEFT and RIGHT as the exact same `FIRST+index` for
all count+1 boundaries. Current rendered source is literal (D141); hidden-source
geometry remains deferred. R28 currently rebases all these24-bit entries for all
following rows, although their X geometry does not change. No version2 writer
may skip them while existing readers consume them.

The actual version2 readers requiring coordinated migration are C22
`read_right/read_left` and `tail_right/tail_left`. They can form the canonical
24-bit boundary as FIRST + current packet index (or count for tail) with checked
addition. C23 reconstructs its hit maps through C20 rather than reading these
arrays. R27 already computes caret-FIRST then reads X. Root should still audit
all consumers and frozen oracle/version checks together before publishing3.

A version3 literal packet can retain the32B prefix, chars/styles/roles and X arrays
at their current offsets, but omit LEFT/RIGHT storage at842/1328. This avoids972
redundant bytes per full row without changing slot size or existing X positions.
R30 then needs to shift/update the edited packet's characters and X boundaries,
and adjust only START/END/NEXT/FIRST of later prefixes, plus header bottom/key.
Summary-tail hidden selection remains its separately guarded canonical range.
An explicit schema/literal-identity flag is safer than silently overloading2;
future hidden-delimiter geometry must select a different representation.

The844B primitive leaves3252B inside R30, before integrated source guards,
checked FE transfers, packet updates,256B glyph CRCs and status. A real link is
required before committing that budget. C6 currently occupies2543B/4096 and may
host extra publication/certificate work if needed; it must not duplicate or
weaken R30's independent source/FE checks. The planned C30 builder is independent
of this hot size and does not need resident BSS/ZP. Root owns any shared entry,
status-only chrome flag, schema consumers, build or dispatcher changes.

## Released private C30 builder

`font-cache.s`, `font-cache.inc`, `font-loans.s`, `font-witness.inc` and
`build-font.py` now provide the actual producer described above. This private
image links at3281B/815B spare with the existing measure/glyph/assets and
`cache.s -DSE_GP_CACHE_WARM_ONLY=1`. The linker is the unchanged overlay-c.cfg;
there is one module-bindings alias object. It is slot1 ID30; the primitive is
slot0 ID30. There is no new resident BSS or zero page.

Owner4 guards every operation before frame access. BEGIN0 returnsA1 for a new
build orA0 for the matching READY tag. STEP1 constructs/writes one glyph and
width, then checks five256-byte readback units;133 STEP calls complete a new
cache. CANCEL2 returnsA0, retaining READY0 for an interrupted build. Index<128,
phase1/2 and verification block<5 are enforced before using continuation offsets.
The32B READY header commits only after the actual readback matches the trusted
normal-font CRC. A matching header includes the exact resident build binding.

The actual GG frame is8B40..8B8C, control8BA0..8BA4, and transfer buffer9000..90FF.
The parent9134..9177 controller is untouched; shared checked transfer request
9178..917D is used normally. This must be scheduled after a complete literal
page, with no source lease and before root caret capture/publication, retaining
C30 across pending slices. It is not a font or source allocator.

```sh
python3 src/render/geos/typing-candidate/build-font.py \
  build/geos-typing-candidate/private-font \
  build/geos-incremental-editor/20261025T081538083121Z/fixture
python3 tests/test_geos_typing_candidate.py --smoke --font
```

C30 proof: `M8/20261025T084331872628Z-geos-typing-candidate/font`. A real current
editor source/mode/paint produced the FE page; the builder then produced all128
normal glyphs, exact1280-byte cache and metadata with wholeRAM/16MiB/source/shim
and live bitmap/page/cache guards. It also passed24 wrong-owner calls, seven
cancellation checkpoints, actual typed-DMA glyph corruption/readbackCRC94 and
retry, six malformed continuation cases and six epoch/source/ownership faults.
The cold-inclusive peak is50127 CPU instructions. No editor typing integration
or native latency result is asserted.

## Complete private C6 / R30 controller (source release)

`build-worker.py` links `worker.s`, `guard.s`, `patch-buffered.s`,
`status-normal.s`, `status-raster.s`, and `transfer.s`, then the one generated
resident alias object, using `cfg/overlay-r.cfg`. R30 slot0/id30 entry is op3.
The real C6 extension is `certify.s` plus `transfer.s`; call
`se_gtt_certify` immediately after the existing `se_gec_capture` at MARK.
`build-c6.py` demonstrates that change against an immutable product archive.
C30 uses the separately released normal-font builder.

R30 op3 checks owner0 before reading any phase state, acquires owner4, performs
bounded begin/paint/commit phases, and releases owner on every return. A0/Cclear
means publish once through the existing `se_er_published`; A2/Cclear means fall
back to the existing R28/full producer. Readonly misses retain GCC/GEC; a failed
partial transaction invalidates derived publication. Cset is a real transport
or provider error. There is no public asynchronous overlay continuation.

This version verifies all 1280 cached normal font bytes against a sealed CRC on
each admitted edit, then compares the exact prefetched glyph and width. It is a
size-conscious first working controller, not the final latency optimization.
Only plain wrapped BSW9 rows with no selection/folds/inline/styles/token roles,
zero pan, clean normal UI, CR/EOF ending, index greater than zero and total width
strictly below320 are admitted. Both whole intersecting tile attribute bands
must already have the same role0 color. Exact320 reflow, first-character edits,
unsupported shapes and shared color bands fall back.

The 47B certificate at9149..9177 is retired phase storage, not new resident BSS.
R30 copies it to8BA0, uses private control8BCF..8BFF, bitmap staging8000..827F,
caret-free nine-scanline buffer8400..8567, temp8580..85A7, ABI3 packet8D00..9049,
header90CA..9109 and metadata910A..9129. Existing text/screen pointers are loaned.
FS save/parent flags912C/912D and the ReadyOS shim remain untouched.

`worker_gate` in the owned test executes real C6 insertion, successive insertion
and backspace, compares every live VIC pixel/attribute to an independent source
oracle, and compares all live ABI3 packet fields plus caret-free **body** cache
bytes with a separately forced-full editor. The cached header/status bitmap is
not refreshed; only physical body rows2..23 and their attributes are authoritative
for the current tile-only caret restore consumer. Live chrome/status are correct.
It also checks a readonly color-band refusal preserves GCC/GEC/FE/source and an
owner1 file phase is opaque. This is a private routing/publication seam proof;
no production root/native/timing acceptance is claimed.
