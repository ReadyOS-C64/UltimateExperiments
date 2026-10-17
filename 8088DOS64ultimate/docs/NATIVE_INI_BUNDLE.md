# Matched INI release build

`make start-ini-bundle` builds fresh source copies of the real 6502 main and the existing native START code with the explicit options profile. It produces exactly five coupled release assets in a new `build/start-ini-bundle/run-*/bundle` directory:

* `START.TPL`:18432-byte disabled, unconfigured native launcher template.
* `START.REL`:64-byte D64S ABI1 descriptor binding that whole template/control131.
* `START.INO`:verified prelaunch parser/validator/I/O overlay,6798 bytes at6000..7A8D.
* `DOS64.PRG`:47105-byte native main including cold options consumer.
* `DOS64.REL`:64-byte options-aware D64L version2 descriptor binding that main.

Only `build/start-ini-bundle/RESULT.json` with status passed authorizes the complete release. Each invocation uses a fresh owned run; all five bindings and original/staged source, compiler, library and product hashes are checked before atomically publishing the run receipt and final result pointer. A failure retains its run/FAILURE.json and preserves a previous complete result. No new options START.PRG is published separately. Compiler commands, maps and source/product before/after ledgers remain in the run.

The default `make start`/`make start-template` still builds the old8b68 launcher. The release generator's default remains v1 with reserved56..59 zero; options requires an explicit argument. D64C, D64R and D64S layouts remain ABI1. This does not yet change SETUP's five-output publisher or install/copy the runtime assets: coordinated publication/deployment must include START.INO and matching main/REL. A mismatched/missing overlay fails closed before CFG access. Never deploy only the new template.

A configured new START rereads same-home `DOS64.INI` each launch. The supported setting is `[emulator] initial_columns=40|80`, default80. Malformed or unreadable present files fail; optional absence requires the firmware's exact18-byte FILE DOESN'T EXIST status plus successful owned closure. Native parser/I/O, ready-last D64O32 at3FF500, one-shot consume and actual BIOS mode1/3 are covered by the matched native component evidence. Runtime timing/IRQ/REP/cache policies are unchanged.

Optional local model targets require no DOS disk images and contact no device:

* `make start-options-tests`:fresh source-only coupled build and23 actual native/Peddle overlay/INI/entry controls, with explicitly synthetic caller-owned file inputs. This is component evidence, not DOS/installer flow.
* `make ini-options-tests unit-sidecar-tests DOS64_ZIG=/path/to/zig`:six actual native consumer groups plus four unit-only sidecar ownership/bank/write controls.
* `make start-ini-bundle-tests`:asset mismatch, re-signed wrong capsule, descriptor/default/version and actual failed-build publication checks.
* `make ini-state-memory-tests`:strict eight-byte mode/cold/error/started/HD/loader/options order/default/range checks; exact legacy structural schemas remain supported.

The unit graph retains the real options consumer and loads a251-byte EF00..EFFA probe/snapshot sidecar plus a207-byte FF00..FFCE helper sidecar. Both are required companions of the unit PRG; the existing hardware vectors remain untouched. It is never loaded by runtime releases. Sidecar count, bounds, caller cold lifetime, RAM bank and readonly code are checked; the release generator rejects unit sidecar images. Normal `make build` emits and verifies both runtime and complete unit artifacts.
