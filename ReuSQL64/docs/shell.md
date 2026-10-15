# Interactive Shell

`build/rsql64_shell.d81` boots the thin ReuSQL64 client shell from device 8.
It initializes the REU database, keeps the engine's eight execution images and
administrative image in their existing caches, and reads one 160-byte logical
line at a time.

Ordinary SQL is entered without a terminator. Mutation statements report the
affected-row count. SELECT streams each row through the public cursor ABI,
prints columns separated by comma and space, and finishes with its row count.
NULL, booleans, signed 8/16/32/64-bit integers, enums, Q8.8 fixed point,
CHAR, and TEXT have readable representations. BLOB prints `<BLOB length>` so
binary control bytes do not reach the screen. FLOAT currently prints its exact
five-byte physical representation as `FLOAT($xxxxxxxxxx)`; decimal FLOAT
formatting is a presentation enhancement, not a query-engine limitation.

The shell accepts all SQL supported by the public API and these aliases:

```text
.HELP
.DATABASE
.TABLES
.SCHEMA table
.INDEXES
.TYPES
.MEMBERS type
.CHECKPOINT
.EXPORT filename SELECT ...
.QUIT
```

The inspection aliases map to `SHOW DATABASE`, `SHOW TABLES`, `SHOW COLUMNS
FROM`, `SHOW INDEXES`, `SHOW TYPES`, and `SHOW MEMBERS FROM`. `.EXPORT` writes
the selected query in version-1 RSQLX framing to a sequential file on the
configured D81 device. It is intentionally for bounded selected data. A full
database can be much larger than a D81 and is saved as an exact raw REU image
by VICE after `.CHECKPOINT`; C64 Ultimate UCI support remains out of scope.

The display callback translates shifted uppercase PETSCII emitted by cc65
string literals into the equivalent unshifted screen characters. This happens
only at CHROUT. SQL strings, CHAR/TEXT values, KERNAL filenames, and RSQLX
payloads retain their original C64 bytes.

The shell is tested as compiled 6510 in Peddle at 512KB and 16MB, including
GETIN editing and captured CHROUT, and by the .NET VICE keyboard automation on
a writable D81. The VICE gate also extracts and byte-compares its export.
