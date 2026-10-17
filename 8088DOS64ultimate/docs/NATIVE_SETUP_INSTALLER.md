# Native SETUP build and current scope

`make setup-installer` builds the native C/6502 installer. This target does not contact the Ultimate or run the long integration tests. It requires Python 3, cc65, ca65, ld65 and cc65's `none.lib`. Tool overrides are `DOS64_PYTHON`, `DOS64_CC65`, `DOS64_CA65`, `DOS64_LD65` and `DOS64_CC65_LIB`.

The outputs are `build/setup-installer/SETUP.PRG`, `SETUP.FAT`, `SETUP.PUB`, labels, map and `RESULT.json`. Each invocation stages and pins the actual compiler inputs in a fresh work directory, builds the phase metadata from measured bytes, checks memory bounds, and verifies the inputs again before publishing the bundle. A passed result is written last. Retain the whole bundle from one successful build.

The current linked PRG is 40,868 bytes, SHA256 `4da35ecc7b2b110de63fdbcca48b4b78cf8470875acdd655acd45da99e4166a5`. It reproduces the source-closed full-coordinator model target, including phase bytes, metadata and all symbol addresses. This is a development build: fresh-install model acceptance is established; physical installer acceptance, early bootstrap error presentation and reconfiguration are still pending.

## Installation flow implemented in the model

Prepare a home folder containing this build's `SETUP.PRG`, `SETUP.FAT` and `SETUP.PUB`, plus `START.TPL` and `START.REL` from `make start-template`. `START.TPL` is an unchanged copy of the disabled `build/start/START.PRG`; `START.REL` is its D64S descriptor. They must match. The generated launcher also needs the matching emulator release's `DOS64.PRG`, `DOS64.REL` and native overlay files in that home; SETUP does not install those release files itself. DOS images are supplied separately by the user and may be selected from another folder.

Load `SETUP.PRG` and run its BASIC entry. The native browser asks for the home folder, the three distinct DOS disk images, an optional existing C image to import, and a 2 or 20 MiB destination C drive. Cursor keys select entries, Return opens folders or selects files, Backspace goes to the parent, F3/F5 change pages, and left/right scroll long paths. F1 chooses the home folder or skips an existing C import. Run/Stop cancels. Review the selected paths before confirming.

The installer loads and independently reads back all five source files, retires the selection UI, and builds C and B before deriving A. It writes and verifies files in this order:

1. `C.IMG`: dynamically created raw hard disk, with the DOS files imported natively.
2. `B.IMG`: a separate working floppy.
3. `A.IMG`: boot floppy with startup files selecting C and its DOS path.
4. `START.PRG`: the verified launcher template with the selected home embedded.
5. `DOS64.CFG`: configuration published only from the verified output facts.

No dummy D81, emulated FORMAT/COPY step or distributed large empty HD image is needed. Sources remain unchanged. Current output creation refuses existing names; it does not overwrite an existing installation. A failed install can leave earlier verified outputs or a partial new file, so the completion caption is required before considering the model installation complete. Reconfiguration and a user recovery workflow remain unfinished.

The complete SYS-to-publication model tests exercise a fresh 2 MiB installation plus C, START and CFG collisions. They check every saved byte, FAT trees, CRCs, output order, source preservation, private completion state and known file closure. Eight direct Zig/Peddle groups exercise the coordinator, relocation lifetime, initial image checks and terminal file-ownership reporting. Independent cleanup tests also cover damaged readback, partial DMA, cancellation, failed CLOSE, stopped clocks, bounded cleanup and foreign-source isolation. Separate FAT-worker tests cover new and imported 20 MiB C images. These results do not establish physical throughput or hardware acceptance.

## Emulator preferences

The selected home is also the intended location of optional `DOS64.INI`. Its native parser foundation is tested, but the file reader, startup overlay, REU settings record and emulator consumer are not connected yet. The current launcher ignores INI. Keep the binary configuration's ABI1 reserved bytes zero. See [configuration and options contract](NATIVE_SETUP_CONFIG.md).

After verified phase preparation, a terminal failure displays its first error code, warns that new files may remain, and reports either known file closure or unconfirmed cleanup. It renders once and performs no file operations or retries. Known closure advises reloading SETUP and choosing a new folder; unknown cleanup advises keeping the screen and avoiding retry. Failures before verified phase preparation cannot use this renderer and still have limited presentation. The initial CRC is checked after bootstrap relocation; it does not authenticate a malformed bootstrap or relocation descriptor before use.

The remaining installation work includes early bootstrap error screens, safe reconfiguration, editable emulator preferences, floppy Save/Discard/Swap with C online, and fresh physical SETUP → START → DOS testing. Model success does not transfer physical acceptance from an older emulator build.
