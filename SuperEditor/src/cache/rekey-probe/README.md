# Private, one-kind REKEY bridge

This is an independently CPU-verified component, not production integration.
The frozen input is `build/cache-editor-product/20261026T031201729970Z/fixture`
(53 assets, resident `2acf47b2b70c35467c8b655030b2c7455b90a7b839d2b44689b201dc52ee3a4c`).
The private builder seals a new C-slot ID38 image against that exact resident.
It never writes the shared build or registers a production asset.

## Reproduce

```
python3 tests/test_cache_rekey.py --fixture build/cache-editor-product/20261026T031201729970Z/fixture
# Small first positive only:
python3 tests/test_cache_rekey.py --smoke --fixture build/cache-editor-product/20261026T031201729970Z/fixture
# Compile only, private destination:
python3 src/cache/rekey-probe/build.py build/rekey-compile-private build/cache-editor-product/20261026T031201729970Z/fixture
```

The released payload is 2381 bytes (1715 spare), with zero BSS/ZP/new objects.
It uses the existing 576-byte owner4 frame. `rekey.inc` publishes offsets;
reader86 is at frame+173, compatible with the existing resident BC_ACTIVE
missing-worker/queued-key cleanup. Parent control9134..9177 is untouched.

Entry ops: 0 BEGIN, 1 STEP, 2 CANCEL. Owner4 is required before any frame reads.
A1/Cclear means pending, A0/Cclear complete, A2/Cclear unsupported, Cset error.
The successful nine-call path peaks at 9980 CPU instructions per call in the
five positive fixtures; these are instruction counts, not native cycle claims.

## Narrow authority

The baseline must already describe the *pending visible text* and have a
complete root, count0 journal, and the current semantic ticket. Then exactly
one actual trusted producer kind2 REKEY flush is accepted. Root current-source
identity may change representation, but semantic ticket, visible revision,
merged24 length, source typed tokens and epochs must agree. Nonzero flush
advances the generation exactly once without wrap; zero/zero preserves it.
The flush tuple must fit both old and new frozen hot windows.

The test produces the pending edit and flush via real public paths. It requests
an actual C7/C34 baseline rebuild while pending through an explicit CPU caller
seam (claim owner4; invalidate the three derived index fields that root normally
invalidates). No root/CR/parser result, source identity, or event is seeded.
Two ring-slot tests set only empty queue topology before real event publication.

**The common old-baseline -> SPLICE -> REKEY queue is deliberately refused.**
This component neither rebases a SPLICE nor blanket-retickets CR records. The
trusted producer contract supplies byte-equivalence; event CRC is corruption
detection, not authentication against coherently forged arbitrary RAM events.

## Transaction and lifetime

The actual read-only arena OPEN selects and checks the previous complete root.
A fresh actual R14 BEGIN captures current59 identity; every subsequent STEP
checks actual source again. Since R14 changes the global object request token,
every arena transfer performs `bca_guard` immediately before checked DMA.
BC_IO overlaps the real FS frame; it is reconstructed after each R14 call.

Publication order is journal32 VALID0 -> journal marker A5 -> alternate128 root
VALID0 -> root VALID1. Only then, without yielding, tail advances and count is
retired. Old root and all CR/inline data remain byte-identical. Semantic ticket
and CR ticket fields remain unchanged. Cancel/error leaves the old root and
unread queue intact; unreachable journal/draft bytes can remain and are safely
overwritten on retry. Each success changes precisely alternate128+32 journal
bytes in the whole16MiB REU; no physical-bank constants are used.

Five positive cases cover insert, net-zero pending edits, all three ring slots,
and position65535 crossing the64KiB boundary. Twenty-seven fault groups cover
all six cancellation stages/retry; marker/kind/reserved/CRC/ticket/revision/gen
and24bit tuple corruption; unread SPLICE; source revision change across yield;
missing R14 and missing C38 cleanup; queued real typing preemption; 18 foreign
owner calls; Plain refusal before frame writes. Actual postbridge forced render
has independent pixel/attribute/source checks and real C35 entries with zero
C24/C34 entries. No native or product performance/integration claim is made.

## Integration deliberately deferred

Production root admission needs a policy for when a baseline already matches
pending visible text; the ordinary older-baseline case remains separate work.
The current root worker range stops before38; extending that exact range would
be necessary for ordinary pending dispatch. Missing-C38 and queued-key cleanup
are tested through the existing resident failure/preemption path directly.
Do not silently add a new baseline build just to make REKEY admissible. The
parent retains canonical integration ownership and its current C21 has only4
bytes free. Current later54-asset production is outside this frozen proof.
