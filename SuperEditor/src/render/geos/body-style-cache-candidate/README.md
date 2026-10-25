# Actual C26 result retention across C20 rows — private release

Source is frozen. Apply `ready.patch` to immutable6604 input
`build/geos-incremental-editor/20261025T204511293143Z/fixture`:

    patch -p1 < src/render/geos/body-style-cache-candidate/ready.patch

Patch SHA256:
`e6e2d5759c41114279c248fb7b4eff5268ced0524584a2f9168eb876fd4b257d`.
It modifies source-line.s/source-inline.s/style-window.s/fold-entry.s and adds
body-cache.s/body-cache.inc. Other copied sources in this directory are
unchanged release dependencies. No coordinator/C26/resident/cfg edits.
Root Make integration: append `build/geos-prod/body-cache.o` to GEOS_FOLD_OBJ,
assemble src/render/geos/body-cache.s with the existing minimal editor-api.inc
and `-I src`; add body-cache.inc to source-line.o/fold-entry dependencies.
R24 keeps cfg/overlay-r.cfg and normal GEOS_IMAGE binding generation exactly
once. Existing C20 `SE_EDITOR_GEOS_INLINE=1` remains. No new compile flag.

Private build/rebind (never shared Make):

    python3 src/render/geos/body-style-cache-candidate/build-once.py OUT FIXTURE

On frozen bc032951a4ff040b1cd687f8eb175884 binding:

| image | payload | full SEO SHA256 |
| --- | ---: | --- |
| C20 geosline |4088|d9708dddb478810c8083cf0df9d8c803afee6a2a0571d7f48c34a2c1c35a5eff|
| R24 geosfold |3125|60bac9ae7214eed60eefbe05b6410653297887ffd79910353f51a30f3bd637ab|

Repeated private builds reproduce both images exactly; all46 other assets and
resident are unchanged. Default non-inline source-line remains byte-identical
494B, SHA8711a155...83ff3db under the same generic external-binding seams.

## Lifetime and checked ABI

Owner4 is checked before all phase access. Old R24 ops0..2 preserve fold
behavior; new3 LOOKUP returns A0hit/A2miss, Cclear;4 STORE returns A0stored or
A2optional-capability-miss;5 COUNT returns min(160,END-SCAN) in A/Cclear;
6 CANCEL/revoke writes VALID0 only to an authenticated ownedFE allocation.
Cset preserves genuine source/provider/argument errors. No held transaction or
read lease is owned by this helper. C20 still owns/releases its actual R14
lease, native32-byte packets and fresh59-byte source-identity comparison.

These ops are a private proportional-source C20 continuation API. GS_ACTIVE,
CONTEXT_VALID and saved actual reader active/owned must be1. Every lookup/store/
count independently compares ALL59 saved source fields against live resident
metadata, rejects busy mutations and validates all three typed source tokens.
The same original R14 read/guard still precedes every packet. Thus repeated
metric/layout calls do not skip source authority.

Only actual successful C26 outputs are retained: up to160 style bytes plus160
semantic roles. No host-inferred style or guessed delimiter closure. Full BODY
closing-delimiter parsing stays unchanged. Full source key + logical
START/END/BODY/ROLE + C26 catalog size/CRC witness + FE capability + complete
CCITT-FALSE record CRC must match before returning outputs. Mutable managed
image_slot bit7 is masked only to obtain declared slot identity. A changed,
missing or incompatible helper is refused; oldR24 returns clean90 and missing
R24 clean17, then normal root cleanup releases only its source lease.

The record window is canonical24-bit, bounded by logicalEND. A later native
packet partially beyond that end receives ordinary base appearance; no query
prefetches beyond END. C20's within-job window and current161-byte output
certificate retain their existing behavior. C26's separate WIDE4/161 path is
unchanged. This is literal editable GEOS; no hidden source-map claim.

## Exact memory and publication

- Existing typedFE bank: reserve FC00..FDFF512B, actual record FC00..FD9F416B.
  FD A0..FFFF is unchanged. EA88..EB68 preview metadata and EB69..FBA8 glyph
  cache are live and preserved. No additional allocation/bank.
- CPU8600..879F416B is explicit transient DOC_LEAF scratch; se_doc_invalidate
  precedes use. Header8500/sourcepacket90EC/parent9134..9177/GSEM8B40..8BFF stay
  unchanged. R14 later refills only its own checked source scratch.
- Private work45A0..45A7 eight bytes comes from the old unowned plan suffix.
  Exact untouched suffix fragments4592..459F and45A8..45E5 are guarded; packed
  continuation45E6..47F2 and13-byte tail remain protected.
- CRC covers413 bytes (all416 except VALID and its two CRC fields). Source is
  rechecked after bulk write, before publishing VALID1. FE ownership/map/epoch
  is revalidated before EVERY checked DMA. Partial/error writes leave VALID0.
  Publication uses two1-byte invalidation/validation stashes around the416B
  bulk stash. Lookup only reads. These synchronous bounded ops do not yield
  with a held cache transaction. No new BSS/ZP/resident bytes/assets.

## Terminal qualification and measured tradeoffs

Actual public CPU: inline19, capacity11, fold28, incremental15, five high24/
pending/pan/exactwidth boundaries; original bridge22frames/21fault groups plus
22 body-cache groups. These include correct-CRC invalid styles/roles, all
metadata corruptions, full source change,24 foreign-owner calls, foreignlease
STOP, real bulk-DMA-entry source/FE-owner injections leaving VALID0/no foreign
REU writes, explicit revoke/refetch, missing/oldR24 clean recovery. Existing
independent pixels/source/history/catalog/shim/typed16MiB guards are retained;
only the exact new416B FE span and8B phase workspace are added to allowances.
All48/seven-helper static stack stays52 foreground +16 IRQ/NMI relative idle.

Whole-page CPU instructions versus released lookahead: diverse422 +0.04%,
inline406 -5.81%, long863 -25.29% (19→6 fullBODY queries,582→231 R14 READs).
No-marker work is virtually unchanged. Cold tiny/single-row pages cost about
3..3.8% extra for record admission/publication; this is an explicit regression.
A retained same-body page can avoid its single parse. Wide-W200 cold improves
16.40%; short-word wrap improves11.40%. Requested bytes are not DMA totals.

Normal PAL native A/B four forcedfresh TOP0 renders, actual IRQ/VIC/REU:

| source | lookahead cycles | cached cycles | change |
| --- | ---: | ---: | ---: |
| diverse422 |9,077,539|9,116,006|+0.42%|
| long863 |32,677,163|23,566,285|-27.88%|
| wide212 |8,736,407|6,948,067|-20.47%|
| short20, retained same body |1,772,531|1,663,478|-6.15%|

Native256k pixels/attributes per variant match the independent oracle, allfour
PNGs are byte-identical A/B and directly reviewed. Explicit public-entry PC/SP
stopwatch intervention measures actual foreground completion; warp is OFF
during timed intervals, ON for setup. First publication and quiescence differ
only~120..163 cycles in these full repaint cases. This is not physical-key
latency or a worst-case bound. Native guards cover exact source/assets/catalog,
shim/probe/stack/disk and rendered pixels; CPU gates separately retain typed
whole16MiB guards. Do not call native timing wholeREU immutability.

Both owned VICE processes closed and8300/text8400 were released. No product
promotion or final combined fixture/native/lifecycle acceptance is claimed.
Long/structural full redraw remains too slow; M8 is still active.
