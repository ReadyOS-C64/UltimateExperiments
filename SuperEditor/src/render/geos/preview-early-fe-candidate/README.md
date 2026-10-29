# Early preview FE allocation: private and deferred

**Recommendation: do not promote.** Root agreed to retain this candidate
privately. It helps long repeated prose but adds fixed initialization cost to
small pages; representative diverse gain is only1.284%, with no warm benefit.

The existing optional allocation block moves unchanged from pc_capture_begin
to pc_miss, after actual source BEGIN succeeds and before metadata seed/release.
Existing nonzero/stale handles are not replaced. Allocation refusal still
renders without caching. Later capture authenticates the existing handle and
does not retry allocation. No new state, BSS, zero page, REU bank beyond the
existing optionalFE, resident bytes, asset slot, helper or nested overlay call.

One backwards longbranch macro grows3 bytes after moving the block. Removing
redundant LDA0 after se_fs_end (its proven A0/Cclear contract) saves2; C27 is
4096 versus baseline4095. This is a complete private compile fit, not a proposed
budget. The baseline C27 SEO byte-matches immutable131207 exactly. Both
variants use its identical released single-fetch productionR23 (4095bytes),
including declared FE glyph extent[EB69,FBA9), not a foreign sidecar/binding.

Measured cold CPU instructions (not cycles/native latency):

| Source | Late allocation | Early allocation | Change |
|---|---:|---:|---:|
| Diverse headings/inline/lists/BASIC/ASM |2641266|2607363|1.284% fewer|
| Repeated prose |4149432|3388921|18.328% fewer|
| Empty |795193|809169|1.758% more|
| Short |914269|939356|2.744% more|

Actual checked DMA calls rise94→488,47→1188,28→160,34→205 respectively.
Early initialization clears128 glyph records and then maintains per-glyph
records; small pages cannot repay that work. Native REU transfer-stall costs
were not measured. Warm body-memo hits are105650–105924 instructions before,
105652–105926 after (repeat after105858); there is no warm improvement.

The public sequence is source40, mode3, preview with no intervening literal
paint; the source40-to-mode3 and preview commands are consecutive real command
API calls. Measurement begins at actual public render, not host seeded glyph
output. This does not claim a physical-key timing path.

For both variants all source/history/catalog/shim, canonical merged bytes,
full independent8000bitmap/1000attrs and full16MiB REU exact-outside-declared
cache spans pass. Before/after first images match exactly and all4 distinct
images were viewed. Warm hits are wholly REU read-only.

Real allocator exhaustion consumes244 remaining handles with ownerA5; both
variants still render correctly with FE0 and no REU writes. Three repeated
STOPs before the first glyph preserve source/foreign REU and release the
source lease/phase. Late allocation retains FE0; early retains exactly one
persistent typedFE handle12 without allocating another. This is intentional
cache retention, not automatic release on STOP. A checked metadata CRC fault
repairs correctly to the full source/font reference.

No product/shared build files or other agent candidates changed. No native
run. Source/profile cases are bounded to these4 fixtures and the listed faults;
this is not an all-face/all-mode acceptance replacement or a completed M8 gate.

Reproduce: python3 tests/test_geos_preview_early_fe.py --fixture
build/geos-incremental-editor/20261025T131207214412Z/fixture.
The source delta is early-fe.patch and remains unpromoted.
