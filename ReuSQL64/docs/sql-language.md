# SQL Language Contract

Canonical scalar types are `BOOLEAN`, `I8`, `I16`, `I32`, `I64`, `FIXED8_8`,
five-byte Commodore `FLOAT`, `CHAR(n)`, `TEXT`, `BLOB`, and named `ENUM8` or
`ENUM16` types.

The complete target dialect includes CREATE/DROP TYPE, TABLE and INDEX;
INSERT/UPDATE/DELETE; SELECT with INNER/LEFT/CROSS joins, WHERE, GROUP BY,
ORDER BY, DISTINCT, LIMIT/OFFSET; aggregates; and scalar, IN and EXISTS
correlated subqueries. `HAVING` is intentionally unsupported.

Unhinted table sources scan deterministically. A source may use
`USING INDEX index_name`; an incompatible hint is an error. ReuSQL64 never
creates cost-based or stored execution plans.

Catalog and capacity introspection uses bounded `SHOW` statements through
`rsql_exec()`:

```sql
SHOW DATABASE;
SHOW TABLES;
SHOW COLUMNS FROM customer;
SHOW INDEXES;
SHOW TYPES;
SHOW MEMBERS FROM state;
```

`SHOW DATABASE` returns one `RsqlDatabaseInfo`. The remaining statements
return the corresponding records declared in `rsql_inspect.h`; callers page
them with the `start`, `capacity`, and `returned` fields of
`RsqlExecRequest.output.inspect`. Only visible schema objects are reported.

`CREATE INDEX index_name ON table_name (column [, ...])` creates a persistent
single-column or compound index over fixed-width columns. Index names are
global. TEXT/BLOB keys, duplicate names, a missing index, and using an index
owned by another table are rejected. The implemented hint form is:

```sql
SELECT projection [, ...]
FROM table_name USING INDEX index_name
[WHERE expression]
```

The index supplies deterministic candidate row IDs; the complete WHERE
expression is still checked against each current row. Aggregate SELECT and
GROUP BY consume the same explicitly named leaf-chain producer.

A direct three-output-source join may name an access path independently for
each source:

```sql
SELECT A.ID, B.ID, C.ID
FROM A USING INDEX IA
JOIN B USING INDEX IB ON B.AID=A.ID
JOIN C USING INDEX IC ON C.BID=B.ID;
```

Any subset of the three hints is legal. Each name is validated against its
source table and its persisted leaf stream drives only that nested-loop level.
The physical leaf order is not a substitute for `ORDER BY`. With a middle or
inner hint, the second ON program is bounded to six predicates because two
otherwise-idle private-predicate name fields retain the hints through binding.

Two-source joins support `JOIN`/`INNER JOIN`, `LEFT [OUTER] JOIN`, and
`CROSS JOIN`. Tables may use an explicit `AS` alias, and qualified references
use `alias.column`:

```sql
SELECT C.NAME, O.ID
FROM CUSTOMERS AS C
LEFT JOIN ORDERS AS O ON C.ID = O.CUSTOMER_ID
WHERE O.TOTAL >= 10 OR O.ID IS NULL
```

Execution is a deterministic outer-then-inner nested-loop scan. ON and WHERE
each use the bounded postfix Boolean evaluator and preserve three-valued NULL
semantics; WHERE is applied after LEFT JOIN NULL extension. Column-to-column
comparisons support compatible signed integers (including different widths),
CHAR, BOOLEAN, FLOAT, FIXED8_8, and identical named enum types. Joined TEXT and
BLOB projections retain normal stable-handle streaming.

