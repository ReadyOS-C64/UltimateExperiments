# Immutable-baseline query capsule

The editor uses a4081-byte C35 seed profile and3528-byte C37 forward profile
through C21, with the managed85-byte viewport proof. Actual foreground normal
rendering and a corrupt-slot handoff are qualified, alongside native11. The
original component profiles below remain separately buildable; the private
probe section records its original component release scope.
Actual integration and remaining performance limits are tracked in
[REU_CACHE_REDESIGN](../../../docs/REU_CACHE_REDESIGN.md).

This is a private callable C-slot component, not an editor cache-hit integration.
It links shared arena `core.s`, `open.s -D BCA_READONLY_OPEN=1`, and `page.s`;
query `query.s`, `source.s`, and `records.s`; and a small binding/owner/selector
entry. The private selector uses ID35, operations 0 BEGIN, 1 STEP, 2 CANCEL,
3 ACK. It currently fits 4038 bytes including its 16-byte resident binding.
No resident BSS, ZP, new asset registration, or general DMA changes are required.

The caller owns phase owner4 for the whole job. `api.inc` defines a query frame
inside the first387 bytes at $8D00, shared arena control61 at +387, and IO128 at
+448. BEGIN takes ABI1, CAPS1 or3, and canonical POSITION24. Flags must be ARMED
without LOST/MUTATING/ACTIVE and the observer queue must be empty. Missing or
unusable baseline returns A2/Cclear. A1/Cclear means another bounded service
call is needed. A0/Cclear is successful completion. Errors set carry and retain
the primary error in BQ_ERROR; C0 argument, C1 changed authority, C2 corrupt
representation, C3 already-busy query, B2 wrong owner. Provider errors propagate.

## Source and representation authority

The query requires a completed semantic root with block/inline ABI1 and no
completed lexical certificate. It compares the root's exact FS59 snapshot and
merged length to an actual R14 BEGIN, then uses actual R14 GUARD on subsequent
unheld boundaries. This intentionally includes pending geometry/caret-related
snapshot fields: navigation equivalence is **not** inferred. Runtime tracing in
the test permits only R14 operations0/1, never READ/parser feeds or other C
workers. Every boundary also checks captured arena/token/ticket/incarnation,
flags/queue, and the real typed object's logical/physical ownership graph.

The readonly OPEN profile shares the actual root A/B selection and checks with
the standard transport. It cannot create, initialize, trim, release, or publish
an object. The profile-absent2257-byte reader and4058-byte writer are byte-identical
to the committed default implementation. Complete page payload CRC is checked
before a retained page proof can serve records; the proof is exclusive-job,
page/generation/kind bound. Headers, CR own CRC/schema/ranges/reserved bytes,
page/slot/gen references, contiguous canonical CR/NEXT progression, root final
EOF/LAST, and complete INLINE event counts/widths/ranges are checked.

The initial writer allocates page chains monotonically. This first query profile
requires increasing page links, and is not yet a reader for arbitrary future
page reclamation/reordering. Record count is bounded to the initial one-bank
writer's capacity. Native inline style events are staged as10-byte records;
this component never supplies a lexical certificate (`BQ_LEX_CERT` is always0).

## Output and lifetime

READY1 holds the complete CR96 in IO and BQ_CR; BQ_RECORD_REF identifies it.
READY2 holds one INLINE10 in IO. Repeated STEP while READY is held checks live
arena authority but leaves IO and all query state unchanged. The caller drains
IO before ACK because actual R14 source exchange aliases part of IO. ACK runs
real source GUARD before advancing. The complete CR and every event are
**provisional** until final A0: a later event/reference/source fault must prevent
consumer publication. No caller may treat READY alone as a semantic hit.

CANCEL clears only this query's arena phase/proof and its own source lease via
resident `se_fs_end`; it never uses the general arena candidate-cleanup cancel
and never frees a published or changed capability. A foreign source lease is
retained. A missing R14 can still clean up through resident END. If the outer
query C asset itself becomes unavailable, the eventual root adapter must run
an equivalent resident cleanup using the saved reader context; that adapter is
outside this component.

