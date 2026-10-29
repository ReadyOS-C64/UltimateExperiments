# Private dual incoming semantic checkpoints

This separate namespace leaves the first checkpoint release immutable. It adds
an authentic immediately preceding logical-event checkpoint and guards against
an old first-only C21 publisher paired with a new predecessor reader. No
canonical edits, shared builds, new asset/bank, resident BSS or ZP.

`build.py OUT FROZEN_FIXTURE` reproduces the sealed2781B C24 control, then links
the pair. On immutable combined48 171440: **C24 4062/4096**, **C21 3866/4096**.
A larger/mutated current source must be linked and requalified independently.

## ABI and ownership

The first release's op3/phase ABI is retained, with a NEW mandatory selector:

- C24 op3 TRY_SEED, owner4 before every phase read.
- QUERY24 at8B40; ALLOW_EDIT at8BF3 is a saved actual GEC_VALID snapshot.
- **8BF7 SELECTOR0 current /1 predecessor**; values>=2 fail90 before a source
  lease or phase mutation. Every new caller must initialize this input.
- Return A0/Cclear with PROOF8BF4=0miss/1exact/2single-GEC-prefix proof.
  Accepted canonical START is8BEA..EC only if PROOF nonzero.
- Own R14 counted read lease is ended before return. CP_VALID2 and the existing
 79-byte CP_STATE hold the checked incoming parser state for the next normal
  C24 BEGIN; no cached-event shortcut applies to incoming2.
- C23 geometry/mode/pan/fold authority remains external. Semantic proof alone
  cannot authorize viewport coordinates or global PAGE navigation.

Current record is typed FE **0600..063F**; predecessor **0640..067F**. Only these
128 bytes are reserved; source-grid authority1600..16FF does not overlap.
Each64B record has magic53/version**2**/length64/VALID1, START24 at4, actual
source key28 at7, incoming fence/language/regions/overflow24 at35, **published
viewportTOP24 at41**, zero reserved44..61, CCITT0..61 at62 (little endian,
initialFFFF, CRC includes VALID1). Full source key and GEC guards are unchanged
from the first release: tokens/generation/epochs never guessed across flush.

SELECTOR1 first reads and checks current record V2/fullCRC, preserves its old
source key28 in the invalid CP_STATE scratch, then fetches predecessor64B.
Their full keys must agree and predecessor's boundTOP must equal actual old
GCC TOP. The selected record then passes the full current/exact or GEC prefix
proof and restores only trusted incoming state. This is two64B reads, bounded
128B total, not a prefix parse. Old V1 C21 records safely miss, even when a
CRC-correct stale V2 predecessor with matching source key was planted at0640.
A partially published pair cannot silently bind a different source or viewport.

## Producer and scratch lifetimes

Before each skipped CR (pos<QUERY), actual incoming9B START3+carry6 is retained
at9000..9008 with VALID9009. The matched target CR, or EOF, captures its incoming9
at8BEA..F2. These are incoming fields BEFORE classification, including the
separate24-bit overflow, not inferred semantic colors or post-event state.

Source READs use90EC, own saved R14 context9040 remains untouched. After actual
query completion, C21 copies predecessor9+valid to owned8880..8889 BEFORE
packing its64B record over9000. There is no overlap with protected diagnostics
8800..887F, VIEW8C00, or an active C20/R21 frame. Caller owns phase4 throughout.
C21's8BFC byte is temporary write offset0/40; no new persistent state.

C21 producer still requires real LINE0, incomingSTART==TOP, CAPTURED1 and full
key equality with its actual guarded header. It writes each64B as VALID0,
then the single VALID1 byte. BOF with no predecessor explicitly writes previous
VALID0. Actual provider rejection on the first record's VALID-last byte leaves
it untrusted and returns optional Cclear; source/history/shim and unrelated REU
remain exact. The selector's current-V2 witness rejects the old remaining pair.

No automatic C21 TRY_SEED/rekey or root reveal routing is added here. Repeated
incremental publications can age the old full key beyond a single GEC; they
then decline until a real producer refresh. No record anchor is blindly rebased.

## Proof and measured cost

`tests/test_geos_semantic_previous.py` actual sealed private pair passes8 cases:
BASIC-opening carry versus first-code carry, region-close carry, overflow16+4,
empty EOF, >64KiB current/previous publication, real C6 pre-flush CRjoin,
VALID-last actual provider refusal, old-publisher/stale-record mismatch, plus
BOF invalidation, malformed selector and own-only cancellation preserving a
separately acquired foreign read lease. Independent five source frames total
320k pixels/5000 attributes. Producer writes use exact declared FE spans; all
lookup/cancel intervals compare all16MiB read-only plus canonical/shim guards.

At original TOP65817, actual C6 W_BACK removes CR65816 while docgeneration2
and pending gap are retained. Current checkpoint correctly misses4505 CPU
instructions; predecessor65800 checks in6614, then actual C24 classifies the
joined line in11723/2 steps, matching the host canonical block oracle. This
stops at the actual C6 service, before root reveal/flush. It does NOT claim
that the current public225M before-TOP path has changed.

Identical cold query65817 on source65837, original/first/dual variants:
11,154,010 /12,773,628 /11,562,227 CPU instructions,2058 READs in each, identical
actual event. Dual adds408,217 (~3.66%) bookkeeping on a fresh BOF scan. The
first private release had extra harmless nonCR captures due to an anonymous
branch spanning CMP24's internal anonymous label; its archive remains unchanged.
The dual path uses an explicit local branch and an X-preserving boundary helper.
These are CPU instructions, not native cycles or public end-to-end latency.

Root owns C23 local E47, pending-reveal routing and later C21 consumers. No
PAGEglobal171 rule, committed generation guard, source quota, parser/lexer
semantics, pixel policy or generic public API is weakened.
