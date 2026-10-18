# Native Ultimate file commands

> Development note: see [current status](STATUS.md), [build instructions](BUILD.md) and [installation](INSTALL.md) for present qualification. Historical measurements below apply to their stated slice, not every current build.


The linked FILE overlay implements bounded IDENTIFY, OPEN, READ, WRITE, SEEK, CLOSE and CHANGE_DIR over the generic UCI owner. Resident `dos64_overlay_files_init/start/poll` wrappers acquire the real payload on each call; asynchronous state and UCI buffers remain resident across TEXT switches. Caller supplies monotonic elapsed `files_now`; no delay or poll-count clock is invented.

Primary protocol is GideonZ/1541ultimate v3.14, commit `830665cd9b41bc34b868f5c1a1179c5baa4989af`, independently inspected `software/filemanager/dos.cc` and file-system definitions. Paths are raw wire bytes with one final NUL. OPEN modes allow read, write, both or create-new, without truncate/overwrite. READ/WRITE counts are 1–512, SEEK is absolute little-endian 32-bit. One file owner/one response block is supported; MORE is rejected with recovery. Unknown handles permit CLOSE only. Exact status/response lengths are validated.

Firmware limitations are reflected in results: successful READ uses empty status; its read-error branch can leave status stale, so higher-level media integrity needs length/hash checks. WRITE discards actual transferred count; accepted status leaves `count_known=0` and uncertainty set. CLOSE discards the file-system close result and cannot establish persistence. A higher layer must reopen/read/compare before claiming saved data. Exact `84,NO FILE TO CLOSE` establishes a known closed state while still reporting operation failure.

Thirteen actual-assembly file tests cover exact command bytes, binary/EOF/short data, 512-byte chunks, seek beyond 16 MiB, elapsed wrap/abort/recovery, statuses/order/targets/path bounds and uncertain handles. Combined overlay tests interleave rendering between polls while preserving all file state. Code is 1,088 FILECODE bytes; state is 25 DEVICESTATE bytes, with no additional ZP, E000 BSS or bounce buffer. [Overlay contract](OVERLAYS_IMPLEMENTATION.md), evidence (local development record, not distributed).

These are modeled firmware-protocol results. Physical UCI acceptance, whole-floppy import/export, HD caching and verified persistent save remain unfinished; no guest DOS file/FAT/INT 21h replacement is implemented.
