# Native startup interface diagnosis

On2026-10-15 the current split256 SAVE target d883c678, configured69cdc2b6, failed its first native ID read atDF1D withFF/UCI_ERR_ID. It had executed zero guest instructions, uploaded zero command bytes, imported no disk and never attempted COPY or SAVE. Complete original4MiB/settings/media/reset/source and five independent post-recovery input/OWNER files passed. This is distinct from the earlier completed512-byte SAVE corruption.

The retained177-byte UCF2 record binds that actual rawFF to the original native ID LDA. It does not record live DDR/port at that boundary. REST underlying RAM0000/0001 cannot supply that missing authority.

## Source-bound diagnostic

Private UID1 candidate4e2241d0/unit44306a09 adds a separate16-byte first-read record. It retains the original single ID LDA, immediately pushes its flags, samples native DDR/port inside the same uninterrupted mapped ENTER scope, records operand/base/stage, and publishesA5 last. It neither retries nor accepts invalid identifiers. ROOT independently replayed9 native and6 decoder groups, with all996 original and copied inputs unchanged; receipt e6c80917. The private candidate is instrumentation, not a production fix or physical acceptance.

DEVICE4096/4096, HDBIOS2917/3584 (667 free), DEVICESTATE1025, MAIN1runtime/0unit. These are private diagnostic budgets; production remains d883/8866 with its existing measured budget. The native author's original budget JSON mistakenly calculated runtimeMAINfree0; separate clarification584b0c44 records the correct1 without editing its seal.

## Conditional public firmware launch race

Pinned public v3.14 source830665cd9b41bc34b868f5c1a1179c5baa4989af establishes this ordering:

1. [C64_Subsys::dma_load](https://github.com/GideonZ/1541ultimate/blob/830665cd9b41bc34b868f5c1a1179c5baa4989af/software/io/c64/c64_subsys.cc) resumes the C64, then calls restoreCart. restoreCart waits for the boot cartridge to disable and calls set_cartridge(NULL).
2. [C64::set_cartridge / set_emulation_flags](https://github.com/GideonZ/1541ultimate/blob/830665cd9b41bc34b868f5c1a1179c5baa4989af/software/io/c64/c64.cc) reapplies settings. set_emulation_flags first disables REU/UCI and then reenables them from configuration.
3. The pinned command RTL provides a constantC9/49 identifier only when its enabled/base decode drives the bus. Protocol busy state alone does not change that constant.

A program already running at64MHz could therefore overlap the public configuration handoff. This is a hypothesis: the installed3.14/FPGA121/core1.47 source/bitstream is not identified, no actual enable transition was captured, and native banking/bus behavior remain alternative unknowns. Do not report this ordering as the deployed cause.

The [pinned runner routes](https://github.com/GideonZ/1541ultimate/blob/830665cd9b41bc34b868f5c1a1179c5baa4989af/software/api/route_runners.cc) distinguish start_prg(file,false) for load_prg from true for run_prg. [Official API documentation](https://1541u-documentation.readthedocs.io/en/latest/api/api_calls.html) confirms load_prg loads without automatically running. A fresh development-only host adapter is being tested: wait for acknowledged load completion and observed BASIC readiness, pause and verify exact loaded/not-started source, queue SYS2061 through KERNAL RAM with count last and readback, then resume. Recovery-service launches remain unchanged. No fixed UCI delay, wrong-ID retry, runtime REST dependency, native gate patch or firmware flash is proposed. Unsupported or ambiguous load fails without falling back to autostart.

Primary files, URLs and SHA256s are retained in agentworking/scratch/firmware-release-research-20261015/sources.json. Hardware must test this handoff before it can establish functional acceptance; the complete floppy SAVE and requested game video remain separate gates.


2026-10-15 physical outcome: two originald883 development attempts using acknowledged runners:load_prg, two observed BASIC READY samples with advancing jiffies, exact visible PRG/cold guards, then one queued SYS2061/resume booted DOS and completed native whole-floppy SAVE. The first run remains failed on four ancillary local metadata pins regenerated accidentally during freeze; the clean fresh repeat passes all3446live/copy pins, native/independent complete image verification, original4MiB restoration/settings/media/reset and remote input closure. Evidence: ../agentworking/evidence/c64u-complete-split-save-20261015.json. This supports the reviewed development handoff. It does not observe installed REU/UCI enable transitions, identify installed firmware source, prove the earlier FF cause, or establish manual cartridge-loader behavior.
