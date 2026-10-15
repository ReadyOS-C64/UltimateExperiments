# Target-Tested SQL Examples

These statements are executed by the compiled 6510 test program in both
Peddle REU sizes and by the automated VICE D81/1581 lane. This is an evidence list,
not a claim that the rest of the planned dialect is already implemented.

## Schema and physical types

```sql
create table sqltypes (
  flag boolean not null,
  tiny i8,
  small i16 null,
  wide i32,
  huge i64,
  money fixed8_8,
  value float,
  label char(9)
);
```

The test reopens the catalog and checks all eight columns, the 33-byte physical
row width (including its null bitmap), the nullable `I16`, and `CHAR(9)`.

```sql
CREATE TABLE SQLVAR (BODY TEXT NULL, RAW BLOB)
```

This verifies variable-value columns occupy stable four-byte handles in the
fixed row.

```sql
INSERT INTO SQLVAR VALUES ('C64 ''TEXT''', X'00FF104142');
INSERT INTO SQLVAR VALUES (NULL, X'');
```

The first statement verifies escaped TEXT plus a binary literal containing a
zero byte. The second verifies nullable TEXT and a zero-length BLOB. The target
checks handle placement, heap kind and length, exact payload bytes, and row
counts.

```sql
CREATE TABLE SQLDML (
  ID I16,
  NAME CHAR(8),
  ACTIVE BOOLEAN,
  SCORE I32 NULL
)
```

## Inserts and literal encoding

```sql
INSERT INTO SQLDML VALUES (42, 'ADA', TRUE, NULL)
```

The test scans the stored row, checks the null bit for `SCORE`, little-endian
`I16`, space padding for `CHAR(8)`, and the boolean byte.

```sql
insert into sqldml values (-7, 'O''NEIL', false, 123456);
```

This covers case-insensitive keywords/names, a negative integer, doubled-quote
escaping, false, a four-byte integer, and an optional trailing semicolon. The
row iterator must return both inserts in deterministic physical order and then
`RSQL_ERR_NOT_FOUND`.

## Named enumerations

```sql
CREATE TYPE MOOD AS ENUM8 (SAD = 1, OK = 2, HAPPY = 7);
CREATE TYPE BIGCODE AS ENUM16 (LOW = 1, HIGH = 300);
CREATE TABLE EDATA (ID I16, STATE MOOD, CODE BIGCODE NULL);

INSERT INTO EDATA VALUES (1, MOOD.HAPPY, BIGCODE.HIGH);
INSERT INTO EDATA VALUES (2, MOOD.SAD, NULL);
SELECT COUNT(*) FROM EDATA WHERE STATE = MOOD.HAPPY;
SELECT STATE, CODE FROM EDATA WHERE ID = 1;
UPDATE EDATA
SET STATE = MOOD.OK, CODE = BIGCODE.LOW
WHERE STATE = MOOD.HAPPY;
```

The target verifies enum widths, member values, table-column catalog IDs,
nullable metadata, one-byte and two-byte physical values, qualified filtering,
typed cursor results, and qualified fixed-record UPDATE. It also rejects an
unknown named column type, duplicate enum values, an ENUM8 member above 255,
missing members, a qualifier for the wrong enum, an enum literal assigned to a
non-enum column, and numeric values outside ENUM8/ENUM16 unsigned ranges.

## SELECT and cursor results

```sql
SELECT BODY, RAW FROM SQLVAR;
SELECT COUNT(BODY) FROM SQLVAR;
```

The cursor reports logical TEXT/BLOB payload lengths rather than the four-byte
physical handle width. `rsql_value_read()` streams the full TEXT and a BLOB
slice, including zero bytes. The second row returns NULL TEXT and a non-NULL,
zero-length BLOB; `COUNT(BODY)` returns one.

```sql
SELECT COUNT(*) FROM SQLDML
```

Opened through the query/cursor ABI. It returns one non-NULL `I64` value equal
to two, then reaches end-of-cursor. Closing it makes a later `next` call return
`RSQL_ERR_CURSOR_STATE`.

```sql
select name, score, id from sqldml;
```

The cursor returns both rows in physical order. Tests check projection order,
the first row's NULL `SCORE`, the second row's `123456`, both IDs, and streamed
eight-byte CHAR values through `rsql_value_read()`.

```sql
SELECT COUNT(*) FROM SQLDML WHERE SCORE IS NOT NULL
```

This verifies NULL-aware filtering happens before aggregation: only the second
row contributes, so the result is one.

```sql
SELECT ID FROM SQLDML WHERE ID < 0
```

This exercises signed, width-aware integer comparison. It returns only `-7`
and then end-of-cursor.

## Compound predicates and LIKE

```sql
SELECT COUNT(*)
FROM SQLDML
WHERE ID < 0 OR ACTIVE = TRUE AND SCORE IS NULL
```

Returns two and proves `AND` binds more tightly than `OR`.

```sql
SELECT COUNT(*)
FROM SQLDML
WHERE (ID < 0 OR ACTIVE = TRUE) AND SCORE IS NULL
```

Returns one, proving parentheses override precedence.

```sql
SELECT COUNT(*)
FROM SQLDML
WHERE NOT (SCORE = NULL) OR ID < 0
```

Returns one. Comparisons with NULL produce UNKNOWN, NOT preserves UNKNOWN, and
`UNKNOWN OR TRUE` becomes TRUE only for the negative-ID row.

```sql
SELECT COUNT(*)
FROM SQLDML
WHERE NAME LIKE 'a_a%' OR NAME LIKE '%NEIL'
```

Returns two and covers folded matching, `_`, `%`, suffix matching, and trimming
of fixed-CHAR padding for LIKE.

```sql
SELECT COUNT(*) FROM SQLDML WHERE NAME NOT LIKE '%NEIL'
```

Returns one and verifies the standard infix `NOT LIKE` spelling.

```sql
SELECT COUNT(*)
FROM SQLDML
WHERE ID >= -7 AND ID <= 42 AND ID != 0
  AND ID <> 99 AND ID > -8 AND ID = 42
```

Returns one while executing every supported comparison spelling in one bounded
postfix predicate program.

## Grouping and aggregates

The aggregate lane creates a data set with duplicate keys, negative values,
and NULL-only groups:

```sql
CREATE TABLE AGGDATA (REGION CHAR(4), AMOUNT I16 NULL);
INSERT INTO AGGDATA VALUES ('N', 10);
INSERT INTO AGGDATA VALUES ('N', 20);
INSERT INTO AGGDATA VALUES ('S', -5);
INSERT INTO AGGDATA VALUES ('S', NULL);
INSERT INTO AGGDATA VALUES ('E', NULL);
INSERT INTO AGGDATA VALUES ('N', 10);
```

```sql
SELECT DISTINCT COUNT(*), COUNT(AMOUNT), SUM(AMOUNT), AVG(AMOUNT),
       MIN(AMOUNT), MAX(AMOUNT)
FROM AGGDATA
ORDER BY 3 DESC
```

The result is `6, 4, 35, 8, -5, 20`. `COUNT(AMOUNT)` ignores NULL and the
current integer `AVG` truncates toward zero into `I64`.

```sql
SELECT DISTINCT REGION, COUNT(*), COUNT(AMOUNT), SUM(AMOUNT), AVG(AMOUNT),
       MIN(AMOUNT), MAX(AMOUNT)
FROM AGGDATA
GROUP BY REGION
ORDER BY 4 DESC
```

The target checks all three groups. `N` gives `3, 3, 40, 13, 10, 20`; `S`
gives `2, 1, -5, -5, -5, -5`; and NULL-only `E` returns NULL for SUM, AVG,
MIN, and MAX.

```sql
SELECT REGION, SUM(AMOUNT)
FROM AGGDATA
WHERE AMOUNT IS NOT NULL
GROUP BY REGION
ORDER BY REGION DESC
```

This proves WHERE is applied before grouping, excludes the NULL-only `E`
group, and orders named group keys directly; results are `S` then `N`.

```sql
SELECT REGION, AMOUNT, COUNT(*)
FROM AGGDATA
GROUP BY REGION, AMOUNT
```

This verifies compound grouping keys, NULL key equality, and duplicate
`('N', 10)` collapse.

```sql
SELECT COUNT(*), COUNT(AMOUNT), SUM(AMOUNT), AVG(AMOUNT),
       MIN(AMOUNT), MAX(AMOUNT)
FROM EMPTYDATA
```

The empty-table result is one row containing `0, 0, NULL, NULL, NULL, NULL`.

## Commodore FLOAT

```sql
CREATE TABLE FLOATDATA (REGION CHAR(2), VALUE FLOAT NULL);
INSERT INTO FLOATDATA VALUES ('A', 1.5);
INSERT INTO FLOATDATA VALUES ('A', 2.25);
INSERT INTO FLOATDATA VALUES ('B', -0.75);
INSERT INTO FLOATDATA VALUES ('B', NULL);
INSERT INTO FLOATDATA VALUES ('A', 2);

SELECT VALUE FROM FLOATDATA;
SELECT VALUE FROM FLOATDATA WHERE VALUE >= 1.5 AND VALUE < 2.25;
UPDATE FLOATDATA SET VALUE = 3.5 WHERE VALUE = -0.75;

SELECT COUNT(*), COUNT(VALUE), SUM(VALUE), AVG(VALUE),
       MIN(VALUE), MAX(VALUE)
FROM FLOATDATA;

SELECT REGION, COUNT(VALUE), SUM(VALUE), MIN(VALUE), MAX(VALUE)
FROM FLOATDATA
GROUP BY REGION
ORDER BY 3 DESC;
```

The target verifies exact Commodore five-byte encodings for positive, negative,
integer-coerced, updated, and aggregate values. The ungrouped row is
`5, 4, 5.0, 1.25, -0.75, 2.25`; group `A` returns count `3`, sum `5.75`, min
`1.5`, max `2.25`; group `B` ignores its NULL and returns `-0.75` for sum, min,
and max. `rsql_value_read()` and inline cursor bytes must agree exactly.

Aggregate/grouped shaping is also combined with pagination:

```sql
SELECT REGION, COUNT(*)
FROM AGGDATA
GROUP BY REGION
ORDER BY 2 DESC
LIMIT 1 OFFSET 1;
```

Group counts are `N=3`, `S=2`, and `E=1`, so the selected row is `S,2`.
Ungrouped `DISTINCT` is a one-row proof; grouped `DISTINCT` is optimized away
when every group key is projected. Exact projected-tuple elimination is tested
when a key is omitted:

```sql
SELECT DISTINCT REGION
FROM AGGDATA
GROUP BY REGION, AMOUNT;
```

The compound groups are `(N,10)`, `(N,20)`, `(S,-5)`, `(S,NULL)`, and
`(E,NULL)`, but the projected result is exactly `N`, `S`, `E`. This proves
deduplication across different group identities without a materialized set.

```sql
UPDATE AGGDATA SET AMOUNT = 1.5 WHERE REGION = 'N';
```

