# Private raw short-line typing authority

Stable review release. No canonical/shared build/Git/native changes. Reproduce with `python3 -u tests/test_grid_raw_typing.py --fixture build/cache-editor-product/20261026T052628862819Z/fixture`.

Final run `build/grid-raw-typing/20261026T064033406598Z/result.json` is terminal PASS. Frozen resident a2578487/binding f50620/54assets. The builder first extracts the frozen product source ZIP and proves original C33/R25 SEOs byte-identical, then reproduces the separately immutable +12-byte caret release before applying this new pair. Both images must be promoted together; no fabricated catalogue IDs/CRC/verification flags are used for positive tests.

## Authority and behavior

NC header byte253 (`N_CAPS`, previously unused after22rowCRCs) stores the exact live render_caps. It is included in the NC254-byte CCITT checksum, captured through FIELD and compared through FIELD on every consumer. Only exact livecaps0/headercaps0 admits raw typing. Full3 and Markdown1 retain the exact C14/R14 managed slot, size and CRC dependency checks plus genuine SP2 sc_check/rekey and original grammar restrictions. NewC33 authenticates onlyR25 for raw type_try; Full/Markdown authenticate all3 dependencies. NewC33/oldR25 and oldC33/newR25 safely decline fast publication under unchanged resident binding because helper size/CRC authentication fails; actual mixed public fallbacks are tested.

Raw uses existing NC source/layout/viewport key28, actual current view initialization, all3 source typed-object validation graphs, source/window state, exactone revision increment and +/-1 merged/window length, pending/delete/caret delta, oldsequence/font/FElogical+physical ownership/epoch, full header and selected packet CRC, row ownership and exact old-to-new bytes. This is the actual NC/window authority, **not a claim of an extra full59-byte FS snapshot**.

Raw skips semantic st_valid1 and sc_check/sc_rekey only. It does not write semantic descriptor revision/length, set st_valid1, create/rekey SP2, or invoke semantic parsers. Raw long_prepare is explicitly refused both before C33 long routing and at R25 op16. Selection, folds, pan/manual/nowrap, row-boundary geometry, malformed capability and authority failures remain prepublication optional misses. The existing checked short-row path repaints one native60/80 row and updates only its cache packet, canonical anchors, current caret/status and NCheader after successful paint.

Raw grammar has no structural meaning. Ordinary printable space, quote, punctuation, *, @ and backslash therefore use the same exact byte-delta path; Full grammar restrictions remain. Col0/end/empty short-line insertions and deletion from len(width-1) are admitted when newlength<width and CR/EOF ownership remains exact. Inserting CR, introducing a new wrapped row, and existing softwrapped paragraphs remain fallback. No inference of semantic carry from uniform role0 is made.

## Measured fit and factoring

R25 payload4056 (40bytes spare, old4095). C33 remains padded4096, CODE+RODATA endsBD70 below fixedBF00native font. New BSS/ZP0. R25 old GEOS tail op0/op1 remain unchanged. Existing6vectors/overlay nesting policy unchanged.

Field compactions preserve all bytes with actual linker assertions: GCvalid3+previousUI+currentUI5, selectionmark+anchor4, foldtoken+count7, foldrowbits+projectiongeneration5. FIELD failure uses the existing returnedCset immediateRTS instead of an absolute jump to SEC/RTS; successful comparisons/copies and failure authority are unchanged. Raw character checking tail-jumps the old alnum checker for semantic modes; its scratchX is dead at both call sites. No selfmodifying code or dropped guard was used to fit.

Exact images: C33 `58aeff5be1a16c64ef1eeed2bd0c7011be406a34dea391eafc70f426381aae49`; R25 `1f442670119293caf1dadfcef17dea70a751ac0cc5e0b55f4e4ac360e32cb8b0`.

## Qualification