## Reproduce

Run `python3 tests/test_cache_query.py`. It first executes the real semantic
producer/writer baseline pipeline, then actual sealed query service calls.
The positive oracle is the independent full-source block/inline model. Sources
include empty/CR EOF sentinels, mixed Markdown/code,300 events across pages,
and a66015-byte logical body. The test retains runtime admission traces,
per-call whole-RAM guards, whole16MiB readonly checks, and fault evidence.
There is no VICE, performance, renderer, navigation-reuse, or UI-hit claim.

## Optional editor ACTIVE profile

Define `BCQ_EDITOR_ACTIVE=1` for all query modules to produce the4061-byte
editor profile. Without that definition the default4038-byte payload remains
byte-identical (SHA256 `9233b2e7b77ec4a04b17f4c6c4e4dcf32c8197c31d6dc0f9bc56b59a8f61d0c0`
for the pinned bf15/4b8f fixture). This is a profile distinction, not a new
persistent schema or source-equivalence rule.

The profile remaps the saved86-byte reader to `BC_FRAME+173 = $8DAD`, sharing
the existing semantic worker's resident fallback contract. Q_LIVE is already
at `BCF_FLAGS` (+3); it is1 only after actual R14 BEGIN succeeds. Only then does
BEGIN claim `BC_ACTIVE`; opening/validating roots before the source lease has
no active resource claim. Subsequent STEP/ACK requires exactly ARMED|ACTIVE
among the four defined flag bits while Q_LIVE1; prelease work requires ARMED.
A competing BEGIN returns busy before altering any frame or existing claim.

Completion/cancel/error with an owned live reader clears only ACTIVE and uses
resident `se_fs_end`, preserving ARMED/LOST and foreign leases. An existing LOST
cause is retained. An unrelated ACTIVE claim encountered before Q_LIVE is
never cleared. A root adapter must own foreground owner4 exclusively throughout
the job; it must not admit a second job over this saved frame.

If the outer C query image is missing, a resident fallback can check owner4 and
ACTIVE, copy reader86 from $8DAD into resident se_fs_state, call resident
`se_fs_end`, copy back the cleared context, clear query state/READY/Q_LIVE and
owned arena phase/proof, and AND ACTIVE out of the live flags. It must preserve
ARMED (unlike a failed baseline writer, whose incomplete baseline needs LOST).
Token/epoch-safe END will never release a newly current graph's lease. Before
source acquisition there is no owned lease and ACTIVE is unset; the root still
owns resetting the abandoned job/frame/phase. No saved stack or C continuation
is required. The private test executes this fallback as a cold-only6510 adapter;
it is not a claim that the product root has already linked that adapter.

Run `python3 tests/test_cache_query.py --editor-active` for the complete positive
and fault matrix plus ACTIVE lifetime, competing BEGIN, unavailable-outer,
foreign-owner fallback, and idempotent cleanup. It also relinks the default
profile and verifies its exact released payload hash.

## Classification-only selector

`classify-entry.s` is a separate private selector for C35, built with
`BCQ_EDITOR_ACTIVE=1`, `BCQ_CLASSIFY=1`, and
`BCQ_SELECTOR_OWNS_OWNER=1` consistently for the query modules. It is4025 bytes
including binding. The selector checks owner4 before any frame access; its
three operations are BEGIN0, STEP1, CANCEL2. The conditional body omission
removes only redundant owner checks whose public selector has already admitted
owner4, and INLINE traversal/schema code not used by this output. The original
default4038/editor4061 payloads remain byte-identical.

BEGIN rejects an existing GSEM_ACTIVE/BC_ACTIVE job before resetting query576,
reads canonical GSEM_QUERY at $8B40 and `se_render_caps`, clears the old C24
checkpoint, and starts the checked query. Root must have requested C35 already;
successful BEGIN changes root operation $9136 to1. Held CR_READY is internal:
the next STEP ACK runs actual final R14 GUARD, ends the owned source lease,
then publishes GSEM fields5..20. It never invokes another C worker per record.
Input query/language/count and parent page9134..9177 survive, except OP9136.

