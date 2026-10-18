# Genuine MODE hardware workflow

> Development note: see [current status](STATUS.md), [build instructions](BUILD.md) and [installation](INSTALL.md) for present qualification. Historical measurements below apply to their stated slice, not every current build.


The optional production runner executes the supplied DOS MODE.COM through DOS's normal loader and BIOS keyboard ring. The default VER/DIR runner is unchanged. The current accepted runtime/unit pair is98fc/6eba. Physical MODE CO40/CO80 passed in run092257 with configuredab50; that evidence remains specific to this target pair.

## Required immutable inputs

Retain a passed `make test-native-mode` report, the build manifest that describes its actual executed source/unit cohort, and both complete8,000-byte bitmap artifacts. A proof descriptor with schema1/purpose`genuine-native-dos-mode-proof` names exactly four roles: build_manifest, report, bitmap40 and bitmap80. Each role carries a path, SHA256 and byte count. Pin the descriptor's own SHA256 explicitly. Do not fabricate or relabel a report after a target change: the checker binds actual unit execution, its paired runtime, target source files and the full bitmap/matrix assertion harness.

The current reviewed six proof is22406c7587ec14f140d4a6c9751af4043cd59abaca1c3b089b3ea4a3ae0d9037. Its retained input directory is`agentworking/scratch/display-workflow-production/proof-inputs/six/`. These are explicit data inputs, never imported code. A clean checkout can produce new evidence with the normal MODE test; it need not reproduce an old timestamped descriptor hash.

The physical runner also requires the current complete build manifest, exact runtime PRG/map/labels, original source image, newly owned unchanged FTP floppy fixture, newly verified exact configured-PRG/service registry, original40fe recovery service, disabled388069 recovery helper, reviewed PAL clock evidence and proposal module pins. Six overlays require paired role-specific package/memory reports. All current manifest entries and watched inputs must remain unchanged during execution. Use a fresh project-owned output directory.

## Launch and acceptance

Use`build_support/c64u_native_display_runner.py --validate-only` with all required arguments first. It performs local proof, artifact, configuration and registry checks without contacting the device. Synthetic offline registries are forbidden for physical execution. Explicit`--observation-interval 2.0 --application-seconds 360` are functional test options; defaults remain0.25/180, and native-file restoration retains its separate600-second phase and maximum two fresh attempts.

Root freezes the exact input hashes and launches through an owned Terminal wrapper. The outer workflow captures/verifies a new immutable complete first4MiB REU backup before application execution. The script sends empty date/time replies, MODE CO40, then MODE CO80. Completion requires instruction progress, correct geometry and cursor-local returned prompt. At each mode checkpoint it retains BDA,16KiB CGA,64KiB host RAM and complete expected bitmap/matrix before publishing acceptance. All source fonts,8,000 bitmap bytes,1,000 matrix bytes and resident/copy-shadow code must match. A changed BDA/instruction count across paused reads fails.

Failures retain raw evidence before recovery overwrites the application. Successful application evidence never substitutes for original-service startup, native recovery CRC/EOF/known CLOSE, all4MiB independent comparison, prior configuration/media equality and reset/resume. Recovery success never converts an application failure into a pass.

KEY tests the genuine BIOS ring, not the physical matrix. RAM checks do not establish external HDMI readability, monitor scaling or RGB calibration. No video/debug stream is started without separately known ownership/prior state. Graphics, HD persistence, upper REU bytes and XT speed remain separate scopes.

Host evidence (local development record, not distributed),current physical DOS (local development record, not distributed),[display implementation](DISPLAY_INPUT.md),[recovery contract](NATIVE_FILE_RECOVERY.md).


## Accepted physical run

Run092257 executes genuine CO40 then CO80, returns both prompts, and independently checks all8,000 bitmap bytes and1,000 matrix bytes per mode. Application and evidence take112.328seconds. Recovery attempt one fails before DMA with a retained protocol/unknown-handle error; attempt two restores and independently compares all4MiB. Observed restoration across both attempts is272.930seconds; the600-second configured phase is per attempt. Independent audit1,443 checks and349 immutable input copies preserve the exact scope. Physical evidence (local development record, not distributed).
