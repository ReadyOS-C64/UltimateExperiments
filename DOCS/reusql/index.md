# ReuSQL64

ReuSQL64 is a SQL-like database engine for a Commodore 64 equipped with a 512KB-16MB
REU. It is being built as a reusable resident service with a stable jump-table ABI and a
small interactive shell.

The original requested query/product feature surface is implemented and target-tested.
Optional extensions include a third correlated subquery level and wider public
variable-value slices. Internal working records remain local; the maintained design and
language references below describe the distributed project.

> **Performance: some advanced queries are very slow right now.**
>
> Joins, correlated subqueries, grouping, sorting and duplicate elimination can walk the same relationships repeatedly. For demanding work, it is often faster to filter/project into TEMP tables, index the useful intermediate columns, and run the next query against that smaller result. The tested seven-step sales pipeline took **425.88 seconds PAL**, compared with **2,300.2 seconds** for the original grouped join—about **5.4× faster**, including its intermediate table and index builds. These are measurements of this fixture, not a guarantee for every query.
>
> [Why this happens and how to stage a query](performance.md).

## Showcase queries from the tests

These are actual queries from the target test clients, formatted for reading. They assume their named fixture tables and indexes already exist. Several exceed the interactive shell's **160-byte input line**; the benchmark and regression clients submit the complete statements through the engine API.

### Three indexed sources, filters and five aggregate forms

The sales benchmark joins orders to customers and products, names an index for each source, filters numeric/Boolean/CHAR values, and groups seven output columns by region and category:

```sql
SELECT C.REGION,
       P.CATEGORY_ID,
       COUNT(*),
       SUM(O.ORDER_TOTAL),
       AVG(O.ITEM_COUNT),
       MIN(O.ORDER_TOTAL),
       MAX(O.ORDER_TOTAL)
FROM SALES_ORDERS AS O USING INDEX ORDER_BUYER_PROD
JOIN CUSTOMERS AS C USING INDEX CUSTOMER_ID_REGION
  ON C.CUSTOMER_ID = O.CUSTOMER_ID
JOIN PRODUCTS AS P USING INDEX PRODUCT_ID_CATEGORY
  ON P.PRODUCT_ID = O.PRODUCT_ID
WHERE O.ORDER_TOTAL >= 1000
  AND O.ITEM_COUNT >= 2
  AND O.DETAILS LIKE 'A%'
  AND C.ACTIVE = TRUE
  AND P.ACTIVE = TRUE
GROUP BY C.REGION, P.CATEGORY_ID;
```