Rejected with `RSQL_ERR_TYPE_MISMATCH`: a decimal FLOAT literal is not silently
narrowed into I16.

## Atomic mutation failure injection

```sql
CREATE TABLE JFAIL (ID I16)
INSERT INTO JFAIL VALUES (1)
INSERT INTO JFAIL VALUES (2)
SELECT COUNT(*) FROM JFAIL
```

The target injects I/O failure before every canonical write in CREATE and in
both INSERT paths. After each failure, the table/row count is unchanged and the
same first free REU page remains available. The non-injected statements then
commit normally and the final count is two.

The variable-value lane repeats this for a two-handle TEXT/BLOB insert. It uses
the committed transaction's measured write count to inject failure at every
write boundary, proving that payload pages, directory entries, handle counters,
the row, and allocation bitmap roll back together.

## DELETE

```sql
DELETE FROM JFAIL WHERE ID = 1;
DELETE FROM JFAIL WHERE ID > 100;
DELETE FROM JFAIL WHERE ID = 2 OR ID = 99;
DELETE FROM JFAIL;
```

The tests verify affected-row counts of one, zero, one, and two, along with
COUNT(*) after each statement. Failure is injected before both writes of a
single-row delete and all four writes of a two-row delete; every failure leaves
both rows and the allocation state intact before a successful retry.

Variable ownership is exercised separately:

```sql
DELETE FROM VDEL WHERE BODY IS NULL;
DELETE FROM VDEL;
DELETE FROM VFAIL;
```

The filtered statement tombstones the empty BLOB handle but leaves the other
row's TEXT/BLOB active. The following statement tombstones those two handles,
and explicit compaction reclaims exactly two payload pages. A two-row VFAIL
statement owns four nonempty handles; failure injection at every measured write
boundary restores both rows and all four active directory entries. The commit
tombstones all four and compaction reclaims four pages.

## UPDATE

```sql
UPDATE UDATA
SET NAME = 'Z', SCORE = 99
WHERE ID >= 2 AND ID < 3;

UPDATE UDATA
SET SCORE = NULL, NAME = 'N'
WHERE ID >= 2;

UPDATE UDATA SET SCORE = 7 WHERE ID > 99;
```

The tests verify affected counts of one, two, and zero; multiple assignments;
compound filtering; CHAR padding; and transitions to NULL. Follow-up COUNT
queries verify the updated predicates. A two-row UPDATE is replayed with
failure before each row-page write; both rows retain their old values and the
allocation state until the successful retry.

Variable ownership is covered in a fifth target lane:

```sql
UPDATE VUP
SET BODY = 'REPLACED', RAW = X'AA00', NAME = 'Z'
WHERE ID = 1;

UPDATE VUP SET BODY = 'BOTH', RAW = X'FF' WHERE ID <= 2;
UPDATE VUP SET BODY = NULL, RAW = NULL WHERE ID = 2;
UPDATE VUP SET BODY = 'BORN', RAW = X'' WHERE ID = 3;
UPDATE VUP SET BODY = 'NEVER', RAW = X'99' WHERE ID > 99;
```

The target proves each matching row receives different handles even when the
literal payload is identical, old handles become tombstones, payload bytes and
zero-length BLOBs remain exact, fixed and variable assignments commit together,
NULL transitions work in both directions, and a no-match update allocates
nothing. A two-row TEXT/BLOB/fixed update is then retried with failure before
every dynamically measured canonical write; every failure restores rows, old
handles, predicates, and the first-free page. The committed retry tombstones
four old handles, and compaction reclaims exactly four payload pages.

## Persistent named indexes

The storage lane builds both compound and single-column indexes:

```sql
CREATE TABLE IDXT (ID I16, NAME CHAR(64), NOTE TEXT NULL);
INSERT INTO IDXT VALUES (42, 'ADA', NULL);
INSERT INTO IDXT VALUES (-7, 'O''NEIL', 'TEXT');

CREATE INDEX IDX_NAME_ID ON IDXT (NAME, ID);
CREATE INDEX IDX_ID ON IDXT (ID);
```

Queries opt in by index name and still apply the complete WHERE predicate:

```sql
SELECT ID
FROM IDXT USING INDEX IDX_NAME_ID
WHERE NAME = 'O''NEIL';

SELECT ID
FROM IDXT USING INDEX IDX_ID
WHERE ID = 42;
```

The target checks the persisted descriptor and first leaf, then exercises
index maintenance through all three DML operations:

```sql
UPDATE IDXT SET NAME = 'GRACE' WHERE ID = 42;
SELECT ID FROM IDXT USING INDEX IDX_NAME_ID WHERE NAME = 'GRACE';

INSERT INTO IDXT VALUES (5, 'BOB', NULL);
INSERT INTO IDXT VALUES (6, 'ZED', NULL);
SELECT ID FROM IDXT USING INDEX IDX_NAME_ID WHERE NAME = 'ZED';

DELETE FROM IDXT WHERE ID = -7;
SELECT ID FROM IDXT USING INDEX IDX_NAME_ID WHERE NAME = 'O''NEIL';
```

The 64-byte CHAR component deliberately gives the compound leaf a capacity of
three, so the fourth row proves leaf splitting and linked-leaf traversal. A
shutdown/reinitialize between insertion and deletion proves index persistence.
The UPDATE is replayed with failure at every measured journal write; every
failure restores both the row and both indexes, while the successful retry
makes only the new key visible.

```sql
CREATE INDEX IDX_NOTE ON IDXT (NOTE);
SELECT ID FROM IDXT USING INDEX NO_SUCH_INDEX;
SELECT NAME FROM PEOPLE USING INDEX IDX_NAME_ID;
```

These respectively reject a variable-width key, a missing name, and an index
owned by a different table. Creating `IDX_NAME_ID` twice is also rejected.

## Two-source joins

The join lane creates customers and orders with duplicate matches, unmatched
rows, a NULL foreign key, signed values, TEXT, and a shared named enum:

```sql
CREATE TYPE STATE AS ENUM8 (ACTIVE=1, INACTIVE=2);
CREATE TABLE CUST (
    ID I16, NAME CHAR(8), STATE STATE, LIMITV FIXED8_8
);
CREATE TABLE ORDR (
    ID I16, CID I32 NULL, TOTAL I16,
    LABEL CHAR(8), NOTE TEXT NULL, STATUS STATE, AMOUNT FIXED8_8
);
```

An INNER JOIN exercises cross-width signed equality, compound post-join WHERE,
LIKE, duplicate inner matches, and TEXT streaming:

```sql
SELECT C.NAME, O.ID, O.NOTE
FROM CUST AS C
INNER JOIN ORDR AS O ON C.ID = O.CID
WHERE O.TOTAL >= 50 AND C.NAME LIKE 'A%';
```

The target receives `(ADA,10,'FIRST')` and `(ADA,11,NULL)` in deterministic
outer/inner physical order and reads `FIRST` through `rsql_value_read()`.

LEFT JOIN verifies both NULL extension and the distinction between ON and
WHERE:

```sql
SELECT C.ID, O.ID
FROM CUST AS C
LEFT OUTER JOIN ORDR AS O ON C.ID = O.CID;

SELECT C.ID
FROM CUST AS C
LEFT JOIN ORDR AS O ON C.ID = O.CID
WHERE O.ID IS NULL;

SELECT C.ID, O.ID
FROM CUST AS C
LEFT JOIN ORDR AS O
  ON C.ID = O.CID AND O.TOTAL > 0;
```

The first returns `(1,10)`, `(1,11)`, `(2,12)`, and `(3,NULL)`. The second
returns only customer 3. In the third, customer 2 is NULL-extended because its
only order fails ON, while customer 3 remains unmatched; the result has four
rows.

CROSS JOIN applies column references and literals in WHERE:

```sql
SELECT C.ID, O.ID
FROM CUST AS C CROSS JOIN ORDR AS O
WHERE C.ID = O.CID;
```

It returns three matching pairs. A separate CROSS query checks literal filters,
and empty-inner tests prove LEFT returns all three outer rows while CROSS
returns none.

CHAR and enum column references are first-class:

```sql
SELECT C.ID, O.ID
FROM CUST AS C JOIN ORDR AS O ON C.NAME = O.LABEL;

SELECT C.ID, O.ID
FROM CUST AS C JOIN ORDR AS O
  ON C.STATE = O.STATUS AND C.ID = O.CID
WHERE C.STATE = STATE.ACTIVE;
```

The target also rejects ambiguous unqualified `ID`, incompatible `CHAR = I16`,
and a self-join without distinct aliases.

FIXED8_8 uses its native two-byte representation for column references and
scales an integer literal before comparison. The same predicate now forces
exact joined scalar DISTINCT across different inner row identities:

```sql
SELECT DISTINCT LENGTH(C.NAME)
FROM CUST AS C JOIN ORDR AS O ON C.LIMITV = O.AMOUNT
WHERE O.AMOUNT >= 2;
```

Four joined pairs qualify: two expose `ADA` and two expose `CY`, so the virtual
LENGTH values are `3,3,2,2`. The target verifies exactly two result rows,
proving fixed-point predicate comparison and scalar duplicate elimination
across different joined pairs.

Joined ORDER BY remains a bounded nested-loop producer rather than a
materialized result:

```sql
SELECT O.ID
FROM CUST AS C
JOIN ORDR AS O ON C.ID = O.CID
ORDER BY O.TOTAL ASC, O.ID DESC;
```

The target returns order IDs `12, 10, 11`, proving inner-source keys,
multi-key direction, and deterministic selection. Pagination composes with the
ordered stream:

```sql
SELECT O.ID
FROM CUST AS C
JOIN ORDR AS O ON C.ID = O.CID
ORDER BY O.TOTAL ASC, O.ID DESC
LIMIT 2 OFFSET 1;
```

This returns `10, 11`. LEFT-null ordering is checked independently:

```sql
SELECT C.ID
FROM CUST AS C
LEFT JOIN ORDR AS O ON C.ID = O.CID
ORDER BY O.ID DESC;
```

It returns customer IDs `2, 1, 1, 3`; the NULL-extended customer is last for
DESC. These cases retain only outer/inner row IDs and a NULL-extension flag.
They do not allocate joined rows or an execution plan.

Joined fixed scalar projections also drive the selection comparator directly:

```sql
SELECT LENGTH(C.NAME), SUBSTR(O.LABEL,2,2), C.NAME||O.LABEL
FROM CUST AS C
JOIN ORDR AS O ON C.ID=O.CID
ORDER BY 3;
```

The ordered concatenations are `ADAADA`, `ADABAG`, and `BOBBAD`. The first row
is checked as `3,'DA','ADAADA'`, and the harness consumes all three rows. This
exercises LENGTH, substring, source-to-source concatenation, a projection
ordinal, and repeated target-row reads without a scalar result buffer.

## Joined grouping and aggregates

The dedicated joined-aggregate lane widens the order fixture with signed I8,
I32, I64, nullable FLOAT, and an empty inner table. It first verifies complete
ungrouped accumulation over an INNER producer:

