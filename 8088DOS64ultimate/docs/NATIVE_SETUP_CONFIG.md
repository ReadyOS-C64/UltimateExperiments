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

## Same-folder emulator options

Accepted user direction, 2026-10-16. START's persistent installation home also locates emulator options. Native startup will read and parse them before DOS boots, then pass validated settings through REU. Preserve the validated home for later native file operations; do not discover or assume a current directory. The isolated native parser foundation now passes 17 Zig/Peddle groups; file I/O, the startup overlay, settings handoff and consumer remain pending.

Keep binary `DOS64.CFG` and its ABI1 reserved-zero rules intact. Plan a separate human-editable `DOS64.INI` for supported emulator options. Changing a display preference should not invalidate disk identities or require regenerating START. SETUP should expose the same settings. Candidate options include initial 40/80-column presentation and supported display preferences; exact names and behavior require implementation. Settings must not implicitly enable unqualified timing/compiled-code profiles or change the original 8088 compatibility target.

Resolve INI from the embedded canonical home and parse once at native startup, with bounded file/line lengths, schema/value checks, exact EOF and known file closure. Missing optional INI selects documented defaults; present malformed or unsupported settings produce a useful startup error. Preserve the first failure and support Run/Stop cleanup. Edits take effect on the next launch without reinstalling. No per-instruction text parsing or configuration file access belongs in the emulator execution loop.

Public START has one byte of headroom below $5000. Prefer a native prelaunch parser overlay with an explicit return/lifetime contract, or another measured startup arrangement; do not assume the parser fits START. SETUP may share parsing code.

Publish a compact binary options record in explicitly allocated REU space, with magic, schema, length, checksum and current release/handoff binding. Invalidate readiness before work and publish last after successful parsing and closed files. The consumer validates values and launch binding, copies frequent settings into resident state, and consumes one-shot validity before arena reuse. Define address/defaults/ownership/lifetime from the combined memory map. This design reserves no range and changes neither D64R nor D64C ABI1. Releases requiring options need matching producer/consumer support and explicit compatibility rejection by older code.

The qualified private parser accepts `[emulator]`, optional `schema=1`, and `initial_columns=40|80` with default 80. It bounds files to 1,024 bytes, lines to 128 bytes and input chunks to 64 bytes; it checks complete values and rejects unknown or duplicate keys. This parser does not apply settings or prove successful file EOF/closure. Its production integration is still pending.

Acceptance requires actual parser/consumer integration tests for defaults, supported values, malformed/oversize input, unsupported versions, stale/corrupt records, cancellation, arena guards and file closure; then cold START-to-DOS tests and physical Ultimate qualification. The existing public launcher does not yet read INI or consume a settings record.
