# Architecture

The engine trades repeated work for a small, predictable memory footprint. The key
design rule is ownership: resident code survives phase switches, while an overlay owns
only the work it can finish before returning. The sections below follow a query from its
client through those phases, then cover storage and recovery.

![Client requests, resident coordination, one overlay window and REU
storage](diagrams/query-flow.svg)

ReuSQL64 consists of a resident coordinator, eight query/storage overlays, one
administrative overlay, REU page storage, a stable jump table, and an implemented thin
client shell.

## Core terms

| Term | Meaning in this engine |
|---|---|
| Resident coordinator | Code that remains available while other execution phases are replaced. |
| Overlay / sidecar | A loadable code payload sharing the same C64 execution window with other phases. |
| Producer | A scan, join or correlated query that yields candidate rows. |
| Row identity | A row ID, joined pair or triple used to revisit the same logical input. |
| Bounded replay | Rerunning a producer while retaining a small amount of selection state. |
| Materialization | Storing a query's result in a real intermediate table, as CTAS does. |
| Stable handle | A logical identifier for a TEXT/BLOB value whose payload pages can move. |
| Before-image journal | Saved old pages used to undo a failed statement's writes. |

## Resident coordination and shared memory

The resident coordinator owns REU DMA, page allocation, transaction journaling, overlay
switching, error state, cursor coordination, and the public ABI. Compact active
statement and cursor records live in work RAM; persistent database state lives in REU.
Each overlay is copied into `$7C00-$BFFF` when its phase is needed; no overlay BSS is
allowed to survive a phase switch.

## Bootstrapping and full-database persistence

D81 is the default removable-media format for bootstrapping overlays and for implemented
bounded query exports. Persistent database state is not constrained to disk capacity: a
database can occupy most of a 16MB REU, so full database checkpoints quiesce the engine,
capture the whole REU externally, replace the whole REU on restore, and reopen it
without formatting. The VICE adapter prefers direct binary-monitor REU-bank transfer.

Because the installed VICE build does not enumerate those banks, the verified path
toggles the emulated REU to flush and reload VICE's native writable `-reuimage` backing
file. The result is an exact raw 512KB-16MB REU image rather than a machine snapshot.
UCI integration is a future device adapter and is not used by this implementation or its
tests.

## The shell as a client

The interactive shell is deliberately outside the fixed engine ABI. Its 160-byte GETIN
line editor, display formatter, SHOW aliases, and D81 export command are linked into the
client area. SQL calls the same `rsql_exec()` and cursor/value entry points as an
application, while checkpoint calls the same quiescing lifecycle entry.

It therefore reuses the eight hot overlays and the fixed administrative cache without
reserving another REU region or changing the persistent format. The shell converts cc65
shifted uppercase PETSCII only at its CHROUT display boundary; SQL values and exported
bytes remain unchanged.

## Overlay loading and statement phases

### One execution window, nine loadable payloads

The linker emits nine independently loadable 17KB PRGs at the same `$7C00` runtime
address: metadata/blob/enum, rows, parser, executor/index, complex query, result
shaping, joined aggregation, direct wide-query execution, and
administration/introspection. Peddle loads the eight execution payloads directly into
the top eight REU cache slots and the administrative payload into fixed pages 34-101 for
fast tests.

VICE autostarts a D81 on a virtual 1581 and uses trapped device-8 KERNAL loads before
storing each execution image to the same top slots and administration to its fixed
cache. Tests overwrite the live window, restore metadata through resident code, and
re-enter the catalog.

### Return to resident code before switching phases

Parser and executor sidecars communicate through work-RAM statement/execution records,
return to resident code, and only then permit the coordinator to load another phase.
CREATE TABLE and positional INSERT use this cooperative path. SELECT binds projections
in the metadata sidecar, then performs cursor scanning and value access in the row
sidecar.

Fixed and streamed variable-column projection plus ungrouped COUNT(*) are live; single
predicates and bounded-memory GROUP BY rescans are live, including COUNT, SUM, AVG, MIN,
and MAX over integer and Commodore FLOAT columns. FLOAT literal conversion and
arithmetic use a `$C000` bridge that remains visible while BASIC ROM covers the row
sidecar; negative literal sign is applied after `FIN`. WHERE compiles at parse time into
a bounded postfix Boolean program evaluated with SQL three-valued logic.

## Row producers