```sql
SELECT COUNT(*), COUNT(O.TOTAL), SUM(O.TOTAL), AVG(O.TOTAL),
       MIN(O.TOTAL), MAX(O.TOTAL), SUM(C.ID)
FROM CUST AS C
JOIN ORDR AS O ON C.ID = O.CID;
```

The row is `3,3,120,40,-5,75,4`. Separate queries verify I8 values
`-100,100,7`, I32 values `100000,-30000,-70000`, I64 values including
`4294967296`, and exact Commodore FLOAT values `1.5,2.25,-0.75`. The I64 sum is
`4294967300`; FLOAT sum/average/min/max are `3,1,-0.75,2.25`.

LEFT and empty-input semantics are explicit:

```sql
SELECT C.ID, COUNT(*), COUNT(O.ID), SUM(O.TOTAL)
FROM CUST AS C LEFT JOIN ORDR AS O ON C.ID = O.CID
GROUP BY C.ID;

SELECT COUNT(*), SUM(E.ID)
FROM CUST AS C CROSS JOIN EMPTYJ AS E;
```

Customer 3's NULL-extended group is `3,1,0,NULL`; the empty ungrouped result is
the required single row `0,NULL`. WHERE-before-grouping is checked with
`O.TOTAL >= 0`.

Nullable inner and compound outer/inner keys are discovered through bounded
first-pair rescans:

```sql
SELECT O.CID, COUNT(*)
FROM CUST AS C CROSS JOIN ORDR AS O
GROUP BY O.CID;

SELECT C.ID, O.CID, COUNT(*)
FROM CUST AS C CROSS JOIN ORDR AS O
GROUP BY C.ID, O.CID
LIMIT 1 OFFSET 5;
```

The first emits physical-first groups `(1,6),(2,3),(NULL,3),(99,3)`; the
second proves compound grouping and pagination with `(2,2,1)`.

Joined grouped shaping covers named inner keys, aggregate ordinals, FLOAT,
exact DISTINCT, two-key ordering, and pagination:

```sql
SELECT C.ID, COUNT(*), SUM(O.TOTAL)
FROM CUST AS C JOIN ORDR AS O ON C.ID = O.CID
GROUP BY C.ID ORDER BY 3 DESC;

SELECT O.CID, COUNT(*)
FROM CUST AS C CROSS JOIN ORDR AS O
GROUP BY O.CID ORDER BY O.CID DESC;

SELECT DISTINCT C.ID
FROM CUST AS C JOIN ORDR AS O ON C.ID = O.CID
GROUP BY C.ID, O.TOTAL ORDER BY C.ID DESC;

SELECT DISTINCT COUNT(*)
FROM CUST AS C JOIN ORDR AS O ON C.ID = O.CID
GROUP BY C.ID ORDER BY 1 DESC;
```

The first returns customer 1 before 2 (`125 > -5`); the second places the
nullable inner key last under DESC; the third collapses three groups to IDs
`2,1`; and the fourth compares aggregate-only projected tuples and returns
counts `2,1`. An ordered compound query with `LIMIT 1 OFFSET 1` returns
`(1,50,1)`. Ungrouped ordered and ordered-empty aggregate queries remain
one-row results.

## Correlated scalar, IN, and EXISTS subqueries

The join lane also exercises the complex-query sidecar as a correlated
subquery executor. EXISTS and NOT EXISTS use both accepted projection forms:

```sql
SELECT C.ID FROM CUST AS C
WHERE EXISTS (
  SELECT 1 FROM ORDR AS O WHERE O.CID=C.ID
);

SELECT C.ID FROM CUST AS C
WHERE NOT EXISTS (
  SELECT * FROM ORDR AS O WHERE O.CID=C.ID
);
```

These return `(1,2)` and `(3)` respectively. A self-correlated query with
distinct `C` and `X` aliases returns all three customers; reusing the same
alias is rejected.

The outer correlated producer also supports bounded ordering:

```sql
SELECT C.ID FROM CUST AS C
WHERE EXISTS (
  SELECT 1 FROM ORDR AS O WHERE O.CID=C.ID
)
ORDER BY 1 DESC;

SELECT C.ID FROM CUST AS C
WHERE EXISTS (
  SELECT 1 FROM ORDR AS O WHERE O.CID=C.ID
)
ORDER BY C.ID DESC
LIMIT 1 OFFSET 1;
```

The first returns `2,1`; the second returns `1`. Together they prove a raw
projection ordinal, a named qualified outer key, descending selection, and
ordered pagination without materializing the correlated result.

Exact correlated DISTINCT uses an empty inner table to make all outer rows
eligible while projecting a duplicate virtual scalar:

```sql
SELECT DISTINCT LENGTH(NAME)
FROM CUST AS C
WHERE NOT EXISTS (
  SELECT 1 FROM EMPTYJ AS E WHERE E.ID=C.ID
);
```

The three outer values are `3,3,2`; the cursor returns exactly two rows. This
verifies complete fixed scalar comparison across prior matching correlated
results.

The same correlated producer orders multiple fixed scalar forms:

```sql
SELECT DISTINCT LENGTH('ABC'), SUBSTR('WXYZ',2,2), C.NAME||'X'
FROM CUST AS C
WHERE EXISTS (
  SELECT 1 FROM ORDR AS O
  WHERE O.CID=C.ID AND O.ID>=10 AND O.TOTAL>-10
)
ORDER BY 3;
```

The rows are ordered by `ADAX`, then `BOBX`. The first row exposes length `3`,
substring `XY`, and concatenation `ADAX`. Three inner predicate values occupy
the normal parsed value slots, proving the independently packed projection
literals survive every ORDER and exact DISTINCT replay.

The inner WHERE owns a separate postfix Boolean program:

```sql
SELECT C.ID FROM CUST AS C
WHERE EXISTS (
  SELECT O.ID FROM ORDR AS O
  WHERE O.CID=C.ID
    AND (O.TOTAL>60 OR O.TOTAL<0)
    AND NOT (O.ID=14)
);
```

It returns customers 1 and 2. Outer predicates compose normally with the
subquery term, including CHAR LIKE and named enum member predicates.

IN, NOT IN, CHAR, enum, and fixed-point cases are target-tested:

```sql
SELECT C.ID FROM CUST AS C
WHERE C.ID IN (
  SELECT O.CID FROM ORDR AS O
  WHERE O.CID=C.ID AND O.TOTAL>=0
);

SELECT C.ID FROM CUST AS C
WHERE C.NAME IN (SELECT O.LABEL FROM ORDR AS O WHERE O.ID=10);

SELECT C.ID FROM CUST AS C
WHERE C.STATE IN (
  SELECT O.STATUS FROM ORDR AS O
  WHERE O.CID=C.ID AND O.STATUS=STATE.ACTIVE
);

SELECT C.ID FROM CUST AS C
WHERE EXISTS (
  SELECT 1 FROM ORDR AS O
  WHERE O.CID=C.ID AND O.AMOUNT>=2
);
```

Each returns customer 1. An IN input containing only NULL produces UNKNOWN and
no row. NOT IN over a set containing NULL also produces no false-positive row.

The combined three-schema enum case uses a joined outer producer and resolves
the member against the correlated third source:

```sql
SELECT C.ID
FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID
WHERE EXISTS (
  SELECT 1 FROM ORDR AS X
  WHERE X.ID=O.ID AND X.STATUS=STATE.ACTIVE
);
```

Only the joined order whose third-source row is active qualifies, so the
result is customer `1`. This exact query runs in both Peddle REU sizes and the
join VICE lane.

Scalar subqueries distinguish zero, one, and multiple rows:

```sql
SELECT C.ID FROM CUST AS C
WHERE C.ID = (
  SELECT O.CID FROM ORDR AS O WHERE O.ID=10
);

SELECT C.ID FROM CUST AS C
WHERE C.ID = (
  SELECT O.CID FROM ORDR AS O WHERE O.CID=C.ID
);
```

The first returns customer 1. The second encounters two rows for customer 1
and `rsql_cursor_next()` returns `RSQL_ERR_SUBQUERY_ROWS`. Empty scalar input
is NULL/UNKNOWN. Incompatible selected types such as `CHAR IN (SELECT I16 ...)`
are rejected during binding.

## ORDER BY, DISTINCT, LIMIT, and OFFSET

The result-shaping lane inserts five deliberately unordered rows with duplicate
CHAR values, duplicate numeric values, signed I8 extremes, NULLs, enum values,
and Commodore FLOATs. These queries verify ordinary ascending and descending
order:

```sql
SELECT ID FROM SRT ORDER BY ID;
SELECT ID FROM SRT ORDER BY ID DESC;
SELECT ID FROM SRT ORDER BY CODE;
SELECT ID FROM SRT ORDER BY NAME ASC, ID ASC;
SELECT ID FROM SRT ORDER BY VALUE ASC, ID DESC;
```

The expected ID sequences are `(1,2,3,4,5)`, `(5,4,3,2,1)`,
`(3,4,2,5,1)` for signed I8 values `-128,-1,0,10,127`,
`(1,3,4,5,2)` for folded CHAR ordering, and `(5,1,4,2,3)` for FLOAT with
NULL first in ASC order.

Compound keys and NULL direction are covered explicitly:

```sql
SELECT ID FROM SRT ORDER BY SCORE ASC, ID DESC;
SELECT ID FROM SRT ORDER BY SCORE DESC, ID ASC;
```

These return `(4,5,3,2,1)` and `(1,2,3,5,4)`. ASC places NULL first; DESC
places it last; the ID key deterministically orders equal SCORE values.

Filtering, qualification, and both LIMIT/OFFSET spellings compose with order:

```sql
SELECT ID FROM SRT
WHERE ACTIVE=TRUE AND NAME NOT LIKE 'G%'
ORDER BY ID DESC LIMIT 2 OFFSET 1;

SELECT ID FROM SRT ORDER BY ID LIMIT 2 OFFSET 1;
SELECT ID FROM SRT ORDER BY ID OFFSET 2 LIMIT 2;
SELECT ID FROM SRT ORDER BY ID LIMIT 0;
SELECT ID FROM SRT OFFSET 3;
SELECT S.ID FROM SRT AS S ORDER BY s.ID DESC LIMIT 1;
```

The corresponding results are `(4,3)`, `(2,3)`, `(3,4)`, no rows, `(2,5)`
in physical scan order, and `(5)`.

DISTINCT is tested across CHAR, BOOLEAN, ENUM16, and nullable I32 values:

```sql
SELECT DISTINCT NAME FROM SRT ORDER BY NAME;
SELECT DISTINCT ACTIVE FROM SRT ORDER BY ACTIVE DESC;
SELECT DISTINCT KIND FROM SRT ORDER BY KIND DESC;
SELECT DISTINCT SCORE FROM SRT
WHERE SCORE IS NOT NULL
ORDER BY SCORE DESC LIMIT 1 OFFSET 1;
```

