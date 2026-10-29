# Sequential semantic batch worker

This is the replacement cache's parser producer, not an editor integration or a
trusted retained-cache hit. It runs the actual SuperMark block and inline code
over the actual checked merged/piece source reader. It emits complete logical
line descriptors and confirmed inline events with 24-bit source offsets.

The original released selector gate is
`build/cache-semantic/20261025T230506994396Z/result.json`: ten positive cases and
eleven fault groups passed. Its complete C-slot capsule is4,082 bytes:
entry60 (including16-byte binding), worker2035, block1076, inline911.
The compact release below preserves that output contract. It adds no BSS or ZP.
The probe binds the new17-byte descriptor and96-byte observer ring to their
granted segment tails in the immutable19fe product fixture; it does not claim
that this capsule or the new arena writer is integrated into that product.

## Compact generic and selector-owned profiles

`build/cache-semantic-selector/20261025T233730179345Z/result.json` executes the
original4082-byte baseline, compact **4019-byte generic** capsule, and compact
**3978-byte selector-owned** capsule. Each passes the same ten cases and eleven
fault groups. Across8757 actual opcode calls per variant, all576 caller frame
bytes, returned A/C, counted leases and owner values are identical. The generic
variants additionally refuse24 direct exported-function calls across all four
operations/six foreign owners without writes outside CPU stack or to16MiB REU.

Default assembly retains the worker's independent owner checks. Compile only
`worker.s` with `BSC_SELECTOR_OWNS_OWNER=1` to remove those duplicate checks and
their private helper. That profile must be entered **only through the actual
owner-checking selector**; its exported worker labels are not safe independent
public entry points. IRQ only queues input and does not change foreground phase
ownership. A future selector/pump must preserve that rule before invoking any
worker routine or reading its frame.

The selector-owned capsule leaves118 bytes below4KiB for parent-owned dispatch
work. This is a linked size, not an assertion that a future pump fits. No extra
clear-record/source/arena helper calls were introduced. The other changes fuse
the two ticket copies with NIL-reference initialization, fuse terminal incoming
and outgoing carry stores, remove loads of already-proven zero, and use short
branches whose signed ranges assemble in both profiles. Bounds, full authority,
source guards, format, read/feed budgets and cancellation are unchanged.

Reproduce with `python3 tests/test_cache_semantic_selector.py`; `--smoke` is an
explicit reduced gate. It requires the immutable original release/source archive
and holds entry/state/API fixed. It does not qualify a later auto-pump selector,
arena writer integration, changed resident binding or native performance.

## Calling contract

The selector at binding+16 reads `se_overlay_frame`:

| Operation | Value | Meaning |
|---|---:|---|
| BEGIN | 0 | Capture exact arena/incarnation/ticket and acquire checked source |
| STEP | 1 | Advance a bounded parser slice or expose a pending output packet |
| CANCEL | 2 | Discard private output and release only this job's source lease |
| ACK | 3 | Acknowledge the pending packet after its consumer has finished |

All entries require owner4 **before reading the phase frame**. The caller owns
that phase claim and must first invalidate persistent line-index state, as for
the other replacement-phase users. The worker never releases the caller's
owner4 claim. BEGIN requires ABI1 and zero STATE/FLAGS. CAPS0 returns miss
without parsing or taking a lease; CAPS1 and3 run the same structural/inline
producer. Lexical coloring is a separate future stream.

Return C clear/A1 means pending, A0 complete, A2 disabled/miss. C set reports
error90 (bad frame), B1 (changed authority), B2 (foreign/busy owner), or the real
reader/overlay error. Cancellation is idempotent and epoch/graph safe. The
counted reader is closed on completion, cancellation, and active-job failure.

## Workspace and source lifetime

The576-byte frame is at8D00. Producer/header0..93, aliased parser94..172,
saved reader173..258, feed packet259..290, and staged CR291..386 belong to this
worker. Arena control387..447 is opaque and unchanged. IO448..575 is shared
only when no outstanding packet is held. No resident state is added.