The fixture checks two groups: `(region 1, category 0)` has 16 sales totaling 28,000; `(region 2, category 1)` has 17 totaling 30,000. Both have an average item count of 3. The exact minimum/maximum values, fixture sizes and timing boundaries are in the [benchmark evidence](tested-queries.md#permanent-real-world-sales-benchmark). This statement has no ORDER BY clause.

Source: [`SQL_SALES_SUMMARY` in the benchmark client](https://github.com/ReadyOS-C64/UltimateExperiments/blob/main/ReuSQL64/src/benchmark_main.c).

### An aggregate filtered by two levels of correlation

For each row in A, the engine finds a matching B row whose value appears in a C scan correlated to that B row. Only qualifying A rows reach the outer COUNT and SUM:

```sql
SELECT COUNT(*), SUM(A.ID)
FROM A
WHERE EXISTS (
  SELECT 1
  FROM B
  WHERE B.AID = A.ID
    AND B.V IN (
      SELECT C.V
      FROM C
      WHERE C.BID = B.ID
    )
);
```

This composes EXISTS, IN and aggregation without materializing the nested result sets. NULL behavior and scalar-cardinality failures have separate cases in the [depth-2 test catalog](tested-queries.md#depth-2-scalar-in-null-and-aggregate-queries).

Source: [`SQL_AGG_IN` in the nested-query client](https://github.com/ReadyOS-C64/UltimateExperiments/blob/main/ReuSQL64/src/nested_main.c).

### Grouped string expressions over three joined sources

This case combines three sources, LENGTH, concatenation, grouping and ordering by a computed projection:

```sql
SELECT LENGTH(A0.K),A0.K||Z.K,COUNT(*)
FROM D AS A0
JOIN E AS Y ON Y.K='AX'
JOIN F AS Z ON Z.BID=Y.ID
GROUP BY A0.K,Z.K
ORDER BY 2 DESC;
```

`ORDER BY 2` selects the concatenated result, not the second source table. The fixture emits `ZBY` before `BYBY`; the engine recomputes and compares grouped values through bounded row-identity replay. The [grouped scalar catalog](tested-queries.md#scalar-expressions-in-grouped-aggregate-results) also preserves the joined and correlated DISTINCT cases.

Source: [`SQL_ORDER_WIDE_GROUP_SCALAR` in the nested-query client](https://github.com/ReadyOS-C64/UltimateExperiments/blob/main/ReuSQL64/src/nested_main.c).

### Make expensive work reusable with TEMP tables

The staged sales benchmark filters into `FILTERED_ORDERS`, joins into `CUSTOMER_SALES`, joins again into `READY_SALES`, and builds explicit indexes between those boundaries. The final statement is:

```sql
SELECT C3, C4, COUNT(*), SUM(C1), AVG(C2), MIN(C1), MAX(C1)
FROM READY_SALES USING INDEX READY_REGION_CATEGORY
GROUP BY C3, C4
ORDER BY C3, C4;
```

Here C1/C2 are order total/item count, and C3/C4 are region/category. CTAS derives column names `C1..Cn`; the full [seven-step pipeline](performance.md#the-tested-seven-step-pipeline) shows how each intermediate schema is built. This is a measured alternative execution strategy, not an optimizer rewrite performed automatically.

## Try the committed interactive image

Mount [build/rsql64_shell.d81](../downloads/rsql64_shell.d81) as device 8 with a 512 KB–16 MB
REU enabled. The disk contains the shell and its required overlays. Load it with:

```basic
LOAD "RSQL64",8,1
RUN
```

The disk directory is authoritative for the bootstrap name. Enter `.HELP` for the client
commands. A small session is:

```sql
CREATE TABLE NOTES (ID I16, BODY TEXT)
INSERT INTO NOTES VALUES (1, 'HELLO REU')
SELECT ID, BODY FROM NOTES
```

The database lives in REU memory, not on the boot disk. `.CHECKPOINT` quiesces state;
saving a complete database additionally requires the host/VICE raw REU capture workflow.
`.EXPORT` writes bounded selected query results, not a complete database backup.

## Documentation map

- [Performance and staged queries](performance.md): repeated scans, measured costs and the full TEMP-table pipeline.
- [Interactive shell](shell.md): loading, editing, inspection, export and display limitations.
- [SQL language](sql-language.md) and [target-tested statements](tested-queries.md): supported syntax, examples and deliberate rejections.
- [Architecture](architecture.md), [memory map](memory-map.md), and [public ABI](public-api.md): resident service, bounded cursors, overlays and client integration.
- [Storage format](storage-format.md) and [export format](export-format.md): persistence and interchange boundaries.
- [HTML documentation](index.html): the same references in a static reading site.

## Capabilities and current scope

### Storage, types and transactions

![How a query moves through the resident engine, overlays and
REU](diagrams/query-flow.svg)

*The resident coordinator keeps ownership while query phases share one overlay window.
Rows and long values remain in REU memory.*

The verified storage milestone includes configurable 512KB-16MB REU probing, persistent
page allocation, redundant superblocks, a catalog, all promised physical type widths,
fixed rows, stable TEXT/BLOB handles with compaction, ENUM8/ENUM16 metadata, and overlay
caching.

### Schema changes and SQL foundations

The implemented SQL core is target-verified for CREATE TABLE and named ENUM8/ENUM16
types; fixed and variable INSERT; fixed and TEXT/BLOB UPDATE; DELETE; projected SELECT
and streamed values; compound three-valued WHERE with LIKE; fixed-width plus streamed
TEXT/BLOB GROUP BY across ordinary, joined, and correlated producers; and COUNT, SUM,
AVG, MIN, and MAX over integer, signed Q8.8 `FIXED8_8`, and Commodore five-byte FLOAT
columns.

Persistent single-column and compound fixed-width indexes are available through explicit
`USING INDEX` hints; indexed rows remain synchronized by transactional DML rebuilds.
Every mutation path is journaled and replayed under injected write failures. See
`docs/tested-queries.md` for the exact positive and rejection matrix.

Two-source INNER, LEFT, and CROSS nested-loop joins support qualified projection, ON and
WHERE predicates, named enums, NULL extension, and streamed variable values.

### Direct three-source queries

Three-output-source INNER, LEFT, and CROSS scans now support fixed-width and streamed
TEXT/BLOB projection, compound ON/WHERE programs, references across all three rows,
named enums, CHAR comparison, fixed-width `GROUP BY`, COUNT/SUM/AVG/MIN/MAX over all
three sources, bounded fixed `ORDER BY`/`DISTINCT`, and LIMIT/OFFSET over raw or grouped
output. CHAR/literal/TEXT LENGTH, substring, and concatenation also compose with wide
projection, ordinal ORDER BY, exact DISTINCT, and pagination.

Raw TEXT/BLOB ORDER BY and DISTINCT plus streamed TEXT/BLOB literal predicates are live
across all three rows. Each of the three sources may now name its own single-column or
compound access path with source-local `USING INDEX`; the engine validates ownership and
drives three independent leaf iterators without an optimizer. Wide CTAS now materializes
fixed, raw TEXT/BLOB, streamed scalar, and grouped aggregate results through bounded
destination staging.

### Ordering, duplicate elimination and pagination

Ordinary scans also support fixed-width and raw streamed TEXT/BLOB `ORDER BY`,
`DISTINCT`, and bounded `LIMIT`/`OFFSET`. Streamed comparison predicates and `LIKE`
compose with that shaping without materializing payloads. Positive projection ordinals
let `ORDER BY` consume fixed scalar expressions, and `DISTINCT` compares their computed
values; sequential `LIMIT`/`OFFSET` composes with grouped aggregates, joins, correlated
subqueries, and explicit index scans.

Joined results can be ordered by up to two qualified fixed-width or raw streamed
TEXT/BLOB source columns, including real column NULLs and LEFT JOIN NULL extension.
Exact DISTINCT compares raw variable projections by logical value, and the same bounded
restart/selection design composes with `LIMIT`/`OFFSET`. Correlated-subquery outer
results use the same bounded rescans; fixed source/scalar keys and raw streamed variable
source keys share the producer-owned shaping path.

### Joins with a correlated third source

An ordinary two-source join may also contain one correlated `EXISTS`, `IN`, or scalar
subquery over a third table scan. The subquery can reference either joined source, and
the composed producer retains joined ORDER BY, DISTINCT, LIMIT, and OFFSET behavior
without materialization.

### Explicit indexes and exact grouped results

`ORDER BY` and `DISTINCT` also consume an explicitly named index without an optimizer or
materialized result. Aggregate/grouped results support bounded ORDER BY over fixed group
keys and aggregate projection ordinals. DISTINCT compares the exact projected grouped
tuple even when the projection omits GROUP BY keys; provably unique cases are removed at
bind time and other cases use bounded prior-group rescans.

Joined and correlated DISTINCT likewise compare complete fixed projected tuples with
prior producer rows. Ordinary grouped scalar projections such as `K||'!'` can also drive
ordinal ORDER BY and exact DISTINCT, as can joined, correlated, and direct three-source
grouped scalars. Joined/correlated aggregate comparison replays the complete
representative outer/inner pair and evaluates the scalar without materializing the
group.

### Aggregation over joined and correlated rows

INNER, LEFT, and CROSS joins also feed COUNT/SUM/AVG/MIN/MAX and fixed or streamed
TEXT/BLOB GROUP BY directly. Joined groups support WHERE, compound outer/inner keys,
LEFT-null groups, aggregate/group-key ORDER BY, exact projected-tuple DISTINCT, and
LIMIT/OFFSET through a dedicated bounded-rescan sidecar. That sidecar also evaluates a
correlated scalar, IN, or EXISTS third-table rescan before accumulation, so joined
aggregates and groups compose with the same three-source predicates without
materializing rows.

An ordinary single-table aggregate/group query may likewise contain one correlated
scalar, IN, or EXISTS subquery. The aggregate sidecar rescans the outer table and
correlated inner predicate directly, so ungrouped and grouped results retain ORDER BY,
exact DISTINCT, LIMIT, OFFSET, and scalar-cardinality errors without a synthetic join or
materialized result.

### Computed and streamed string values

Fixed scalar projection ordinals participate in joined and correlated `ORDER BY` and
`DISTINCT`: the complex producer compares virtual LENGTH, substring, and concatenation
values directly from row IDs without allocating a joined row or result buffer.
Quoted-literal scalar operands are supported for joins and correlated outer scans; a
packed parser pool keeps projection literals independent of the live inner predicate
program. Variable scalar-result shaping now streams through ordinary, joined, and
correlated ORDER BY/DISTINCT.

Explicit-index variable grouping is also live.

### Checkpoint, export and nested predicates

Whole-REU checkpoint/restore is implemented through a quiesce/capture/reopen ABI.
Bounded selected-query export to D81, schema/storage introspection, and an interactive
shell and a bounded second correlated EXISTS level are also implemented. That second
level now supports scalar, IN/NOT IN, and EXISTS/NOT EXISTS predicates and feeds raw,
ungrouped aggregate, and grouped aggregate producers with NULL and scalar-cardinality
semantics.

A third correlated level remains an active milestone.

### Materialized tables and resumable cleanup

`CREATE [TEMP] TABLE ... AS SELECT` is now live for fixed columns, aggregates, raw
TEXT/BLOB, and streamed TEXT substring/concatenation results. Materialized variable
values receive new blob handles and remain valid after source handles are deleted and
compacted.

This covers ordinary, correlated, fully composed two-source, and direct
three-output-source producers. TEMP tables are hidden and reclaimed automatically by
shutdown and the next initialization. `DROP TABLE name` uses the same resumable path for
persistent or temporary tables and releases owned indexes, rows, and TEXT/BLOB chains in
bounded journaled steps.

`DROP INDEX` and restricted `DROP TYPE` use matching restartable descriptor lifecycles.
CTAS destinations are catalog-linked but hidden while building; rows and bounded
variable payload chunks commit in transactions (240 bytes for ordinary/two-source
producers and 64 bytes while a third source is live), and one final marker write
publishes the completed table. Initialization reclaims an interrupted build.

Verified fixed and variable results exceed the 16-page transaction journal without
weakening rollback.

### String expression combinations

Projection expressions support `LENGTH`, `SUBSTR`/`SUBSTRING`, binary `||`, and
`CONCAT`: CHAR and literals support all four forms, while streamed TEXT supports
`LENGTH`, zero-copy substring reads, and two-part concatenation with TEXT, CHAR, or one
quoted literal in either operand order. Each TEXT handle is resolved sequentially and
every read is streamed across the logical boundary; no combined value is materialized.
Variable TEXT scalar values can be ordered and deduplicated through the same streamed
descriptor comparator.

## Current build

```sh
make tools
make
make test
make memory-report
make vice-test
```

Host tools resolve from environment variables first and then the known sibling tooling
locations:

- `RSQL_CC65`, `RSQL_CC`, `RSQL_CA65`
- `RSQL_ZIG`
- `RSQL_VICE`
- `RSQL_DOTNET`, `RSQL_VICE_TASKS`

### Regression images and target tests

The target build produces fifteen independent regression PRGs, each with eight hot
execution sidecars plus one 17KB administrative sidecar, a D81, linker map, and labels.
`make test` runs all compiled 6510 lanes in Peddle at both REU extremes. `make
vice-test` drives all fifteen D81s in headless VICE on virtual 1581 drives through the
sibling .NET binary-monitor harness and captures RAM, state, and sampled REU artifacts.

### Boot disks, database images and persistence

D81 is the standard bootstrap and bounded export medium. The database itself remains
REU-native and may be much larger than any disk image. Full-size database persistence
uses whole-REU capture and restore through VICE.

The automation uses binary-monitor REU banks when exposed and otherwise toggles VICE's
native writable `-reuimage` backing to flush and reload an exact raw REU image. Future
C64 Ultimate UCI support is deliberately outside the current scope.

The interactive image is `build/rsql64_shell.d81`. It accepts SQL directly and adds
`.HELP`, `.DATABASE`, `.TABLES`, `.SCHEMA table`, `.INDEXES`, `.TYPES`, `.MEMBERS type`,
`.CHECKPOINT`, `.EXPORT file SELECT ...`, and `.QUIT`. See `docs/shell.md` for its exact
behavior and current formatting limits.

## Safety boundary

This project must not use the physical C64 Ultimate. Target-device automation is
performed only against VICE through the .NET task harness.

## Repository and dependencies

ReuSQL64 shares the Ultimate Experiments Git repository. Its source, build definitions,
tests and design references are committed, along with the interactive-shell D81. Other
regression D81s, object files, caches, logs and internal working records are ignored.


The Peddle host tests currently require the pinned sibling source described in
[third_party/README.md](dependencies.md). A standalone distribution must vendor
that source and its license. Physical C64 Ultimate automation remains outside this
project's test boundary.
