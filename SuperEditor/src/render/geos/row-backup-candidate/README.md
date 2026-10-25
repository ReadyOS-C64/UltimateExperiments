# Private R28 row-backup removal

Frozen combined48 baseline: `build/geos-incremental-editor/20261025T171440790321Z/fixture`, PRG b33cc41e... / D81 da5f2235... . Control reassembly must equal packaged R28 byte-for-byte.

The entire two row backups FE[D568,DD68) and FE[DD68,E568) are write-only. Production references exist only in R28 ADMIT/VERIFY `copy_row` calls and its helper. Neither C21/C22 nor R27/R30, history, or cancellation reads them. CANCEL authenticates the cache, clears its live VALID byte, and discards the transaction. Subsequent root rendering rebuilds canonical source; there is no rollback from either backup. No asynchronous lifecycle capture is admitted while owner4 is active.

Remove exactly both `ROW→slot→copy_row` call blocks and dead helper. Retain the checked 64-byte old-header witness at D528, all source/provider/owner guards, row parse/rebuild/VERIFY/REBASE/VALID-last behavior, all eligibility classes0..4, phase fields and constants, error/STOP cleanup, and unchanged cache-warm664. Do not reclaim or reuse the dead spans yet.

R28 shrinks4096→3928 bytes (168 bytes freed); no BSS/ZP/state growth. Two2048-byte copies formerly issued64 checked DMA calls total (32 fetch,32 stash;8192 transferred bytes). Actual same-build CPU success saves12,188 instructions at identical overlay-load counts; old-row-only wrap refusal saves6,094. These are CPU instruction counts, not native cycles.

Actual72-case control/candidate gate: all72 PNG pairs byte-identical, independent and forced-full pixels/attributes/all anchors, canonical history/source and16MiB guards. A deliberate checked-FE poison covers both4096 dead bytes and requires unchanged bytes on every subsequent actual render. STOP/missing-R28/C21/C22 recovery and revision/epoch/map/owner faults with Undo/Redo pass. Ordinary15/heading-forward37/heading-back35 regressions retain their original source/fullrenderer/pixel guards. The current ordinary verifier is directly reused; historical forward expected-feature predicates retain their already reviewed adaptations.

New tests only: `test_geos_row_backup_candidate.py`, `test_geos_row_backup_recovery.py`, `test_geos_row_backup_regressions.py`. Failed initial harness fixtures (mode0 has no FE yet; obsolete control expected-path; old plain-prose recovery now bypasses R28) are preserved and corrected explicitly, without changing product oracles.

No canonical files/shared build/native claim. Parent must revise public derived-backup comments and narrow FE write guards if this private candidate is promoted.