The fully composed join path is bounded to two sources, eight result columns,
eight predicates, and 24 Boolean opcodes. A three-output-source
INNER/LEFT/CROSS scan path is implemented for fixed and streamed projections
and predicates. Its
second ON and final WHERE may reference any available source and use named
enum members. COUNT/SUM/AVG/MIN/MAX may consume numeric columns from any of
the three sources, fixed-width keys from any source may be grouped, and
LIMIT/OFFSET applies to raw or grouped output. Three-source LEFT, ORDER BY,
DISTINCT, TEXT/BLOB and scalar projection, plus independent source-local index
hints are supported. `CREATE [TEMP] TABLE ... AS SELECT` materializes this
form too, including fixed columns, raw TEXT/BLOB, streamed TEXT scalars, and
grouped aggregates. A fourth JOIN is a syntax error. Qualified reference
text is at most 15 characters, so
long table names should use a short `AS` alias. A joined result may use up to
two qualified fixed-width source columns or positive ordinals selecting fixed
scalar projections in ORDER BY, including ASC/DESC and LEFT-null placement;
LIMIT/OFFSET composes with that ordered stream. Joined DISTINCT compares
complete fixed raw or scalar projected tuples across prior joined pairs.
LENGTH, substring, concatenation, and string-literal projections are compared
as virtual values without materialization. Streamed TEXT/BLOB ON and WHERE
predicates compose with joined ORDER BY and exact DISTINCT rescans; each
pending predicate is evaluated in the predicate sidecar before the joined
producer resumes. Joined aggregates accept fixed
outer or inner GROUP BY keys, including compound and LEFT-null keys, and the
same COUNT/SUM/AVG/MIN/MAX integer/FIXED8_8/FLOAT set as ordinary scans. Joined grouped
results support named group-key or aggregate-ordinal ORDER BY, exact fixed
projected-tuple DISTINCT, and LIMIT/OFFSET. Ordinary two-source scan joins and
the direct three-output-source form accept an independent named index after
each source; each name is validated against its owning table and drives that
source's leaf iterator. Correlated-subquery and aggregate join producers reject
index hints explicitly. A hint is an access path, not implied SQL ordering.

One bounded subquery may appear as an outer WHERE term and may be combined
with the outer Boolean program:

```sql
SELECT C.ID FROM CUSTOMERS AS C
WHERE EXISTS (
  SELECT 1 FROM ORDERS AS O WHERE O.CUSTOMER_ID = C.ID
);

SELECT C.ID FROM CUSTOMERS AS C
WHERE C.ID IN (
  SELECT O.CUSTOMER_ID FROM ORDERS AS O WHERE O.TOTAL >= 0
);

SELECT C.ID FROM CUSTOMERS AS C
WHERE C.ID = (
  SELECT O.CUSTOMER_ID FROM ORDERS AS O WHERE O.ID = 10
);
```

Scalar, `IN`/`NOT IN`, and `EXISTS`/`NOT EXISTS` preserve SQL UNKNOWN behavior.
A scalar subquery returning no rows supplies NULL; more than one row returns
`RSQL_ERR_SUBQUERY_ROWS`. Inner WHERE supports its own parentheses, NOT, AND,
OR, comparisons, NULL tests, CHAR patterns, compatible column references,
FLOAT/FIXED8_8 values, and named enum literals. Execution is a deterministic
correlated nested rescan with no plan or materialized result.

The outer producer may also be an ordinary two-source join:

```sql
SELECT O.ID
FROM CUSTOMERS AS C JOIN ORDERS AS O ON C.ID = O.CUSTOMER_ID
WHERE EXISTS (
  SELECT 1 FROM ORDERS AS X
  WHERE X.ID = O.ID AND X.CUSTOMER_ID = C.ID
)
ORDER BY O.ID DESC LIMIT 1;
```

The third-source inner program may correlate to either joined row. Scalar,
IN/NOT IN, and EXISTS/NOT EXISTS retain their ordinary cardinality and NULL
rules. The output identity remains the outer/inner joined pair, so fixed
ORDER BY, projected-tuple DISTINCT, LIMIT, and OFFSET continue to use the
joined bounded-rescan path.

The ordinary bound is one correlated subquery, one fixed-width selected value,
eight inner predicates, and 24 inner Boolean opcodes. A correlated EXISTS may
contain one additional scalar, IN/NOT IN, or EXISTS/NOT EXISTS subquery over a
third table. Its innermost predicate program may correlate to either earlier
row, preserves NULL/UNKNOWN and scalar-cardinality rules, and feeds ordinary
scan, ungrouped aggregate, or grouped aggregate cursors. A further nesting
level and explicit index scans within nested subqueries are not supported. A
joined outer producer may feed either a scan or aggregate/group cursor; a
single-table correlated outer producer may also feed either cursor mode. Named
enum literals resolve against the exact outer, joined, or third-source enum
column in a combined predicate. LIMIT/OFFSET is supported on the outer result.
ORDER BY accepts up to two fixed outer-source columns or projection ordinals,
including fixed LENGTH, substring, and source-to-source concatenation scalar
values. It supports ASC/DESC and composes with LIMIT/OFFSET by restarting the
correlated producer. DISTINCT compares the complete fixed raw or scalar outer
projection against prior matching outer rows and composes with ORDER and
pagination. Quoted literals are stored in a separate packed SELECT pool, so
correlated scalar shaping composes with a live inner predicate program.

Depth-2 aggregate examples include:

