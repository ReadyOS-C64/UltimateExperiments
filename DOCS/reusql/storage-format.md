# Storage Format v2

The REU image is a page-based database, not a dump of native C structs. This reference
follows its reserved regions, catalog roots and owned page chains, then explains the
journal and publication boundaries.

All persistent pages are 256 bytes. Multi-byte values are explicitly encoded
little-endian; native C structures are not written as database pages.

## Fixed reservations

- Pages 0-1: checksummed superblock copies with generation and catalog root.
- Pages 2-33: 8KB allocation bitmap, sized for a 16MB REU.
- Pages 34-101: rebuildable 17KB administrative sidecar cache.
- Top 544 pages: eight rebuildable 17KB overlay images.
- All other allocated pages: catalog, table, row, enum, index, and
  variable-value objects.

The allocator opens the newest valid superblock and falls back when either copy is
corrupt. A catalog-root update writes the secondary superblock before the primary.

### Format versions and compatibility

The superblock format is version 2 and persistent catalog/object pages carry storage
version 4. Version 4 reserves pages 34-101 and the eighth 68-page hot overlay slot, so
allocator-owned pages begin at page 102 and stop below the top 544 pages on every
supported REU. This is a deliberate pre-release compatibility break: there is no
in-place v1-to-v2 migration.

Initialization with formatting disabled rejects even checksummed older superblocks as
`RSQL_ERR_CORRUPT_STORAGE`; callers must explicitly create a new image and import
selected data. The checkpoint target constructs and rejects a valid- checksum version-1
pair as a regression test.

## Catalog and tables

The catalog root links table descriptors, enum descriptors, index descriptors, and blob
directory pages. Each table descriptor contains its name, fixed row width, row chain,
row count, and up to eight column descriptors. Every row begins with a null bitmap.

The remaining values are fixed-stride and a row may occupy at most 240 bytes in format
v2.

### Table lifecycle flags

Table descriptor byte 5 contains `TEMPORARY`, `DROPPING`, and `BUILDING` lifecycle bits.
Catalog name lookup ignores `DROPPING` or `BUILDING` descriptors. TEMP cleanup,
interrupted-build cleanup, and explicit `DROP TABLE` advance durable row, blob, and
index links in bounded transactions before freeing each old page, so initialization can
resume an interruption and finally unlink the descriptor.

### Index and enum cleanup flags

Index descriptor byte 5 and enum descriptor byte 39 contain a `DROPPING` bit. Named
lookup and index rebuilds ignore marked descriptors. Index cleanup advances the
descriptor leaf head before each leaf free.

Enum cleanup advances the descriptor's first-member link before each member-page free,
then unlinks the descriptor and decrements the root enum count. The next enum ID remains
monotonic after a drop.

### Column widths and row slots

Physical widths are BOOLEAN/I8/ENUM8 = 1, I16/FIXED8_8/ENUM16 = 2, I32 = 4, I64 = 8,
Commodore FLOAT = 5, CHAR(n) = n, and TEXT/BLOB = a four-byte stable handle.

Row pages contain a four-byte used-slot bitmap and up to 32 fixed-stride rows. Deleted
slots are cleared and reused before another row page is allocated.

## Variable values

TEXT and BLOB directory entries hold a monotonically assigned four-byte handle, kind,
byte length, and first payload page. Payload pages are linked and carry 246 bytes
apiece. Delete marks a directory entry as a tombstone; `rsql_blob_compact` releases its
chain and clears the directory slot.

Handles are never reused.

## Enumerations

Enum descriptors have a stable 16-bit catalog ID and width of one or two bytes. Named
members live in linked member pages. Lookups fold ASCII/PETSCII letters, support
name-to-value and value-to-name, and reject duplicate names or numeric values.

## Indexes

The root's index link points to globally named index descriptors. A descriptor records
its source table, one or more source-column ordinals, encoded compound key width, entry
count, and the head and tail of a doubly linked leaf chain. Only fixed-width columns can
be indexed; TEXT and BLOB are rejected.

Each leaf stores a sorted sequence of encoded key plus physical row ID entries. Keys
contain a NULL marker and the column's fixed physical bytes. Leaves split when full and
remain linked in key order.

ReuSQL64 does not create or persist an execution plan: a query must opt in with `USING
INDEX index_name`, and the row predicate is still evaluated against every returned row
ID.

### Index rebuilds and journal capacity

INSERT, UPDATE, and DELETE rebuild every index belonging to the changed table inside the
same transaction. This correctness-first implementation preserves row/index atomicity
but is bounded by the 16-page before-image journal; a larger rebuild can return
`RSQL_ERR_JOURNAL_FULL` and roll back cleanly.

> **Performance: some advanced queries are very slow right now.**
>
> Joins, correlated subqueries, grouping, sorting and duplicate elimination can walk the same relationships repeatedly. For demanding work, it is often faster to filter/project into TEMP tables, index the useful intermediate columns, and run the next query against that smaller result. The tested seven-step sales pipeline took **425.88 seconds PAL**, compared with **2,300.2 seconds** for the original grouped join—about **5.4× faster**, including its intermediate table and index builds. These are measurements of this fixture, not a guarantee for every query.
>
> [Why this happens and how to stage a query](performance.md).

## Atomicity boundary

Checksums detect torn or corrupt pages. A 16-page REU before-image journal makes CREATE
TABLE, CREATE TYPE, CREATE INDEX, INSERT, UPDATE, and DELETE statement-atomic. On an
injected or real write failure, catalog, allocation, row, blob, enum, and index pages
are restored before control returns.

### CTAS publication is a separate boundary

CTAS can own more than sixteen pages without enlarging or weakening that journal. Table
flag `BUILDING` (`0x04`) is committed with the new descriptor; catalog lookup ignores
the descriptor until publication. Fixed rows commit one at a time.

Each non-NULL TEXT/BLOB handle is first stored as a zero-length directory entry in its
hidden row, after which one payload page and its owner links commit per transaction.
Clearing `BUILDING` is the only publication write. Initialization treats a remaining
BUILDING descriptor like resumable garbage and reclaims its rows, handles, chains, and
descriptor.
