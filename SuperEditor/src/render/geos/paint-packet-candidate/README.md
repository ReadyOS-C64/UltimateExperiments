# Private C22 checked contiguous packet gather — released

Replace only `src/render/geos/page-paint.s` with this directory's `page-paint.s`
(or apply `ready.patch` against immutable174216). Existing Makefile, cache ABI3,
entry, native-pan, config and resident interfaces remain unchanged.

The original bounded proportional chunk is1..64 glyphs. One checked
`se_gp_cache_read` from CHARS+offset now gathers324+COUNT bytes into existing
8D20 scratch, covering the same CHARS/STYLES/ROLES slices. CHARS are already
in place; an ascending scatter copies styles from8DC2 and roles from8E64.
Its maximum end is8EA4 exclusive, inside the existing painter scratch and
below the actual FS8EE0 context. Overlapping role destinations can only
clobber style indices already copied. FLAGS/MAP are produced afterwards.
Each later chunk refetches, so rows longer than64 and161-glyph clipped rows
remain supported. Native8 code follows the original separate field path.

Every actual STEP retains its original full cache/source/owner validation.
The combined transfer removes two intermediate guarded READ steps, does not
hold stale pointers, and makes no REU write or canonical/source change. An
explicit1..64 count check precedes every array request. No state/BSS/ZP/asset
is added. Payload4017→4085 (+68),11 bytes spare. No new JSR/PHA path.

Build/test against immutable current48:

```
python3 tests/test_geos_paint_packet_candidate.py --suite fit
python3 tests/test_geos_paint_packet_candidate.py --suite inline
python3 tests/test_geos_paint_packet_candidate.py --suite fold
python3 tests/test_geos_paint_packet_candidate.py --suite incremental
python3 tests/test_geos_paint_packet_candidate.py --suite identity
python3 tests/test_geos_paint_packet_candidate.py --suite boundaries
python3 tests/test_geos_paint_packet_faults.py
python3 src/render/geos/paint-packet-candidate/package.py
```

The package helper substitutes the source in the source ZIP, rebuilds private
C22 only, packages a private D81, and compares resident/all48 packaged assets.
The default fixture is174216 (b33 resident/current R21strip+R283928), not a live
build. The control C22 must reassemble byte-identical before any A/B assertion.
The identity/boundary suites use actual C21-derived packets, exact independent
pixels/attributes, poisoned obsolete affinities, full64KiB allowlist and whole
16MiB read-only guards. Historical ABI2 wording inside the reused test is
superseded by the wrapper's explicit actualABI3 scope.

Matched native forced TOP0 diverse422 result:
11,533,063→11,262,227 PAL cycles (-270,836/-2.35%). Loads118 unchanged;
overlaycalls1015→967; checkedDMA748→652; bytes444,296→448,176 (+3,880).
Service peak412,474→412,449 is effectively unchanged. Final PNG bytes identical.
This is a modest generic improvement, not a usable full-page latency claim.
Native measurement explicitly invokes the actual public render with PC/SP
stopwatch seam, not physical keyboard latency. The original native source,
asset/catalog, shim, bitmap/attrs, cold probe and stack checks remain intact;
whole16MiB immutability applies to the CPU painter gates, not blanket native
capture intervals.
