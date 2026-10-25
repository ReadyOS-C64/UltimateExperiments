# Completed inline-body receipt feasibility — private, not integrated

Do not edit the released body-style-cache-candidate. Input is frozen6604 plus
that exact released C20/R24 pair, not mutable canonical. Cost verifier:
`tests/test_geos_linear_body_profile.py`; result
`build/geos-linear-body-profile/20261025T212353279337Z/result.json`.
The profiler rebuilds C26 from its frozen source and asserts byte identity with
its actual3327-byte payload before trusting any labels.

| actual TOP0 render | long863 | long436 | manypairs800 |
| --- | ---: | ---: | ---: |
| whole render instructions |6,229,609|3,074,097|6,927,234|
| actual parser feeds |5,142=6×857|1,296=3×432|4,800=6×800|
| parser-feed inclusive instructions |175,038|44,145|203,472|
| C26 entries / inclusive instructions |274 /987,710|99 /301,473|798 /1,811,644|
| C26 reader calls / inclusive instructions |401 /582,208|123 /176,104|920 /1,251,695|
| R21 inclusive instructions |3,333,385|1,756,757|3,127,299|

Inclusive columns overlap; reader includes resident/actualR14 work. This is CPU
instruction attribution, not cycles. Exact independent pixels/attrs/source/
history/catalog/shim and original typed16MiB write guards pass. Whole render
stops before905 post-render verification instructions counted by the separate
query profile. Native long23,566,285PAL cycles belongs to the released pair's
independent native gate, not a new receipt optimization.

The six-window body scan is confirmed, but eliminating *all* C26 has only a
15.9% whole-instruction upper bound in long863; R21 remains53.5%. No eventual
speedup estimate is justified yet.

## Candidate executable boundary

Persist actual completed SM_PAIR/SM_ESCAPE events, in original emission order.
Each event10B = kind/style/width/open24/close24/reserved0. No inference of
unmatched delimiters: only the actual parser emits closed spans, and a receipt
becomes usable only after successful FINISH plus final event drainage. Empty
completed event lists certify literal unmatched input. Replay uses unchanged
C26 clipping/style/code-exclusivity/hide handlers; canonical bytes still come
from actual C20 R14 READ32. Input remains source-literal, no marker hiding mode.

Metadata96B +400events×10B =4096B exactly. Proposed FE spanD568..E567 is the two
former R28 row backups. Existing live oldheaderD528..D567, GTF_DATAE568..EA87,
preview metadataEA88..EB68, glyph cacheEB69..FBA8, and released BSC FC00..FD9F
are excluded. Source definitions GEX_ROW_BACKUPS=0 and no active references in
edit-cache.s/typing/*.s/style-typing/*.s/code-typing/*.s support the dead-backup
finding. Historical *candidate* sources still contain those names and are not
permission to overwrite live data. Parent must approve the actual ownership
change before any production use.

Bind source identity59B, logical START/END/BODY/baseROLE10B, FE capability4B,
C26 size/CRC4B, count2B, eventCRC2B, headerCRC2B and version/state in96B. Guard
all header bounds before reading records. Validate CRC before appearance output
publication; private style arrays may be filled speculatively but never exposed
on failure. Publish VALID last, revoke on partial write/error. Overflow beyond
400 falls back to original parser; a source-key-bound negative overflow result
may prevent repeated failed capture, but must never certify styles. Source-
change/cancel/foreign ownership use existing exact epoch-safe cleanup.

A bounded 80B batch fits GS_OVERLAP9096..90E5 while C26 owns the continuation.
Actual C26 reader uses realFS8EE0..8F35, snapshot9040..9095, packet90EC..910B;
it does not touch9096..90EB. C20 restores/saves the overlap before its next
reader call, so the batch is dead on handback. This avoids borrowing GI outputs
past COUNT, which would violate the generic output-tail guard. Caller-private
22B8ECA..8EDF follows GI_LAST_ROLE at8EC9 and precedes realFS8EE0; this is an
explicit placement to prove, not a new resident allocation.

## Fit gate before integration

Existing C26=3327 leaves769B; released R24=3125 leaves971B. C20=4088 leaves8B,
so it should remain byte-identical. New receipt dispatch should live in R24
ops>=7 and reuse its full source/capability/producer checks. C26 needs optional
BEGIN probe/capture, an event hook, FINISH/commit, and cached-event feed phase;
generic ops/default behavior must remain unchanged when disabled. C26→R24 is
legal; R14 guards return before R24 executes, with no same-slot nesting. Root
still services the sameC26 request and preserves STOP between bounded STEPs.

An actual small assembler size probe is required: 769+971 cannot be treated as
an already-proved full controller budget. No new asset/resident/BSS/ZP/bank,
no weak source guards, no overwrite of current416B FC00 record. Disk pressure
currently forbids another large fixture/REU/native capture copy; small objects
and maps may use the existing frozen source path. This note is a measured
boundary, not implementation completion or a quadratic-work speed claim.