### Scans, indexes and two-source joins

Persistent single/compound indexes use executor-owned sorted linked leaves; `USING
INDEX` selects their row-ID stream and the row phase reapplies the full predicate.
Two-source INNER, LEFT, and CROSS joins bind both schemas in the metadata phase, then
execute deterministic nested loops in the complex-query phase. The two existing 240-byte
row buffers hold outer and inner records, so no materialized joined row or execution
plan consumes C64 RAM.

The same complex- query sidecar executes bounded scalar, IN, and EXISTS subqueries by
rescanning the inner source for each outer row.

### Three-source rows and triple identities

For a three-output-source INNER/LEFT/CROSS scan, the execution row is the third buffer
and its schema already occupies execution scratch. The administrative sidecar originally
owned binding and the outer-middle-inner continuation, but grouping filled it. Direct
wide execution now owns hot slot 7; administration remains in fixed pages 34-101.

Storage version 4 reserves eight top slots. Triple row identities drive bounded fixed
ORDER/DISTINCT and grouped aggregate replay. `$FFFF/$FF` middle or inner identities
represent LEFT-null rows, and unshaped TEXT/BLOB projections stream through the generic
value API.

### The original nested-EXISTS slice

An ordinary correlated EXISTS may contain one further EXISTS over a third table. The
outer, middle, and innermost rows occupy the cursor row, scan row, and execution row
respectively. The nested predicate can reference either earlier level, and the innermost
scan recursively reuses the existing EXISTS producer and Boolean evaluator.

This depth-2 slice does not add a fourth row buffer, plan, REU cache, or aggregate
nesting mode.

### Correlating a third table against a joined pair

For join/subquery composition, the outer and joined rows remain in the two cursor
buffers while the third schema and row reuse execution scratch. Source descriptors
distinguish outer, joined-inner, and subquery-local columns. Each joined pair can
therefore run a correlated third-table rescan whose predicates reference either joined
row.

The pair remains the cursor identity, allowing the existing joined
ORDER/DISTINCT/pagination selector to restart the complete three-source producer without
another buffer or plan.

### Apply correlated predicates before accumulation

Joined aggregate sidecar 6 compiles the same raw producer core together with the compact
third-source evaluator. It applies the correlated predicate before accumulation and
repeats it during bounded group, ORDER, and DISTINCT replays. The evaluator reports
storage and scalar-cardinality errors through the pair producer, so an UNKNOWN predicate
result cannot hide a failed subquery scan.

## Result shaping through bounded replay

### Ordering joined and correlated output

> **Performance: some advanced queries are very slow right now.**
>
> Joins, correlated subqueries, grouping, sorting and duplicate elimination can walk the same relationships repeatedly. For demanding work, it is often faster to filter/project into TEMP tables, index the useful intermediate columns, and run the next query against that smaller result. The tested seven-step sales pipeline took **425.88 seconds PAL**, compared with **2,300.2 seconds** for the original grouped join—about **5.4× faster**, including its intermediate table and index builds. These are measurements of this fixture, not a guarantee for every query.
>
> [Why this happens and how to stage a query](performance.md).

 A bounded replay keeps row IDs rather than a complete result set. To choose the next
ordered result or prove that a value is distinct, the engine may restart its producer
and revisit source rows. That saves RAM but can multiply the cost of joins and
correlated predicates.

Joined and correlated-subquery fixed-source ORDER BY remain in their producer-owning
complex-query sidecar. A phase-neutral ABI dispatcher selects sidecar 4 for either
complex producer and sidecar 5 for ordinary/index shaping. For each output position,
selection restarts the existing producer.

A join retains the best outer/inner row-ID pair plus the LEFT-null flag; a subquery
needs only its outer row ID. The selected key source row is reread for comparison. This
supports two ASC/DESC keys, SQL NULL placement, and LIMIT/OFFSET without a joined-row
buffer or cross-overlay return path.

### Exact DISTINCT and virtual scalar comparisons

For correlated DISTINCT, each matching candidate restarts the subquery producer and
compares its complete fixed raw projected tuple against matching outer rows before it.
The same source comparator supplies NULL, CHAR, numeric, FLOAT, and enum semantics; the
candidate row is reread after the prior scan. Joined DISTINCT uses the same loop with
the full outer/inner row-ID pair and LEFT-null flag as its stopping identity.

