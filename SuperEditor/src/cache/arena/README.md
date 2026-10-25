# Checked optional arena transport

This is a private, CPU-tested transport foundation, not an integrated cache or
semantic reuse authority. Link `core.s`, `open.s`, `page.s`, `control.s` against
one sealed resident's actual object/provider/CRC exports and the new17B cache
state. No BSS or zero-page allocation. The linked four modules are2257bytes.
No editor Makefile, asset catalogue or startup was changed by this lane.

`cache/api.inc` is the parent-owned shared contract. `arena/api.inc` declares the
61B transport control at `$8E83-$8EBF`; fixed IO128 is `$8EC0-$8F3F`. The entire
preceding387B of the replacement job is opaque and preserved. This job cannot
coexist with legacy FS at `$8EE0`; drain semantic IO before invoking transport.
All functions are foreground-only and nonreentrant; A/X/Y/P and the resident
object/DMA/CRC foreground requests are scratch. Every public call checks owner4
before reading or writing this frame. Leave ownership4 asserted across the job.

## Calls

All public calls return carry-clear A0 complete or A1 pending; carry-set A is
an actual provider/object error or C0 argument, C1 changed descriptor/request,
C2 malformed metadata, C3 busy. These optional failures must become cache misses,
never failed document edits. `BCA_ERROR` is reserved, not a last-error latch.

- `se_bc_arena_open`: phase must0. If the live token is absent, allocate one
  typed53 logical object with one bank and committed size65536. STEP zeroes only
  page0 in32 slices, writes an INVALID empty root, then commits its state byte
  and publishes the CPU incarnation/token last. Until that last call the token
  stays unpublished and CANCEL owns cleanup. Existing arenas may have1..16
  extents, with exact committed size equal to capacity; all logical and physical
  ownership is checked through the existing object service. OPEN selects rootA
  orB by highest32-bit sequence among CRC-valid current-incarnation roots, then
  refetches and validates the winner. Equal sequences refuse as ambiguous.
  Successful existing OPEN leaves selected root128 in IO.
- `se_bc_arena_step`: at most one checked DMA of128bytes. New OPEN takes34
  steps; existing OPEN3. Owner, capability, incarnation, ticket and mutation
  latch are rebound each slice. The unpublished candidate has separate guards.
- `se_bc_page_begin`: after OPEN, set `BCA_PAGE`1..255, `BCA_KIND`1..7,
  `BCA_GENERATION`16 other thanFFFF. STEP reads/checks the individual8B directory
  entry, then64B page header, then the ENTIRE used payload in <=128B slices.
  Directory, header and payload CRCs are separate. Complete proofA5 appears only
  after the payload CRC matches; the four request bytes are frozen across all
  slices and reads. Page0 and unavailable pages refuse before DMA.
- `se_bc_arena_read`: with completed page proof, set absolute `BCA_OFFSET`24 and
  `BCA_LENGTH`1..128. Reads only that certified page's used payload, excluding
  header and unused tail. The result appears in fixed IO128. Live descriptor,
  source-observation ticket/incarnation, full typed object graph and request
  are rechecked. It does not follow refs or interpret CR/inline/lex records.
- `se_bc_arena_cancel`: revoke temporary page proof/phase. Release only an
  unpublished owned candidate whose complete current type53 capability still
  validates, never the live published token. Stale capabilities are retained
  for outer recovery rather than guessing physical frees. Idempotent whenidle.
- `se_bc_arena_trim`: idle only; validate the live type53 capability fully,
  then release its logical extents, clear token/proof, clear ARMED and set LOST.
  Observer ticket/incarnation are retained. A stale/foreign token is not freed.

The completed-page proof belongs to this exclusive owner4 job. Completed pages
are immutable until generation revocation. A later cache writer must cancel
that proof before changing directory/pages, and use the shared MUTATING /
incarnation / ticket protocol as appropriate; there is no unchecked public
write function here. This is not a persistent verified-body memo across jobs.

## Empty root and binary format