```sql
SELECT COUNT(*), SUM(A.ID)
FROM A
WHERE EXISTS (
  SELECT 1 FROM B
  WHERE B.AID=A.ID
    AND B.V IN (SELECT C.V FROM C WHERE C.BID=B.ID)
);

SELECT A.ID, COUNT(*)
FROM A
WHERE EXISTS (
  SELECT 1 FROM B
  WHERE B.AID=A.ID
    AND EXISTS (SELECT 1 FROM C WHERE C.BID=B.ID)
)
GROUP BY A.ID ORDER BY A.ID;
```

NULL follows three-valued SQL behavior. Text defaults to folded PETSCII
comparison with `COLLATE BINARY` available. FLOAT columns accept signed integer,
decimal, and scientific-notation numeric literals; BASIC ROM `FIN` produces the
canonical five-byte value. Other numeric conversions allow only lossless
integer widening unless an explicit CAST is present.

Named enumerations are created with `CREATE TYPE name AS ENUM8 (...)` or
`ENUM16 (...)`. Members receive zero-based sequential values unless an
explicit unsigned value follows `=`. A table column names the enum type
directly, and INSERT, WHERE, and fixed-record UPDATE accept qualified member
literals such as `MOOD.HAPPY`. The qualifier must identify the exact enum
catalog ID bound to the column; wrong enum types, missing members, and values
outside the enum's unsigned width are errors. Cursor results retain the
physical ENUM8/ENUM16 tag and catalog ID.

The implemented aggregate subset is `COUNT(*)`, `COUNT(column)`, `SUM`, `AVG`,
`MIN`, and `MAX` over signed I8/I16/I32/I64, signed Q8.8 FIXED8_8, and FLOAT columns, with zero or more
fixed-width GROUP BY keys. An ordinary single-table producer also accepts
TEXT/BLOB group keys and compound mixtures; it compares logical payloads by
streaming REU pages, folds TEXT case, retains binary BLOB identity, and treats
all NULLs as one group. COUNT returns non-NULL I64; the other aggregates
return NULL for an empty input or NULL-only group. Aggregate numeric results
over integer columns are I64 and integer AVG truncates toward zero. FLOAT
SUM/AVG/MIN/MAX return canonical five-byte FLOAT values using BASIC ROM
arithmetic. FIXED8_8 SUM/AVG/MIN/MAX retain the two-byte FIXED8_8 result type.
Their accumulator stores signed raw Q8.8 units in I64; AVG divides that raw
sum by the non-NULL count and truncates toward zero to the nearest 1/256.
SUM outside the two-byte signed Q8.8 result range reports
`RSQL_ERR_NUMERIC_OVERFLOW` when the result column is accessed or streamed,
rather than wrapping. Without ordering, group results follow first physical key
occurrence. Aggregate/grouped ORDER BY accepts up to two named fixed group keys
or positive projection ordinals selecting an aggregate result; integer,
FIXED8_8, and FLOAT aggregate values, ASC/DESC, SQL NULL placement, LIMIT, and OFFSET are
supported. Aggregate function text is not repeated in ORDER BY: select it and
use its ordinal. DISTINCT is valid for ungrouped and grouped aggregate queries.
The one-row ungrouped case and grouped projections containing every group key
are proven unique at bind time. If a grouped projection omits a group key, the
engine compares the complete projected tuple against prior groups and removes
duplicates exactly, including NULL and aggregate values.
The same rules, including streamed TEXT/BLOB group keys and group-key ORDER BY,
apply after INNER, LEFT, or CROSS join production and after a correlated
single-table producer. ON and WHERE
are evaluated before accumulation; COUNT(*) includes a LEFT-null extension,
COUNT(inner_column) does not, and non-COUNT aggregates return NULL for a
NULL-only joined group. The joined WHERE may include one correlated scalar,
IN/NOT IN, or EXISTS/NOT EXISTS subquery over a third table; its Boolean
program may reference either joined source, and only qualifying pairs enter
the aggregate or group.

The direct three-output-source INNER/LEFT/CROSS producer uses the same aggregate
types and NULL rules for fixed-width columns. Group keys and aggregate inputs
may come from any source, nonaggregate projections must be group keys, and
ungrouped aggregate output is one row. Fixed source/group keys and aggregate
ordinals support bounded ORDER BY; DISTINCT compares complete raw or grouped
projected tuples. Raw TEXT/BLOB projection streams through the value API.
CHAR/literal/TEXT `LENGTH`, `SUBSTR`/`SUBSTRING`, `CONCAT`, and `||`
projections are also live; positive projection ordinals order their computed
values and DISTINCT compares them exactly by replaying triple identities and
streaming TEXT payload chunks from REU.
Raw TEXT/BLOB keys participate in ORDER BY and exact DISTINCT, with case-folded
TEXT and bytewise BLOB comparison. WHERE may stream TEXT/BLOB literal
comparisons and TEXT LIKE from any of the three sources. Independent explicit
per-source access paths and wide CTAS are live.

