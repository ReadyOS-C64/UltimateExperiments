# Native SETUP build and current scope

> Development note: see [current status](STATUS.md), [build instructions](BUILD.md) and [installation](INSTALL.md) for present qualification. Historical measurements below apply to their stated slice, not every current build.


**Current physical qualification:** fresh native 2 MiB installation and its generated START reach DOS. Native 20 MiB creation fails at WRITE_NEW/UCI03 after 65,536 produced bytes. Use [INSTALL.md](INSTALL.md) for the preview; CONFIG/media/Finish and complete human acceptance remain open. Turbo IDE/save/compile/run/restart works on a separate host-prepared 20 MiB development fixture. This does not qualify the installer. Versioned sizes/hashes below identify historical builds.


The current disk-menu candidate is `make v1-candidate DOS64_V1_CANDIDATE_ARGS="--runtime-media"`: twelve matched SETUP/CONFIG/runtime/cold assets, including startup diagnostics and the tested FAT/PUB/INO failure details. See [current candidate instructions](V1_CANDIDATE.md). This source-built package passes host packaging controls; final physical installation and the remaining file-specific error messages are still open. The nine-file descriptions below apply to the default INI-only profile.

`make v1-candidate` builds SETUP and its two overlays, CONFIG, and the five coupled INI launcher/emulator assets from fresh public sources. It validates their receipts, shared source identities, descriptors and both SETUP's and CONFIG's exact release binding before writing one zip. The archive contains nine native files, a short installation guide, an INI example and checksums; it contains no DOS/vendor images, configured launcher, CFG or blank HD. Its path is recorded in `build/v1-candidate/RESULT.json`.

This is a development candidate, not a completed V1 release. The matched native disk menu, durable floppy/CFG recovery and final physical installer/media/Turbo acceptance remain open. SETUP still expects the program assets already copied into the selected home; candidate packaging supplies them together. The candidate's release-bound SETUP validates all five runtime assets alongside the three DOS inputs before creating output files; a missing or mismatched runtime file names the failed source. Standalone `make setup-installer` retains its prior unbound build. Use a fresh folder, preserve existing installations and supply the three DOS images separately.

`make v1-package-tests` builds the candidate and exercises thirteen host packaging controls around the actual native products: corruption of every native asset, missing INI overlay, unbound SETUP, mismatched SETUP/CONFIG/release or receipt, conflicting source generations, failed components, existing destinations, archive copy drift and first-error/prior-result preservation. These checks add packaging evidence without transferring earlier component model success to physical acceptance.

`make setup-installer-preflight` builds SETUP against `build/start-ini-bundle/RESULT.json` (override `DOS64_SETUP_BUNDLE_RESULT` for another matched release). `make setup-installer-preflight-tests` runs eight actual native/Peddle groups and eleven host controls with deterministic DOS-sized fixtures; it requires no vendor disk images. The bound SETUP is42,627 bytes, SHA256 `7901183a628406fe555e6940a0c568bcea38c05ed1da56e3b5e9c5d1c26d2da8`. Its close/reopen/full-read checks cover missing/corrupt sources before CREATE. This lane establishes dependency validation, not DOS boot or physical installation.


`make setup-installer` builds the native C/6502 installer. This target does not contact the Ultimate or run the long integration tests. It requires Python 3, cc65, ca65, ld65 and cc65's `none.lib`. Tool overrides are `DOS64_PYTHON`, `DOS64_CC65`, `DOS64_CA65`, `DOS64_LD65` and `DOS64_CC65_LIB`.

The outputs are `build/setup-installer/SETUP.PRG`, `SETUP.FAT`, `SETUP.PUB`, labels, map and `RESULT.json`. Each invocation stages and pins the actual compiler inputs in a fresh work directory, builds the phase metadata from measured bytes, checks memory bounds, and verifies the inputs again before publishing the bundle. A passed result is written last. Retain the whole bundle from one successful build.

The current linked PRG is 41,363 bytes, SHA256 `0df4c4cfd24afb940e05054270963bc62a08a2f40daccc3eeb389a1781b91838`. It reproduces the source-closed full-coordinator model target, including phase bytes, metadata and all symbol addresses. This is a development build: fresh-install model acceptance is established; physical installer acceptance, early bootstrap error presentation and reconfiguration are still pending.

