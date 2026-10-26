# Private View menu discovery

This changes only copied `menu-data.inc`: View gains `P Preview / source (GEOS)`
using existing E_SOURCE67, and `S Preview settings...` using E_SETTINGS103.
Nine-item View remains a count-driven11-row popup at row3. Existing seven items,
other menus, parser/cache policies, session ABI and resident code are unchanged.
The non-GEOS P route deliberately keeps the existing77 refusal; no implicit
mode switch or editable preview is introduced. No help text was changed.

Base: committed3a68a59 fixture
`build/nr-committed/20261026T210259832190Z/fixture`, resident938321, binding7abb,
actual59 assets. Earlier454 CPU16-frame proof remains historical; final CPU and
native results below include the real3a C33 cleanup, not a capsule substitution.

## Actual private CPU result

`build/view-menu-current/20261026T210541922992Z/result.json` PASS:

- C7 control3026 and R22 control3953 reassemble byte-for-byte to frozen payloads.
- Candidate C7=3030 (+4 array bytes), R22=4003 (+50 label bytes).
- Only menu40/popups are changed in a genuine private D81; every other member's
  bytes match the base, including resident/fontpack/other57 capsules.
- Public F1/View letters and arrows/Return in40/60/80/GEOS; both P rejection
  routes outside GEOS; source/preview toggle; Settings H/reset/cancel; preview
  Settings STOP restores UI4; selection/clipboard and genuinely pending Q.
- Independent whole-frame pixels/attributes and57 canonical/history/selection/
  clipboard/catalog/observer/shim guard intervals. UI-only draws preserve all
  16MiB REU exactly. Preview creation uses the released precise authenticated FE
  spans; no53/history/source/foreign whole-bank allowance is added.

Private fixture:
`build/view-menu-current/20261026T210541922992Z/link/fixture`.
D81 SHA256 `3ca55cbbdbe38404d09cde34969b7ee00c0dd43b3393dd880550e2659045ac73`.
CPU uses existing ROM/font transport seams. A separate genuine native12-frame
gallery is now qualified below; physical keyboard latency remains unclaimed.

## Reproduce / promotion boundary

```sh
python3 tests/test_view_menu_current.py --fixture FROZEN_3a_FIXTURE
```

The script extracts only include dependencies, reproduces sealed controls,
hardlinks immutable base members and atomically replaces the changed private
members before packaging. It never writes shared build or canonical files.

Only possible production change: copy this `menu-data.inc` to
`src/editor/menu-data.inc`, then serially rebuild C7/menu40 and R22/popups with
existing Make dependencies. No other source promotion, state, aliases, assets,
resident or lifecycle changes are needed. The payload room after this change is
1066 bytes C7 and93 bytes R22.

## Preserved host/verifier failures

- First setup hit ENOSPC while copying the fixture; second extraction also hit
  ENOSPC. No product event executed. Only own unsealed generated mirrors were
  reclaimed; receipt `build/view-menu-current/failed-setup-recovery.json`
  retains compiler identities and all immutable base/source inputs remain.
- Existing fontpack directory caused a setup-only FileExists error; corrected
  wrapper now reads/asserts existing immutable bytes rather than rewriting a
  hardlinked file.
- The released settings oracle is explicitly source40-only. For60/80 it was
  initially used as a whole screen, interpreting bitmap bytes as characters.
  The correction copies only its independently modeled dialog rectangle over
  the proper mode's body/chrome. Both View mode60 pixels and settings rectangle
  remain independently checked.
- Preview Settings initially used literal-source body outside the dialog;
  corrected to the unchanged preview body oracle while preview is active.
  No product error, pixel mismatch or REU guard was accepted as correct.

Original traces: `build/view-menu-current*.log` (including `-cpu.log` and
`-cpu2.log`); final terminalPASS is `build/view-menu-current-cpu3.log`.

## Native current3a qualification

Source `tests/test_view_menu_vice.py`; evidence
`agentsworking/evidence/M8/20261026T210929010804Z-view-menu-native`.
One genuine D81 File/Open of DIVERSE422, F2/right4/copy0B/STOP makes a real
four-byte clipboard, then sourceGEOS creates the genuine semantic baseline.
Actual F1 View letters and arrow/Return invoke Settings in40/60/80/GEOS, H sets
Plain, R resets Full, STOP closes. View P enters preview; preview Settings STOP
restores UI4, then View arrows/Return returns to editable GEOS.

All12 screenshots pass768,000 independent VIC pixels/12,000 attributes, exact
source/history/clip/settings/fonts/all59 sealed code/shim and unchanged whole
D81. Eleven whole16MiB comparisons allow only documented current typed FE spans;
four same-mode UI-only pairs preserve the ENTIRE16MiB exactly. The actual type53
capability and complete allocation payload remain identical in all12 captures.
Observer ticket/incarnation/ring and empty queue are exact; ARMED/noLOST/
MUTATING/ACTIVE are checked. Source60/80's inactive8D00..8EFF union matches the
ENTIRE independently calculated512-byte CCITT table, rather than falsely
interpreting table byte8EE8=$7C as a live FS ownership flag. Other views require
FSowned0; all views have actual foregroundowner0/docreadlocks0/clipbusy0.

All12 images reviewed in `gallery/contact-1.png` and `contact-2.png`; native80
View, GEOS View and preview Settings also inspected individually. Existing
preview before/afterSettings PNGs are byte-identical. VICE29689 exited normally;
all owned8100/8200..8239 listeners are closed. Plan640steps/142IRQ bytes, warp and
drive traps; no physical chord, lifecycle, SaveAs, or physical-device claim.
`closed_runtime_copy` shares final own immutable raw dumps only after native
success/close, retaining its exact receipts.

A host-only final evaluator scope lookup did not recognize the word gallery,
after its functional assertions had passed. Original trace is retained; an
own local `editing -> gallery` output alias runs the unchanged released engine
assertions, then records the truthful no-file-write scope. Empty saved-name
list is intentional: this scenario does no SaveAs, and ENTIRE D81 equality is
required. No native rerun occurred. A later extra FS flag assertion exposed the
inactive CRC-table alias described above; original trace is preserved and the
replacement checks all512 actual bytes, not just a relaxed flag.

## Provenance clarification

The original private input freeze inherited its parent's exact-commit policy,
although its two menu images and one menu-data source were private changes.
The unchanged original is preserved as `cpu-input-freeze-original.json` in the
native archive; `provenance-clarification.json` states parent3a68a59 plus exactly
one source override and two assets. It does not relabel the completed run as a
Git build. Future builder metadata now sets git_commit=null, source_parent3a
and explicit menu-only source policy. Root's eventual committed source archive
is separate. Native final verification source and manifest hashes are preserved.
