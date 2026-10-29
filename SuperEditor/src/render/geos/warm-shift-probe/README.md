# Warm-shift benchmark controls

The candidate below is now the canonical style-typing/wide.s implementation.
These preserved before/after sources and the private builder reproduce the
original differential component/public/native proof. Their source hashes and
private-substitution ancestry remain historical; the coherent canonical package
has separate registered62 CPU evidence. Native ready8 has48 actual captures and
24 exact PNG pairs. See ../style-typing/README.md and docs/PERFORMANCE.md.

The release notes below describe the private release before promotion.

## Original private release

Only `wide.s` is a production source candidate. SHA256:
`2a2b64fd064fe8bc64d2f8223afed97699706872b057a1ccc8144bff22e97684`.
Frozen original `wide-before.s` SHA256:
`a4965783550a40c031e91fd2d095fd9d6f046e2ef5c12071ec2d7bb2c6fb48ad`.
No canonical file, Make/shared output, Git, native process, or hardware changed.

## Promotion recipe and budget

Copy `wide.s` over `src/render/geos/style-typing/wide.s` (or apply `ready.patch` against the original SHA), rebuild with the existing `src/render/geos/style-typing/build.py` pipeline, and package normally. C32 and R30 MUST be rebuilt together: R30 embeds the sealed C32 raw/image CRC and length. No build flag, ABI/include/catalog entry, new resident state, BSS/ZP, frame, asset, font position, stamp, table or validation policy changes. Existing seven R30 helper vectors A020..A032 are unchanged. No JSR/call-graph edge or stack frame is added.

The real original source rebuild is byte-identical to the pinned product pair. Candidate C32 is3803 bytes (raw3771) versus3806/raw3774, R30 remains3662. Raw end is$5EBB, below stamp$5FE0;293 raw bytes remain. Original source guard/certificate/source packet/font capability/CRC/geometry/attribute checks are retained verbatim. Actual candidate pair on this binding:

- C32 raw-with-header `e5ddbc6afd038f612c2e27bf999dbd245e297a20b50de42f16f8fc58a3237128`.
- C32 SEO `710fa8fc95becfeff31ba06b0435503d74fc51b139e4d3bbf4ca629f6c2deeb3`.
- R30 raw `da5bbc82c31caa8a7c60ed22958ba2998f68fc5346f3343499d0694c1866ce2c`.
- R30 SEO `fd6eb710f9f6fad6428909910c0aca611b2012baa18d8bd9c5c9b70cdb283da6`.

Pinned current62 input: `build/cache-rebase-committed/20261026T224637147761Z/fixture`, PRG2924ddbc...a686 / binding39cea9cc8e4af5b2970e1030d502d7a4. This private CPU fixture substitutes exactly the two rebuilt SEOs and source-matched raw/labels/maps. Its original D81 and source ZIP are intentionally retained as input ancestry, not claimed to be a newly coherent product package. `build.py` extracts the original source closure into an independent private project, copies only128-byte frozen font widths, and replaces only `wide.s`. Original and candidate projects/build products are preserved. Root must qualify a coherent promoted package/native timing separately.

## Exact arithmetic

For source byte S[i] and n1..7, right-shifted output is `(S[i]>>n)|(S[i-1]<<(8-n))`; left-shifted output is `(S[i]<<n)|(S[i+1]>>(8-n))`, masked to8 bits. A third byte cannot affect these outputs. The original repeated three-byte chains did unnecessary second-neighbor loads and shifts. Narrow insertion now uses LSR previous/ROR current, narrow deletion ASL next/ROL current. For insertion n8+r (r0..3), the exact result selects immutable previous byte then shifts only r using previous-previous carry. Missing bytes at the beginning of the row are explicitly zero. Existing wide deletion is unchanged.

Prefix/suffix/end masks, dirty input-tail zeroing, source-before-output ordering, glyph/caret union and9-row output loops remain common. No fallback or input restriction is added: advances1..11 and all pixel phases retain their original validated semantics.

## Actual proofs

