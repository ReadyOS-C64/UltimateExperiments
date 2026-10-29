# Retained cache: source observation foundation

This is the implemented producer contract on `supereditor/reu-cache-redesign`.
The renderer does not yet consume the replacement semantic cache. CPU tests
explicitly arm the optional observer after creating a real type `$53` object;
that setup is not proof of a completed semantic baseline. Product startup leaves
it disarmed. See [the redesign plan](REU_CACHE_REDESIGN.md) for remaining work.

## Memory and residency

`src/cache/state.s` links last in the existing work segments:

| State | Address | Bytes |
| --- | --- | --- |
| Arena capability, ticket, incarnation, flags and queue indices | `$9FB5–$9FC5` | 17 |
| Three producer records | `$9D85–$9DE4` | 96 |

Existing data addresses remain unchanged. Ordinary BSS remains 1,534 bytes,
zero page remains 24 bytes, and `$C600–$C9FF` is reserved. Cold initialization
already clears the new tails. The standalone warm image includes these bytes;
that alone does not establish cache authority after lifecycle restoration.
The replacement cache still needs explicit resume revocation before integration.

C6 retains ordinary gap edits, caret movement and postpublication W_COMMIT.
R32 HOTCOLD handles window loading, load continuation, flush preparation and the
fallback packet operation. Its source is shared with the standalone hot probe.
The normal C4 fast packet path remains. The observer runs inside the mutation
image already loaded: it adds no overlay call or REU DMA to a warm local edit.
R32 cannot call another overlay and allocates no BSS or zero page.

## Source events

The separate 32-bit edit ticket describes visible source changes. Existing
render revision behavior is preserved; render revision is not a universal
source identity. All offsets and splice lengths are 24-bit canonical values.

- C6 reserves after quota and boundary admission, then publishes after the
  successful gap mutation. INSERT, BACKSPACE and DELETE each emit one SPLICE.
  BACKSPACE records its position after the preliminary LEFT. Movement emits none.
- R2 reserves after all fallible staging and append resizing, immediately before
  authoritative root publication. It uses the actual transaction position,
  exclusive end and insertion length. This covers byte/reference splices and
  the product's C4 edits and C5 undo/redo routes. Failed, dry-run or cancelled
  transactions emit none. The separate document replay probe is not linked into
  this editor and is outside this product observer contract.
- R32 PREPARE can reserve an uncommitted REKEY intent for a hot flush. R2 checks
  the hot/history phase, owned byte splice, actual tuple and captured revision
  and generation before consuming it. Publication commits a REKEY without
  advancing the edit ticket: those bytes were observed when they became visible.
  C6 W_COMMIT handles the checked zero/zero flush with unchanged generation.
  Later history-storage failure cannot erase an already-published observation.
- Successful H_INIT for a new history/source context clears the queue and
  ticket, advances incarnation and disarms the cache with LOST set. Repeated
  H_INIT for the same context is idempotent. This hook is after source validation
  and allocation; it is not at rollbackable file candidate adoption.

A generic committed splice while a pending merged gap has no proved matching
flush intent causes LOST, rather than guessing a coordinate translation.

## Queue and failure rules

Each 32-byte record contains kind, ticket, before/after render revisions,
position/delete/insert, before/after document generations, and CRC16. The exact
offsets are in `src/cache/api.inc`. CRC covers bytes 1–28 and reserved byte 31;
it excludes the marker at 0 and CRC at 29–30. The A5 marker, count and head publish
last. Producers bound indices; consumers must also validate queue continuity
(`head == (tail + count) mod 3`), every record and the complete ticket chain
before rebasing retained data.

Reservation sets MUTATING without advancing the queue. Publication validates
head, tail and capacity again. An abandoned intent remains MUTATING and is not a
committed record; queries must refuse it. A subsequent mutation marks LOST.
Queue overflow, malformed indices, an unexpected reservation or ticket wrap
disarms the cache, retains unread records and lets source editing continue.
Recovery requires a fresh verified baseline; no guessed or partial cache hit.

Missing R32 operations follow the existing hot-window ownership rules. A missing
fast C4 packet now takes the resident failure/cancel path, preserving the pending
gap and releasing owned history/splice work. W_COMMIT stays in C6 so cleanup
after successful publication does not depend on loading a cold helper.

## Replacement job frame

The new semantic and arena components share an exclusive owner-4 frame at
`$8D00–$8F3F`, replacing the old phase contents rather than adding resident BSS:

| Part | Offset | Bytes |
| --- | --- | --- |
| Request and semantic control | 0 | 94 |
| Block parser / phase-aliased inline parser | 94 | 79 |
| Checked source reader, including full source identity | 173 | 86 |
| Source packet | 259 | 32 |
| Semantic record | 291 | 96 |
| Arena control | 387 | 61 |
| Shared DMA/output buffer | 448 | 128 |

Legacy R14 source state overlaps the shared IO area. Output must be drained and
acknowledged before the next R14 exchange. Retaining a source reader and parser
continuation makes BODY scanning linear rather than restarting at each viewport
or inline event. Component CPU verification is separate from deployment and
renderer cache-hit verification.