- 60 three-way actual public frames: original/releasedcaret/raw each20 (60/80 ×Plain/Full ×RIGHT/DOWN/UP/insert/BACK). Original independent source, pixels, attributes, map/caret/TOP, history/Undo and exact observed checked-DMA16MiB checks remain. Plain has zero semantic module entries. First publication and complete settled instructions remain separate in JSON.
- 40 raw public cases across both widths: punctuation/space/quotes/markers/backspace, column0/endCR/endEOF/emptyCR/emptyEOF, raw leadingmarkers, last-safe insertion, maxshort deletion and >64KiB position. Every case verifies actual short-row branch, independent fullpixels, actual source and Undo, no phase or SP2/semantic-descriptor publication, exact checked-DMA guards.
- 62 strict refusals cover CRC-valid wrongcaps, livepolicy change, source/epoch/length/revision/map/header/packet metadata, roles/flags, selection/fold/pan/manual/nowrap, foreignowner, retiredFE, logicalowner/map/epoch/font/helper faults, wrongrevision/delete/pending, CR and softwrap. Each returnsA2/Cclear before bitmap/cache/source/phase writes; all16MiB exact and owner/lease/shim preserved.
- 16 actual mixed-pair public frames safely fall back; 8 direct actualC6 mutation tests prove missing C14/R14 permits raw and refuses Full. Raw direct success permits only exactone240Bpacket+NC256Bheader in the whole16MiB and declares/checks whole64KiBRAM scratch/overlay/pixel/request effects. Canonical/history/source and phase remain exact after the actualmutation. This is not a claim that the input mutation itself leaves history unchanged.
- 18 three-way fallback frames independently match source/pixels and Undo. 8 additional source40/GEOS Plain/Full RIGHT/insertion frames preserve existing behavior, including zero-load source40RIGHT. No new native timing or physical-key claim.

Six representative three-way image rows are directly reviewed in review.png; independent fullpixel/hash checks cover allframes.

## Timing and remaining fallback penalty

**CPU instruction counts only.** Native cycle/latency remains rootqualification. The short-line common cases now improve both controls. Full behavior is effectively unchanged.

| Case | Original settled | Caret-only settled | Raw settled | Raw loads |
|---|---:|---:|---:|---:|
| m1-plain-right | 236,514 | 33,779 | 33,739 | 2 |
| m1-plain-down | 326,218 | 80,897 | 80,857 | 5 |
| m1-plain-up | 319,875 | 73,961 | 73,921 | 5 |
| m1-plain-insert | 272,693 | 429,152 | 94,699 | 4 |
| m1-plain-delete | 272,316 | 428,862 | 94,431 | 4 |
| m1-full-right | 33,908 | 33,711 | 33,671 | 2 |
| m1-full-down | 81,120 | 80,923 | 80,883 | 5 |
| m1-full-up | 74,172 | 73,976 | 73,936 | 5 |
| m1-full-insert | 2,815,950 | 2,815,162 | 2,815,069 | 29 |
| m1-full-delete | 2,814,748 | 2,813,960 | 2,813,867 | 29 |
| m2-plain-right | 217,482 | 34,970 | 34,930 | 2 |
| m2-plain-down | 278,234 | 83,293 | 83,253 | 5 |
| m2-plain-up | 271,887 | 76,371 | 76,331 | 5 |
| m2-plain-insert | 253,710 | 410,165 | 66,195 | 4 |
| m2-plain-delete | 253,311 | 409,775 | 65,943 | 4 |
| m2-full-right | 35,136 | 34,939 | 34,899 | 2 |
| m2-full-down | 83,463 | 83,266 | 83,226 | 5 |
| m2-full-up | 76,527 | 76,331 | 76,291 | 5 |
| m2-full-insert | 2,087,545 | 2,086,757 | 2,086,664 | 29 |
| m2-full-delete | 2,087,089 | 2,086,301 | 2,086,208 | 29 |

Unsupported structural/wrapped cases remain correct but regress versus original because the now-admitted postpaint CAPTURE scans all22packets and raw short admission also fails first. This is an explicit remaining cost, not a completed general typing solution:

| Fallback case | Original | Caret-only | Raw |
|---|---:|---:|---:|
| 60 softwrapped | 354,527 | 491,361 | 501,430 |
| 60 introduce-wrap | 338,190 | 474,578 | 484,668 |
| 60 insert-CR | 329,539 | 466,880 | 484,223 |
| 80 softwrapped | 250,062 | 385,876 | 395,907 |
| 80 introduce-wrap | 264,717 | 400,537 | 410,619 |
| 80 insert-CR | 252,828 | 389,751 | 407,754 |

The standalone caret-only release is not modified. Parent must account for the fallback penalty when deciding promotion and further work; do not report Q-only success as general Plain completion.