Folded CHAR duplicates collapse to `Alpha`, `beta`, `Gamma`; BOOLEAN returns
TRUE then FALSE; ENUM16 returns `60000` then `1`; the shaped SCORE query returns
only `20`.

Fixed scalar projections are compared as computed values. Positive ORDER BY
ordinals select expressions from the projection list:

```sql
SELECT SUBSTR(REGION,1,1) FROM AGGDATA ORDER BY 1;

SELECT DISTINCT REGION || '!'
FROM AGGDATA
ORDER BY 1 DESC;
```

The first returns `E,N,N,N,S,S`; the second returns `S!,N!,E!`. This proves
that substring and concatenation values, rather than their source columns, are
used by ordering and duplicate elimination.

The variable-update lane separately proves numeric scalar ordering while the
source column itself is streamed TEXT:

```sql
SELECT LENGTH(V) FROM SL ORDER BY 1 DESC;
SELECT DISTINCT LENGTH(V) FROM SL ORDER BY 1;
```

For `V` values `A`, `CCC`, and `BB`, the results are `(3,2,1)` and `(1,2,3)`.
The I32 LENGTH result and streamed TEXT scalar results both participate in
shaping; the latter coverage is listed in the scalar-string section below.

LIMIT/OFFSET also exercises every non-materialized cursor producer:

```sql
SELECT REGION, COUNT(*) FROM AGGDATA
GROUP BY REGION ORDER BY 2 DESC LIMIT 1 OFFSET 1;

SELECT COUNT(*) FROM AGGDATA LIMIT 0;

SELECT C.ID FROM CUST AS C JOIN ORDR AS O
ON C.ID=O.CID LIMIT 1 OFFSET 1;

SELECT C.ID FROM CUST AS C
WHERE EXISTS (
  SELECT 1 FROM ORDR AS O WHERE O.CID=C.ID
) LIMIT 1 OFFSET 1;

SELECT ID FROM IDXT USING INDEX IDX_NAME_ID LIMIT 1 OFFSET 1;
```

Explicit indexes also feed ORDER BY and DISTINCT shaping directly:

```sql
SELECT ID FROM IDXT USING INDEX IDX_NAME_ID
ORDER BY ID DESC LIMIT 1;

SELECT DISTINCT LENGTH(NAME) FROM IDXT USING INDEX IDX_NAME_ID
ORDER BY 1 DESC LIMIT 1;
```

With rows `(42,'GRACE')`, `(-7,'O''NEIL')`, `(5,'BOB')`, and `(6,'ZED')`,
these return `42` and `6`. The first proves ordering differs from the named
`(NAME,ID)` index's natural key order; the second combines index traversal,
computed DISTINCT, projection-ordinal order, and LIMIT. The result sidecar
validates and rescans the index leaves rather than falling back to a table
producer.

Rejection coverage retains duplicate ORDER keys, missing columns, and invalid
ordinals:

```sql
SELECT ID FROM SRT ORDER BY ID, ID;
SELECT ID FROM SRT ORDER BY MISSING;
SELECT REGION FROM AGGDATA ORDER BY 0;
```

Raw streamed TEXT/BLOB keys now participate in ordinary shaping. With rows
`('payload',X'02FF')`, `(NULL,NULL)`, and `('PAYLOAD',X'02FF')`, the result lane
executes:

```sql
SELECT DISTINCT BODY,RAW
FROM T
WHERE BODY LIKE 'p%' AND RAW=X'02FF'
ORDER BY RAW,BODY
LIMIT 1;
```

It returns one `payload` tuple. The query jointly proves streamed TEXT `LIKE`,
binary BLOB equality, binary/text ordering, case-insensitive TEXT duplicate
elimination, and pagination without copying either variable key into a C64-RAM
result buffer. Joined/correlated variable keys, variable scalar expressions,
and explicit-index variable grouping are covered below.

## Scalar string projections

The result lane exercises all eight projection slots in one CHAR/literal query:

```sql
SELECT LENGTH(NAME),
       SUBSTR(NAME,2,3),
       SUBSTRING(NAME,5),
       NAME || '!',
       CONCAT('<',NAME),
       NAME || NAME,
       'A' || 'B',
       'solo'
FROM SRT
WHERE ID=1
LIMIT 1;
```

For physical `NAME='Alpha   '`, results are I16 `5`, `lph`, `a`, `Alpha!`,
`<Alpha`, `AlphaAlpha`, `AB`, and `solo`. Tests verify result type/declared
width, logical length, the first eight inline bytes, a complete
`rsql_value_read()`, and a four-byte read crossing the `Alpha|Alpha`
concatenation boundary. A nullable CHAR row proves NULL propagation through
length, substring, and concatenation.

The same expression representation is exercised over every cursor producer:

```sql
SELECT LENGTH(NAME)
FROM IDXT USING INDEX IDX_NAME_ID
WHERE NAME='ADA';

SELECT LENGTH(C.NAME), SUBSTR(O.LABEL,2,2), C.NAME || O.LABEL
FROM CUST AS C
JOIN ORDR AS O ON C.ID=O.CID
ORDER BY 3;

SELECT O.LABEL || 'X'
FROM CUST AS C
LEFT JOIN ORDR AS O ON C.ID=O.CID
WHERE C.ID=3;

SELECT LENGTH(C.NAME), SUBSTR(C.NAME,2,2), C.NAME || C.NAME
FROM CUST AS C
WHERE EXISTS (
  SELECT 1 FROM ORDR AS O WHERE O.CID=C.ID
)
ORDER BY 3;
```

These return `3`; the joined sequence ordered by `ADAADA,ADABAG,BOBBAD`; NULL
from the LEFT extension; and the correlated sequence ordered by
`ADAADA,BOBBOB`, respectively.

TEXT uses stable-handle metadata and direct range streaming:

```sql
SELECT LENGTH(BODY),
       SUBSTR(BODY,2,3),
       SUBSTRING(BODY,5),
       SUBSTR(BODY,20,3),
       SUBSTR(BODY,1,0)
FROM T;
```

For `payload`, results are I32 `7`, `ayl`, `oad`, an empty TEXT, and an empty
TEXT. A second NULL row makes all five expressions NULL. The test reads every
nonempty substring through the cursor streaming ABI; no full TEXT value is
copied into an engine buffer.

The variable-value lane streams every two-part TEXT concatenation class:

```sql
SELECT BODY || 'X', CONCAT('<', BODY), BODY || BODY,
       BODY || TAG, TAG || BODY
FROM VDEL;
```

For `BODY='ALPHA'` and `TAG='Z'`, the values are TEXT `ALPHAX`, `<ALPHA`,
`ALPHAALPHA`, `ALPHAZ`, and `ZALPHA`. Full `rsql_value_read()` calls and
three-byte slices cross the left/right boundary for literal/TEXT, TEXT/TEXT,
TEXT/CHAR, and CHAR/TEXT. For the following NULL row, all five expressions are
NULL. Each stable handle is resolved sequentially and no combined heap or C64
RAM value is allocated.

Rejections cover non-string operands, zero starts, incompatible concatenation,
and aggregate composition:

```sql
SELECT LENGTH(ID) FROM SRT;
SELECT SUBSTR(NAME,0,2) FROM SRT;
SELECT NAME || ID FROM SRT;
SELECT LENGTH(NAME), COUNT(*) FROM SRT;
```

Streamed scalar shaping is tested without materializing a TEXT result:

```sql
SELECT DISTINCT LENGTH(BODY), SUBSTR(BODY,2,3),
       BODY || '!', BODY || BODY, '<' || BODY
FROM T
WHERE BODY LIKE 'p%'
ORDER BY 1,2;

SELECT O.ID, SUBSTR(O.NOTE,1,2)
FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID
ORDER BY 2,O.ID DESC;

SELECT DISTINCT LENGTH(O.NOTE)
FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID;

SELECT DISTINCT LENGTH(O.NOTE)
FROM ORDR AS O
WHERE NOT EXISTS (
  SELECT 1 FROM EMPTYJ AS E WHERE E.ID=O.ID
);
```

The first query folds case-equivalent `payload`/`PAYLOAD` results into one
tuple while comparing substring and all supported TEXT concatenation forms.
The joined query orders NULL and streamed substrings, and the final two prove
DISTINCT scalar evaluation over joined and correlated producers.

## Single-table aggregate producers with correlated subqueries

These query-lane cases prove that the correlated outer scan feeds slot 6
directly, without pretending to be a join.

```sql
SELECT COUNT(*)
FROM SQLDML AS D
WHERE EXISTS (
  SELECT 1 FROM SQLDML AS X WHERE X.ID=D.ID
);
```

For the two rows `(42,TRUE)` and `(-7,FALSE)`, the result is `2`.

```sql
SELECT DISTINCT COUNT(*), SUM(D.ID)
FROM SQLDML AS D
WHERE D.ID IN (
  SELECT X.ID FROM SQLDML AS X WHERE X.ID=D.ID
)
GROUP BY D.ACTIVE
ORDER BY 2
LIMIT 1 OFFSET 1;
```

The Boolean groups are `(1,-7)` and `(1,42)`. Exact projected-tuple DISTINCT
remains active because the group key is omitted; aggregate ordinal ordering,
OFFSET, and LIMIT return `(1,42)`.

```sql
SELECT COUNT(*)
FROM SQLDML AS D
WHERE D.ID=(SELECT X.ID FROM SQLDML AS X);
```

The cursor opens successfully, then its first `rsql_cursor_next()` returns
`RSQL_ERR_SUBQUERY_ROWS` because the scalar inner scan returns both rows. This
proves the alternate aggregate producer does not collapse a cardinality error
into UNKNOWN/false.

All three run as compiled 6510 in Peddle at 512KB and 16MB and in the query
VICE D81/1581 lane.

## Joined aggregate producers with correlated subqueries

These queries exercise a joined pair as the outer row context while a third
table scan evaluates the correlated predicate before aggregation.

```sql
SELECT COUNT(*), SUM(O.TOTAL)
FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID
WHERE EXISTS (
  SELECT 1 FROM ORDR AS X
  WHERE X.ID=O.ID AND X.CID=C.ID
);
```

The result is `(3,120)`. The inner program references both joined sources, and
all three matching joined pairs enter the ungrouped aggregate.

```sql
SELECT C.ID, COUNT(*), SUM(O.TOTAL)
FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID
WHERE O.ID IN (
  SELECT X.ID FROM ORDR AS X WHERE X.TOTAL>=O.TOTAL
)
GROUP BY C.ID
ORDER BY 3 DESC
LIMIT 1;
```

Every joined order finds itself in the correlated set. Grouping yields
customers `(1,2,125)` and `(2,1,-5)`; aggregate ordering and LIMIT return the
first tuple.

```sql
SELECT DISTINCT C.ID, COUNT(*)
FROM CUST AS C JOIN ORDR AS O ON C.ID=O.CID
WHERE O.CID=(
  SELECT X.CID FROM ORDR AS X WHERE X.ID=O.ID
)
GROUP BY C.ID
ORDER BY C.ID DESC
LIMIT 1;
```