SELECT projection expressions support these bounded string forms:

```sql
LENGTH(value)
SUBSTR(value, one_based_start [, maximum_length])
SUBSTRING(value, one_based_start [, maximum_length])
CONCAT(left, right)
left || right
```

Operands may be CHAR columns, TEXT columns in the bounded forms described
below, or quoted string literals. CHAR `LENGTH` ignores physical trailing
padding and returns I16. CHAR substring and concatenation
return a cursor CHAR value whose reported length is the logical payload;
`rsql_value_read()` supports slices across a concatenation boundary. Binary
concatenation accepts two columns, one column plus one literal in either order,
or two literals. SQL NULL propagates through all operations.

`LENGTH(TEXT)` returns I32. `SUBSTR`/`SUBSTRING` over TEXT reports a TEXT value
and translates each `rsql_value_read()` slice directly into the stable REU blob
range; it never materializes the full payload in C64 RAM. A start of zero is a
syntax error, an omitted length means through the logical end, and zero or an
out-of-range span returns an empty non-NULL string. Any concatenation with a
TEXT operand returns TEXT. `TEXT||literal`, `literal||TEXT`, `TEXT||TEXT`,
`TEXT||CHAR`, `CHAR||TEXT`, and their `CONCAT` spellings stream the two logical
pieces in order. TEXT handles are validated one at a time and fixed CHAR
operands use their trimmed logical length; the payload is never materialized
in C64 RAM. Scalar projections compose with ordinary scans, explicit indexes,
two-source joins, correlated subqueries, direct three-source joins, and
LIMIT/OFFSET. Fixed and streamed TEXT scalar results compose with ORDER BY and
DISTINCT on ordinary, joined, correlated, and direct three-source scans.
Aggregate/grouped cursors may also project `LENGTH`, substring,
concatenation, and string literals when every referenced column is a GROUP BY
key; an ungrouped aggregate may project literal-only scalars. These forms are
verified for ordinary, two-source, direct three-source, and CTAS producers.
Composed aggregate scalars participate in positive-ordinal ORDER BY and exact
DISTINCT for ordinary, joined, correlated, and direct three-source
aggregate/group cursors. Their logical bytes are recomputed from each group's
representative row (or representative joined pair/triple) and compared in
bounded chunks. No grouped result is materialized for comparison.

Ordinary, joined, and correlated outer scans support `ORDER BY`, `DISTINCT`,
`LIMIT`, and `OFFSET` over fixed values and raw streamed TEXT/BLOB columns.
ORDER BY accepts one or more source columns or positive SELECT-list
ordinals with independent ASC/DESC directions. An ordinal must be in the
explicit projection list; zero and out-of-range ordinals are rejected. ASC
places NULL before non-NULL and DESC places NULL after
non-NULL. Signed integers compare numerically across their physical widths;
CHAR uses folded, trailing-space-insensitive comparison; BOOLEAN, identical
named enums, FIXED8_8, and FLOAT retain their native ordering. TEXT compares
case-insensitively and BLOB compares binary bytes; both stream across linked
REU pages. Duplicate ORDER keys are rejected.

DISTINCT compares the complete projected tuple using SQL value identity,
including one shared NULL value and streamed raw TEXT/BLOB columns. `LENGTH`, substring, and
concatenation results are evaluated before comparison, so their computed values
rather than source columns determine duplicates. It can be combined with WHERE,
ORDER BY, LIMIT, and OFFSET. Streamed comparisons and LIKE are reevaluated on
each bounded shaping rescan. Variable scalar keys use normalized descriptors
and compare streamed REU bytes without materializing the result. Joined
variable predicates also compose with ORDER BY and DISTINCT: each shaped
rescan suspends, evaluates, and restores the streamed predicate phase.
When `USING INDEX name` is present, result shaping validates and rescans that
index's persisted leaf chain for candidate row identities, then reapplies WHERE
and the requested ordering/distinct comparison. The hint is not ignored and no
optimizer or materialized result is introduced.
LIMIT and OFFSET accept unsigned 16-bit literals in either `LIMIT n OFFSET m`
or `OFFSET m LIMIT n` order. Without ORDER/DISTINCT they are applied by the
resident cursor dispatcher and therefore also work with grouped aggregates,
joins, correlated subqueries, and explicit index scans. No result plan or
materialized CPU-RAM table is created.