It continues the replay through that candidate even after finding a duplicate, so the
nested-loop continuation state is restored naturally for the main selection pass. Fixed
scalar ORDER and DISTINCT remain in this producer phase as well. A virtual comparator
rereads the target source row by ID and streams logical bytes for LENGTH, trimmed CHAR
substring, concatenation, and literals; it never constructs the scalar result or a
combined joined row.

Correlated shaping accepts source-only scalar descriptors so the inner Boolean program
can retain ownership of parsed literal slots. Projection-backed ORDER descriptors use
bit 6, while bit 7 continues to identify an inner joined source.

### Ordinary and indexed result shaping

Result sidecar 5 performs bounded selection scans for ordinary fixed-width ORDER BY and
DISTINCT queries and binds/evaluates fixed string expressions. It stores row identities
rather than complete rows, compares at most two keys, and leaves projected values in the
ordinary cursor path.

Positive ORDER BY ordinals are bound either to their raw fixed source or to a
scalar-expression marker; the sidecar evaluates fixed scalar values against each
candidate row for ordering and complete projected-tuple DISTINCT comparison. Scalar
descriptors reuse SELECT-idle UPDATE and aggregate vectors rather than growing work BSS.

For an explicit index producer, the result sidecar validates the named index descriptor
and each persisted leaf, rescans leaf row identities for every bounded selection pass,
and reuses the ordinary row/WHERE comparison path. This preserves the explicit access
hint without calling through a replaced executor overlay or creating a plan.

## Group identity and aggregate replay

### Streamed TEXT/BLOB group keys

Variable grouping splits comparison ownership without changing group identity. Row
sidecar 1 retains ordinary representative/candidate row IDs, compares all fixed and NULL
key components, and runs WHERE plus aggregate rescans. For a qualified pair, resident
orchestration loads result sidecar 5 and invokes its existing two-chain logical
comparator for only the TEXT/BLOB key components, then reloads slot 1 with
equal/not-equal.

Equal values may have unrelated stable handles; TEXT is folded, BLOB remains binary, and
payloads stay in REU. The SELECT-only `update_variable` byte marks this continuation. No
variable group key, hash table, or result row is materialized.

Joined and correlated group production keeps pair identity and aggregation in sidecar 6,
then uses the same resident owner-restoring bridge to compare variable sources in
sidecar 5 before resuming the pair scan.

### Aggregate ordering and group-level DISTINCT

Aggregate ordering remains in producer-owning row sidecar 1. It enumerates the first
physical representative of each group, compares named fixed keys directly or variable
keys through sidecar 5, and recomputes only the requested integer/FIXED8_8/FLOAT
aggregate ordinal when comparing two representatives. Each output position retains a
best row identity and the selected group is rescanned once more to publish its normal
aggregate state.

No group/result tuple is materialized. DISTINCT is removed at bind time when grouping
proves it redundant: one ungrouped row, or every GROUP BY key exposed by the projection.
Otherwise each candidate is compared with prior physical group representatives over its
complete projected tuple.

Raw group values and recomputed integer/FIXED8_8/FLOAT aggregates share SQL NULL and
value comparison semantics; a match suppresses the candidate.

### Joined and correlated aggregate producers

Joined aggregation lives in sidecar 6 with a duplicated raw nested-loop core. It
consumes INNER, LEFT, and CROSS pairs after ON and WHERE evaluation, so COUNT,
signed-integer/FIXED8_8/FLOAT accumulation, and LEFT-null semantics share the ordinary
join producer. Group discovery identifies the first physical pair for each fixed or
streamed variable outer/inner compound key; prefix rescans reject duplicate
representatives, and full rescans recompute only the selected group.

ORDER BY selects a best representative using named group keys or aggregate projection
ordinals, while exact DISTINCT compares complete projected group tuples with prior
representatives. State is bounded to outer/inner row IDs and the LEFT-null bit. No
joined row, result tuple set, hash table, or plan is stored.

Sidecar 6 also has a compact alternate producer for correlated single-table aggregates.
It scans the ordinary outer table, evaluates the already-bound scalar/IN/EXISTS
predicate for each row, and marks the joined-inner identity as NULL so the existing
representative structure means “outer row only.” The same first-group, accumulation,
ORDER BY, exact DISTINCT, and pagination replays then operate without a synthetic join
or a second aggregate executor.