The scalar subquery returns exactly one row for each pair. The groups are
`(1,2)` and `(2,1)`; descending order selects `(2,1)`, while exact DISTINCT and
LIMIT exercise the shaped aggregate replay over the correlated producer.
All three run as compiled 6510 in Peddle at 512KB and 16MB and in the joined-
aggregate VICE D81/1581 lane.

## Rejection tests

```sql
INSERT INTO SQLDML VALUES (40000, 'X', TRUE, NULL)
```

Rejected with `RSQL_ERR_TYPE_MISMATCH` because `40000` does not fit signed
`I16`.

```sql
INSERT INTO SQLVAR VALUES (X'41', X'00');
INSERT INTO SQLVAR VALUES ('OK', 'NOT BINARY');
INSERT INTO SQLVAR VALUES ('OK', X'0');
```

The first two reject TEXT/BLOB literal-kind mismatches. The odd-length hex
literal is a syntax error.

```sql
UPDATE UDATA SET ID = 40000 WHERE ID = 1;
UPDATE UDATA SET NAME = 'A', NAME = 'B' WHERE ID = 1;
UPDATE VUP SET BODY = X'41' WHERE ID = 1;
UPDATE VUP SET RAW = 'NO' WHERE ID = 1;
```

These reject an out-of-range I16, a duplicate SET target, and TEXT/BLOB
literal-kind mismatches respectively.

```sql
CREATE TABLE BROKEN (ID CHAR())
```

Rejected with `RSQL_ERR_SYNTAX`; `rsql_last_error()` must contain a nonzero byte
offset.

```sql
SELECT * FROM SQLTYPES
```

This exact call is passed to the non-result `rsql_exec()` entry and must return
`RSQL_ERR_UNSUPPORTED_SQL`; result-producing SELECT statements use
`rsql_query_open()` and the cursor ABI.

```sql
SELECT REGION, SUM(AMOUNT) FROM AGGDATA
```

Rejected because an ungrouped result column cannot be mixed with aggregates.

```sql
SELECT REGION, COUNT(*)
FROM AGGDATA
GROUP BY REGION
HAVING COUNT(*) > 1
```

Rejected with `RSQL_ERR_SYNTAX`; `HAVING` is intentionally outside the
dialect.

## Materialized result tables

```sql
CREATE TEMP TABLE UR AS
SELECT ID, NAME, SCORE
FROM UDATA
WHERE ID >= 2
ORDER BY ID DESC;

CREATE TABLE UA AS
SELECT COUNT(*), SUM(SCORE) FROM UDATA;
```

These prove fixed projections, ordering, NULL propagation, aggregate result
types, affected-row counts, and immediate querying of persistent/TEMP result
tables.

The dedicated CTAS lane crosses blob-page boundaries and composes streamed
scalar output:

```sql
CREATE TEMP TABLE VCOPY AS
SELECT BODY,
       RAW,
       SUBSTR(BODY, 240, 17),
       BODY || 'END'
FROM VSRC;
```

The first source row contains a 256-byte TEXT and 250-byte BLOB; the second has
NULL TEXT and a non-NULL empty BLOB. Tests verify fresh handles for every
non-NULL result, exact bytes across the 246-byte payload boundary, scalar
lengths 17 and 259, and NULL propagation. All destination values remain valid
after every source handle is tombstoned and its four payload pages compacted.

Staged CTAS rollback targets descriptor creation, owned-row creation, every
write position of a mid-chain payload append, and final publication using:

```sql
CREATE TABLE RFAIL AS
SELECT ID, BODY, BODY || '!' FROM RSRC;
```

After each forced I/O failure, `RFAIL` is absent, the first free REU page is
unchanged, and `SELECT COUNT(*) FROM RSRC` still returns two. The final retry
commits two rows.

Large-result coverage deliberately exceeds the sixteen-page journal in both
physical shapes:

```sql
CREATE TABLE BIGCOPY AS SELECT BODY FROM BIGTEMP;

CREATE TABLE WIDE (BODY CHAR(119));
CREATE TABLE WIDECOPY AS SELECT BODY FROM WIDE;
SELECT COUNT(*) FROM WIDECOPY;
```

`BIGTEMP.BODY` is a 4096-byte TEXT occupying seventeen source pages. BIGCOPY
uses eighteen independently committed 240-byte destination pages, retains its
length and handle after BIGTEMP is dropped, and releases every captured page
when dropped. WIDE contains thirty-four programmatically inserted rows; at two
rows per page, WIDECOPY owns seventeen destination row pages and returns count
34. Dropping both source/result pairs restores the exact allocator baseline.
A persistent table descriptor manually marked only `BUILDING` is invisible
and fully reclaimed by the next `rsql_init`.

## TEMP lifecycle and explicit DROP TABLE

The lifecycle lane creates a persistent table with an index and a 4096-byte
TEXT value, whose payload occupies seventeen REU pages:

```sql
CREATE TABLE BIGTEMP (ID I16, BODY TEXT);
CREATE INDEX BIGIDX ON BIGTEMP (ID);
DROP TABLE BIGTEMP;
```

`DROP TABLE` reports zero affected rows, hides the descriptor first, and then
reclaims the index leaf and descriptor, row and row page, blob-directory
handle, all seventeen payload pages, and the table descriptor. This exceeds
the sixteen-page journal capacity by design and proves reclamation is a series
of resumable bounded mutations. Repeating the DROP returns
`RSQL_ERR_NOT_FOUND`; incomplete `DROP TABLE` text returns
`RSQL_ERR_SYNTAX`. The persistent `RSRC` source remains queryable throughout.

`CREATE TEMP TABLE VCOPY AS ...` is independently removed by
`rsql_shutdown()`. A `STALE` TEMP descriptor is then marked `DROPPING` to model
an interruption immediately after the durable visibility transition;
`rsql_init()` completes its row and descriptor reclamation. Finally:

```sql
CREATE TEMP TABLE TROLL (ID I16);
DROP TABLE TROLL;
```

Failure injection on the DROP's first persistent write leaves `TROLL` visible
and allocated. Retrying the same statement succeeds, makes the name absent,
and frees its descriptor. This distinguishes atomic publication of the
visibility marker from the deliberately incremental cleanup that follows it.

## DROP INDEX and DROP TYPE

The variable-update/schema lifecycle lane verifies standalone index removal
without changing its table:

```sql
CREATE TYPE DTYPE AS ENUM8(OFF, ON);
CREATE TABLE DROW (ID I16, STATE DTYPE);
INSERT INTO DROW VALUES (1, DTYPE.ON);
CREATE INDEX DIDX ON DROW (ID);

SELECT COUNT(*) FROM DROW USING INDEX DIDX;
DROP TYPE DTYPE;
DROP INDEX DIDX;
```

The indexed count is one. The first `DROP TYPE` is rejected with
`RSQL_ERR_DEPENDENT_OBJECT` because `DROW.STATE` retains the exact enum catalog
ID. Failure injection at the index visibility write leaves `DIDX` usable;
retry returns zero affected rows, frees its leaf and descriptor, and makes
`USING INDEX DIDX` return `RSQL_ERR_NOT_FOUND`. A repeated DROP also returns
NOT_FOUND while an ordinary table scan still sees the row.

```sql
DROP TABLE DROW;
DROP TYPE DTYPE;
```

After the table is gone, failure injection at the type visibility write leaves
`DTYPE` resolvable. Retry reclaims its member page and descriptor. The test
checks that every page allocated by this fixture returns to the free pool.

Restart recovery uses a fourteen-member enum, which occupies two member pages,
and a populated single-leaf index. Their descriptor dropping bits are written
to model an interruption immediately after visibility publication. Calling
`rsql_init()` frees both index pages, both member pages, and the enum
descriptor; the base table and its row remain available by sequential scan.
The stale index name and enum type name are absent, and dropping the remaining
table restores the exact first-free page.

## FIXED8_8 grouping and aggregates

The dedicated fixed-point lane stores Q8.8 values `1`, `2`, `-2`, NULL, and
three copies of `127`. Its ordinary aggregate query is:

```sql
SELECT COUNT(*), COUNT(V), SUM(V), AVG(V), MIN(V), MAX(V)
FROM F
WHERE R < 3;
```

It returns `(4, 3, 1, 0.33203125, -2, 2)`. The average is raw Q8.8 `$0055`
(85/256): division truncates the signed raw sum toward zero to one Q8.8 unit.
All four numeric results retain the two-byte `RSQL_TYPE_FIXED8_8` tag and are
also verified through `rsql_value_read()`.

Grouped accumulation, aggregate ordering, exact DISTINCT, NULL exclusion, and
the original fixed-width key type are exercised together:

```sql
SELECT DISTINCT R, COUNT(V), SUM(V), AVG(V), MIN(V), MAX(V)
FROM F
WHERE R < 3
GROUP BY R
ORDER BY 3 DESC;
```

The rows are `(1,2,3,1.5,1,2)` followed by `(2,1,-2,-2,-2,-2)`.

The joined producer uses the same accumulator after pair production:

```sql
SELECT COUNT(*), SUM(Y.V), AVG(Y.V), MIN(Y.V), MAX(Y.V)
FROM K AS X JOIN F AS Y ON X.R = Y.R;
```

It returns `(4,1,0.33203125,-2,2)`. A correlated ordinary producer is covered
independently:

```sql
SELECT SUM(O.V), AVG(O.V)
FROM F AS O
WHERE O.R < 3
  AND EXISTS (SELECT 1 FROM K AS X WHERE X.R = O.R);
```

It returns `(1,0.33203125)`. Empty input preserves SQL aggregate NULL rules:

```sql
SELECT SUM(V), AVG(V), MIN(V), MAX(V) FROM F WHERE R = 9;
```

All four values are NULL. The widened raw accumulator must not silently wrap
when converted back to the public two-byte type:

```sql
SELECT SUM(V) FROM F WHERE R = 3;
```

The mathematical sum is 381, outside signed Q8.8. Both
`rsql_cursor_column()` and `rsql_value_read()` return
`RSQL_ERR_NUMERIC_OVERFLOW`.

Finally, CTAS preserves the result type and exact raw values:

```sql
CREATE TEMP TABLE Z AS
SELECT SUM(V), AVG(V), MIN(V), MAX(V) FROM F WHERE R < 3;
SELECT * FROM Z;
```

`Z` contains `(1,0.33203125,-2,2)`, with all four columns physically
`FIXED8_8` rather than widened I64.

## Streamed TEXT/BLOB GROUP BY

The same lane creates five rows whose equal logical values have independent
stable handles:

```sql
CREATE TABLE G (T TEXT NULL, B BLOB NULL, V I8);
INSERT INTO G VALUES ('a', X'0102', 1);
INSERT INTO G VALUES ('A', X'0102', 2);
INSERT INTO G VALUES ('b', X'01FF', 3);
INSERT INTO G VALUES (NULL, NULL, 4);
INSERT INTO G VALUES (NULL, NULL, 5);
```