GSEM_ERROR24 starts at2 and becomes0 only at final publication. The initial exactFS59 or mergedlength mismatch after actualR14BEGIN also returns
A2/Cclear: a valid baseline can be inapplicable after hotcursor movement. This
ends only the owned source lease and publishes no semantic result. Midjob changes,
CRC failures, and actual R14 errors remain errors. A2/Cclear is an
optional MISS with ACTIVE0/ERROR2 and no classification publication; Cset stores
the actual error and ends owned resources. GSEM_ACTIVE21 is1 while pending and0
at completion/miss/cancel/error. CANCEL does not turn an incomplete result into
ERROR0. The root can distinguish A0 completion from A2 MISS after routing back
to its parent through ERROR. Outputs exactly reproduce current C24 semantic
kind/language/level/marker, START/BODY/END, palette role, heading inverse, and
8/9px height mapping. A terminal FF descriptor becomes ordinary empty prose.

This selector does **not** depend on inline grammar: after a fully checked CR,
it completes without opening the referenced INLINE pages. CR inline flag/ref/
count schema remains checked, as do root/page/record CRC, source59, typed graphs,
canonical bounds and final source guard. Deliberately corrupt INLINE schema or
payload CRC cannot influence this classification. There is no INLINE completion
or lexical certificate in its output. For kinds0..3 it sets GSEM_INLINE169 to1
as a conservative **hint**, allowing the existing actual C26 fallback to compute
inline styles; that is not cached inline reuse. Other kinds set it0, matching
the current literal C20 inline-eligible scope. The classification never creates
a C24 parser checkpoint, so CP_VALID is0.

`python3 tests/test_cache_classify.py` builds this profile and byte-checks both
older profiles, then runs real baseline producer→writer→classification services.
The independent full-source model checks40 positions spanning all9 block kinds,
BASIC/ASM, empty/CR terminal events, pending merged input and >64KiB anchors.
Faults cover owner opacity, MISS/error handoff, held-CR source change, cancellation,
competing BEGIN, corrupt CR payload and corrupt unrelated INLINE data. Runtime
tracing allows only C35 plus R14 BEGIN/GUARD. No block/inline parser runs in the
classification operation. This remains a private selector qualification, not a
renderer integration, body cache hit, native performance or navigation-reuse claim.


## Optional viewport CR-page proof

The explicit `BCQ_PAGE_REUSE=1` classification profile fits4075 bytes. The
normal corrected classifier4025 and original full-query4038/editor4061 profiles
remain separately buildable; the latter two retain their released bytes. This
profile reuses only an already verified CR page, not INLINE events or a lexical
certificate. Each new query still performs readonly OPEN/root CRC, actual R14
BEGIN, exactFS59/length comparison, and typedarena/source authority checks.

`proof-api.inc` reserves85 bytes at GSEM+29..113: source59, authority13,
page/generation/kind4, USED2, NEXT4, SLOTS1, CRC2. CRC covers bytes82..0 in
descending order with the existing CCITT-FFFF primitive. C20/C25/C26 must preserve
this area. A parent clears `BC_PAGE_PROOF` on a fresh viewport, legacy C24
fallback, and painting. Every checked type53 CPU→REU write must clear the bit
before DMA; other typed objects do not revoke this proof. The private verifier
executes a cloned actual frozen DMA routine with that additional hook. The main
resident hook and C21 wiring are parent-owned and are outside this component test.

BEGIN arms the bit as an exclusive-job writeguard. If it was already clear,
BEGIN first invalidates the old external certificate kind. Every subsequent
STEP/ACK requires the bit, including CRC-in-progress and held-CR boundaries.
Thus a type53 write cannot leave either local BCA_PROOF or a saved external
certificate usable. Restore requires bit32, certificateCRC, exact59+13 authority,
and matching CR page/generation/kind; a failure performs ordinary page validation.
Used block geometry/schema and whole root/page/CR CRC checks remain. Unused INLINE
count/ref completion checks are omitted only in this classification profile.