## Binding, literals and execution ownership

### Enum identity across three schemas

Before either complex sidecar executes, the phase-neutral enum prepass sees the
metadata-loaded outer and joined schemas plus the third schema staged in execution
workspace. A shared source lookup resolves a predicate's enum column across all three
qualifiers, detects unqualified ambiguity, and converts the qualified member only after
matching its catalog enum ID. Table-qualified RHS names remain column references for the
later sidecar binder.

### Keep projection literals separate from predicates

SELECT projection literals are packed downward in the parser's 256-byte enum- member
workspace while ORDER descriptors grow upward. Each literal scalar's offset and length
reuse its scan-only group-column descriptor; parsing rejects pool overlap. Predicate
values remain in their original array, so a correlated inner program can no longer
overwrite literal LENGTH, substring, constant, or concatenation operands.

Result and complex sidecars read the packed bytes directly during public projection,
ORDER, and DISTINCT replay.

### Single-cursor execution and static locals

The row cursor is compiled with cc65 static locals. That converts control-path
temporaries to shared BSS and keeps exact grouped DISTINCT inside the 17KB row sidecar.
This is compatible with the engine's explicit single-cursor, non-reentrant execution
contract; cursor requests cannot overlap.

## Phase-neutral dispatch and streamed values

### Fixed entry points select the owning overlay

All four shaped sidecars expose a three-byte jump at the same `$7C00` overlay address.
The phase-neutral ABI dispatcher therefore selects slot 1 for ordinary aggregates, 4 for
joins/subqueries, 5 for ordinary/index results, or 6 for aggregate/group results over
either joined or correlated producers and tail-calls one fixed address. A compact
resident selector computes the complex slot arithmetically without growing the ABI into
reserved `$CFEF`.

### Read variable ranges across overlay boundaries

TEXT length and substring return through the existing variable-value continuation, so
metadata can inspect/read the stable handle while no overlay calls code that has
replaced itself. For concatenation, result sidecar 5 first captures two stable operand
pointers, trimmed fixed lengths, NULL state, and a two-bit TEXT mask from the positioned
cursor row pair.

Metadata sidecar 0 then resolves each marked handle sequentially and a compact 6510
streamer delegates TEXT ranges to the checked blob reader while copying CHAR/literal
ranges directly. Reads may cross either boundary without retaining overlay-local
pointers or materializing the result. Ordinary result shaping also streams raw TEXT/BLOB
keys page by page for predicates, ordering, and duplicate elimination; its transient
state reuses otherwise idle correlated-schema scratch.

Blob compaction is a maintenance phase in parser sidecar 2, entered through a
phase-neutral ABI trampoline. It never overlaps parsing, and moving it leaves result
sidecar 5 room for variable comparison without returning its directory scan to
metadata-sidecar space.

### Pagination belongs to the resident dispatcher

LIMIT/OFFSET is applied by the resident dispatcher, so sequential limits also compose
with aggregate, join, subquery, and explicit-index cursors without creating a plan or
materialized result set.

## CTAS publication and recovery

### Build privately, then publish once

`CREATE [TEMP] TABLE ... AS SELECT` opens the ordinary bound cursor first and derives a
`C1`-`C8` schema in the parser phase. The destination descriptor is catalog-linked with
a persistent `BUILDING` bit, which hides it from ordinary lookup while making it a
durable ownership root.

Each complete fixed row commits independently. A non-NULL variable column first receives
a zero-length active handle stored in that committed hidden row; resident code then
streams at most 240 source bytes through the public value reader, and executor sidecar 3
allocates, links, and lengthens one payload page per bounded transaction. The source
handle is never stored in the destination row.

One final marker transaction clears `BUILDING` and publishes the table. Any error enters
the resumable table-drop path, while initialization reclaims a build interrupted after
any earlier commit.

### Bounded chunks and failure coverage

CTAS request objects and counters are static resident state. That removes an 88-byte
cc65 software-stack frame across overlay switches and is consistent with the existing
single-cursor, non-reentrant ABI. The owned page appender lives in executor overlay 3.

A ninth test client verifies two-page values, empty and NULL values, scalar output,
independent handles after source deletion/compaction, a 17-row-page fixed result, a 4KB
TEXT copied through eighteen append transactions, targeted rollback at every append
write position, publication failure, and BUILDING-only restart cleanup.

### Preserve all three source rows during CTAS

