# Private authenticated INLINE consumer probe

This is an **unregistered component**, not a renderer/editor integration. The
sealed private C36 image is4091 bytes including its16-byte binding. Operations
0BEGIN/1STEP/2CANCEL require owner4 before phase access. No BSS, ZP, new bank,
object allocation, ReadyOS reserve or production build change is introduced.
A future asset number/routing adapter is deliberately not chosen here.

It consumes a genuine completed baseline built by the actual semantic producer
and typed writer, followed by successful actual C35/C37 classification and the
85-byte managed CR-page certificate. It does not parse source or infer events
from colors. A1 means pending; A0 means all outputs have passed final actual
R14 GUARD/END; A2 is inapplicable/unsupported and requires a real C26 fallback.
Carry errors preserve the actual source/provider/representation error. X/Y are
not promised. Existing root REQUEST routing is not qualified by this component.

## Exact input and staging lifetime

Inputs are the current immutable GSEM_QUERY24, COUNT0..161, START/END/BODY24 and
baseROLE0..13, with GSEM_FIRST19 frozen across every STEP. Current source syntax
caps must admit structure. The cached CR must have inline-eligible kind0..3;
region/code/other kinds return A2 rather than silently omitting presentation.
The CR START, END and BODY must exactly match the previous completed classifier
context. QUERY>=START and QUERY+COUNT<=actual merged source length are checked
before event use. A packet may cross END; bytes outside matched interiors keep
base presentation, matching the existing C26 contract.

The actual C20 GL frame is8D00..903F (832 bytes), not8880. The query overwrites
its first576 bytes, so the caller must already have saved its live core/map and
native packet through the existing SOURCE continuation4400..47FF. Before C20
continues, its actual inline_resume must restore the backed data, acquire a fresh
reader, and compare all59 old identity bytes. The343-byte stage8880..89FF is
inactive R21/glyph work during C20 layout; it is not the live C20 GL frame.
The343-byte staging layout is styles161 at8880, roles161 at8921, hidden21 at89C2;
control89D7..89F0 holds frozen inputs and bounded-work state. The query owns the
existing576-byte frame8D00..8F3F, including saved actual reader86 at8DAD,
transport61 and IO128. Header memo5 at query+134..138 is provisional until
complete payload CRC succeeds. GSEM8B40..8BFF remains unchanged except ACTIVE21
and ERROR24. The native source packet8200 and prefix8100 are preserved.

SharedIO aliases the first10 published role addresses8F36..8F3F. These bytes are
IO scratch while pending, **not consumable output**; ERROR remains2 and there is
no A0. They are saved before frame initialization and restored for unused cells
when COUNT<10. Final publication happens only after complete event ACK/source
GUARD/END, with no further DMA or source call: count styles8300, first160 roles
8F36, separate161st role8FEB, and all21 hidden bits8FD6. Out-of-count output is
preserved on success; failed/cancelled jobs leave IO aliases unspecified and must
not be consumed. This distinction is enforced in the private verifier.

## Retained authority and bounded work

BEGIN verifies the global typed53-write revocation bit, empty observer queue,
ARMED without LOST/MUTATING/ACTIVE, current full13-byte token/ticket/incarnation,
full typed logical/physical graph, CRC85, page/kind/generation/SLOTS/USED, then
actual R14 BEGIN and exactFS59 equality. The slot outside CRC85 is untrusted:
its actual CR96 must pass complete own CRC/schema/range checks and match the
previous real canonical START/END/BODY. Thus this second read needs neither
readonly root OPEN nor a repeated prefix scan/global-root record counter. The
selected CR's completion authority was established by the preceding classifier;
this component cannot select a different CR or reuse unrelated geometry.

CR flags, all INLINE refs/counts and event10 schema/width/body/end bounds remain
checked. Every new INLINE page requires actual directory CRC, header CRC and
full payload CRC; page/gen/kind request binding and live typed authority remain
checked on every service. The operation-specific header memo stores NEXT/SLOTS
only provisionally after authenticated header checks, then publishes them to the
query cursor only after full payload CRC completion. Header geometry still
requires SLOTS>0 and USED=SLOTS*10. Checked typed53 writes revoke authority even
while a header/payload/event is held. No unvalidated event or partial stream can
publish a style result.

The worker stays loaded for the whole visible packet. Each paint slice handles
at most32 cells of one checked event; parser events are never delegated through
another C supervisor. Matched strong/emphasis combine, code is exclusive role4,
confirmed escape and matched delimiters set hidden bits, unmatched bytes remain
literal. The complete persisted event count is drained, including chained pages
and bodies beyond64KiB. Final actual source GUARD and token/epoch-safe END precede
any consumable output. Cancellation closes only this job's reader/ACTIVE and
preserves foreign source leases and the published arena.

## Budget provenance and qualification

`core.s`, `page.s`, `query.s`, `source.s`, `records.s` are private operation-sized
profiles copied from the released query/arena implementation, with explicit
pruning only: uncalled root CRC/OPEN and CR prefix scan, unused output/reference
copies, copied-to-itself seed comparisons, and the authenticated-header memo
above. Actual FS59, AUTH13, typed graph, page/event CRC, used schema and bounds
are retained. No released query/arena source is edited by this experiment.
Production promotion should reconcile these profiles with shared micromodules;
this directory is not permission to add a duplicate generic supervisor.

Run `python3 tests/test_cache_inline.py`. The test builds actual sealed workers,
executes producer→writer→C35seed→consumer, and compares outputs to the independent
whole-source inline model. It includes repeated 161-cell initialization,0..161
counts, nested/exclusive/escape/heading/list cases, a66004-byte body and300 events
across INLINE pages. Faults cover owner opacity,85 certificate corruptions,
frozen inputs, actual checked writes at four phases, source changes, missingR14,
foreign leases, bad payload CRC and malformed event/header geometry even with
recomputed valid CRCs. WholeRAM, canonical source, shim and full16MiB guards are
retained. C20 backing/restore, parent dispatch, font/raster/pixel output, and
native timing are **not qualified** by this component result.