1. `python3 tests/test_geos_warm_shift.py --out NEW_OUTPUT`
   `build/geos-warm-shift/component1/result.json`: original1456 vectors plus698 dirty-tail/empty/EOF/near319 vectors and17 malformed-frame/attribute refusals per variant. All advances1..11, caret widths1..11, phases0..7, both directions, top16..183 and sampled/random row widths. Exact64KiB per-call output oracle, actual pending C6 source fixture, full16MiB provider/source/history/shim unchanged. Same2154 hashes, zero instruction regressions;47,118,779→40,183,154 total primitive instructions(-14.719%), max saving12942. Payload1156→1153 bytes. This is not an exhaustive Cartesian product of every old row width/top/phase.

2. `python3 tests/test_geos_warm_shift_public.py --out NEW_OUTPUT`
   `build/geos-warm-shift/public4-physical256/result.json`: genuinely rebuilt original pair (must match packaged bytes) and candidate pair,56 actual public key/render/idle intervals each. Five INSERT/BACK pairs and two RIGHT/LEFT pairs per ordinary Plain/Markdown/Full and Full strong interior. Explicit256 physical banks; actual typed DMA observation; independent pixels/source/caret, canonical/history preservation across render, real Undo/Redo witness, shim/catalog and whole16MiB exact outside authenticated FE `[0,64)+[0200,EA88)`. All pixel hashes match, all parser init/feed counts remain zero, same loads/steady DMA. Prior `public3` used inherited physical32 default (2MiB provider); it compared the16MiB address space but must not be described as actual16MiB provider proof. That limitation also applies to the earlier warm-input-profile archive; public4 is the stronger rerun and produces identical costs.

3. `python3 tests/test_geos_warm_shift_guards.py --fixture build/geos-warm-shift/public4-physical256/build-after/fixture --out NEW_OUTPUT`
   `build/geos-warm-shift/guards4/result.json`:24 actual Q/W/M insert/BACK transactions across plain/bold/italic/combined styles match a forced actual full-render reference and independent glyph/source oracle; complete header/live chars/styles/roles/X compare. Actual selection replacement and nowrap correctly decline the fast transaction and render exact fallback. Positive26 have preciseFE/whole16MiB and whole64KiB declared-write guards. Source requests/cache/read scratch and public object request/validation bytes are explicitly allowed by frozen symbols; document metadata/roots, object ownership tables, history/hot bytes and shim remain independently exact. Supplemental18 negative calls use the real R30 overlay-entry seam: foreign owners1/2/3, GEC0, old GTC generation1, GTC CRC, glyph/width mismatch, stage binding/body corruption via checked owner2 writes, catalog CRC/size/owner, physical owner, stale epoch, missing stage/worker, source token. All refuse with exact expected A/carry, canonical/history/pixels/whole16MiB/shim unchanged; foreign phase opaque. No C32 bytecode bypass or fake packet/certificate is used.

The guards4 fixture is the same candidate pair as public4, generated in public3; actual supplemental source setup explicitly uses256 banks. Host failures retained: missing include caused by relative builder paths; missing frozen font widths; supplemental mistaken2MiB-vs16MiB buffer lengths; undeclared document/object reader/request scratch. These did not identify product pixel defects; final guards use source-declared scratch and preserve all source/history assertions.

## Whole public cost and limits

Steady Plain INSERT42269→40883(-3.28%); BACK40783→39343(-3.53%). Full ordinary43381→41995 and41889→40449. Full strong46266→44511(-3.79%) and44758→42922(-4.10%). First keys also improve; first INSERT saves1338 ordinary /1707strong, first BACK1392/1788. Caret costs unchanged. These are CPU instruction counts, not native PAL cycles, physical input or IRQ latency.

The primitive win is substantially diluted by unchanged transfers, packet/source/certificate guards, whole-row copies, status and four actual overlay loads per edit. This is a small no-growth optimization, not a six-frame latency closure. The source guard and CRC tax is not removed. Large remaining costs and structural candidates are documented separately in warm-input-profile-probe/README.md.

All26 supplemental PNGs were directly inspected using two1:1 labeled contacts, no issue. The12 public profile PNG pairs are byte-identical to reviewed original/current62 CPU-oracle outputs. These are CPU-rendered screenshots, not native captures. No native proof is claimed.
