# Private RAM-owned SC2 producer (source released)

This is a separate candidate after the immutable `geowrite-reflow-candidate` release. It keeps the actual in-progress128-byte paragraph record in owner2 RAM and writes FE only twice per successful C14 job: BEGIN revokes the previous record with VALID0; FINISH authenticates the complete current context and publishes A5. No source/parser shortcut, new asset, bank, resident byte, BSS or ZP is added.

Final combined private payloads against immutable203233: C14=4089, R14=4050, R25=4095 unchanged, C33=4096. C14/C33/pixel-worker behavior is the earlier released candidate; this change affects only R14's publisher/source path and the generated C33 R14 witness.

## RAM and caller contract

- `$8A00..8A7F`: in-progress SC2 record, owned from successful BEGIN until FINISH/failure/cancel.
- `$89C0..89C6`: ROW,INDEX,MASK,LIVE,JOB,capturedFElogical,capturedFEphysical. JOB is A5 only after successful BEGIN revocation; LIVE0/1/2/80 retains the previous clean/rejected/failed semantics.
- Actual C14 state is8D00..8E10; block parser8E11..8E5F; inline8E60..8EA3; lexer8EA4..8EDF; FS8EE0 onward. VIEW8C00, checkpoint4770 and colorplan4800 are disjoint. C14/C15 write source data only into their fixed `st_buffer`.
- R14 READ now explicitly requires **owner2 output exactly `st_buffer`** before any DMA. Other owners retain the generic existing host bounds. This excludes both the record and7-byte scratch even for crossing/partial forged requests. The read-error wrapper poisons JOB while preserving the original source error A/C. Successful READ retains the original full source validation, then the producer's provider/source guard; no guard is removed merely because RAM is retained.
- Every working access checks the captured FElogical+physical capability and the existing owner/epoch/width/source guard. FINISH additionally checks full33-byte source/style key, document epoch, pending generation, width and all69 anchors before publication. All producer failures are sticky: repairing a field cannot finalize the abandoned partial job.
- SC_H semantic work bits are trusted owner2 phase state, like the actual SM parser state. This is not a defense against arbitrary malicious CPU writes to parser/work RAM. The complete declared caller graph and runtime writer proof are required; a merely unused-looking address is insufficient.

Static calls during a style job are C14/C15 plus R14 and resident source/provider code. Input cancels owner2 before another phase claims scratch; completion releases owner2 before R16 rendering. Per-instruction lifetime proof on the final leaf observes8,669 CPU stores and **zero DMA writes** into the working record/scratch during15 classified frames+13faults; every writer is R14. All documented6510 store/RMW addressing modes and overlapping REU READ destinations are checked. The captured working RAM is never reloaded from the revoked FE record.

A provider epoch replacement can prevent R14 itself being admitted. In that case the resident controller drops its owner/FS continuation and leaves the FE record revoked; it deliberately does not decrement a possibly foreign document lease. The old context requires provider/document reinitialization. The proof does not fake an epoch rollback into a usable continuation.

## Build / integration

```
python3 src/render/grid/producer-buffered-candidate/build.py NEW_PRIVATE_OUTPUT
```

The builder consumes the earlier released immutable private recipe and a chosen exact fixture. It emits the additional source-read error hook, uses the two explicit private branch-shortened source modules, generates aliases and all current witnesses, and seals the actual images. All34 initial source conditional branch shortenings and the later early-error island are range-checked by ca65; flags/targets/source checks are unchanged. No shared Make or canonical source is edited.

Parent promotion boundaries:

1. Use this `producer.s` in place of the prior optional paragraph producer.
2. R14 READ entry on source Cset preserves A, calls `se_sc_read_failed`, restores A and returns Cset. Its successful A0 path still calls normal SC scan.
3. Use the private source-read/context modules or equivalent **R14-only** conditional patches. The owner2 `st_buffer` restriction is an editor adapter contract; do not silently impose it on independent generic callers/probes. Branch shortening alone is semantically neutral. Existing generic sources in the checkout remain unchanged.
4. Keep prior strict op7/pixel worker and C14 negative event bypass. Rebuild the C33 exact R14 witness from the resulting asset. R25, fixed fonts, op3 and all existing seven staged helpers remain unchanged.

The final `leaf/` generated sources, configs, aliases and SEOs in the archive are authoritative. The baseline product-source ZIP covers resident/unchanged assets, not these overrides.

## Verified result and limits

Final exact gates:40 accepted/37 readonly public edits,15 classification frames/13provider-owner failures,16 extra malformed-target/field-repair/epoch/cancel/corrupt-revoked-record cases,30source40 screens/26,400cells/690anchors, whole16MiB intervals and shim, plus full48asset/7helper static77-byte stack qualification. The source40 wrapper updates only the test's obsolete8-array catalog decoder to the declared6-array64catalog/managed-bit policy; no pixel/source assertions are relaxed.

Final native PAL12 uses actual D81 boot/open/input/scheduler and matches the same exact203233 control pixels in every capture. Admitted paragraph settled costs remain0.919–0.935M60 and0.841–0.860M80; mixed422 fallback settles10.319–10.494M60 and7.607–7.663M80 versus10.829–10.950M /8.117M control. First publication stays around3.77M60/2.28M80; the larger settled time is reported separately. This improves but does not finish typing usability.

In the forced-full CPU attribution, mixed record checksums48→2 and totalDMAs165→119; clean4000B paragraph checksums74→2 while producer guard calls38→37. Fresh source/provider checks remain. The former FE intermediate record can be corrupted during the job and is safely overwritten from the genuine RAM parse, since it is revoked and never read as authority.

Selection/folds/markup/code/geometry changes retain the same normal fallback as the earlier SP2 consumer. No ReadyOS resume or general arbitrary-long-paragraph speed completion is claimed.
