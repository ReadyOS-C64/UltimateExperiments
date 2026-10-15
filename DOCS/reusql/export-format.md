# Selected-Query Export Format

`rsql_export_d81()` streams any supported SELECT result to a CBM sequential
file. D81/1581 is the standard target because it is the largest conventional
Commodore disk used by this project, but export is intentionally bounded by
free disk space. It is not a whole-database persistence format; databases too
large for removable media use raw whole-REU capture through VICE.

Version 1 is a compact typed row stream. All lengths and numeric payloads are
little-endian. The file begins with:

| Bytes | Meaning |
|---|---|
| `52 53 51 58` | Numeric ASCII signature `RSQLX` |
| `01` | Export format version |
| `cc` | Selected column count |

Each row begins with marker `52`. Every selected field then has a four-byte
header `{type_tag, is_null, length_lo, length_hi}` followed by exactly `length`
payload bytes unless `is_null` is nonzero. Fixed values retain their public
cursor representation. TEXT and BLOB values are read in 64-byte chunks, so no
variable result is materialized in C64 RAM. String payloads are raw C64 bytes
(normally PETSCII); BLOB payloads are unchanged binary bytes.

The stream ends with marker `FF` and a four-byte row count. A short KERNAL
write, full disk, open failure, query error, or value-read error aborts the
adapter and returns the relevant engine error or `RSQL_ERR_IO`; the cursor and
file are closed on every path. A partial sequential file can therefore exist
after an error and must not be treated as complete without the footer.

The adapter is client-side source in `src/export_d81.c`, not a fixed-address
ABI entry. This keeps disk naming and device policy out of the resident engine
and leaves a future C64 Ultimate UCI adapter possible without implementing or
testing UCI now.
