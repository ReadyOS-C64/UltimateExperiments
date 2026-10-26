# Private Plain source-grid caret dependency boundary

Source release for review; no canonical integration or native run. Frozen input: `build/cache-editor-product/20261026T052628862819Z/fixture`, resident a2578487, binding f50620,54 packaged assets. The builder reads only the immutable source ZIP/report/assets and first proves original C33 and R25 byte-identical to packaged images.

## Exact change and budget

Move initial dependency authentication after the existing OP/typed-revision split. CAPTURE and unchanged-revision caret authenticate only R25 (LDY0). `type_try` first authenticates all three dependencies (LDY2), retaining the exact C14/R14 sizes, CRCs and managed verified-slot checks. Every existing source/layout/canonical key, source typed graph, epoch, font, packet/header CRC, geometry, selection/fold and color check remains. R25 is byte-identical. No parser calls or fabricated verified bits are introduced.

Actual CODE grows12bytes (B000..BD08 → B000..BD14), RODATA endsBD5F, comfortably below BF00 fixed native font. The sealed padded C33 remains4096bytes; zero BSS/ZP. Candidate C33 SHA256: `da98ca6a346991d4cae89b1173df13610bb33a06b6313350aa4ac34637ed39c5`.

Reproduce: `python3 -u tests/test_grid_plain_caret.py --fixture build/cache-editor-product/20261026T052628862819Z/fixture`

Final terminal run: `build/grid-plain-caret/20261026T061939600451Z/result.json`.

## Qualification

All32 paired public frames PASS: source60/80 × Plain/Full × RIGHT/DOWN/UP/actual Q insertion. Original independent source/font/pixel/map/history/Undo and exact observed checked-DMA16MiB assertions remain unchanged. The exact bitmap+attribute hashes, caret and TOP agree control/candidate. Source40 Plain/Full RIGHT remains zero-overlay-load (2 additional cases). Plain intervals contain zero semantic parser/module entries. The scenario prepares actual GOTO2/fiveRIGHT in diverse422-byte source, primes RIGHT, then times actual input→first publication→settled root idle. This runtime Plain matrix does not substitute for a cold host-default-Plain native boot; root owns that independent test.

22 direct admission/refusal cases PASS (11 each60/80): missing C14/R14 permits caret; missing R25, wrong helperCRC, foreign owner, headerCRC, rowCRC, validCRC row22, fontCRC all decline; actual C6 insertion then missing C14/R14 still declines typing. Declines preserve source/history/pixels/phase and whole16MiB. Successful direct TRY stages only the exact NC256-byte header (next draw sequence+CRC), matching the real root publication contract; it does not claim wholeREU readonly on success. The paired public test observes actual final root publication.

Five released transport/STOP/recovery cases PASS: missing C33 mandatory fold planner, corrupt checked-owner2 C33, actual pending FileOpen directory planner owner1 opacity, real queued STOP in C11, exact64,000-pixel/1,000-attribute render recovery. Pending directory case proves opacity, not successful DOS completion.

Six representative control/candidate pairs were visually reviewed in `review.png`; exact model/hash checks cover all frames.

## Measured costs and limitation

**CPU instructions, not cycles or physical-key latency.** Settled is complete measured interval; first publication is separately preserved in JSON. No native speed claim.

| Case | Control settled | Candidate settled | Overlay loads |
|---|---:|---:|---:|
| m1-plain-right | 236,514 | 33,779 | 4 → 2 |
| m1-plain-down | 326,218 | 80,897 | 7 → 5 |
| m1-plain-up | 319,875 | 73,961 | 7 → 5 |
| m1-plain-insert | 272,693 | 429,152 | 7 → 9 |
| m1-full-right | 33,908 | 33,711 | 2 → 2 |
| m1-full-down | 81,120 | 80,923 | 5 → 5 |
| m1-full-up | 74,172 | 73,976 | 5 → 5 |
| m1-full-insert | 2,815,950 | 2,815,162 | 29 → 29 |
| m2-plain-right | 217,482 | 34,970 | 4 → 2 |
| m2-plain-down | 278,234 | 83,293 | 7 → 5 |
| m2-plain-up | 271,887 | 76,371 | 7 → 5 |
| m2-plain-insert | 253,710 | 410,165 | 7 → 9 |
| m2-full-right | 35,136 | 34,939 | 2 → 2 |
| m2-full-down | 83,463 | 83,266 | 5 → 5 |
| m2-full-up | 76,527 | 76,331 | 5 → 5 |
| m2-full-insert | 2,087,545 | 2,086,757 | 29 → 29 |

Plain RIGHT improves approximately6–7× and removes2loads; local DOWN/UP also improve. Full cases are essentially unchanged. **Plain insertion regresses by~156k instructions and2loads**, because postpaint CAPTURE now succeeds and scans/checks all22rows instead of rejecting on unverified semantics. This release must not be described as an unqualified typing or overall usability win. Root should make an explicit policy/architecture decision before promotion; do not hide the regression by disabling assertions or excluding typing. No changes to the released patch are made here.

The public matrix depends on actual loaded semantic verification state for Full; direct missing-C14/R14 cases independently establish the intended new boundary. The new pure-caret scope does not permit inferring prose/carry from role0, and cannot authorize the typing path without its exact paragraph dependencies.
