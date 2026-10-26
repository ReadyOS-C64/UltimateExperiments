# Frozen public hot-path profile

Released diagnostic only. Input `build/cache-editor-product/20261026T052628862819Z/fixture` (resident a2578487, binding f50620, 54 packaged assets). No product replacements, shared labels/builds or native ports.

Reuses the checked DMA observer from test_cache_observer and the public input/idle path from test_presentation_bypass. Overlay interval boundaries are those used by test_display_timing_vice, resolved from the frozen resident. The new read-only observer attributes each executed instruction to the actual active catalogue tag; authenticated5000 stage namespaces are separate. Every byte of each tested resident/SEO remains unchanged.

Run: `python3 -u tests/test_cache_hotpath_profile.py --fixture build/cache-editor-product/20261026T052628862819Z/fixture`

Run output: `build/cache-hotpath-profile/20261026T055941645322Z`. 24 cases: source40/source80/GEOS, Plain/Full, warmed RIGHT/local DOWN/local UP/interior Q insertion. Diverse422B source; actual GOTO2 plus five RIGHT operations prepares the prose caret. Initial document/preset/mode/cache warming is excluded. Each interval starts at actual editor input and follows actual root idle until no job/redraw/drawbusy/owner/sourcelease/style-request. An actual Undo after each insertion independently recovers the original source.

**Counts are CPU instructions, not cycles or physical-key latency.** First publication is observed immediately after the real draw sequence changes; settled includes any later optional styling/publication. Do not report the first value as complete latency.

| Case | First publication | Settled | Loads | DMA calls | Overlay CRC instructions |
|---|---:|---:|---:|---:|---:|
| m0-plain-right | 3,441 | 3,452 | 0 | 1 | 0 |
| m0-plain-down | 31,056 | 31,067 | 4 | 9 | 0 |
| m0-plain-up | 31,112 | 31,123 | 4 | 9 | 0 |
| m0-plain-insert | 9,795 | 9,806 | 0 | 1 | 0 |
| m0-full-right | 3,679 | 3,690 | 0 | 1 | 0 |
| m0-full-down | 31,280 | 31,291 | 4 | 9 | 0 |
| m0-full-up | 31,350 | 31,361 | 4 | 9 | 0 |
| m0-full-insert | 76,412 | 736,195 | 15 | 16 | 0 |
| m2-plain-right | 216,446 | 217,482 | 4 | 28 | 0 |
| m2-plain-down | 277,198 | 278,234 | 7 | 36 | 0 |
| m2-plain-up | 270,851 | 271,887 | 7 | 36 | 0 |
| m2-plain-insert | 252,674 | 253,710 | 7 | 31 | 0 |
| m2-full-right | 35,130 | 35,136 | 2 | 7 | 0 |
| m2-full-down | 83,457 | 83,463 | 5 | 16 | 0 |
| m2-full-up | 76,521 | 76,527 | 5 | 16 | 0 |
| m2-full-insert | 646,032 | 2,087,545 | 29 | 153 | 0 |
| m3-plain-right | 10,744 | 10,763 | 0 | 14 | 0 |
| m3-plain-down | 80,065 | 80,084 | 11 | 37 | 0 |
| m3-plain-up | 80,784 | 80,803 | 11 | 37 | 0 |
| m3-plain-insert | 1,682,950 | 1,734,910 | 53 | 437 | 102,715 |
| m3-full-right | 10,872 | 10,891 | 1 | 15 | 0 |
| m3-full-down | 80,006 | 130,060 | 12 | 39 | 49,510 |
| m3-full-up | 80,728 | 80,747 | 11 | 37 | 0 |
| m3-full-insert | 759,376 | 811,336 | 31 | 352 | 161,888 |

## Immediate feasible boundary

Plain source80 RIGHT costs217,482 instructions/4loads against Full35,136/2loads. Plain makes C33op1 then falls back to C16/R16 source/finalize, draws one source row plus120native chrome cells, then C33op0 also misses. Full makes C33op1 and12R25 helper calls; no body or full chrome repaint. Both source40RIGHT paths retain zero overlay loads (~3.5k instructions).

The exact blocker is frozen `src/render/grid/caret/caret.s` authenticate_helper: y=2..0 unconditionally authenticates dependencies25,14,14 with slot checks0,$81,$80. Plain never executes C14/R14 semantic workers, so their managed verified bits are clear. This fails before admit/fields/R25. The se_st_valid==1 test belongs to the typing admission path and is not this caret rejection.

A safe candidate boundary is R25-only dependency authentication for CAPTURE and unchanged-revision caret; retain exact helper/source/layout/token/epoch/FE/font/header/rowCRC/selection/fold/color checks. Before any type_try/SP2/paragraph operation, require all three dependencies with their existing exact sizes/CRCs/verified bits. Do not fabricate verification bits or invoke parsers in Plain. Pure caret reads actual CRC-checked cached characters/roles/flags and alters only the caret/selection union; it does not derive block carry from role0. Any paired-generation or live-source/map fault must retain current refusal behavior. This is a proposed private qualification boundary, not an already promoted optimization.

## Remaining end-to-end cost

Full source80 interior insertion first publishes646,032 instructions but settles at2,087,545/29loads. R16 painter self792,762; resident558,852; C14self234,824; R14source/producer self176,248; C15self52,968. ActualR16 operations:27rows,240chrome cells and2admissions. Plain insertion paints1row+120cells and settles253,710. Overlay CRC is zero in both source80 typing samples, so removing more CRC cannot explain or solve the main gap. Retaining validated unaffected role/color plans through local edits and avoiding the plain-then-colored repaint is the larger algorithmic target; its semantic carry and color authority must be proved rather than inferred from role0.

Full source40 insertion similarly first76,412→settled736,195; C14/C15 plus R14 guard/read/producer work remains material. The measured C14self includes parser coordination and plan work, not a claimed pure parser-instruction count. R14 operation counts distinguish BEGIN/GUARD/READ and paragraph producer3/4/5 directly from actual overlay-frame bytes.

Plain GEOS insertion also misses the staged fast worker: R30 supervisor explicitly rejects render_caps0 before owner/certificate admission (9self instructions). It then paints31R21 strips (929,430self) and totals1,734,910, versus Full811,336/3strips. Any future raw typing admission needs a genuine raw certificate; this profile does not authorize bypassing the semantic/style certificate blindly.

## Guard and attribution scope

Independent source40/80 and GEOS full-source font/pixel/attribute models match every settled frame. All16MiB changes require exact observed checked DMA spans; source/history/clipboard/catalog/shim and insertion Undo are checked. Plain profiles contain zero semantic C14/C15/C24/C25/C26/C34/C35/C37/C39 entries. Live lease checks use actual owner/lock fields, not dead aliased source-phase bytes.

Self totals sum exactly to each interval. Nested overlay intervals are separately paired at actual resident call/jump/return boundaries; admission excludes final cleanup, and inclusive values overlap. Resident includes root/loader/CRC/typed guards/DMA. Module self is only actual PC within that module; stagedC32/C31 execution is separately identified. No per-byte CPU execution is intercepted or replaced.