Compound variable grouping is exercised with aggregates through an explicitly
named fixed-width index:

```sql
CREATE INDEX I ON G (V);
SELECT T, B, COUNT(*), SUM(V)
FROM G USING INDEX I
GROUP BY T, B;
```

The index leaf order controls representative discovery while grouping still
produces the same three logical tuples. `a` and `A` merge
despite having different handles because TEXT group identity is case-folded
logical content. Both `X'0102'` handles merge by exact binary content, while
`X'01FF'` remains distinct. All NULL pairs form one group. The projected TEXT
and BLOB representatives are verified through `rsql_cursor_column()` and
`rsql_value_read()`.

Streamed predicate evaluation and pagination compose with grouping:

```sql
SELECT T, COUNT(*), SUM(V)
FROM G
WHERE T LIKE 'a%'
GROUP BY T
LIMIT 1;
```

It returns `('a',2,3)`. This proves that each bounded duplicate and
accumulation rescan evaluates the TEXT predicate, then compares the logical
group key without materializing either payload in C64 RAM.

Variable group ordering covers case-folded TEXT, binary BLOB, NULL placement,
and exact DISTINCT when an omitted compound key would otherwise duplicate the
projection:

```sql
SELECT T, COUNT(*), SUM(V)
FROM G USING INDEX I GROUP BY T ORDER BY T DESC;
SELECT B, COUNT(*) FROM G GROUP BY B ORDER BY B;
SELECT DISTINCT T FROM H GROUP BY T, B;
```

The first query returns `b`, `A`, then NULL. The second returns NULL,
`X'0102'`, then `X'01FF'`. In the third query the independent `a` and `A`
groups have different BLOB keys, but exact projected-tuple DISTINCT merges
their case-folded TEXT results and returns only `a`, `b`.

Joined and correlated aggregate producers exercise variable keys from either
side of a pair and from a correlated outer row:

```sql
SELECT X.T, COUNT(*), SUM(X.V)
FROM G AS X CROSS JOIN K AS Y
GROUP BY X.T ORDER BY 1 DESC;

SELECT Y.T, COUNT(*)
FROM G AS X CROSS JOIN H AS Y
GROUP BY Y.T ORDER BY 1;

SELECT O.T, COUNT(*), SUM(O.V)
FROM G AS O
WHERE EXISTS (SELECT 1 FROM Q AS X WHERE X.R = O.V)
GROUP BY O.T ORDER BY 1;
```

These verify outer and inner TEXT ownership, independently allocated equal
handles, aggregate rescans, NULL groups, ordinal variable ordering, and the
correlated producer replay. Raw joined shaping is covered separately:

```sql
SELECT O.ID
FROM CUST AS C JOIN ORDR AS O ON C.ID = O.CID
WHERE O.NOTE > 'E'
ORDER BY SUBSTR(O.NOTE,1,2), O.ID DESC;

SELECT DISTINCT C.NAME, O.NOTE, O.ID
FROM CUST AS C JOIN ORDR AS O ON C.ID = O.CID
WHERE O.NOTE < 'S';
```

The ORDER query returns IDs `10,12`, ordered by the streamed scalar prefixes
`FI` and `RE`. The DISTINCT query returns `(ADA,FIRST,10)` and
`(BOB,RETURN,12)`. Both force a live streamed NOTE predicate to suspend slot 4,
run in slot 6, restore slot 4, and continue the ORDER/DISTINCT rescan.

## Whole-REU checkpoint and restore

The eleventh target lane establishes durable and temporary state:

```sql
CREATE TABLE CP (ID I16, NOTE TEXT);
INSERT INTO CP VALUES (1,'ALPHA');
INSERT INTO CP VALUES (2,'BETA');
CREATE TEMP TABLE SCRATCH (ID I16);
```

It calls `rsql_checkpoint()`, after which `SCRATCH` must already be absent
because checkpoint is a quiescing lifecycle boundary. The client then proves
the live database can diverge:

```sql
DELETE FROM CP;
```

The affected-row count is exactly two. The host replaces the complete REU with
the captured bytes, and the client calls `rsql_restore()` with formatting
disabled. These observations verify restored catalog, rows, and variable heap:

```sql
SELECT ID, NOTE FROM CP ORDER BY ID;
SELECT ID FROM SCRATCH;
```

The first query streams `(1,'ALPHA')` and `(2,'BETA')`; the second returns
`RSQL_ERR_NOT_FOUND`. Peddle performs a literal full-REU byte copy at 512KB and
16MB. VICE performs the same capture/load semantics through a native writable
REU image when its binary monitor does not enumerate REU banks; the verified
16MB artifact is exactly 16,777,216 bytes.

## Schema, size, and selected-query export

The checkpoint lane now adds a named type and index:

```sql
CREATE TYPE STATE AS ENUM8(NEW=1,DONE=2);
CREATE TABLE CP(ID I16, NOTE TEXT NULL, STATUS STATE);
INSERT INTO CP VALUES(1,'ALPHA',STATE.NEW);
INSERT INTO CP VALUES(2,'BETA',STATE.DONE);
CREATE INDEX CP_ID ON CP(ID);
```

It executes every introspection form through `rsql_exec()`:

```sql
SHOW DATABASE;
SHOW TABLES;
SHOW COLUMNS FROM CP;
SHOW INDEXES;
SHOW TYPES;
SHOW MEMBERS FROM STATE;
```

The assertions cover allocator capacity/used/free arithmetic; one visible
table with three columns, two rows, and nonzero row-page use; paginated column
ordinal 1 (`NOTE`, TEXT, physical offset 3); index `CP_ID` with two entries and
a nonempty leaf chain; enum type `STATE`; and paginated member ordinal 1
(`DONE=2`). The TEMP table created before checkpoint is absent from the
restored visible schema.

The selected export query is:

```sql
SELECT ID, NOTE, STATUS FROM CP ORDER BY ID;
```

`rsql_export_d81()` writes it as `cpexport` on device 8. Peddle models the
KERNAL sequential-file calls and compares all 52 emitted bytes, including both
row markers, type/null/length headers, streamed PETSCII TEXT bytes, ENUM8
values, and footer row count. The VICE checkpoint plan writes the same file to
its attached D81; extraction with `c1541` proves it is a 52-byte SEQ file with
the same framing. The lane finally converts both valid version-2 superblocks
into checksummed version-1 copies and verifies restore rejects the old format
with `RSQL_ERR_CORRUPT_STORAGE`.

## Interactive shell transcript

The twelfth lane drives the real GETIN/CHROUT loop rather than calling the
engine directly. Peddle injects the same commands at 512KB and 16MB; VICE types
them into the shell booted from a D81 on a virtual 1581:

```sql
CREATE TYPE STATE AS ENUM8(NEW=1,DONE=2)
CREATE TABLE NOTE(ID I16, BODY TEXT, STATUS STATE)
INSERT INTO NOTE VALUES(1,'LONG NOTE',STATE.NEW)
SELECT ID, BODY, STATUS FROM NOTE ORDER BY ID
```

The SELECT display is exactly one comma-separated row followed by `(1 ROW)`.
The plan then exercises every class of shell-only command:

```text
.TABLES
.SCHEMA NOTE
.TYPES
.MEMBERS STATE
.EXPORT shexport SELECT ID, BODY, STATUS FROM NOTE ORDER BY ID
.CHECKPOINT
.QUIT
```

The assertions cover visible table/column/type/member text, a successful
checkpoint, and clean termination. Peddle compares all 36 bytes written by the
export adapter. VICE extracts `shexport` from the writable D81 with `c1541` and
compares the same RSQLX header, typed row, streamed TEXT bytes, and footer.

## Depth-2 correlated EXISTS

The join/subquery lane composes its existing one-level query at runtime with a
second EXISTS so the full client image does not duplicate the common prefix:

```sql
SELECT C.ID
FROM CUST AS C
WHERE EXISTS (
  SELECT 1 FROM ORDR AS O
  WHERE O.CID = C.ID
    AND EXISTS (
      SELECT * FROM CUST AS X
      WHERE X.ID = O.CID
        AND X.ID = C.ID
        AND X.STATE = STATE.ACTIVE
    )
);
```

Only customer `1` is returned. The innermost scan is correlated directly to
both earlier levels and resolves a named ENUM8 member against the third-table
column. The focused Peddle lane passes at 512KB and 16MB, and the D81-backed
VICE/1581 plan passes without degradation.

## Depth-2 scalar, IN, NULL, and aggregate queries

The dedicated nested lane uses three nullable fixed-width tables and executes
the following depth-2 forms at both 512KB and 16MB:

```sql
SELECT A.ID FROM A
WHERE EXISTS (
  SELECT 1 FROM B
  WHERE B.AID=A.ID
    AND B.V IN (SELECT C.V FROM C WHERE C.BID=B.ID)
);

SELECT A.ID FROM A
WHERE EXISTS (
  SELECT 1 FROM B
  WHERE B.AID=A.ID
    AND B.V NOT IN (SELECT C.V FROM C WHERE C.BID=20)
);

SELECT A.ID FROM A
WHERE EXISTS (
  SELECT 1 FROM B
  WHERE B.AID=A.ID
    AND B.V=(SELECT C.V FROM C
             WHERE C.BID=B.ID AND C.ID<400)
);
```

The first returns only `A.ID=1`. The second returns no row because both the
left value and selected set exercise SQL UNKNOWN; a separate empty-set
`NOT IN` case returns IDs `1,2`, including a NULL left operand. The scalar form
returns ID `1`, while a version selecting both rows for `B.ID=30` returns
`RSQL_ERR_SUBQUERY_ROWS`.

Nested predicates also feed aggregate and grouped producers:

```sql
SELECT COUNT(*),SUM(A.ID) FROM A
WHERE EXISTS (
  SELECT 1 FROM B
  WHERE B.AID=A.ID
    AND B.V IN (SELECT C.V FROM C WHERE C.BID=B.ID)
);

SELECT COUNT(*) FROM A
WHERE EXISTS (
  SELECT 1 FROM B
  WHERE B.AID=A.ID
    AND B.V=(SELECT C.V FROM C
             WHERE C.BID=B.ID AND C.ID<400)
);

SELECT A.ID,COUNT(*) FROM A
WHERE EXISTS (
  SELECT 1 FROM B
  WHERE B.AID=A.ID
    AND EXISTS (SELECT 1 FROM C WHERE C.BID=B.ID)
)
GROUP BY A.ID ORDER BY A.ID;
```

The first returns `(1,1)`, the second returns `1`, and the grouped query returns
`(1,1),(2,1)`. An aggregate whose nested scalar produces two rows propagates
`RSQL_ERR_SUBQUERY_ROWS` rather than silently completing accumulation. The
same client boots from an 819,200-byte D81 on VICE's virtual 1581.

## Three-output-source fixed scans