Root magic is ASCII `BCA1`, ABI1. Directory/page committed state is1. Data-page
magic bytes are42,50 (`BP`). The root/page offsets and CRC exclusions follow
`PERSISTENT_BLOCK_CACHE_ABI.md`. Directory CRC excludes its bytes4,5.
Uninitialized directory entries and rootB remain zero/INVALID. NILrefs areFFFF
FFFF. A new root has sequence1, current ticket, completeness0, no retained refs,
and a zero source snapshot. This is **format validity only**. OPEN never sets
ARMED, never clears LOST, and never claims that zero snapshot is a real source
identity. A semantic baseline writer must provide the actual snapshot/carry and
VALID-last publication before any reader can reuse meaning.

No root baseline/page append/eviction writer, observer integration, arena growth,
record parser, source-key semantic validation, native VICE or editor performance
claim is included. Ordinary checked CPU→REU stashes also revoke `$CC4D` through
the actual resident provider; that existing derived invalidation is expected.

## Repeatable proof

`python3 tests/test_cache_arena.py`

Default fixture is the immutable19fe native evidence, residentbf153ce4. The test
copies PRG/report/labels into its unique build directory, binds the exact17B
OBJECTS tail (`9FB5..9FC5`) and ring (`9D85..9DE4`) as an explicit prospective
state seam, and executes the real frozen object/provider/DMA/CRC instructions.
It does not reset an existing editor during a tested operation. Deliberate
provider resets between independent capacity scenarios are test setup only.
Schema pages are seeded by actual checked object writes; that is a transport
fixture, not a claim that a semantic producer has emitted them.

Final gate:17 groups,720 whole64KiB RAM intervals,32 whole16MiB REU intervals,
1240 actual service calls; peak10298 instructions per call. All public calls
are checked for <=1DMA/128B, including initialization and payload validation.
Tests cover VALID-last, rootA/B selection/faults, full4032B payload and exact
1MiB capacity end,16 extents mapped to even physical banks, all request/token
bytes, rechecksummed metadata mutations, cancellation, object/bank pressure,
and stale epoch/ownership before DMA/free. Foreign RAM/source/hot/history/font
state and ReadyOS shim are protected by the whole-RAM comparisons. The test
allows only declared transport state, actual object/provider request/allocation
fields, CPU stack, REU registers, and existing provider invalidation `$CC4D`.

## Initial semantic baseline writer profile

`writer.s`/`writer.inc` add a real initial-baseline publisher. A single leaf
containing both the full read-page validator and writer exceeds4KiB; do not
link that combination into a deployed image. The measured R33 **writer** profile
links `core.s`, `open.s`, `writer.s`, and `control.s` assembled with
`BCA_WRITER_PROFILE=1`, plus the caller's sealed16B binding/entry. It omits
`page.s`. The executable test's8-op wrapper yields4038B,58B spare. The separate
read consumer profile remains2257B. No additional supervisor, asset, BSS or ZP
was introduced by these modules. The caller supplies the actual existing17B
persistent state. The generic read-profile bytes remain unchanged.

The test wrapper's opcodes are OPEN0/STEP1/CANCEL2/TRIM3/WRITE_BEGIN4/APPEND5/
FINAL6/WRITE_CANCEL7. They are an explicit private entry contract; parent build
integration may use the same export functions in a production wrapper.

Only the initial EMPTY/unarmed root is accepted. An existing armed baseline is
not overwritten: a later rebuild must first TRIM/OPEN a new incarnation or use
future checked COW/eviction logic. The writer uses pages1..14, reserving15.
CR pages hold42 records; INLINE pages hold at most255 ten-byte events because
the four-byte reference has only an8-bit slot. That deliberately leaves spare
payload bytes instead of silently wrapping slots above255. Stream references
cross pages using their authenticated NEXT refs. Exhaustion returns A3/CLC
(`BC_STREAM`), leaves the old EMPTY root unarmed, sets LOST and retires this
attempt. It never reports a truncated baseline as complete.

Call sequence:

1. OPEN/STEP to ready. Configure the real semantic worker's header/arena tuple,
   then run its BEGIN through the actual R14 source provider. It owns the
   actual source lease and full86B reader context at frame+173.
2. `se_bc_write_begin` requires READY0 and that live owned reader. It independently
   reads/validates the selected EMPTY root, then STEP clears the directory in
   sixteen128B slices. No source snapshot is fabricated. If LOST is set, bit7
   of `BCF_BUDGET` must explicitly request REBUILD; LOST remains set.
