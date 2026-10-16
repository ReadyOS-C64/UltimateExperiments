# Native SETUP configuration codec

`tools/setup/install_config.c` is actual cc65 C for the native installer and launcher. `make setup-config-tests` compiles it to 6510 code and runs Zig assertions through the existing Peddle bridge. It is an optional component, separate from the emulator build. The generated test PRG is a callable fixture, not a user-facing SETUP or START program.

The configuration is a 576-byte binary record with explicitly defined byte offsets and little-endian integers. C structures are not serialized. Paths contain canonical absolute host ASCII with zero padding, including the terminator; each field is 128 bytes. Uppercase PETSCII is not silently treated as host ASCII. The frontend must make the necessary character conversion before invoking this codec.

| Offset | Length | Meaning |
| --- | --- | --- |
| 0 | 4 | ASCII `D64C` |
| 4 | 1 | Format version 1 |
| 5 | 2 | Record length, 576 |
| 7 | 1 | Reserved zero |
| 8 | 128 | Installation home, `/` permitted |
| 136 | 128 | A image filename, required |
| 264 | 128 | B image filename, or all zero when absent |
| 392 | 128 | C image filename, or all zero when absent |
| 520 | 4 | A/B profile zero, C profile 0 for 2 MiB or 1 for 20 MiB, reserved zero |
| 524 | 1 | Read-only bits A=1, B=2, C=4; only present drives |
| 525 | 1 | Present bits A=1, B=2, C=4; A required |
| 526 | 2 | Reserved zero |
| 528 | 4 | A image CRC32 |
| 532 | 4 | B image CRC32, zero when B absent |
| 536 | 2 | Bootstrap ABI 1 |
| 538 | 4 | Explicit configured REU capacity, 4–16 MiB in 64 KiB banks |
| 542 | 30 | Reserved zero |
| 572 | 4 | CRC32 of bytes 0–571, reflected polynomial EDB88320, initial/final XOR FFFFFFFF |

The configured capacity supports larger memory budgets. It is not capacity detection: frontend, allocator and transport must still establish a safe hardware configuration and check each transfer against owned ranges. No larger cache or new runtime arena is activated by the codec itself.

The globals and callable entry points are declared in `tools/setup/install_config.h`. `d64_config_make` validates semantic fields from the input, creates canonical header/reserved/checksum bytes, and publishes the output only after success. `d64_config_validate` checks header, reserved bytes, CRC and fields before publishing. Both return 1 on success or 0 on failure; the input and previous output survive a failure. Error codes are 1 for header/bootstrap ABI, 2 for CRC, 3 for path, 4 for flags, 5 for disk profile and 6 for capacity.

`d64_path_join` combines an absolute home and relative pathname; `d64_path_parent` navigates toward `/`. Both enforce a 127-character total bound and reject empty components, dot/dot-dot components, trailing slashes, backslashes, colons, control characters and non-ASCII bytes. FatFs-forbidden filename characters (quote, asterisk, angle brackets, question mark and pipe) and component endings with spaces/dots are also rejected. Internal spaces, parentheses, leading spaces and embedded consecutive dots remain valid. This matches the pinned Ultimate FatFs `create_name` behavior, which strips trailing spaces/dots and rejects its forbidden character set. A drive filename cannot be `/`. A failed operation preserves previous output and both inputs.

Actual target tests compare serialization/CRC against an independent host oracle, reject a changed bit at every one of 576 record bytes, reject correctly re-signed malformed fields, cover absent drives and capacity bounds, and exercise navigation/path length failures. Each call has a CPU-cycle budget and verifies software-stack restoration, hardware-stack bounds and all target writes. Passing these tests establishes the codec behavior only; file publication, safe REU handoff, bootstrap DMA/NMI behavior and the end-user installer remain separate integration work.