The real block79 and inline68 layouts are link-checked against separately
assembled original parser state objects. Incoming/outgoing six-byte block
carry, offsets, kind and language leave block state before inline aliases it.
Only eligible prose/heading/list BODY is fed through inline. Code/fence/region
rows retain actual block classification without invented inline interpretation.

The checked source reader's86-byte context is exchanged with the existing R14
FS context for each actual BEGIN/GUARD/READ. That legacy context aliases IO;
therefore no R14 exchange occurs while READY is held. No VIEW cache, raw bank,
flattened whole source, or presumed physical mapping is used. Resident FS END
permits safe cleanup even when the R14 image is missing.

Each STEP accepts at most32 source bytes in total and issues at most one actual
source READ. The current inline BODY packet/cursor survives output backpressure;
successive event windows do not restart or refeed that BODY. Classification
and inline are separate passes, so eligible BODY bytes participate in both
phases. Block prefetch beyond CR may be read again, but feed counters prove
each canonical byte enters block once and each eligible BODY byte enters
inline once. Cold source-image CRC admission remains part of the measured
instruction cost; no native cycle or latency claim is made.

## Output and publication

READY1 exposes a96-byte CR descriptor at IO; READY2 exposes a10-byte inline
event. Repeated STEP with READY nonzero leaves that packet and parser progress
unchanged. The consumer must finish APPEND before ACK. It must drain/copy the
packet before any arena/source service reuses IO. ACK revalidates both current
cache authority and the full checked source before clearing READY.

The CR uses the retained-cache ABI: START24 and END/BODY/NEXT-relative24,
incoming/outgoing carry6, captured ticket/proof/ABI fields, language/level and
marker. Its CCITT-FALSE CRC excludes publication byte0 and bytes74..75;
publication byte0 is written last. Inline-complete is set only after the whole
eligible BODY, FINISH and every pending event have drained. Confirmed events
remain in actual parser order: kind/style/width, OPEN-relative24,
CLOSE-relative24, reserved0. Event count is24-bit.

The descriptor's stream references remain NIL until the consumer assigns real
arena references, reseals the descriptor, and publishes a validated root. A
NIL inline reference with nonzero count is a completed **staged** semantic
result, not a persistable trusted CR. Empty source and terminal CR have an
explicit kindFF layout EOF sentinel; it is not represented as a parser event.
An unterminated real line receives EOF directly.

BEGIN/STEP/ACK validate captured token5/incarnation4/ticket4 against the live
descriptor and validate its complete typed object capability (type53). Source
guards retain all actual reader identity fields. MUTATING always refuses.
LOST refuses except for explicit BUDGET bit7 REBUILD with an unarmed arena.
The worker never clears LOST or publishes ARMED; the baseline writer must
independently authorize the initial EMPTY/unarmed root and commit VALID last.

## Reproduction and limits

Run `python3 tests/test_cache_semantic.py` or use `--smoke`; `--fixture PATH`
selects an immutable product fixture. It builds only private outputs. The
released gate executes all operations through the actual selector and real
sealed R14 calls, not host parser events. Host models independently check
classification, full six-byte carry including region overflow, inline spans,
record CRCs, and exact24-bit ranges.

The matrix includes empty/CR/EOF, mixed dialect, nested/escaped/unclosed inline,
32-byte boundaries,1510-byte late closure,66052-byte BODY, region overflow,
actual pending edits, and36 actual piece-table splices. Faults cover all four
entries under six foreign owners, token/ticket/incarnation changes, foreign
epoch/graph leases, held output/cancellation, missing R14, stale source,
malformed pending gap, and out-of-range progress. Complete16MiB REU remains
read-only in this producer-only proof; canonical source/history/capabilities,
catalog, shim, VIEW/NAV/diagnostic memory and arena61 remain exact. Explicit
real transport/source workspaces and hardware DMA registers are the only RAM
write allowances.

This release does not yet prove arena append/root commit, retained lookup,
observer replay, renderer integration, suspend/resume, small-REU admission,
native execution, or improved end-to-end latency.
