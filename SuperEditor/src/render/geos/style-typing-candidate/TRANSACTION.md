# Private styled typing transaction handoff

Released 2026-10-25; no canonical production/Make/router edits from this lane.
Managed-current proof: `build/geos-style-transaction/20261025T114909347533Z`.
Its fixture is exact `build/geos-incremental-editor/20261025T112646631270Z/fixture`.
The earlier 104900 runs are historical, not current managed-policy evidence.

## Actual fit and authority

C6 producer4060B, R30supervisor2073B, C32data3226B (raw3194), zero added BSS/ZP.
`build-transaction.py OUT FROZEN_FIXTURE` builds all three private sealed images.
A production build should retain its own C6 build and merge only the producer
changes described below; the private recipe builds C6 from the immutable fixture.
It does not modify the canonical tree or overwrite any source on a build.

C32 has a32B safe C header atB000; CODE/RODATA run at5000. Its public C entry at
B010 merely returns0. It is imported as slot1/ID32, never entered during typing.
Raw executable begins at asset offset32, jump5000→transaction5003. No nested C
call occurs; C6 remains in its C slot. The same existing R30 ID is retained.

R30 has binding atA000, safe public entryA010, and six fixed JMPs:

|Address|Service|
|---|---|
|A020|se_gtt_admit|
|A023|se_gtt_current|
|A026|se_gp_cache_slot|
|A029|se_gp_cache_read|
|A02C|se_gp_cache_write|
|A02F|se_gcc_status|

Only these six leaf helpers are numerically aliased into C32. All other resident
calls/ZP loans use the exact generated resident binding. Link C32 first, derive
rawlength/CRC and completepayload length/CRC into `stage-constants.inc`, then
link R30. The normal1280B FE font and per-glyph expectedCRC tables remain genuine;
authenticate normal9B+width before bold/italic transform.

R30 op3 refuses foreign owner or invalidGEC/GTC before touching its frame,
claims4, authenticates C32 from typed overlay backing, calls5000, then always
restoresowner0. Stage guard compares full asset epoch, all allocated logical
asset owners, selected physical owner/map, ID/slot (`image_slot&1`), complete
length/CRC metadata, residentbinding and full rawCRC before execution. Runtime
reuse requires GF_FACE=FF, GF_VALID=42 and the five-byte capability stamp at5FE0.
This uses the same managed writable-window authority as existing41/C31. Every
legal5000 writer must clear GF_VALID; code41/font windows force42refill and vice
versa. Unnotified external REU/RAM mutation is outside that managed contract.

## Admission and correctness

The only producer changes beyond released neighboring-role proof are removing
GPR_INLINE from the prose restriction, permitting whole-row GG styles0..3
(instead of requiring styleszero), and allowing oldadvance1..11. Whole roles
remainzero. `styles` is the appended bounded30B net helper. Existing fullsource,
publication, prefix, geometry, font and certificateCRC guards stay in place.
C6 is4060B,36B spare on the current4030B producer base.

The staged `prepare.s` also bounds every actual style<=3/role0. If oldINLINE or
any nonzero style exists, insertion must be strictly between alphanumeric bytes
of equal style; insertedbyte must be alphanumeric. Deletion requires the old
byte and both unchanged neighbors alphanumeric with equal style. Firstbyte is
still alphabetic/unchanged under C6. Such an edit cannot split/join '*'/'@'
runs or £ escape adjacency. The actual unchanged inline parser locality gate
separately proves event/style mapping; spaces, punctuation, delimiteredges and
matched inlinecode refuse. This is deliberately conservative, not new grammar.

The trusted normal glyph transforms with genuine GG bold1/italic2, advance
width+bold+italic (1..11), nine16bit rows. The942B wide primitive preserves
three-byte crossings and caret geometry. Surviving styles move with characters,
X boundaries shift by transformedadvance, and nextcaret width comes from its
actual surviving X pair. The full current canonical row is reread and matched
before cache/pixel mutation. Only then are derivedvalid bits cleared and the
existing transactional body/cache/prefix/status publication runs.

White liveattributes alone remain insufficient. The C6 neighbor helper must
prove every actual glyph role of every row intersecting both changed physical
8px bands is0. This is the earlier concrete minoritycyan fix. The wide primitive
also checks both actual attribute bands, but does not replace that role proof.

## Placement

- Transform frame8A44..8A69 (38B), wide frame8A80..8AE8 (105B).
- Existing normal prefetched glyph8B4A..8B52/width8B43 remains unchanged until
  copied into transform input. Existing packet8D00..9049 and source/header/
  certificate/metadata scratch remain originalR30 locations.
- Stage guard scratch8BF0..8BF4 and stamp5FE0..5FE4; GFstateCBC0 uses namespace42.
- Existing base8400..8567 and temp8580..85A7; typed FE cache body authoritative,
  status-cache bytes are not promised refreshed (same existing typing contract).
- Borrow existing foreground text_ptr/screen_ptr only; no new ZP/BSS/objects.

## Evidence and limits

`tests/test_geos_style_transaction.py --base FROZEN_FIXTURE` passes12 frames:
bold/italic/combined/plain insert+backspace plus four repeatedcombined edits.
Every8000bitmap byte,1000attribute byte, livepacket chars/styles/roles/X/prefix,
header, canonical/history, shim and all16MiB outside ownedFE match both actual
forced full renderer and independent source/font model. Twenty refusals/faults
cover lexicaledges/code/foreignowners/fontbits+width/typedcatalog+epoch+map/
binding/rawCRC/missingstage/source token. Genuine source fault invalidates
GCC/GEC as existing failure policy; pure eligibility misses preserve GCC.

Warm0loads:56,742..67,433 CPUinstructions. Current forced full reference:
499,338..757,239 on these shortdocuments. Cold firststage153,943..163,582 and
one R30load. These are CPU instructions, not PALcycles or a native latency claim.
Twelve PNGs are retained; bold/italic/combined/plain insertion and repeated
combined insertion were inspected directly. Parent owns real integration,
public routing, native verification and performance acceptance.