```sql
SELECT A.ID,B.ID,C.ID
FROM WA AS A
JOIN WB AS B ON B.AID=A.ID
JOIN WC AS C
  ON C.BID=B.ID AND C.AID=A.ID AND C.K=B.K
WHERE C.STATE=A.STATE AND (C.STATE=WS.ON OR A.ID=2);

SELECT A.ID,B.ID,C.ID
FROM WA AS A
CROSS JOIN WB AS B
CROSS JOIN WC AS C
WHERE A.ID=B.AID AND B.ID=C.BID
LIMIT 2 OFFSET 1;
```

The dedicated lane also rejects ambiguous unqualified projection, duplicate
aliases, a fourth JOIN, and invalid aggregate/group forms with focused error
codes. The fixed wide SELECT below is also materialized and read back:

```sql
CREATE TABLE WOUT AS
SELECT A.ID,B.ID,C.ID
FROM WA AS A
JOIN WB AS B ON B.AID=A.ID
JOIN WC AS C ON C.BID=B.ID AND C.AID=A.ID AND C.K=B.K;
```

The same lane now executes direct three-source aggregation:

```sql
SELECT COUNT(*),SUM(C.ID),AVG(B.ID),MIN(A.ID),MAX(C.ID)
FROM WA AS A
JOIN WB AS B ON B.AID=A.ID
JOIN WC AS C ON C.BID=B.ID AND C.AID=A.ID AND C.K=B.K
WHERE C.STATE=A.STATE;

SELECT C.STATE,COUNT(*),SUM(C.ID),AVG(B.ID),MIN(A.ID),MAX(C.ID)
FROM WA AS A
JOIN WB AS B ON B.AID=A.ID
JOIN WC AS C ON C.BID=B.ID AND C.AID=A.ID AND C.K=B.K
WHERE C.STATE=A.STATE
GROUP BY C.STATE;

SELECT SUM(C.V),AVG(C.V),MIN(C.V),MAX(C.V),SUM(C.F),AVG(C.F)
FROM WA AS A
JOIN WB AS B ON B.AID=A.ID
JOIN WC AS C ON C.BID=B.ID AND C.AID=A.ID AND C.K=B.K
WHERE C.STATE=A.STATE;
```

The ungrouped integer row is `(2,300,15,1,200)`. Groups appear in first-triple
order as `WS.ON` then `WS.OFF`. The last query verifies raw Q8.8 values
`3.0/1.5/1.0/2.0` and BASIC FLOAT `4.0/2.0`.
The lane also rejects a projected nongroup key and `SUM(CHAR)` with focused
errors.

The current wide lane additionally executes these result-shaping and streaming
queries against tables `A`, `B`, and `C`:

```sql
SELECT A.ID,B.ID,C.ID
FROM A JOIN B ON B.AID=A.ID JOIN C ON C.BID=B.ID
ORDER BY C.ID DESC,B.ID;

SELECT DISTINCT A.ID,A.ID,A.ID
FROM A JOIN B ON B.AID=A.ID JOIN C ON C.BID=B.ID
ORDER BY A.ID DESC;

SELECT DISTINCT A.ID,A.ID,A.ID
FROM A JOIN B ON B.AID=A.ID JOIN C ON C.BID=B.ID
ORDER BY 1 DESC LIMIT 1 OFFSET 1;

SELECT C.STATE,COUNT(*),SUM(C.ID)
FROM A JOIN B ON B.AID=A.ID
JOIN C ON C.BID=B.ID AND C.AID=A.ID AND C.K=B.K
WHERE C.STATE=A.STATE
GROUP BY C.STATE ORDER BY C.STATE;

SELECT C.STATE,COUNT(*),SUM(C.ID)
FROM A JOIN B ON B.AID=A.ID
JOIN C ON C.BID=B.ID AND C.AID=A.ID AND C.K=B.K
WHERE C.STATE=A.STATE
GROUP BY C.STATE ORDER BY 3 DESC LIMIT 1 OFFSET 1;

SELECT DISTINCT COUNT(*)
FROM A JOIN B ON B.AID=A.ID
JOIN C ON C.BID=B.ID AND C.AID=A.ID AND C.K=B.K
WHERE C.STATE=A.STATE
GROUP BY C.STATE ORDER BY 1;

SELECT A.ID,B.ID,C.T
FROM A JOIN B ON B.AID=A.ID
JOIN C ON C.BID=B.ID AND C.AID=A.ID AND C.K=B.K
WHERE C.STATE=A.STATE;

SELECT A.ID,B.ID,C.ID
FROM A LEFT JOIN B ON B.AID=A.ID
LEFT JOIN C ON C.BID=B.ID AND C.K=B.K
ORDER BY A.ID,B.ID,C.ID;
```

These verify descending and ordinal keys, exact raw and grouped DISTINCT,
aggregate-key ordering, pagination, streamed third-source TEXT reads, and
ordered null extension at both LEFT edges. A dedicated fourteenth target adds
fixed scalar projection and shaping:

```sql
SELECT LENGTH(C.K),SUBSTR(C.K,2,1),A.K||C.K,CONCAT('Q',B.K)
FROM A JOIN B ON B.AID=A.ID
JOIN C ON C.BID=B.ID
WHERE C.ID=100;

SELECT LENGTH(C.K),C.ID
FROM A JOIN B ON B.AID=A.ID
JOIN C ON C.BID=B.ID
WHERE C.ID<400
ORDER BY 1 DESC,C.ID;

SELECT DISTINCT A.K||C.K
FROM A JOIN B ON B.AID=A.ID
JOIN C ON C.BID=B.ID
WHERE C.ID<400
ORDER BY 1;

SELECT DISTINCT SUBSTR(C.K,2,1)
FROM A JOIN B ON B.AID=A.ID
JOIN C ON C.BID=B.ID
WHERE C.ID<400
ORDER BY 1 DESC LIMIT 1 OFFSET 1;
```

These verify scalar results sourced from every wide row, literal operands,
case-folded comparison, positive ordinal ordering, exact computed-value
DISTINCT, and pagination without materializing a result set. The same lane now
also executes:

```sql
SELECT C.T,C.ID
FROM A JOIN B ON B.AID=A.ID JOIN C ON C.BID=B.ID
WHERE C.ID<400 ORDER BY C.T DESC,C.ID;

SELECT DISTINCT C.T
FROM A JOIN B ON B.AID=A.ID JOIN C ON C.BID=B.ID
WHERE C.ID<400 ORDER BY 1;

SELECT DISTINCT C.RAW
FROM A JOIN B ON B.AID=A.ID JOIN C ON C.BID=B.ID
WHERE C.ID<400 ORDER BY 1 DESC;

SELECT C.ID
FROM A JOIN B ON B.AID=A.ID JOIN C ON C.BID=B.ID
WHERE A.T LIKE 'OUT%' AND B.RAW>=X'10' AND C.T LIKE 'AL%';
```

These prove case-insensitive logical TEXT equality, binary BLOB ordering,
duplicate handles with equal payloads, stable secondary keys, and streamed
literal predicates sourced from every wide row. The same compiled client now
tests streamed TEXT scalar projection and shaping:

```sql
SELECT LENGTH(C.T),SUBSTR(C.T,2,3),A.T||C.K,CONCAT(B.K,C.T)
FROM A JOIN B ON B.AID=A.ID JOIN C ON C.BID=B.ID
WHERE C.ID=100;

SELECT LENGTH(C.T),C.ID
FROM A JOIN B ON B.AID=A.ID JOIN C ON C.BID=B.ID
WHERE C.ID<400 ORDER BY 1,C.ID;

SELECT SUBSTR(C.T,2,3),C.ID
FROM A JOIN B ON B.AID=A.ID JOIN C ON C.BID=B.ID
WHERE C.ID<400 ORDER BY 1 DESC,C.ID;

SELECT DISTINCT A.T||C.T
FROM A JOIN B ON B.AID=A.ID JOIN C ON C.BID=B.ID
WHERE C.ID<400 ORDER BY 1;
```

For `C.ID=100`, the projection returns I32 `5`, TEXT `LPH`, TEXT
`OUTER-ONEBY`, and TEXT `AXALPHA`. Length ordering yields IDs
`200,100,300`; substring ordering yields `100,300,200`; and folded DISTINCT
collapses `OUTER-ONEALPHA` with `OUTER-ONEalpha`, leaving `OTHERBETA` and
`OUTER-ONEALPHA`.

## Independent wide source indexes

The same target creates one single-column and two compound indexes:

```sql
CREATE INDEX IA ON A(ID);
CREATE INDEX IB ON B(AID,ID);
CREATE INDEX IC ON C(BID,ID);
```

It then drives all three nested-loop levels explicitly:

```sql
SELECT A.ID,B.ID,C.ID
FROM A USING INDEX ia
JOIN B USING INDEX IB ON B.AID=A.ID
JOIN C USING INDEX IC ON C.BID=B.ID;

SELECT A.ID,COUNT(*),SUM(C.ID)
FROM A USING INDEX IA
JOIN B USING INDEX IB ON B.AID=A.ID
JOIN C USING INDEX IC ON C.BID=B.ID
GROUP BY A.ID ORDER BY 3 DESC;
```

The first query checks case-insensitive lookup, all three independent iterator
restarts, and compound leaf traversal. The second forces repeated indexed
group/aggregate/ORDER rescans and returns `(1,2,400)` then `(2,1,200)`.
Mixed masks are exercised by raw TEXT/BLOB ORDER/DISTINCT and streamed TEXT
scalar queries that hint only outer, only middle/inner, or only the third
source. Missing `NOPE` returns `RSQL_ERR_NOT_FOUND`; naming C's `IC` for B
returns `RSQL_ERR_TYPE_MISMATCH`. A single-table `USING INDEX IA` control proves
that the wide raw stream reproduces the existing engine leaf order. Explicit
`ORDER BY`, not physical leaf order, remains the semantic ordering mechanism.

## Direct three-source CTAS

The fixed-width materializer retains the triple identity while it builds each
destination row:

```sql
CREATE TABLE WOUT AS
SELECT A.ID,B.ID,C.ID
FROM A JOIN B ON B.AID=A.ID
JOIN C ON C.BID=B.ID;

SELECT C1,C2,C3 FROM WOUT ORDER BY C3;
```

Variable and scalar values are copied into independent destination handles and
retain explicit source-local access paths and semantic ordering:

```sql
CREATE TABLE WTEXT AS
SELECT A.ID,C.T,A.T||C.T,LENGTH(C.T)
FROM A USING INDEX IA
JOIN B USING INDEX IB ON B.AID=A.ID
JOIN C USING INDEX IC ON C.BID=B.ID
WHERE C.ID<400
ORDER BY C.ID;

SELECT * FROM WTEXT;
```

The verified rows are `(1,'ALPHA','OUTER-ONEALPHA',5)`,
`(2,'BETA','OTHERBETA',4)`, and `(1,'alpha','OUTER-ONEalpha',5)`. The length
column is physically I32.

Grouped wide output is also materializable:

```sql
CREATE TABLE WAGG AS
SELECT A.ID,COUNT(*),SUM(C.ID)
FROM A USING INDEX IA
JOIN B USING INDEX IB ON B.AID=A.ID
JOIN C USING INDEX IC ON C.BID=B.ID
GROUP BY A.ID ORDER BY A.ID;

SELECT * FROM WAGG ORDER BY C1;
```

This returns `(1,2,400)` and `(2,1,200)`, proving that grouping and aggregates
are evaluated by the wide producer before bounded destination staging.

## Independently indexed two-source joins

The ordinary two-source scan path now consumes one validated leaf iterator per
source while retaining scalar projection, LIKE, semantic ORDER BY, and joined
predicate behavior:

```sql
SELECT A.T||'!',B.ID
FROM A USING INDEX IA
JOIN B USING INDEX IB ON B.AID=A.ID
WHERE A.T LIKE 'OUT%'
ORDER BY 2 DESC;
```

Companion negative cases name a nonexistent index and an index owned by the
wrong table. They return `RSQL_ERR_NOT_FOUND` and `RSQL_ERR_TYPE_MISMATCH`
respectively; neither silently falls back to a heap scan.

## Scalar expressions in grouped aggregate results

The ordinary producer combines packed literal metadata, grouped keys, scalar
evaluation, and an aggregate in one cursor:

```sql
SELECT LENGTH(K),SUBSTR(K,1,1),K||'!',COUNT(*)
FROM D
GROUP BY K;
```

For `D = ('BY'),('BY'),('Z')`, the rows are
`(2,'B','BY!',2)` and `(1,'Z','Z!',1)`. The same test deliberately combines a
literal-bearing scalar with GROUP BY so the shared descending parser pool is
exercised.

Two-source and direct three-source aggregate producers exercise source-to-
source concatenation:

```sql
SELECT LENGTH(X.K),X.K||Y.K,COUNT(*)
FROM D AS X CROSS JOIN E AS Y
WHERE X.K='BY'
GROUP BY X.K,Y.K;

SELECT LENGTH(A0.K),A0.K||Z.K,COUNT(*)
FROM D AS A0
JOIN E AS Y ON Y.K='AX'
JOIN F AS Z ON Z.BID=Y.ID
GROUP BY A0.K,Z.K;
```

The first returns `BYAX/4` and `BYLM/2`; the second returns `BYBY/4` and
`ZBY/2`. An ungrouped literal is also valid:

```sql
SELECT 'G',COUNT(*) FROM D;
```

It returns `('G',3)`. In contrast,
`SELECT LENGTH(K),COUNT(*) FROM D` is rejected because `K` is neither grouped
nor aggregated.

The ordinary grouped comparator orders and deduplicates computed scalar
values rather than their source columns:

```sql
SELECT K||'!',COUNT(*) FROM D GROUP BY K ORDER BY 1 DESC;
SELECT DISTINCT 'G' FROM D GROUP BY K;
```

The first returns `('Z!',1)` then `('BY!',2)`. The second sees two physical
groups but emits one logical row, `('G')`. Direct three-source aggregate replay
also orders a composed projection:

```sql
SELECT LENGTH(A0.K),A0.K||Z.K,COUNT(*)
FROM D AS A0
JOIN E AS Y ON Y.K='AX'
JOIN F AS Z ON Z.BID=Y.ID
GROUP BY A0.K,Z.K
ORDER BY 2 DESC;
```

It returns `('ZBY')` before `('BYBY')`. Two-source joined pair replay is tested
with a source-to-source concatenation whose second operand used to collide
with aggregate ORDER scratch:

```sql
SELECT X.K||Y.K,COUNT(*)
FROM D AS X CROSS JOIN E AS Y
WHERE X.K='BY'
GROUP BY X.K,Y.K
ORDER BY 1 DESC;
```

It returns `('BYLM',2)` then `('BYAX',4)`. Exact DISTINCT over multiple joined
groups is independently checked by:

```sql
SELECT DISTINCT LENGTH(X.K)
FROM D AS X CROSS JOIN E AS Y
WHERE X.K='BY'
GROUP BY X.K,Y.K;
```

Both groups evaluate to `2`, so exactly one row is emitted. Correlated
aggregate scalar replay is covered for both shaping operations:

```sql
SELECT DISTINCT 'G'
FROM D AS X
WHERE EXISTS(SELECT 1 FROM F AS Y WHERE Y.K=X.K)
GROUP BY X.K;

SELECT X.K||'!',COUNT(*)
FROM D AS X
WHERE EXISTS(SELECT 1 FROM F AS Y WHERE Y.K=X.K)
GROUP BY X.K
ORDER BY 1 DESC;
```

The DISTINCT form emits one `G` across the qualifying `BY` and `Z` groups;
the ordered form emits `('Z!',1)` then `('BY!',2)`.

Finally, grouped scalar output is materialized and read back through CTAS:

```sql
CREATE TEMP TABLE GS AS
SELECT LENGTH(K),K||K,COUNT(*) FROM D GROUP BY K;

SELECT * FROM GS ORDER BY C1 DESC;
```

The destination derives `C2` as fixed `CHAR(6)`, so its public table read
contains `BYBY` or `ZZ` followed by physical trailing spaces. This distinguishes
logical scalar cursor length from materialized fixed-width CHAR semantics.

## Permanent real-world sales benchmark

The permanent benchmark database contains 2,054 rows across five readable
tables. It deliberately bounds the hot query to 128 sales while retaining a
1,920-row archive, so normal Peddle/VICE suites remain finishable.

| Table | Rows | Row width | Logical row bytes | REU row pages | Bytes incl. descriptor |
|---|---:|---:|---:|---:|---:|
| `SALES_ORDERS` | 128 | 92 | 11,776 | 64 | 16,640 |
| `ORDER_ARCHIVE` | 1,920 | 83 | 159,360 | 960 | 246,016 |
| `CUSTOMERS` | 2 | 85 | 170 | 1 | 512 |
| `PRODUCTS` | 2 | 20 | 40 | 1 | 512 |
| `DISCOUNT_RULES` | 2 | 7 | 14 | 1 | 512 |

`SALES_ORDERS.DETAILS`, `ORDER_ARCHIVE.DETAILS`, and `CUSTOMERS.NAME` are
physical `CHAR(80)` columns. Thus 2,048 rows carry an 80-character value.

The most demanding query is:

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

Every explicit join key is indexed. `ORDER_BUYER_PROD` contains
`(CUSTOMER_ID, PRODUCT_ID)`, `CUSTOMER_ID_REGION` contains
`(CUSTOMER_ID, REGION)`, and `PRODUCT_ID_CATEGORY` contains
`(PRODUCT_ID, CATEGORY_ID)`. The query asserts exactly:

| Region | Category | Count | Sum | Average items | Minimum | Maximum |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 16 | 28,000 | 3 | 1,100 | 2,300 |
| 2 | 1 | 17 | 30,000 | 3 | 1,200 | 2,400 |

Correlated EXISTS is independently exercised without introducing another
join:

```sql
SELECT O.ORDER_ID, O.CUSTOMER_ID, O.ORDER_TOTAL
FROM SALES_ORDERS AS O
WHERE O.ORDER_TOTAL >= 900
  AND EXISTS (
    SELECT 1
    FROM DISCOUNT_RULES AS R
    WHERE R.CUSTOMER_ID = O.CUSTOMER_ID
      AND O.ORDER_TOTAL >= R.MIN_TOTAL
  )
LIMIT 1;
```

It asserts `(9, 1, 1300)`. Peddle reports 504,420,468 instructions for the
grouped join and 1,294,796 for EXISTS. VICE reports query-only device times of
115,010 and 305 jiffies. Those are 2,300.2 and 6.1 seconds at 50Hz PAL, or
1,916.833 and 5.083 seconds at 60Hz NTSC. Timing
excludes all D81 loading, schema creation, fixture loading, and index creation.

| Index | Entries | Key width | Leaf pages | Bytes incl. descriptor |
|---|---:|---:|---:|---:|
| `ORDER_BUYER_PROD` | 128 | 5 | 5 | 1,536 |
| `CUSTOMER_ID_REGION` | 2 | 5 | 1 | 512 |
| `PRODUCT_ID_CATEGORY` | 2 | 4 | 1 | 512 |

The captured database owns 1,043 REU pages / 267,008 bytes: all table and
index pages above plus the catalog root. The VICE whole-REU export is
16,777,216 bytes; the D81 bootstrap image is 819,200 bytes.

## Opt-in staged TEMP-table benchmark

The alternative benchmark keeps the original test and materializes the same
hot analytical workload in explicit, timed stages:

```sql
CREATE TEMP TABLE FILTERED_ORDERS AS
SELECT ORDER_ID,CUSTOMER_ID,PRODUCT_ID,ORDER_TOTAL,ITEM_COUNT
FROM SALES_ORDERS
WHERE ORDER_TOTAL>=1000 AND ITEM_COUNT>=2 AND DETAILS LIKE 'A%';

CREATE INDEX FILTERED_BUYER_PRODUCT ON FILTERED_ORDERS(C2,C3);

CREATE TEMP TABLE CUSTOMER_SALES AS
SELECT O.C1,O.C3,O.C4,O.C5,C.REGION
FROM FILTERED_ORDERS AS O USING INDEX FILTERED_BUYER_PRODUCT
JOIN CUSTOMERS AS C USING INDEX CUSTOMER_ID_REGION
  ON C.CUSTOMER_ID=O.C2
WHERE C.ACTIVE=TRUE;

CREATE INDEX CUSTOMER_PRODUCT_REGION ON CUSTOMER_SALES(C2,C5);

CREATE TEMP TABLE READY_SALES AS
SELECT S.C3,S.C4,S.C5,P.CATEGORY_ID
FROM CUSTOMER_SALES AS S USING INDEX CUSTOMER_PRODUCT_REGION
JOIN PRODUCTS AS P USING INDEX PRODUCT_ID_CATEGORY
  ON P.PRODUCT_ID=S.C2
WHERE P.ACTIVE=TRUE;

CREATE INDEX READY_REGION_CATEGORY ON READY_SALES(C3,C4);

SELECT C3,C4,COUNT(*),SUM(C1),AVG(C2),MIN(C1),MAX(C1)
FROM READY_SALES USING INDEX READY_REGION_CATEGORY
GROUP BY C3,C4 ORDER BY C3,C4;
```

CTAS output names are `C1..Cn`; the test source documents their business
meaning at each boundary. All three TEMP tables contain 33 rows. VICE measures
21,294 jiffies for the full seven-step pipeline and 6,015 jiffies for a second
execution of only the final query: 425.88s and 120.30s PAL, or 354.90s and
100.25s NTSC. The Peddle counts are 81,867,885 and 26,600,681 instructions.

The resulting database owns 90 pages / 23,040 bytes. Its five indexes have 2,
2, 33, 33, and 33 entries. The opt-in commands are
`make emu-pipeline-benchmark-test` and
`make vice-pipeline-benchmark-test`; ordinary `make test` and `make vice-test`
do not run either long benchmark.