The optional C21 capture helper is133 bytes. It requires bit32 on entry, clears
it immediately, then verifies successful completed query state, owned-reader
closure, saved proofA5, and CR kind. A skipped capture returns Cset and leaves
bit32 clear; it never writes the certificate. Success copies85 bytes including
CRC and sets bit32 last before returning Cclear. There is no DMA, yield, or
foreground interleaving inside this CPU-only helper. C21 must not clear bit32
before calling it, and must skip outgoing carry publication on Cset. This also
rejects a type53 write between queryEND and capture. No fake C24 checkpoint is
created; any outgoing carry adapter must consume actual authenticated CR carry.

Run `python3 tests/test_cache_query_proof.py` for actual producer→writer→query
control/reuse A/B, prospective capture, and executable typedwrite-hook tests.
The suite checks multiple CR pages, all block kinds, pending/24-bit sources,
all85 certificate byte corruptions, in-job writes at four distinct boundaries,
post-END writes, false capture preconditions, and unrelated FE writes. Per-call
wholeRAM and whole16MiB readonly guards remain. Timings reported here are CPU
component instruction counts, not complete renderer/native latency.

## Private retained-forward classifier probe

`fast-entry.s` is a separate C37 probe, not registered by this component. It
links query/source/records with `BCQ_FORWARD_QUERY=1`, `BCQ_FORWARD_SEED=1`,
`BCQ_PAGE_REUSE=1`, `BCQ_CLASSIFY=1`, `BCQ_EDITOR_ACTIVE=1`, and
`BCQ_SELECTOR_OWNS_OWNER=1`; arena core/page are linked, readonly OPEN is not.
The sealed image including binding is3491 bytes. No BSS, ZP, bank allocation,
additional phase span, or resident instruction is added by the probe.

The companion C35 seed profile adds only `BCQ_FORWARD_SEED=1` to the PAGE build
and is4081 bytes. After actual final source GUARD/END and classification mapping,
its publisher saves the matched CR slot to `BCQP_SLOT = GSEM+114`. Under this
classification-only flag `BQ_RECORD_REF` aliases the still-current BQ_REF, so
no extra reference staging is needed. The85-byte certificate remains unchanged.
All four released profiles (4038/4061/4025/4075) retain their exact payloads when
the new flags are absent. The slot is deliberately **not** trusted authority.

C37 BEGIN first checks owner4 and competing jobs before resetting query576.
It requires ARMED, an empty observer queue, the global managed-write proof bit,
and a nonbackward query relative to the previous real GSEM_START. It captures
current13-byte authority, checks the full typed object graph, verifies CRC85 and
its full59/13/page/gen/kind binding, and checks page allocation, generation,
SLOTS1..42 and USED=SLOTS*96. It then runs actual R14 BEGIN, claims ACTIVE only
after acquiring its source lease, and compares the exact59 source snapshot.
Actual merged length comes from that checked reader. No root or payload CRC is
repeated on this path: the managed viewport certificate retains that proof.

The first96-byte record must pass its own complete CRC/schema/range checks and
its canonical START must equal the previous real GSEM_START. A corrupt slot
therefore cannot select an unrelated classification: invalid slots and first
START mismatch release only this query's lease and request actual C35 BEGIN.
Within the page, START/NEXT continuity and exact checked membership remain;
page-local remaining count bounds traversal. Every STEP and final ACK retains
all source,13-byte tuple, typed graph, flags/queue, and write-revocation guards.
There is no relaxed source-equivalence assumption or cached inline certificate.

