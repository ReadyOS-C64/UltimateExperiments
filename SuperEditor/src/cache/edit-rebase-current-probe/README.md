# Private current-schema single-edit materialization

This is an executable, unregistered component proof against immutable
`build/lexical-batch-current/20261026T194420618867Z/fixture`. It does not change
canonical sources, Make, resident code, catalog registration or physical devices.
Its public comparison uses the actual unmodified C35/C37/C39/C45 readers from
that fixture, rather than a mapped-selector or forged page-proof profile.

## Admission and authority

C40 accepts exactly one genuine unread observer SPLICE: one inserted literal
byte, no deletion, ticket+1, revision+1 without wrap, unchanged document
generation, one committed old baseline and one current pending merged source.
The old arena must be actual BASE|LEX flags5/ABI1, zero durable journal entries,
one CR page of 1..42 records, and exactly one retained CODE_LINE LEX reference.
Unknown flags3/7 remain refused. The dirty event must be an interior insertion
in a complete, CR-terminated ordinary line with completed empty INLINE, no
prefix/markup/CR change. Actual SuperMark reparses the complete current dirty
line from its authenticated incoming carry; matching actual outgoing carry and
boundaries is required. It does not infer convergence from a source hash.

The retained lexical BODY must lie strictly before the insertion. Its genuine
LXC1 body/end and absolute spans stay unchanged; only its real current FS59 and
AUTH13 descriptor fields are replaced after this proof. There is no implicit
shifted-code transform. Unchanged CRs get live absolute START and tickets only
after the one-event source proof and parser convergence; relative fields and
inline references remain unchanged. The production readers revalidate the
result and consume it without any schema acceptance changes or parser feeds.

## ABI and placement

- Private C40, slot1: op0 BEGIN, op1 STEP, op2 CANCEL; A1 pending/A0 complete,
  A2 safe admission miss, carry set error. Owner4 is required before phase access.
- Private R34, slot0: existing arena OPEN0/STEP1/PAGE2/READ3 transport plus
  COW_BEGIN4/COW_STEP5. C40 and R34/R14 finish sequentially, never same-slot
  nesting. Only C40's owned source lease survives yields.
- No new BSS, ZP, object or physical-bank assumption. Existing BC_FRAME576 and
  scratch `$8880..$8B3F` are borrowed only under owner4. Actual SM79 occupies
  BC_FRAME+94; its dead storage becomes the publication controller after parse.
  The actual source86 snapshot remains BC_FRAME+173, compatible with the pinned
  resident cache-job emergency cleanup.
- Existing arena **logical** pages14 and15 must have empty directory entries.
  They hold the new CR and LEX pages. Offset translation is through the typed
  logical object service. No fixed physical REU bank is used.
- Old selected root and reachable pages remain unchanged. Allowed writes are
  exactly alternate root128, directory entries14/15 (16B), journal event32,
  CR64+96*N bytes and LEX64+used bytes. Bytes outside used payloads stay guarded.
- Canceled drafts can leave unreachable pages/directory entries. A retry refuses
  occupied pages; reclamation/general allocation is not implemented or claimed.

## Publication and cancellation

Every yielded C40 STEP checks actual current FS59, AUTH13, event bytes/CRC,
head/tail/count, capabilities and source lifetime. COW transfers remain at most
128B. Each original page payload and individual CR CRC is checked while copied.
The terminal critical call rereads the old selected root byte-for-byte, verifies
both complete candidate pages and their private expected payload CRCs, writes
alternate root VALID0 then VALID1, and only then retires the RAM event. There is
no yield between final verification and publication/retirement, and no global
revocation bit is borrowed. The terminal page verification is bounded by two
4032B payloads; its cost must remain visible in any later product latency review.
The actual tested six-record/short-LEX case costs about34k CPU instructions for
that terminal call, not a claimed worst-case 42-record latency bound.

STOP, missing C40/R14/R34, source/ticket changes and errors preserve canonical
bytes, history, pending input, unread events and old root/pages. An actual
provider-epoch mismatch deliberately does not release an old graph's lease:
that is the existing `se_fs_end` no-foreign-release contract. The verifier's
synthetic epoch rollback restores the actual saved reader only for explicit
same-lifetime test teardown; it is not a production recovery claim.

## Reproduction

```
python3 tests/test_cache_edit_rebase_current.py --length 1000 --faults
python3 tests/test_cache_edit_rebase_current.py --length 8000 --mixed --faults
python3 tests/test_cache_edit_rebase_current.py --length 65520
```

`build.py OUTPUT FROZEN_FIXTURE` assembles from the fixture's source ZIP and
resident report only. It separately proves byte identity for the actual C24/C25
parser symbol maps. No shared build or mutable generated aliases are read.
Source hashes, exact byte budgets, results, independent images and prior host
assertion failures are recorded in the release receipt/evidence archive.

The measurement includes genuine public Q insertion, component rebase and an
explicitly forced full public repaint. It is CPU instructions, not PAL cycles,
native key latency or a normal fast-typing-path claim. A 1k line regresses; a
long retained code line benefits. Glyph/layout work on that long line remains.

## Production boundaries still required

This is not a production promotion request. A real implementation needs:

1. Review of source/observer trust and a policy admitting only useful eligible
   edits; do not route small cases indiscriminately or accept unread REKEY.
2. Explicit catalog registration for the two private profiles (59->61 of64),
   resealed resident ABI and all-asset/disk verification. The pinned COLD segment
   has48 bytes before `$0F00`; two packed entries cost6 bytes plus DOS names (or
   proven aliases). No resident hook, name registration or growth is hidden here.
3. Owner4 orchestration before old C21 layout, preserving exact source lease
   cleanup if the new caller is missing. The private caller explicitly clears
   `se_i_ready`, `se_i_count`, `se_n_cache_count` before borrowing the phase union.
   Actual resident/overlay byte budgets and all-mode error/input routing must be
   linked and tested; this leaf proof alone does not certify that integration.
4. A general logical COW allocator/reclamation plan, further event classes and
   REKEY composition. Multiple edits, edit-before-code/shifted lexical spans,
   deletion/replacement, delimiters/fences/CR, multiple CR pages and root1 plain
   baselines remain explicit fallback cases. Existing flags3/7 are not adopted.
5. Actual public integrated/natively measured render, navigation, cancellation,
   capacity/lifecycle and stack qualification after any integration.
