# A+C development workflow

> Development note: see [current status](STATUS.md), [build instructions](BUILD.md) and [installation](INSTALL.md) for present qualification. Historical measurements below apply to their stated slice, not every current build.


The ordinary A drive boots genuine DOS3.3. The complete20MiB C image contains all three supplied DOS floppy collections, convenient DOS commands, GW-BASIC/Hangman and original English Turbo Pascal7.01 real-mode TURBO/TPC. DOS itself loads and executes these programs. See [installation](TURBO_PASCAL.md) and physical acceptance (local development record, not distributed).

## Build and offline checks

From this project directory:

```sh
make ac-close-helper
make ac-helper-tests
DOS64_AC_TEST_CONTEXT=/absolute/path/to/TEST_CONTEXT.json \
DOS64_AC_TEST_CONTEXT_SHA=EXACT_CONTEXT_SHA256 make ac-host-tests
```

`ac-helper-tests` runs six groups against actual linked6502 code in Peddle. The43 host checks require an explicit locally supplied fixture context; `tests/tooling/test_ac_development_layout.py` provides six default packaging/cache-authority regressions. None of these targets activates hardware. Complete image generation and its16 population tests remain separate explicit targets documented in [disk tools](DISK_TOOLS.md).

The public implementation is `build_support/ac_development/`, with the separately linked helper under `tools/hd_close_reopen/`. Its frozen support dependencies are verified before importing project modules. Bytecode is disabled and the selected cache path must remain absent before the first project import; `-B` alone does not reject existing bytecode.

## Prepare a new physical run

Prepare an exact source-bound genuine DOS/BASIC/TPC proof for the selected runtime/unit pair. The ordinary A+C registration accepts its specific proof and A identity; an original TURBO editor experiment requires separate purpose-specific registration and acceptance, rather than widening that contract. The existing4589 physical or4cc model proofs do not authorize a different binary.

Create fresh owned media/PRG/helper directories on the Ultimate and retain complete independent readbacks and owner markers. Never reuse the old staged DOSHD.IMG as the original source: it legitimately contains files created during testing. Use the original complete-image fixture and configure only reviewed native startup envelopes and helper backing path. `ac_runner.py --arguments ARGUMENTS.json --prepare-only FRESH_DIRECTORY` prepares artifacts offline; `--validate-only` checks the complete registration/staging contract. `ac_freeze.py` constructs the exact source/artifact guard consumed by execution. Offline validation registries cannot activate hardware.

Run physical network operations through a newly owned macOS Terminal, with a fresh output directory and concrete reviewed guard/hash. Do not retry an ambiguous native command. The existing acknowledged load-only/BASIC READY/SYS path is required; asynchronous UCI commands use complete queue/state observations rather than fixed pacing.

## Persistence and recovery

Before loading destructive helpers, retain original RAM, complete changed4MiB REU, regular A and every byte of all seven immutable overlay slots. Native target2 CLOSE/reopen/INFO precedes changed-sector and boundary comparisons, exact EOF/final CLOSE, and independent whole20MiB FTP inspection. Check all original file payloads, directory ownership and FAT allocations. Open-handle FTP visibility is insufficient: the accepted physical run retained an incomplete preclose directory entry and a clean postclose image.

The outer original40fe recovery restores changed REU chunks and independently compares all4MiB, then restores settings/media and resets/resumes. It preserves the first application or cleanup error through bounded local reporting attempts. The changed owned HD is retained rather than rolled back. Verify the complete frozen source/artifact closure after recovery. Upper REU beyond4MiB is untouched and not compared. This is verified development control; native Save/Discard UI and power-loss durability remain separate work.
