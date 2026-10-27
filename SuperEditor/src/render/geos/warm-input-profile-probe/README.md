# Warm input attribution support

The runner remains a test dependency for the warm-shift component/public/native
suite. The profile notes below describe its original release and proposed next
work at that time. The byte-shift candidate has since passed native48 and is now
canonical; see ../style-typing/README.md. Original reduced-provider profiles
remain distinct from later explicit256-bank runs.

# Current62 warmed input attribution (CPU instructions)

Pinned input: `build/cache-rebase-committed/20261026T224637147761Z/fixture`.
PRG `2924ddbc0379cdfdeba3b9d57c386d9bb0db0f764d6e174fdfc59e660021a686`, binding `39cea9cc8e4af5b2970e1030d502d7a4`, D81 `2379bd2a779833fb25f7d8685296e5ebab3dced1b16992e91d06792f194acd98`.

`python3 tests/test_geos_warm_input_profile.py --out NEW_DIRECTORY`

This is a read-only CPU observation extension; it builds only its own runner. Actual registered62 assets execute unchanged. Setup uses real source/provider import, typed syntax/mode/top commands, public RIGHT and INSERT/BACK keys. Each of ordinary Plain/Markdown/Full and strong Full runs five INSERT/BACK pairs then two RIGHT/LEFT pairs. The public CPU PC/SP call/idle seam is disclosed: this does not measure native cycles, raster/IRQ contention, physical keyboard latency, or natural startup stack.

Results: `build/geos-warm-input-profile/current62-full/result.json` (56 intervals) and supplemental `build/geos-warm-input-profile/callsite-plain/result.json` (8 intervals, adds ordered overlay/window-change events and local stage-loop attribution). Each directory saves the exact verifier used. Source metadata/payload/labels are from the pinned fixture; reviewed source files match its source ZIP. No product patch is supplied.

| Dataset | First INSERT / BACK | Last INSERT / BACK | Warm RIGHT / LEFT |
|---|---:|---:|---:|
| Plain ordinary | 222733 / 118342 | 42269 / 40783 | 9524 / 9709 |
| Markdown ordinary | 223466 / 119086 | 42166 / 40674 | 9526 / 9710 |
| Full ordinary | 224680 / 120301 | 43381 / 41889 | 9526 / 9711 |
| Full strong interior | 227582 / 123182 | 46266 / 44758 | 9779 / 9773 |

All measured operations execute zero real SuperMark/inline/lexer init/feed entries. This is warm certified-local typing, not general edit/reflow or the first semantic page build. The first caret after typing costs 73377–73630 instructions / eight loads, then warm caret costs zero loads. Input, publication-completion, and optional idle intervals are separate fields; optional idle is 946 instructions. Publication-completion means the public renderer returned, not the first changed VIC pixel.

## Dominant work and actual load order

Ordinary Plain steady INSERT42287 self instructions: C32 staged transaction23869, resident8330, R30 gtype5245, C6 window3811, R14 source535, AUXsmall remainder. BACK40791: C3222539, resident8142, R305224, C63842, R14535. Inclusive call/module counts overlap; exclusive self counts alone sum to the operation total.

C32 local-region counts on INSERT: whole-row bitmap copy3610, bit shift3069, gather1999, scatter1990, byte setup1881, base copy1602, attributes1200, tail zero972. BACK: bitmap3610, shift2700, gather1999, scatter1990, base1602, left setup1440, attributes1200, tailzero1008. Nearest local-label ranges are instruction regions, not asserted semantic loop-only counts; the detailed PCs are saved.

Every steady edit actually calls C6(id6)/op3-or4 → R30(id30)/op3 → AUX(id13)/op6 → R14(id14)/BEGIN0. All four reload, fetching14809 owner2 bytes. The post-publication AUX source-checkpoint refresh evicts C6 and R14 evicts R30. First INSERT primes the executable C32 window, then first-ever AUX strict load at resident `request_stage` clears its shared GF_VALID42; hence first BACK primes it again. The event trace records the exact instruction causing 42→0. Subsequent loads are managed-verified and preserve the staged window.

Steady FE requests: six stashes1674B;22 fetches2108B INSERT /2112B BACK. These include full842B row packet and640B caret-free tileband transaction. Steady CRC is only88 certificate bytes plus10 glyph/advance bytes (~1032–1074 self instructions); CRC removal is not the primary target. C6 already checks actual row COUNT style/role bytes, despite an obsolete whole-array comment.

## Next bounded candidate

First pursue exact byte-shift simplification, preserving the generic primitive and every surrounding certificate/source/font/stage/packet guard. For advances1..7, the second-neighbor byte cannot reach the output through the third-byte carry chain; omit that fetch and shift. For insertion8..11, displace one byte then shift remainder0..3, analogous to existing wide deletion. This is general phase/width arithmetic, not an AT/string special case. Require complete primitive differential/negative vectors and the same56 actual-public intervals before measuring gain. No speed claim or variant exists in this profile release.

Larger subsequent opportunities are the measured whole40-column base/VIC copies and640B transfers for a ~100px row. A bounded dirty-width path would need proof for old/new tail, old/new caret, dirty input-tail clearing, adjacent rows sharing physical bands, and attributes. Existing generic unused-tail-zero semantics must remain; simply skipping zero stores would be incorrect. Post-publication refresh routing could save two loads only with an explicit freshness/checkpoint contract; a valid-bit shortcut is not proposed. These are not implemented here and do not overlap general wrapped semantic convergence.

## Correctness and limits

Every measured render preserves the exact post-key canonical source/history/hot state. Merged bytes/caret and independent Plain/Markdown/Full bitmap+attributes match after every key. Final actual Undo/Redo proves source restoration. Catalog identity and ReadyOS1024 shim are unchanged. Actual checked DMA is observed for every interval, and the whole16MiB comparison permits only authenticated FE `[0,64)` plus `[0200,EA88)`; FE64..1FF/EA88..FFFF and all other banks stay exact. Actual edits in this setup remain pending-hot; immutable document/history REU is therefore unchanged. This does not claim source graph immutability for a future edit that flushes/appends history.

Twelve original CPU-oracle PNGs were visually inspected in a labeled 1:1 contact, with no issue. They are CPU-rendered evidence, not native VICE captures. Two preserved host setup failures precede the successful smoke: runner recursion and missing C++ `<cstdlib>`; neither launched a product test. No ports/native/hardware/Git/shared build were used.
