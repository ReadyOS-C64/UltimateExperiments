# Bounded heading-to-prose row update

Released private R28 candidate: 4012 bytes (original 3768, +244), 84 bytes free in its 4 KiB slot. No new BSS, zero page, or phase bytes. The original cache-warm object remains unchanged. `edit-cache.s` SHA256: `3aca283c94baec3364c84852fea0a541252017e4ce9919358b400bce2e932fb7`.

This adds one conservative admission class, `GEX_CLASS=2`: a single alphabetic INSERT at the complete raw START of an old heading. Its old prefix must be one through six `#` bytes followed by space; all old glyph roles must be heading role 2. Old flags must be exactly heading reverse, kind BSW, with no fold, pan, selection, preview, or modal context. Existing canonical graph, provider, epoch, revision, length, caret, operation, complete CR/EOF, START/FIRST/count/END/NEXT and preceding-CR checks remain in force.

The old TOP and HEIGHT must also equal resident `GCC_Y` and `GCC_HEIGHT`. Those values belong to the saved painted caret row under the full GCC key/sequence witness. This closes a real admission gap where a plausible but corrupted FE TOP (for example 17) could otherwise supply false dirty geometry. Movement within that same row leaves these row geometry witnesses valid.

C21 already dispatches actual C24/C20/C26 for nonzero classes. This candidate needs no C21 change and never substitutes predicted parser output. VERIFY still requires the new row to have flags 0, the same height/TOP/START/FIRST and CR/EOF reason, and exact END/NEXT+delta. A newly wrapped row abandons staging and performs the full repaint. The existing suffix rebase, physical-band repaint and majority color arbitration are retained.

Headings change parser event metadata without changing post-CR fence/language/region carry. Inserting the alphabetic byte changes a valid heading to prose while preserving that carry. Fence and region openers remain excluded; an actual heading inside an existing explicit region is allowed. Inline-code or foreign old roles refuse the shortcut. BACK removing the inserted leading letter, and all other prose-to-heading transitions, still perform a full repaint.

The extra class uses existing scratch only. The row scan allows START equality; class 2 validates the heading witness and bypasses the interior-only unchanged-first-letter test. The checked-array helper accepts an expected byte via Y (`zero_field` supplies 0; heading roles supply 2) in existing admit-dead `GEX_ARRAY`. All owner/operation barriers and A0/A2/carry behavior remain unchanged. Production may replace literal class 2 with `GEX_HEADING_CLASS=2` without changing bytes.

## Proof and cost

Frozen base: `build/geos-incremental-editor/20261025T130401385558Z/fixture`, 47 assets. The builder proves byte-identical original R28 reassembly before creating the private candidate SEO. No shared product or build output is modified.

Actual public candidate/control each passed 37 frames; all 37 PNGs are byte-identical. Tests use the independent semantic/font model plus the forced actual full renderer, exact pixels, attributes, all source row anchors and geometry, bottom, canonical source/history/catalog, leases and shim. Whole 16 MiB REU guards permit only the declared active FE cache spans; the real folded fallback separately audits exact typed-46/FE DMA stashes. Fourteen corrupt metadata cases and six opaque owner/operation entry barriers pass. Levels 1–6, EOF, inline headings, headings after CR and within regions are covered. Wrapped rows, new wrap, fences/regions, seven hashes, foreign roles, preexisting two edits and inverse BACK remain fallback.

Diverse prefix input+render measured 3,201,521 → 678,162 actual 6510 instructions (−78.82%); overlay loads 120 → 17. This is an instruction measurement, not a native cycle claim. Short EOF rendering can require an extra load (16 → 17), so no universal latency claim is made. The unchanged 19-frame inline regression passes. The ordinary 15-frame regression passes with only its final prefix expected-path predicate updated in an isolated wrapper; all its full-render, source and memory assertions remain unchanged.

Authoritative results: candidate `20261025T132450955957Z`, control `20261025T132452075389Z`, inline `20261025T132708392352Z`, ordinary wrapper `20261025T132906137516Z`.

## Commands

```
python3 tests/test_geos_heading_transition.py --fixture IMMUTABLE
python3 tests/test_geos_heading_transition.py --fixture IMMUTABLE --variant control
python3 tests/test_geos_heading_transition.py --fixture PROMOTED --packaged
python3 tests/test_geos_heading_transition.py --fixture PRIVATE_CANDIDATE --incremental-regression
```

`--packaged` uses actual frozen R28 directly, without private reassembly or replacement. `--incremental-regression` transplants only the historical final prefix path predicate and records its original verifier hash and exact replacement. It intentionally fails for manual review if that original verifier text changes. Central verifier updates belong to the coordinator.
