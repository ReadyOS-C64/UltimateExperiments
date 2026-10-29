# Incoming SuperMark checkpoint candidate (private, source GEOS only)

This is a tested private C21 producer/C24 consumer pair, not a canonical change.
`build.py OUT FROZEN_FIXTURE` first requires a byte-identical sealed C24 control,
then links C24 with TRY_SEED and C21 with the producer. It does not invoke Make,
change the product, allocate another asset/bank, or edit C23. On combined48
171440, C24 is 3926/4096 bytes and C21 is 3768/4096 bytes. There is no additional
resident BSS, zero page, or REU allocation.

## Frozen first-checkpoint contract

Typed FE bytes **0600..063F** contain one 64-byte record. This is row0 slot0200
plus0400, beyond the occupied842-byte ABI3 packet. No other row's +0400 area is
reserved; the separate source-grid authority lane reserves1600..16FF.

| Offset | Meaning |
| --- | --- |
|0..3|magic53, version1, length64, VALID1|
|4..6|canonical incoming logical START24|
|7..34|full actual guarded merged-source key28|
|35..40|incoming fence, language, regions, regionOverflow24|
|41..61|zero/reserved|
|62..63|little-endian CCITT (initialFFFF) of bytes0..61 including VALID1|

The key is canonical metadata/original/append tokens15, docgeneration2,
visible revision4, merged length3, REU epoch2, document epoch2. It describes the
actual R14 snapshot, not a guessed render-damage union or a raw-bank pointer.

Private C24 operation **3 TRY_SEED** uses ordinary overlay frame op3, owner4.
Input QUERY is the caller's canonical24 anchor at8B40;8BF3 must be a saved actual
GEC_VALID value0/1. Only the full sequence/revision/length/epoch proof can admit
an edited source, regardless of that provisional byte. Root remains responsible
for taking the snapshot before a failed R28 attempt consumes GEC_VALID.

The operation returns A0/Cclear on completed hit **or optional miss**, genuine
R14/source failures retain the existing Cset path. It performs no source READ
and never scans to QUERY on a miss. Output:

| Address | Meaning |
| --- | --- |
|8BF4|proof0 miss /1 exact published source key /2 single prefix-preserving GEC|
|8BEA..8BEC|accepted original logical START24, meaningful only if proof nonzero|
|8B5C (existing CP_VALID)|2 trusted incoming parser state, or0 miss|
|8B7A (existing CP_NEXT)|accepted incoming canonical anchor|
|8B7D..8BCB (CP_STATE)|79-byte initialized parser with exact incoming carry|

The existing counted R14 read lease is ended before TRY_SEED returns, including
miss/failure. No lease crosses C20. Next ordinary C24 BEGIN accepts CP_VALID2,
validates its full current key/mode/QUERY>=anchor, restores incoming state and
runs the real parser. Unlike CP_VALID1 it cannot serve a cached event. Caller
must still invalidate ordinary CP_VALID on phase reuse as before. Proof is not
an enduring resident capability and is invalidated by later phase use.

The lookup checks FE handle/physical/epoch against the actual last source-page
GCC witness, current typed logical/physical ownersFE, nonretired/nonzero provider
epoch, source widthFF, and actual R14 capability/snapshot. Exact-key reuse also
requires actual GCC_VALID1 and GCC's complete published source key. Edited reuse
requires GEC's actual last publication sequence, matching old visible revision
and length, current revision exactly old+1 without wrap, unchanged committed
generation/tokens/epochs, exact length delta1 and editPOS>=incoming START.
Multiple unpainted edits, representation flush, replay, foreign maps, invalid
record CRC or changed prefix decline. No committed-generation rekey is guessed.

## Producer hooks

`build.py` generates the following minimal C21 changes:

1. After the real owner4 claim (never before its owner check), snapshot GEC_VALID
   to8BF3.
2. At `classified/@ready`, before C20/C25 phase reuse, call `gsc_publish`.
3. Include `publish.inc` in C21.

C24 captures9 actual incoming bytes at8BEA..8BF2 before feeding the matched CR,
or before EOF finish, and sets CAPTURED8BF6. Its persistent parser carry is
exactly fence/language/regions/overflow24; it never infers these from role0.
Private block internals are derived from the **actual linked** `se_sm_state`
(offset20 sm_line, offset76 overflow; link assertion state79); they must not be
silently imported from the editor style parser's different8E.. aliases.

The producer requires LINE0, CAPTURED1, genuine incoming START==current TOP and
full key equality with the actual freshly guarded GEOS header. It uses the
existing checked FE writer and source-cache invalidation. It writes64B with
VALID0 followed by the single VALID1 byte; errors disable this optional record
and do not fail the source render. Softwrap TOP declines. Existing literal
packets, canonical roots/history/selection and fonts are unchanged.

The first pair publishes one checkpoint only. It does not automatically invoke
TRY_SEED, rekey a record after every incremental edit, or accelerate C23. Root
owns those integration decisions and all new consumer scheduling.

## Local E_POSITION consumer authority

A successful semantic proof is necessary but not sufficient to reuse viewport
geometry. Initial C23 localE47 should additionally require accepted START==old
TOP, target>=oldTOP, old editPOS>=oldTOP, and independently checked old GCC
TOP/pan/fold/mode authority. It can then initialize relative ordinal0/TOP_ROW0
and run actual C24/C20 from that anchor. PAGEglobal±171 remains unchanged.

Actual far CRjoin is **not** covered: before BACK, TOP65817/docgen2; BACK removes
CR65816 before TOP, and resident reveal flushes before C23, yielding TOP65800/
docgen3. The old checkpoint must miss. The measured225,359,621 instructions and
9403 C24 queries remain a distinct open navigation/performance issue.

A sound follow-on can preserve the immediately preceding logical incoming9B
at9000 before each skipped CR, capture the target9B only once, and publish a
second64B record at0640. It still cannot cross a flush without explicit commit
representation authority or changed pending-reveal routing. That follow-on is
not implemented in this released first pair.

## Evidence and limits

- Actual source+R14+pure parser codec:6 scenarios,385 record faults and28 current
  identity faults, all malformed misses preserve parser79/record64.
- Actual private sealed TRY_SEED: near and65807 anchors; FE/capability/CRC/input
  faults, foreign-owner opacity, actual C6 pending certificate. At far65807,
  BOF query12,678,804 CPU instructions/2058 steps becomes lookup5244 plus seeded
  query11560/2 steps. An actual pending insertion uses lookup5333/query14789.
- Actual public C21/C24 producer:4 source GEOS frames including65807 ASM carry;
  independent256,000 pixels,4000 attributes, canonical/history/catalog/shim,
  whole16MiB guards. Exact occupied842-byte row packets, checkpoint64, existing
  GCC/backup/GTF spans only may change. GTF128x9 glyphs/widths independently match
  the immutable font assets. The ACTUAL emitted record feeds TRY_SEED.
- Peddle CPU instructions are not native cycles. No native evidence, C23
  integration, automatic parser speedup, preview support, or completion claim.