3. Drive the actual semantic worker. For READY2 INLINE10 or READY1 CR96, invoke
   `se_bc_write_append`; if A1, drive R33 STEP until A0. **Only then** ACK the
   producer. It stays paused with READY set throughout. The writer reads but
   never mutates the first387B owned by the producer.
4. After the producer returns complete and releases its reader, invoke
   `se_bc_write_final` and STEP until complete. It seals remaining pages and
   publishes the other root copy INVALID first, then its VALID byte last,
   then retires the prebaseline ring indices and updates CPU ARMED while clearing
   LOST/ACTIVE. The observed ticket is never reset. Before that byte, the EMPTY
   root remains authoritative and no semantic reuse is allowed.
5. On any error/missing service/STOP, cancel the producer to release its owned
   source lease, then invoke WRITE_CANCEL. It retires temporary phase/proof,
   clears ACTIVE/ARMED and sets LOST, without freeing source or arbitrary banks.
   A missing R33 requires the parent to perform that tiny fail-closed descriptor
   cleanup; no saved overlay continuation is required. TRIM can discard the
   optional arena once producer ownership has been released.

Every service boundary checks the full13B token/incarnation/ticket against both
live state and the producer's frozen header, all59 actual FS identity fields
against live source/hot state, merged length, document validity, and all three
actual typed source capability graphs. Source guard calls restore the arena
request before DMA. The caller's source producer must run its actual R14 guard
immediately before calling the service; no intervening foreground mutation is
allowed. Across publication slices the writer repeats the above checks itself.
It never trusts arbitrary zero reader data or a revision counter alone.

FINAL requires actual producer EOF1, cursor equal to the frozen merged length,
producer line count equal to persisted CR count, no pending inline events,
STATE/READY/live flags allzero and reader active/owned bothzero. CANCEL alone
therefore cannot masquerade as completed parsing. Grammar/inline ABI1 is stored;
lexical ABI and lexical completeness remain zero. Root FLAGS1 means the actual
block/inline baseline is retained, never that code lexical runs were produced.

APPEND preserves original parser event order. It checks the CR CRC before every
resumed write, binds ticket and event count, inserts real stream refs and NIL
adjacency refs, and reseals record CRC. INLINE pending10 bytes are temporarily
held at IO118..127, outside the legacy FS exchange extent, and checksum-bound
across page seals. Page payload CRCs are updated from actual packets; page header,
page VALID, directory entry and directory VALID are separate bounded writes.
No refs become reachable from a committed semantic root until all its referenced
pages are sealed. There is no arbitrary unchecked public write API.

`python3 tests/test_cache_arena.py --writer`

The private test runs the actual4082B semantic C worker and actual sealed R14
against the frozen19fe editor; R33 is a genuine checked imported sidecar. It
compares emitted pages/refs/CRCs and actual parser output, then checks complete
source block/inline semantics with the independent host oracle. It also reopens
each completed arena and selects the newer baseline root (sequence2, EMPTY1). Seven positive
cases include mixed headings/code/inline, empty EOF,61 CRs over pages,300 events
in one logical line,66015B source, pending merged input, and LOST rebuild.
Eight fault groups include formal incomplete FINAL, partial cancel, all13+13
header authority bytes, actual source graph failure, malformed CR CRC, both CR
and INLINE pressure, missing R33 lease cleanup, LOST/zero snapshot refusal and
foreign owners. Every R33 call also preserves the producer387B, whole64KiB RAM
outside declared module/provider/loader scratch, canonical source/history,
font/hot/shim state; complete16MiB intervals allow only the owned arena bank.
These are executable private pipeline proofs, not an editor hit-path, automatic
idle-fill, native VICE, growth or performance claim.

### Baseline retirement qualification

Successful full baseline publication subsumes all queued events through the
captured ticket. Only after its REU root VALID byte commits, and before ARM,
the writer clears `se_bc_head`, `se_bc_tail`, `se_bc_count` to zero. It never
changes `se_bc_ticket` or the96 historical ring bytes. A refusal/cancel keeps
the queue intact. The retirement test seeds three CRC/schema-valid stale REKEY
records as an explicit ring fixture (not a claim of replaying their edits), runs
the real full-source producer, verifies their retention on every append/seal,
observes root INVALID and count3 immediately before the commit call, then
observes root VALID/ARMED and count0 after that same successful call. It also
checks refusal and partial-cancel retention. The unchanged17-group read profile
is byte-identical to its original2257B release.
