# Private managed preview body memo

This is a bounded, tested feasibility candidate. It has not changed production.
Apply `preview-body-memo.patch` only to an editor with
`se_overlay_managed_verification=1`, and compile `src/lifecycle/copy-entry.s`
with `EDITOR_MANAGED_CODE=1` as well as the existing managed resident flags.
Every asset must be rebuilt/rebound to the new resident. The private builder
performs that complete build. No shared editor or D81 is rebuilt here.

`PPC_BODY_MEMO = PP_STATE+77 = $CC4D` is the only new persistent field; it was
unused. `$CC4B-$CC4C` remain PPC_SAVED. No new BSS, ZP, allocation or object.
States are0dirty,1verified,80verifying. The field is a conservative sticky assertion about the unchanged preview body,
not an authenticated source or metadata key. It never replaces those checks.

- Every validated general CPU-to-REU transfer, for any typed owner2..254,
  clears the memo before `$DF01`. Read and invalid requests preserve it.
- Existing `se_overlay_unverify` also clears it for managed provider changes
  and fresh resume. Captured warm state may contain1; the fresh prelude clears
  it before any overlay execution.
- The validated R26 direct DMA helper clears it before every stash, including
  header, payload and publication. This covers legitimate FC/FE bank recycling,
  without assuming ownership alone preserves historical bytes.
- The cold physical probe transfers only offset `$FFFD`, before imports and
  before a preview can be published. All cold imports use checked owner2
  writes and establish zero. Other direct writers in `src/lifecycle/probe-copy.s`
  and `src/style/probe-source.s` are isolated probes, absent from production.
  The fixed lifecycle restore macros are fetch-only; fresh prelude revokes.
- Capturing computes the body CRC, stores body/metadata, then publishes VALID
  last; memo1 follows only a successful final publication write. Initial strict
  lookup sets1 only after its complete body CRC matches.

On an authenticated hit, the existing metadata CRC, all59 source identity bytes,
64 session bytes, top, typed FE ownership/mapping/epoch, fold token/count/
generation/capability bounds and font FD descriptors remain checked. The only
skipped work is the bounded 7920-byte body CRC sweep and its repeated guards. An initial strict sweep arms80; any inter-slice checked write returns it to0 and causes a full miss/rebuild, so writes to already-scanned bytes cannot be forgotten.
The same two fetch DMAs and canonical anchors are published. A body write at
any point revokes the witness, forcing the strict sweep on next lookup.

Unnotified raw hardware/host REU mutation is outside this optional managed
contract. Such mutation must explicitly call `se_overlay_unverify` (or otherwise
clear `$CC4D`) before a lookup. This candidate does not promise CRC detection of
an unreported raw body bit flip. All original checked-write corruption tests
remain strict and pass. Cold/probe debug REU seeding is a disclosed test seam.

Actual complete frozen-source build first proves all47 baseline SEO files and
resident byte-identical to the immutable122004 fixture. The resident delta is
six bytes, with RODATA through `$3EFD` (two bytes left); COLD ends `$0EFD`.
C27 remains4095 bytes: The memo logic is balanced by an equivalent
bottom-bound branch sequence, seven ca65 range-checked short branches, removal of one unused scratch store, two redundant carry clears (guaranteed by callees), and one internal carry-only helper result load. R26 grows eight bytes. All other defaults
are unchanged; slow/fast generic cache+provider+DMA+header linked capsules and
full symbol sets are byte-identical with the managed flag undefined.

Private candidate resident SHA256:
`4e64d113b50f425bba3368edc9604da05c37daa91b4b5892a08225549c941fed`.
Private fixture:
`build/geos-preview-body-memo/20261025T124523372904Z/fixture`.
The retained baseline D81 is labeled historical; this is CPU PRG/SEO proof,
not a packaged/native candidate.

Proofs:

- Public preview68: 4,352,000 pixels, 68,000 attrs, canonical bottom/anchors,
  genuine faces/settings/inline/code/page keys, source/history/catalog/shim
  and complete16MiB REU guards. All58 unique images visually inspected.
- Existing cache gate:63 checked frames, every64 settings-key byte,15 original
  source/provider/fold/font/ownership/STOP faults, checked body/header corruption,
  partial pending source and >64KiB anchors. No expected failure was weakened.
  The copied verifier masks only the published image_slot bit7 under the
  already-enabled managed policy.
- Callback gate:253 actual typed owners; reads/refusals preserve witness;
  exact owned-byte/full16MiB guards. Instruction spy observes258 hardware stash
  commands and zero nonzero witnesses before `$DF01`. Actual C29/R26 capture and
  fresh prelude callbacks are included; C29's clipboard prerequisite is created
  with actual `se_clip_init`.
- Inter-slice checked-write regression: after128 CRC bytes, a real checked write flips already-scanned B200. The original candidate demonstrably copied corrupt pixels; the final armed candidate invalidates/rebuilds to exact reference. Historical failed candidate is retained and explicitly superseded.
- Same-image comparison: forced first verification387604 instructions/65 R14
  calls; memoized105729/4; second memoized105727/4. Reduction72.72%. Hit is fully
  REU-read-only. CPU instructions are not native cycles/latency measurements.

Reproduce the private fit with `python3 .../preview-body-memo-candidate/build.py`;
use NEW `tests/test_geos_preview_body_memo.py --base <run>` and
`--callbacks-only`/`--generic-only`. The public68 run calls unchanged
`test_geos_preview_editor.run(out, fixture)`. Root owns integration, native
measurement and affected final acceptance deltas; this evidence does not close
M8 or assert a performance target.