A successful result has the same GSEM fields/error/ACTIVE contract as C35 and
publishes the new slot. Invalid/revoked certificate, backward input, or exhausting
the page releases owned resources, sets GSEM_ACTIVE0, REQUEST=$9135=35 and
OP=$9136=0, then returns A1/Cclear. The caller must invoke that requested worker
on the next foreground slice; this is not a nested C call. C37 ordinary pending
retains REQUEST37/OP1. Initial source geometry mismatch returns A2/ERROR2;
midjob source/provider/record errors remain carry errors. X/Y are unspecified.

The integrated resident preserves odd query workers' pending operations.
Actual foreground rendering and corrupt-slot C37→C35 BEGIN0 handoff are covered
by `tests/test_cache_forward_editor.py`. The manual component frontend below
still has the narrower scope stated by its verifier.

`python3 tests/test_cache_query_forward.py` runs real producer/writer, seededC35,
and C37 through actual sealed outer-worker calls, following REQUEST/OP explicitly.
Its101 positions include a complete60-CR+EOF sequential walk with exactly two
C35 BEGINs (initial page and one page-boundary handoff). The independent model
checks classification for all9 kinds, languages, pending and >64KiB input. Tests
cover every256 slot values, all85 certificate byte flips, foreign owner opacity,
checked identical type53 writes during READ/heldCR, actual public W_LOAD snapshot
inapplicability, cancel and prior classifier faults. WholeRAM and16MiB guards
remain. This is component CPU performance evidence; no complete editor/native
latency claim follows from it.

## Optional completed-empty inline shortcut

`BCQ_EMPTY_INLINE_HINT=1` adds37 bytes to C37 only (3528 total); the default
3491-byte C37 profile remains byte-identical. For an eligible prose kind, hint0
requires the already checked CR to contain completed-inline flag4, zero24-bit
event count and the canonical four-byte FF reference. Every other case retains
hint1 and the existing C26 parser. There is no INLINE page traversal or claim
that nonempty events were reused. All other semantic fields and source/record
validation remain unchanged. Source policy and repeated parser work are tracked
in the public redesign document.

`tests/test_cache_inline_hint.py` retains independent pixel/counter A/B cases,
real PETSCII5C escape and A3-literal distinctions,256 events, source/record faults,
foreign owners, and conservative valid-CRC malformed metadata cases. Actual
editor5/foreground2/parser55/incremental15/stack68/native11 pass on the enabled
product. Native Full10,976,686 PAL cycles is still above the older9,511,774 path.

## Committed-only source admission

`BCQ_COMMITTED_IDENTITY=1` adds a C35→C37 operation3→C35 operation1
continuation when the immutable baseline's full source snapshot differs from
the newly acquired real reader. Both pending flags must be zero and all29
canonical prefix bytes identical; C35 has already checked merged length.
C37 checks the current13-byte authority, flags/queue and real R14 GUARD before
copying its actual current59-byte identity to the local query snapshot. All
subsequent guards and published page certificates remain exact59.

C354090/C373636 (including empty-inline hint) fit existing slots. No extra
resident/catalog/BSS/ZP bytes are required. Inapplicable identity returns MISS2
without output; source/authority faults close the owned lease and return an
error. An old C37 certificate still refuses changed geometry: fresh C35
admission is required. Pending edits, REKEY/SPLICE and observer rebasing are
not authorized. Flag-off profiles compile byte-identically to their predecessors.

The component gate covers102 modeled positions,20 fault groups and1362
wholeRAM calls, including actual W_LOAD beyond64KiB. Actual public rendering,
missing-C37 and queued-key cancellation/recovery, parser bypass, incremental
edits, stack and native11 also pass. Performance remains open: the small
navigation case regresses11.96%. The initial sparse66-KiB case regressed19.75%
because its C35 seed induced198,000 unnecessary C26 feeds. The compact C35
publisher now uses the same completed-empty check as C37, removing those feeds
and reducing the same-source interval92.066M→56.358M instructions. Its direct
publisher/result seam checks1,050 independently modeled fields/predicates and14
A/P/SP cases;30 public frames, six fault groups and1,920 predicates also pass.
No source/authority check was removed. See the public redesign document.
