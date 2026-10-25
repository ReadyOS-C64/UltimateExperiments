# Private fixed-grid reflow candidate (source released)

This is a tested candidate against immutable `build/geos-incremental-editor/20261025T203233990688Z/fixture`, not a change to the shared editor build. No resident bytes, BSS, zero-page bytes, asset IDs or banks are added. All original SP2 semantic/source/provider/pixel preflight refusals remain.

## What changed

`shift-row.s` replaces repeated per-bit loops with fixed 4/5-bit scanline shifts and gathers/scatters only from the edit's physical byte through the row's last text byte. The strict scalar entry is 759 bytes. `controller.s` replaces the SP2 C33 paragraph controller: validate every source/cache row first; remove the old caret; paint the affected suffix rows consecutively through R14; then commit the row packets consecutively through R25. The latter remains byte-identical. A late error leaves derived grid validity cleared so the ordinary renderer repairs the display.

This trades two extra overlay loads for less pixel work. It does not assume a retained font at AC00. The inserted/terminal glyph comes from the existing authenticated managed-font helper; insertion carries each old row's last glyph and deletion reads the next untouched row's first glyph after removing the old caret. The new caret is applied once.

`producer-live.s` adds an owner2 scratch latch at `$89C3`: 0 absent, 1 clean candidate, 2 irreversibly rejected, $80 failed. Only an actual authenticated SM_PROSE event can enable it. READ2 does no record authentication when the candidate is absent/rejected; successful clean scans retain the existing full typed-FE/source/key/anchor checks. Rejection stops the optional scan immediately. CLOSE requires the clean latch as well as the authenticated record fields before approving row bits. Failed optional publication poisons the latch; FINISH still authenticates the full in-progress record and actual source before setting A5. The C14 dispatch additionally avoids the R14 EVENT call for a non-prose event when there is no live candidate. This is a negative shortcut, never an alternative parser.

`SC_H=$8A00..8A7F` and the latch belong to owner2. Actual frozen C14/C15 parser, inline, lexer and style state lie at 8D00..8EDF; FS is 8EE0 onward; VIEW is 8C00. R14 source output is the declared style buffer, not SC_H. A per-instruction lifetime gate observes normal 6510 store/RMW destinations and REU copies during owner2: 7,804 stores and 200 DMA writes, all from R14, across the actual classification/fault suite. This supports this latch; it is not a blanket claim that all editor modes preserve an arbitrary phase buffer.

## Repeatable private build / integration boundary

`build-current.py` extracts the chosen fixture's exact product sources and builds against its resident aliases. It can reproduce the untouched C14/R14/C33/R25 bytes (`pixel=False, producer=None`). It does not invoke shared Make.

Final recipe:

```
python3 src/render/grid/geowrite-reflow-candidate/build-live-dispatch.py NEW_PRIVATE_OUTPUT
```

For another coherent binding call its `build(output, fixture)` function. The final generated source/alias/header/config files in the proof's `leaf/` are authoritative.

Production promotion would require only these boundaries (parent owns it):

1. Replace paragraph `controller.inc` with `controller.s`; retain `long.inc` ABI plus private `LS_EDIT=LS+20`. Remove the old shift-row object from C33 (or use the emitted empty CODE object).
2. Link the strict `shift-row.s` into R14 with `LPF=$8D40`. Add R14 op7: check owner4 before any frame access, then jump to `se_lp_shift_row`. Existing source operations0..2 and producer3..5 remain.
3. Replace the producer with `producer-live.s`. Its explicit short branches are assembler-range checked; the local `current_bad` error return is identical A2/Cset. The old unused LDY in candidate-row enumeration is removed.
4. C14 reader EVENT wrapper: actual `se_sm_kind==0` or `$89C3!=0` calls normal op4; otherwise A0/Cclear locally. Final generated `leaf/project/src/style/reader-dispatch.s` contains the exact 14-byte change. If the shared C15 build also consumes this source, retain its old behavior or use an explicit C14 define; C15 never calls these producer entry points.
5. Regenerate the existing exact C14/R14/R25 witnesses before linking C33. The recipe does this; it does not hardcode a private resident seal.

Final payloads: C14 4089, R14 4095, R25 4095 unchanged, C33 4096. C33 has substantially more pre-font code space; the overall image still deliberately occupies its fixed 4096-byte layout. No new opcode is needed in C33; root's existing op3 reveal preparation is preserved.

## Evidence and limits

The final suite passes 40 accepted edits +37 readonly refusals, history Undo/Redo, caret movement, 840 independent primitive pixel/full-RAM cases +7 invalid frames, 15 classified publication frames +13 transient-provider/opaque-owner faults, and the unchanged full48-assets/7-helper static stack proof (77-byte qualified ancestry bound). Native PAL pairs use the same immutable203233 source fixture and actual cold D81 open/input/scheduler route: 12 captures each, all 768,000 VIC pixels identical between variants and independently modeled. Source/history/shim and exact foreign 16MiB intervals remain checked. Monitor entry timing is not a physical keyboard-chord measurement.

Final native settled costs:

- Admitted60-column paragraph: 0.920–0.935M PAL cycles vs 1.016–1.027M control, about9% less.
- Admitted80-column paragraph: 0.841–0.860M vs 0.922–0.938M, about8.3–8.7% less.
- Mixed422-byte fallback: 10.55–10.66M vs 10.83–10.95M60; 7.83–7.84M vs8.117M80, about2.5–3.5% less. First publication is essentially unchanged; settled latency is the larger number.
- Admitted typing loads rise2→4. Mixed fallback remains29 loads. These costs remain usability limitations, not completion of the overall typing goal.

The geoWrite comparison is source-based: pinned `640f1aba...`, geoWrite-2.s L3AD9/L3BE4 compares old/new line end, height/baseline and incoming/outgoing font state, retaining a horizontal prefix through a6 and stopping at convergence. Fixed-width source wrapping generally cannot converge inside an inserted/deleted logical paragraph: every later row still shifts until CR. This candidate retains the unaffected horizontal prefix and later CR-separated rows, without claiming false source-end convergence.

Still unsupported: changed visible wrap-row count, physical caret boundary cases, selection, collapsed folds, manual pan, markup/code/mixed roles, and unproven semantic transitions. They retain the normal renderer fallback. The live-producer improvement removes redundant absent/rejected work but does not remove all per-clean-read authentication/publication. A separate RAM-resident producer experiment is the next bounded opportunity; no such weakening is part of this release.
