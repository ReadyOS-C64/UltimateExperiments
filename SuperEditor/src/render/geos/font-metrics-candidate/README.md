# Preview-only trusted font metrics candidate

Released actual private proof: `build/geos-font-metrics-candidate/20261025T082539388324Z`.
Control R23 reassembles byte-for-byte equal to immutable42-asset080336fixture,
PRGe0c9007124f0031037266ec8f29156a67e5a7a1af55c2443910946958766cab9.
No existing production or shared build files were modified by this lane.

## Integration

Promote this directory's `catalog-glyph.s` as a separate production
`catalog-preview.s` and link it ONLY into R23, replacing that image's ordinary
catalog-glyph object. Keep generic `src/render/geos/catalog-glyph.s` unchanged
so the standalone public primitive retains independent linkage. The candidate
wrapper imports/calls `se_geos_catalog_glyph_preview`; fontstore remains the
actual unchanged runtime module compiled with SE_GEOS_PREVIEW_FAST=1.

Candidate R23 is3581B versus3373B control (+208B), leaving515B in4096.
No new BSS, ZP, resident state, settings schema or phase frame. Existing CG
scratch COUNT stores a per-call private-path flag until index selection.
The private entry temporarily pushes the two context-pointer bytes around the
actual FD guard because fontstore borrows those same pointer loans. No CPU
stack worst-case or native-cycle bound was measured by this glyph test.

## Trust and API

Strict `se_geos_catalog_measure/glyph` still validate the complete font index.
The added preview entries first require owner4, then retain full frame/scalar,
encoding/style/flags/clip, native/font span and overlap checks. Packed private
entry requires font pointer5000 and exact verifiedGF_LENGTH. It calls the
actual `se_gf_fetch_preview`, including full face/capability/epoch/mapping/load
witness and expectedCRC verification/refill semantics; a caller-set Boolean is
not authentication. All header/stride/height/baseline/exactextent checks remain.
Only the whole96/97-index ordering walk is omitted for the authenticated raw
catalog. Selected start/end ordering/width and end<=stride*8 remain checked.
Native-only pointer0/length0 takes the matching native path without a packed
font-store dependency. The wrapper initially retains its own guard as well;
this deliberate extra guard prevents direct privateentry callers bypassing it.

## Evidence

All43 packed faces:79,523 paired wrapper/rawglyph/style/inverse/clip/measure
cases, plus4096 native-only pairs. Every real glyph uses all8 B/I/U styles and
both inverse flags. All outputs match actual control R23 and an independent
rawfont metrics/ink/coverage model. Every glyph call checks all64KiB RAM against
exact allowed frame/pointer/stack/fontwindow/FDdescriptor/DMA-request writes.
Every face and fault group checks all16MiB REU bytes. The authoritative fixture
explicitly sets256 provider banks and overrides the inherited2MiB reader.

187 counted fault/boundary calls in10 groups preserve strict scalar/context/
malformed global-index errors, foreign-owner opacity, exact trusted pointer/
length, actual FD owner/map/epoch/READY/busy refusal, refill after sticky staging
borrow/loadtag change, strictFETCH CRC-on-hit and selected-index extent bounds.
Existing public primitive sources and their default159178-call test remain
unchanged; this proof does not claim that whole historical suite reran here.

The measured43-face operation work is1,488,963,336→1,071,493,581 instructions:
28.04% reduction (1.390×). BSW9 is25,841,735→15,703,238 (39.23%,1.646×).
These counts include each actual invoked glyph route and first cold face fetch,
exclude host/direct-test prefetch setup, and do not predict whole preview-frame
or native C64 cycle speedups. Source/GUI/native integration remains root-owned.