WHERE expressions support parentheses, prefix NOT, AND, OR, all six ordinary
comparisons, IS NULL, IS NOT NULL, LIKE, and NOT LIKE. Precedence is
`NOT`, then `AND`, then `OR`. Evaluation uses SQL TRUE/FALSE/UNKNOWN logic.
LIKE currently targets fixed CHAR values, folds ASCII/PETSCII letter case,
recognizes `%` and `_`, and ignores physical trailing CHAR padding.

INSERT accepts quoted TEXT literals and `X'0011A0'` binary literals for BLOB
columns. This first bounded parser form carries up to 63 decoded bytes per
literal; the heap and stable-handle format remain variable-width. SELECT may
project TEXT/BLOB columns through the cursor ABI, which reports logical length
and streams payload slices with `rsql_value_read()`. COUNT(variable-column)
uses ordinary NULL semantics. TEXT/BLOB values are valid GROUP BY keys for
ordinary sequential, joined, and correlated producers, including compound and
NULL groups. Group-key ORDER BY uses the same streamed logical comparison;
an explicit named fixed-width index may drive the ordinary row stream while
the group keys remain streamed TEXT/BLOB values. Streamed TEXT/BLOB
comparisons and TEXT LIKE predicates are supported, including joined shaped
ORDER/DISTINCT rescans.

DELETE supports `DELETE FROM table` and `DELETE FROM table WHERE expression`,
using the same bound predicate program and returning an I64 affected-row count.
Deleting a row tombstones every non-NULL TEXT/BLOB handle in that row in the
same statement transaction. Payload pages remain allocated until explicit blob
compaction, preserving stable-handle and recoverability semantics.

UPDATE accepts `UPDATE table SET column = literal [, ...] [WHERE expression]`.
The fixed-record path supports BOOLEAN, I8/I16/I32/I64, FLOAT,
FIXED8_8, CHAR, ENUM8/ENUM16, and NULL with the same range and nullability
rules as INSERT.
It reports an I64 affected-row count and is statement-atomic for zero, one, or
multiple matches. Duplicate assignment targets are rejected. TEXT/BLOB
replacement creates a distinct stable handle for every matching row,
tombstones that row's old non-NULL handle, and supports transitions both to and
from NULL. Metadata and row work alternate only through resident continuations,
so all handle, payload, directory, allocation, fixed-row, and affected-count
changes remain inside one statement journal.

`CREATE [TEMP] TABLE name AS SELECT ...` derives `C1`-`C8` columns from the
result cursor and supports fixed, aggregate, raw TEXT/BLOB, substring, and
concatenation projections across ordinary, correlated, joined, and direct
three-source producers. The destination remains hidden under a persistent
BUILDING marker while rows and variable payload pages commit in bounded
transactions; clearing that marker publishes the complete result atomically.
Variable values receive independent handles. A reported failure or the next
initialization reclaims an unfinished build, including results larger than the
sixteen-page journal.

`TEMP` tables have session lifecycle rather than merely a catalog label.
`rsql_shutdown()` marks them invisible and reclaims their indexes, rows, and
variable payloads; `rsql_init()` resumes cleanup interrupted after that
visibility transition. Persistent tables are unaffected.

`DROP TABLE name` applies the same lifecycle to a persistent or TEMP table.
The first transaction commits the `DROPPING` visibility marker; a failure
before that write leaves the table visible, while an interruption afterward
leaves it invisible and initialization completes reclamation. A missing name
returns `RSQL_ERR_NOT_FOUND`.

`DROP INDEX name` first marks the named index invisible, then advances and
frees its leaf chain before unlinking the descriptor. A marked index is ignored
by explicit `USING INDEX` binding and DML rebuilds; initialization resumes an
interruption. The indexed table and its rows are not changed.

`DROP TYPE name` supports ENUM8/ENUM16 catalog types. It is restricted: if any
visible table column still carries that enum catalog ID, the statement returns
`RSQL_ERR_DEPENDENT_OBJECT`. Otherwise it marks the type invisible, reclaims
member pages one at a time, and unlinks the descriptor; initialization resumes
a marked type. Enum IDs remain monotonic and are not reused. `IF EXISTS` and
`CASCADE` are not implemented.
