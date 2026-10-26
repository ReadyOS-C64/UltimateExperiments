# C23 far styled navigation: read-only findings and next private boundary

Status: source audit/current canonical54 cost probe only. No navigation runtime,
resident dispatcher, cache profile or shared build changed. The packaged C39
SOURCE4K proof is separately archived; it is not proof of fast styled navigation.

## Actual lifetime and cause

C23 `navigation.s` claims owner4 and persists68B GN_STATE at9134..9177;
REQUEST/OP are9135/9136. BEGIN snapshots canonical28 key, query/top/pan/mode,
preferred and fold-valid/generation. Each C23 STEP rechecks those fields using
actual view initialization. The cold path starts at BOF or a real C24 incoming
checkpoint; it does not possess a complete styled visual-line index.

`line_begin` requests C24 BEGIN, GN_STATE5. `semantic_ready` waits for real
GSEM_ACTIVE to clear, then `metric_ready` initializes GL and requests C20.
For a soft-wrapped continuation GN_SCAN advances to the next visual source
anchor, while logical GSEM_START/BODY/END may still describe the same CR line.
C24's real parser checkpoint can save block prefix feeding, but it is not the
85B typed53 CR/page certificate and cannot authorize C39.

C20 styling delegates SOURCE3 to C26 after saving live GL core110/map324,
packet32 and identity59 in inactive4400..47FF. GL itself is832B at8D00..903F.
C26 complete-body lookahead repeats for each visual row/window. For a long
nonempty inline body this dominates cold reveal: the prior actual66K styled
reveal exceeded200000 job12 services with error0. This is a performance limit,
not evidence that C39 corrupted continuation state. A public Plain→far→Markdown
setup is intentionally used by the current C39 repaint proof instead.

## Phase alias hazards

* Query576 at8D00..8F3F overwrites GL. Query must finish/capture before C20
  initializes GL; an old BQ frame cannot survive C20.
* GSEM at8B40 is separate from GL. C24 CP current/state occupies the same area
  as the85B CR certificate at+29..113. CP_VALID must remain0 while that area is a
  CR certificate. Actual C24 fallback changes it to a real checkpoint and ends
  the typed53 certificate route; do not infer or manufacture79B parser state.
* C39 staging8880..89F0 is inactive R21 memory, distinct from C23 GN_STATE.
  C20 SOURCE backup/restore must remain the existing path.
* C35 initial admission can MISS on inapplicable source/geometry. That must
  choose real C24, once per job/context, without clearing a valid published
  baseline or turning ordinary navigation into a user error.

## Resident routing prerequisite

Current `dispatch.s cache_complete` sends all completed odd query workers to
C21/STEP, even if root job is12. Calling C35 directly from C23 is therefore wrong.
The existing `worker_complete` label already chooses C23 when se_e_job==12 and
C21 otherwise. A prospective same-size local branch change is:

```
cache_complete:
    and #1
    bne worker_complete   ; instead of branch over owner0 store to set_page
    sta se_f_owner        ; even baseline completion still restarts C21
    jmp set_page
```

This must be range/assembled-routing qualified before any C23 query call.
C34 baseline building should not be introduced in job12: it clears owner and
restarts C21, and would overwrite C23's logical navigation continuation. A
missing/unarmed baseline should use existing C24/C20 navigation.

## Bounded next candidate, not yet implemented/fit-qualified

A genuine typed53 CR classification can supply logical kind/language/START/
BODY/END and a checked complete INLINE reference once per logical CR. Capture
its actual85B page certificate before C20 overwrites BQ. Then C39 can service
successive C20 windows without reparsing the entire body. A subsequent soft row
may reuse that classification only while GN_SCAN remains in the same actual
logical CR and current source/fold/navigation guards hold; cross-CR goes back to
checked query, and backward/page/cancel/MISS retain legacy behavior.

Budgets of frozen033702: C234063 (33free), C373636 (460free), C354090 (6free),
C204096, R144095, R254095. Copying the C21 capture+dispatch path into C23 cannot
fit. A plausible no-new-asset split is new explicit C37 operations >=4 for the
navigation classification selector/capture, moving C23's existing parsed
`line_begin` orchestration there to free C23 space. C35 remains the actual
checked lookup, and C37 still needs to capture only after its real A0/final
source guard. The C23 caller, C35 return, C37 capture and C20 transition need
measured total swaps; no per-INLINE-event supervisor is acceptable.

This is a budget hypothesis, not an assembled fit claim. New C23/old C37 under
the same resident binding needs an explicit managed catalog size/CRC API witness
and safe legacy fallback before calling new opcodes. Existing local_seed_cap
already checks such a witness for C24; any sharing/generalization must preserve
its old guard and remaining33B budget. No fake CP or unchecked role0 admission.

The first private implementation should retain current cached-page fast paths,
Plain zero-parser navigation, all command36..39/47/74/75 semantics, source lease
and root STOP/missing-outer cleanup. Do not equate fewer parser feeds with a
complete usability result: variable-width visual geometry still has to be
walked, and initial baseline/cold navigation costs remain visible.

## Measured current54 probe

`build/cache-navigation-study/20261026T035157670007Z/result.json` is terminalPASS.
The read-only probe privately reassembles C26 from the frozen source ZIP and
requires its entire3436B payload to byte-match packaged C26 before using its
`se_si_feed` label. No mutable shared label/bin is consumed. Both actual source
setup and navigation run the unchanged canonical54 assets/resident.

The interval is actual W_LOAD(target), then exported resident
`se_editor_reveal` (the same safe-point continuation used by real render/motion),
then actual service draining. It is not a physical-key measurement. Source,
history, clipboard, shim and all16MiB remain exact during navigation; actual
public rendering afterward matches the independent fullpixel model.

|Logical body|Target|Preset|Instructions|Loads|DMA|C26 feeds|
|---|---:|---|---:|---:|---:|---:|
|1024|768|Plain|211098|7|36|0|
|1024|768|Markdown|666995|11|60|1024|
|4096|3072|Plain|2287044|121|256|0|
|4096|3072|Markdown|57952554|421|7296|282624|

For4KiB Markdown,69 C26 SOURCE begins plus10143 C26STEP calls consume53684041
instructions (92.6% of the interval). Actual inline feeds282624 =4096×69. C24
has199 calls/935865 instructions; C20 has278 calls/3003969 instructions. These
are complete resident service-call attribution buckets, including that call's
admission and nested R14 work, not a claim of pure parser self instructions.
The remaining cost includes root C23, hot load, loader and initial reveal.

The1024 body fits the existing cached page, so Markdown only reparses one
logical body while resolving styled current-row metrics. The4KiB target is
outside the initial page and reconstructs69 styled visual rows. Visual TOPs
legitimately differ (Plain3021/Markdown3061) because bold has a different advance.