For the intended 64 MHz development profile, select **Turbo Control: Manual** and **CPU Speed: 64** in the Ultimate settings before running SETUP or START. These programs currently do not select turbo through `$D031`. A saved speed of64 with register-controlled turbo is therefore insufficient evidence of the executing speed. Manual mode uses the menu setting and prevents software register changes; see the [official turbo controls](https://github.com/GideonZ/1541u-documentation/blob/master/config/turbo_mode.rst). Historical accepted hardware campaigns explicitly set and restore Manual/64; physical timing still requires measurement. The current read-only retention campaign preserves the original mode and is not a speed benchmark.

## Installation flow implemented in the model

Prepare a home folder containing this build's `SETUP.PRG`, `SETUP.FAT` and `SETUP.PUB`, plus `START.TPL` and `START.REL` from `make start-template`. `START.TPL` is an unchanged copy of the disabled `build/start/START.PRG`; `START.REL` is its D64S descriptor. They must match. The generated launcher also needs the matching emulator release's `DOS64.PRG`, `DOS64.REL` and native overlay files in that home; SETUP does not install those release files itself. DOS images are supplied separately by the user and may be selected from another folder.

For editable emulator preferences, use `make start-ini-bundle` instead of `make start-template`. Copy all five files from the bundle named by `build/start-ini-bundle/RESULT.json` into the selected home: `START.TPL`, `START.REL`, `START.INO`, `DOS64.PRG` and `DOS64.REL`. This is a coupled release; keep those files together. SETUP then creates the folder-aware `START.PRG` using that template. Leave the supplied DOS images elsewhere or in this folder as preferred. No INI is required for the default 80-column startup.

Load `SETUP.PRG` and run its BASIC entry. The native browser asks for the home folder, the three distinct DOS disk images, an optional existing C image to import, and a 2 or 20 MiB destination C drive. Cursor keys select entries, Return opens folders or selects files, Backspace goes to the parent, F3/F5 change pages, and left/right scroll long paths. F1 chooses the home folder or skips an existing C import. Run/Stop cancels. Before F1 accepts the home folder, the complete directory scan checks for A.IMG, B.IMG, C.IMG, START.PRG and DOS64.CFG, including files outside the displayed page. Existing names keep the user in the picker with a message to choose another home folder. This advisory check uses exact names without case sensitivity; final CREATE_NEW still protects against aliases and later changes. Review the selected paths before confirming.

The installer loads and independently reads back all five source files, retires the selection UI, and builds C and B before deriving A. It writes and verifies files in this order:

1. `C.IMG`: dynamically created raw hard disk, with the DOS files imported natively.
2. `B.IMG`: a separate working floppy.
3. `A.IMG`: boot floppy with startup files selecting C and its DOS path.
4. `START.PRG`: the verified launcher template with the selected home embedded.
5. `DOS64.CFG`: configuration published only from the verified output facts.

No dummy D81, emulated FORMAT/COPY step or distributed large empty HD image is needed. Sources remain unchanged. Current output creation refuses existing names; it does not overwrite an existing installation. A failed install can leave earlier verified outputs or a partial new file, so the completion caption is required before considering the model installation complete. Reconfiguration and a user recovery workflow remain unfinished.

The complete SYS-to-publication model tests exercise a fresh 2 MiB installation plus C, START and CFG collisions. They check every saved byte, FAT trees, CRCs, output order, source preservation, private completion state and known file closure. Eleven direct Zig/Peddle groups exercise the coordinator, relocation lifetime, initial image checks, terminal file-ownership reporting and directory conflict authority. Five additional native model tests cover whole-directory conflicts, stale/forged observations, failures and actual keyboard-driven F1 refusal/selection. Independent cleanup tests also cover damaged readback, partial DMA, cancellation, failed CLOSE, stopped clocks, bounded cleanup and foreign-source isolation. Separate FAT-worker tests cover new and imported 20 MiB C images. These results do not establish physical throughput or hardware acceptance.

## Emulator preferences

The options-enabled launcher reads optional `DOS64.INI` from the selected home on each launch. It supports `initial_columns=40` or `80` in an `[emulator]` section; absent INI defaults to 80. Edit this ordinary ASCII file without reinstalling. Native startup handles parsing and passes a checked, one-shot binary record through REU before DOS runs. The legacy template from `make start-template` ignores INI. Keep the binary configuration's ABI1 reserved bytes zero. See [syntax and options contract](NATIVE_SETUP_CONFIG.md#same-folder-emulator-options).

After verified phase preparation, a terminal failure displays its first error code, warns that new files may remain, and reports either known file closure or unconfirmed cleanup. It renders once and performs no file operations or retries. Known closure advises reloading SETUP and choosing a new folder; unknown cleanup advises keeping the screen and avoiding retry. Failures before verified phase preparation cannot use this renderer and still have limited presentation. The initial CRC is checked after bootstrap relocation; it does not authenticate a malformed bootstrap or relocation descriptor before use.

The remaining installation work includes early bootstrap error screens, safe reconfiguration, a SETUP preferences editor, floppy Save/Discard/Swap with C online, and fresh physical SETUP → START → DOS testing. Model success does not transfer physical acceptance from an older emulator build.
