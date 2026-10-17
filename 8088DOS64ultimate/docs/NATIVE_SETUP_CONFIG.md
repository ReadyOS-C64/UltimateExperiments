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

The options-enabled launcher reads `DOS64.INI` from its embedded installation home on every cold launch, parses it before DOS boots, and passes validated settings through REU. The emulator copies the initial display setting into resident state. Editing INI takes effect on the next launch without reinstalling or regenerating START. Surviving REU contents never substitute for rereading the file.

For example, a launcher configured for `/usb1/DOS64` reads `/usb1/DOS64/DOS64.INI`, regardless of the Ultimate browser's current folder. The same home locates `DOS64.CFG`, `DOS64.PRG` and `START.INO`; the disk-image paths in CFG can point elsewhere. Future options should follow this prelaunch parsing and validated binary handoff pattern, with frequently used values copied into resident state. Only the initial column setting is implemented today.

Build the complete matched release with `make start-ini-bundle`; use all five files from the bundle named by `build/start-ini-bundle/RESULT.json`. The default `make start-template` remains the legacy launcher, which ignores INI. Do not mix the two launchers or their release assets. See [installation](NATIVE_SETUP_INSTALLER.md) and [the options handoff](NATIVE_START_HANDOFF.md#options-enabled-launcher).

Binary `DOS64.CFG` and its ABI1 reserved-zero rules stay intact. INI currently supports the initial 40/80-column display setting only; it does not enable timing or compiled-code experiments. A native SETUP preferences editor is still pending.

Missing optional INI selects 80 columns. Only the exact qualified file-not-found response with successful recovery and known closure permits that default; inaccessible paths and other I/O errors stop startup. A present malformed or unsupported setting also stops startup. Reads have bounded lengths, exact EOF and known closure; cancellation retains the first failure. No INI file access or text parsing occurs in the emulator execution loop.

The options launcher verifies and installs the 6,798-byte `START.INO` prelaunch overlay at $6000. That code is retired by the final emulator payload DMA; no C frame survives that handoff. This fits without enlarging the 18,432-byte START template.

A separate 32-byte D64O record at REU $3FF500 carries the validated setting, checksum and current CFG/main binding. START invalidates readiness before work, verifies the body by readback, and publishes readiness last after closing files. The main validates and consumes readiness, proves consumption by independent readback, then applies BIOS text mode 1 (40 columns) or 3 (80 columns). Legacy entry ignores this record and starts in mode 3. D64R and D64C ABI1 are unchanged; options-enabled START requires the matching D64L version 2 descriptor.

The parser accepts `[emulator]`, optional `schema=1`, and `initial_columns=40|80` with default 80. Names are case insensitive; ASCII spaces/tabs, CR/LF and `;` or `#` comments are supported. Files are limited to 1,024 bytes and lines to 128 bytes, read in chunks of at most 64 bytes. Unknown sections/keys, duplicate keys, unsupported values and non-ASCII input are rejected.

Place this ordinary ASCII file alongside `START.PRG` and `DOS64.CFG`:

```ini
[emulator]
schema=1
initial_columns=40
```

The initial setting does not prevent DOS `MODE CO40` or `MODE CO80` from changing modes later. Actual 6510/Peddle tests cover parser/I/O, stale and corrupt records, readback failures, cancellation and both generated START-to-DOS modes. Physical qualification of this new launcher/main pair remains pending.

## Native reconfiguration model proof

The separate native CONFIG development program now runs from its actual BASIC SYS entry through keyboard selection, existing configuration inspection, disk-image checks and creation of a new launch folder. It keeps the original absolute A/B/C image paths and readonly settings, refreshes the floppy checksums, and creates `DOS64.PRG`, `DOS64.REL`, `START.INO`, `START.PRG`, `DOS64.INI`, then `DOS64.CFG` last. Each file uses create-new semantics and full readback; partial files after a failure are not a completed installation. The destination folder must already exist and must differ from the old installation and release-source folders.

The preference is an explicit **new** 40/80 setting, initially 80. CONFIG currently leaves the old INI unread and unchanged. Old and new launchers share the existing images; reverting a launcher does not undo writes to those images. CONFIG runs independently of a running emulator.

Both actual output sets boot genuine DOS 3.3 in Peddle and pass VER and complete paged A:/C:\\DOS listings. The START/CFG/main/overlay/descriptor bytes are identical between modes; only the INI column digit changes. Source-closed evidence is in [the integration receipt](../agentworking/evidence/native-config-generated-dos-root-20261017.json). Public build packaging and physical CONFIG qualification remain pending; this proof does not turn the current SETUP into an options editor.
