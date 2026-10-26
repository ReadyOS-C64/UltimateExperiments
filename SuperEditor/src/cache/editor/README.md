# Automatic semantic baseline pump

This is a qualified component, not editor registration or a retained-cache
consumer. C34 remains loaded while its selector drives the actual block/inline
producer, R14 checked source reader and R33 checked baseline writer. There is no
host per-record APPEND/ACK supervisor and no extra R32 clear-record call.

Link `entry.s`, the semantic worker/state and actual block1076/inline911 code.
Compile **worker.s only** with both `BSC_SELECTOR_OWNS_OWNER=1` and
`BSC_AUTO_OWNS_CANCEL=1`. The whole image is **4096 bytes**: entry214 (including
binding16), worker1895, unchanged parsers1987. No new BSS/ZP. Generic4019 and
selector-only3978 profiles remain byte-identical to their preceding release;
the automatic profile exports private `se_bsc_owned_release` instead of the
unused public worker CANCEL wrapper.

## Caller and admission

The caller owns owner4 before entry. It has already opened/validated an EMPTY,
unarmed typed53 arena through the real R33 OPEN and drained that operation.
Initialize the actual shared576-byte frame/ABI/caps and its captured token5,
incarnation4/ticket4. The existing arena control61 must still describe that OPEN;
do not clear it after admission. LOST rebuild additionally needs explicit budget
bit7. This component does not allocate/admit the arena itself.

All opcodes check owner4 before frame access. The selector reads
`se_overlay_frame`: BEGIN0, STEP1, CANCEL2. ACK3 is internal, never a public pump
opcode. Unknown opcodes return90 without cancelling a competing job. A failed
BEGIN returns its error without cleanup: an existing active phase must not be
mistaken for a newly acquired lease. Once its own producer BEGIN succeeds,
writer/source/controller failures run owned cleanup.

**Required root scheduling contract:** after C7 publishes REQUEST34/OP0 and
C34 returns pending A1, the resident dispatcher must retain REQUEST34 and
publish OP9136=1 for the next service. C34 does not write that parent field.
Calling BEGIN again is correctly busy, not continued work. The component test
uses real opcode calls on an old immutable resident and therefore does not
qualify the new resident service route. That route needs its own product test.

The binding/header and all resident imports must be regenerated for the target
resident; the released proof uses immutable19fe/bf15's actual provider/loader
and explicit new descriptor/ring tail seams. It imports private sealed C34 and
R33 images through the real loader; it does not add them to product startup,
the D81 manifest or its frozen source catalogue.

## Work and return values

BEGIN starts the checked semantic producer and R33 baseline transaction. STEP
performs one producer slice, one writer service, or one ACK transition. It
never feeds more than32 parser bytes and never requests R33 more than once per
public invocation. Actual overlay/source admission costs are included; this
does not promise <=128 total DMA bytes per call because overlay loading itself
may copy4KiB. R33's actual individual metadata/payload operation bounds remain.

Header byte82 is the private APPEND-in-progress latch, cleared by producer
BEGIN. A READY packet is APPENDed before ACK. While R33 is pending, the producer
and its output remain held. ACK runs only at BW_IDLE after APPEND completes,
then parsing may resume. FINAL runs only after actual parser completion/lease
release and every packet is drained. R33 publishes record/page/root VALID last
and retires the covered observer queue only after the root commit.

Returns C clear/A1 pending, A0 completed baseline with ARMED, A2 Plain miss,
A3 STREAM (optional capacity fallback); C set carries the real error. Plain
miss neither acquires a source lease nor requests R33. Inactive CANCEL is an
opaque A0 no-op. Active CANCEL is idempotent, runs no R33 call and leaves
LOST|REBUILD_TRIED (18). Closed STEP returns90 instead of pending forever;
after successful completion it preserves the existing ARMED baseline.

STREAM must call **owned_cancel directly**: the writer has already cleared
ACTIVE on exhaustion, so the public ACTIVE-gated CANCEL would skip the still
owned source lease. The fixed path releases it and sets LOST|TRIED. The root
can then fall back to ordinary rendering without immediately retrying the same
failed baseline. H_INIT/new-source policy owns resetting the retry witness.

## Cleanup and the missing-admission boundary

Owned cleanup uses actual saved reader86 and always-resident epoch/token-safe
FS END. In this automatic profile it does not trust the producer's separate
live-flag byte to decide whether to end an acquired lease; malformed producer
flags are still rejected at their next use. It clears the CPU writer phase and
page proof, marks LOST|TRIED and preserves the canonical document. It never
depends on loading the failed R33 image. New graph/epoch foreign leases are not
decremented. Producer private flags/state/output are discarded, not committed.

This cannot clean up when **C34 itself cannot be admitted**. The real provider
epoch fault test returns asset error18 in63 instructions before C34 entry;
the complete576-byte phase and seven newly current leases stay unchanged. The
eventual resident root must restore the owned saved86 into real FS, call the
resident END while the stale epoch/graph is still visible, and revoke its own
CPU job/owner. Do not restore the old epoch and then release foreign leases.
Missing C34 and resume/provider rebind cleanup need that same explicit root
integration. No such integration is claimed by this component proof.

## Qualification

Run `python3 tests/test_cache_pump.py`; `--smoke` is explicitly reduced. Only
private outputs are written. The test retains the released writer's independent
serialized root/page/CR96/INLINE10/source oracle and replaces only its host
per-packet supervisor with actual C34 calls. It records real instruction-entry
R14/R33 admissions and R33 opcodes, constant C34 residency and APPEND/ACK order.

Seven positive cases cover mixed dialect, empty EOF,61 records/180 events,
300 events in one BODY,66015-byte source, real pending merged bytes and explicit
LOST rebuild with a historical observer queue. Eleven fault groups cover
inactive/Plain/busy/foreign entry, eight cancel phases, CR/inline STREAM,
missing R33 at four stages, missing R14, full authority/source/CRC/ABI/phase
faults, graph/epoch foreign leases and an actual successful pending edit
invalidating an old job. Damaged producer-local flags may be detected after
bounded private directory staging, but before semantic publication; source and
all REU outside the typed arena remain unchanged.

Each actual pump call checks wholeRAM outside declared real service workspaces,
canonical roots/gap/history/selection, source capability/provider tables,
catalogue identity, bitmap/font and ReadyOS shim. Whole16MiB intervals permit
writes only inside the actual validated arena extent, not a hardcoded bank.
The positive cases independently verify every completed serialized payload and
CRC. No editor render/cache hit, native timing, hardware keyboard, small-REU,
lifecycle or end-to-end latency claim follows from this component gate.