Direct three-source CTAS retains the producer triple while the destination row is
assembled. It starts with a blank result row, patches each fixed value or new variable
handle through a row-sidecar overlay, and restores the selected triple after every
patch. Variable source/scalar bytes stream through the 64-byte aggregate scratch buffer
because `execution.row` remains the live third source; ordinary CTAS keeps its 240-byte
chunk.

Destination schema/page state is saved independently, so no fourth materialized source
row or query plan is introduced.

## Resumable object cleanup

TEMP descriptors carry a persistent dropping bit. Shutdown and initialization scan for
TEMP or already-dropping descriptors in executor sidecar 3. Explicit `DROP TABLE`
resolves the visible descriptor and enters that same phase.

The first small transaction sets that bit, and catalog lookup immediately hides the
table. Resumable cleanup removes owned index leaves/descriptors, advances and frees each
variable-value chain one page at a time, clears rows, releases row pages, and finally
unlinks the descriptor. Every step publishes its next durable link before freeing the
old page in the same bounded transaction.

An interrupted cleanup is therefore continued by the next initialization without
exposing partial rows or leaking owned pages. Cleanup restores metadata sidecar 0 before
returning so the established low-level catalog phase remains intact. Standalone indexes
and enum types have their own persistent dropping bits.

Initialization drains marked index leaves and enum-member chains before TEMP tables.
`DROP TYPE` scans visible table descriptors and refuses to mark a type while a column
retains its enum ID.

## Fixed ABI and automation boundaries

The append-only ABI jump table begins exactly at `$C000`; checkpoint and restore remain
fixed at `$C01B` and `$C01E`. Ordinary ABI code ends at `$CFEE`; `$CFEF` remains the
reserved Peddle BASIC-FLOAT marker. The joined variable-predicate bridge uses the
separately verified `$CFF7-$CFFE` control tail, leaving `$CFF0-$CFF6` for existing
automation controls.

`$CFFF` is the checkpoint adapter handshake. Link verification rejects growth across
each of those boundaries.

## Persistent objects and atomic mutations

### Pages, handles and named indexes

The storage engine uses 256-byte pages. Persistent objects are reached from redundant
superblocks. Tables use fixed-stride rows with a null bitmap.

TEXT and BLOB values use stable directory handles so their page chains can move during
compaction. Indexes are named sorted leaf chains. There is no optimizer: source order
and explicit `USING INDEX` clauses control access.

### Before-image journal and index rebuilds

Mutating SQL statements use a 16-page REU before-image journal. A canonical page is
copied once before its first write; failure restores logged pages in reverse order,
including allocation-bitmap pages. CREATE TABLE, INSERT, CREATE INDEX, multi-row DELETE,
and fixed/variable UPDATE are journaled.

Affected-table indexes are fully rebuilt before DML commit. TEXT/BLOB INSERT
materializes heap handles inside the transaction before the row sidecar runs. DELETE
binding caches the blob-directory root in work RAM; the row sidecar tombstones each
owned handle before clearing the matching row, while explicit compaction later frees
payload chains.

### Variable UPDATE crosses phases safely

UPDATE reuses DELETE's metadata-bound predicate and resident transaction coordinator.
Fixed-only updates scan and apply entirely in the row sidecar. Variable updates seek one
match in the row sidecar, return to resident, create distinct replacement handles and
tombstone old handles in metadata, then return to the row sidecar to apply fixed fields
and write that row.

The scan's current and next row IDs live in shared work RAM, so sidecars never replace
an active return path.

## Depth-2 correlated execution

One correlated EXISTS may contain one additional scalar, IN/NOT IN, or EXISTS/NOT EXISTS
scan. The parser stores a marker in its existing bounded private predicate vector.
Administrative overlay 7 resolves the marker's middle-source operand and third-source
projection, packing both source bytes into its 16-bit parameter.

The normal complex-query overlay and aggregate overlay each save the active subquery
kind, projection, comparison, and depth selector, run the established subquery scanner
recursively against the third row buffer, and restore the middle scan before continuing.
NULL/UNKNOWN and scalar multirow errors travel through the same side channel as
one-level subqueries. Grouping and aggregates therefore consume only qualifying outer
rows and repeat the nested scan on their bounded replays.

No plan, hash table, materialized subquery result, new REU cache slot, or fourth row
buffer is introduced.
