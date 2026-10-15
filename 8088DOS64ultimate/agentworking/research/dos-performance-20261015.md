# Genuine DOS workload performance, 2026-10-15

Private research against the frozen unit PRG supplied during the clock/keyboard/UCI implementation slice. This is measured Peddle execution of the actual linked 6510 interpreter and unchanged supplied DOS 3.3 image. No production source, shared test, global build, device or original image was changed.

The complete script passes: genuine reset and boot-sector IO.SYS load, date/time empty replies through the assembly keyboard backend, returned COMMAND prompt, `VER` reporting 3.30, and `DIR` matching all 35 root names/sizes plus 9,216 free bytes before the final prompt. The original assertions remain active. The private instrumentation records CPU clocks around each real CPU-step call, observes the final decoded opcode and completed-instruction counter, and accumulates exact native instruction PC clocks. It never supplies guest results, sectors, file operations or altered guest state.

## Baseline and scope

- Unit PRG SHA-256: `8c7e5a429f406473fa07c2acb06a86dd40e359696ca99f1a62d280c1325a5301`.
- Labels SHA-256: `5178e43920bf254ee7234c209ae710240328bec333de4193a3d1f6031e1aa9c0`.
- Immutable source image: `bca98992b476dfee95667b1edc9a71c255858e588c03edece04ad7237ca6ffdb`.
- Oracle: `6b99967e3861777a1e6a07fb6dc6c49d110fa534cf3bcbf25f006141fb15f3ca`.
- 588,937 completed guest instructions; 592,171 CPU-step calls; 1,269,694,142 native CPU-step clocks; 387,642,514 native instructions in those calls.
- Native support clocks: 9,698,220, separately covering coherent observations and keyboard injection. Setup: 26,364,820 clocks, separately covering cache/disk/BIOS/CPU initialization.
- Sum of every native-PC histogram entry exactly equals 1,269,694,142. Private instrumentation adds host bookkeeping only, with no modeled target instructions or clocks.
- Zig 0.16.0, Debug host assertions, C++ Peddle sources compiled with `-O2`. Instrumented lane: 1/1 test passed, approximately 16 seconds execution after compilation. Debug output appears under Zig's `run test w` warning display; exit status is 0 and its summary reports success.

Clocks exclude the caller JSR, REU DMA stalls, real VIC/CIA contention, physical display work and elapsed hardware time. At a hypothetical uninterrupted 64,000,000 native clocks/second, CPU-step work alone corresponds to 19.839 seconds; setup and measured support bring the arithmetic floor to 20.402 seconds. These are lower-bound clock divisions, not calibrated C64U duration, guest MHz or an XT comparison.

## Phases

Phase boundaries follow actual coherent screen observations and keyboard enqueues. The first phase ends at the proved IO.SYS entry. The next includes the kernel and COMMAND startup until the date prompt is observed. Observation granularity is normally 256 completed guest instructions, with forced checks during BIOS waiting; phase clocks can therefore include that bounded observation lag.

| Phase | Completed guest instructions | CPU-step calls | CPU-step clocks | Share |
|---|---:|---:|---:|---:|
| reset_to_IOsys | 392 | 392 | 11,860,328 | 0.93% |
| IOsys_to_date_prompt | 119,553 | 122,559 | 303,840,211 | 23.93% |
| date_reply_to_time_prompt | 8,960 | 8,960 | 16,561,007 | 1.30% |
| time_reply_to_COMMAND_prompt | 64,768 | 64,772 | 108,002,026 | 8.51% |
| VER | 20,480 | 20,574 | 37,157,911 | 2.93% |
| DIR | 374,784 | 374,914 | 792,272,659 | 62.40% |

`DIR` dominates this particular script. Its 374,784 guest instructions include DOS file/directory work and character output; this does not establish a universal application workload mix.

## Opcode and native costs

Opcode rows classify each scheduling call under the actual decoded opcode after the call. Prefix bytes are included in that call's time. REP continuations retain their string opcode and contribute calls/clocks without incrementing the completed guest count until the instruction finishes. Consequently calls are not hardware instruction retirement counts.

| Opcode | Completed | Calls | Clocks | Share |
|---|---:|---:|---:|---:|
| `E6` | 3,050 | 3,050 | 169,424,053 | 13.34% |
| `A5` | 159 | 1,738 | 54,245,550 | 4.27% |
| `E8` | 24,521 | 24,521 | 53,051,244 | 4.18% |
| `C5` | 11,861 | 11,861 | 42,270,193 | 3.33% |
| `83` | 22,677 | 22,677 | 41,231,529 | 3.25% |
| `C3` | 23,159 | 23,159 | 38,882,431 | 3.06% |
| `8B` | 18,443 | 18,443 | 37,694,063 | 2.97% |
| `03` | 20,443 | 20,443 | 35,081,644 | 2.76% |
| `E2` | 35,105 | 35,105 | 34,560,734 | 2.72% |
| `CD` | 5,722 | 5,722 | 31,638,617 | 2.49% |
| `AD` | 16,905 | 16,905 | 31,068,126 | 2.45% |
| `80` | 11,459 | 11,459 | 27,379,136 | 2.16% |
| `A4` | 269 | 1,641 | 26,680,778 | 2.10% |
| `8C` | 12,109 | 12,109 | 24,213,390 | 1.91% |
| `74` | 33,045 | 33,045 | 24,127,887 | 1.90% |

Native module costs assign each executed native instruction to its linked object/segment address range. They are exclusive instruction-PC ownership, not inclusive function costs; memory work called from a BIOS gate appears under memory, not video. `address.o` and `fetch.o` are intentionally separate from `cpu.o`.

| Native object | Clocks | Share |
|---|---:|---:|
| memory.o | 368,936,629 | 29.06% |
| cpu.o | 309,245,403 | 24.36% |
| fetch.o | 254,007,237 | 20.01% |
| address.o | 126,097,248 | 9.93% |
| operands.o | 42,811,101 | 3.37% |
| stack.o | 35,443,671 | 2.79% |
| alu.o | 34,269,527 | 2.70% |
| video.o | 31,732,966 | 2.50% |
| strings.o | 24,410,247 | 1.92% |
| range.o | 16,310,795 | 1.28% |

The dispatcher itself, bounded from `cpu_dispatch` to `cpu_io`, consumes 125,569,332 clocks (9.89%). There are 588,937 dispatch entries. The stack-opcode linear scan repeatedly executes its compare/branch at the hottest individual native PCs, about 4.64 million times. This is a direct optimization target rather than a guess from source size.

Warm fetch is already effective: `dos64_fast_fetch` enters 1,331,381 times; only 140,221 refill entries occur (10.53%). Its checks and pointer advance still account for 20.01% of the whole workload. Redirect/refill correctness remains essential under operand eviction and self modification; do not remove ownership checks based on the warm ratio alone.

## BIOS gates and guest addresses

These are inclusive CPU-step clocks for guest private-OUT callbacks, so they overlap the module totals above:

| Guest ROM IP / AH | Calls | Inclusive clocks | Meaning |
|---|---:|---:|---|
| `0150 / 0E` | 1,913 | 113,173,019 | Text teletype, wrapping and scrolling |
| `0100 / 02` | 81 | 50,191,278 | Floppy read, coherent copy included |
| `0180 / 01` | 978 | 5,558,587 | Keyboard status |
| `0180 / 00` | 10 | 39,870 | Keyboard consume |
| `0190 / 00` | 50 | 197,846 | Clock read |

There are 34 native `v_scroll_window` entries. The video object itself uses 31,732,966 clocks, with 12,632,496 within the scroll routine's native address span; its called memory/cache work accounts for much of the larger teletype-gate cost. A later coherent span API could accelerate scrolling and disk copies together. A direct REU bypass would be incorrect while dirty cached guest pages remain authoritative.

Hot guest physical addresses include `F0150` (113.17 million clocks), `F0100` (50.22 million), `9E927` (41.48 million over 1,319 scheduling calls and 41 completed instructions), `0D47C` (29.42 million), `0D47F` (28.10 million), `0D47D` (26.64 million), and `0E1C4` (21.82 million over 1,240 calls and two completed instructions). Guest RAM can be reused during boot and program loading: final RAM bytes at these addresses are not a trustworthy disassembly of every earlier execution. Address histograms are physical aggregation, not stable DOS symbols.

## Proved dispatch-table prototype

A private replacement maps all 256 opcode values to the same family handlers, keeping unsupported opcodes at the existing explicit fault path. Two 256-byte low/high address arrays replace the long comparison chain and stack-opcode scan. The jump uses the existing synchronous `cpu_jump` scratch; no new state is allocated. The dispatcher explicitly reloads the original opcode into A before tail entry.

The first experimental version omitted that reload. Existing immediate/exchange handlers consume the accumulator supplied by the dispatcher; the unchanged kernel byte oracle immediately failed. The corrected version preserves that ABI. This is a useful lesson for any dispatch refactor: the dispatcher's accumulator is part of its internal calling convention, even where a separate module reloads the opcode itself.

The corrected prototype passes the entire genuine-DOS script. It exactly matches baseline final registers/instruction count, all 640 KiB guest RAM hash, all 16 KiB CGA VRAM hash, BIOS read history, keyboard history, every recorded screen observation, all directory entries/free bytes and completion reason.

- CPU-step clocks: **1,269,694,142 → 1,164,611,699**.
- Saving: **105,082,443 clocks; 8.2762%** of baseline CPU-step work.
- Prototype PRG: `59f411a0f6f759ac94f2a806729f36952cfc1c10ea10978bcf12cb34f9cca416`.
- Prototype labels: `c596fd039a51c6203c701636583502f30d54720b409d5a70dfa860b6d2d22c67`.
- The hypothetical 64 MHz CPU-step floor becomes 18.197 seconds, 1.642 seconds lower. Physical elapsed improvement remains unmeasured.

This validates the workload prototype, not every opcode. Production adoption still requires the quick behavior gate, all 5,701 pinned original-8088 hardware cases, the same long DOS gate and the profile workload. Prefix/alias/unsupported entries and internal register/carry assumptions need explicit review.

### Layout cost and compact alternatives

| Linked item | Baseline | Prototype | Change |
|---|---:|---:|---:|
| CPU CODE bytes | 2,179 (`0883`) | 1,770 (`06EA`) | −409 |
| CPU RODATA bytes | 25 (`0019`) | 537 (`0219`) | +512 |
| Net MAIN use | — | — | **+103 bytes** |
| Unit CODE | `080D–3B0A` | `080D–3971` | — |
| Unit RODATA | `3B0B–3E82` | `3972–3EE9` | — |
| Unit fixture code | `3E83–3EA6` | `3EEA–3F0D` | — |
| DEVICECODE | `5000–5E63` | `5000–5E63` | unchanged |

The private unit snapshot leaves 242 MAIN bytes after the prototype and 412 DEVICE bytes. The proposed overlay manager's 134 MAIN/363 DEVICE bytes would leave 108/49 bytes on this snapshot. Root's later 11-byte MAIN delta would reduce MAIN slack to 97 bytes. These are integration estimates against a moving baseline, not linker evidence of a combined build. Production and unit layouts differ because unit-only fixtures consume additional resident bytes. Do not move permanent dispatch tables into a live overlay window.

A compact option, not implemented or timed here, is one 256-byte opcode→handler-ID table plus 64 bytes for its 32 distinct target low/high addresses. That saves 192 RODATA bytes relative to this prototype at the cost of an extra indirection; repeated handlers make this plausible. A 16-entry nibble parity table could reclaim up to 240 bytes from the existing 256-entry table, but extra parity-update instructions need measured proof and full flag conformance. Current measured net +103 bytes fits the stated immediate overlay budget; compacting is optional unless later resident growth consumes the remaining margin.

## Next measured experiments

1. **Adopt/review the proved dispatcher first.** It has an 8.276% measured workload saving and only 103 net MAIN bytes, with no device/state growth. Preserve and test the accumulator ABI. The full hardware corpus remains mandatory before adopting it.
2. **Translate the segment address with accumulator nibble operations.** `dos64_physical` enters 1,033,584 times and costs exactly 122 clocks/call here, totaling 126,097,248 (9.93%). An independently calculated A-only nibble construction can implement the same 20-bit sum in 98 clocks while preserving X/Y/P and the inputs. The theoretical 24-clock difference would remove 24,806,016 clocks (1.95%) if call count stays fixed. This is a static instruction-cost estimate, **not a proved optimization**. Required proof: edge/wrap and seeded segment/offset oracle, X/Y/P preservation, complete CPU corpus and exact DOS-state comparison. Relinking may also change page-cross branch costs elsewhere.
3. **Instrument and prototype coherent same-page word/span operations.** There are 226,659 guest word reads and 160,730 writes, versus 1,443,261 total byte-memory accesses. Those word operations cover 774,778 byte accesses (53.68%). Their helper bodies alone cost 26,919,443 clocks (2.12%), with translation/cache costs additional. Pairing eligible bytes could remove one translation and resolution per word, but the actual same-page eligibility and saved body cost are not yet measured. Preserve offset-FFFF wrapping, physical/page boundaries, ROM/hole/CGA policy, generation/write epoch, dirty marking and partial-failure semantics. The same infrastructure can serve 34 text scrolls and 81 BIOS disk reads. No numerical speedup is claimed until a private prototype reproduces the state/trace oracles.

## Reproduction and retained evidence

All raw and generated artifacts are under ignored project-local `agentworking/scratch/dos-performance/`:

- `snapshot.json`: copied baseline PRG/labels, original harness and model source identities.
- `proof-identities.json`: frozen modified harness, bridge, source, scripts, baseline and prototype binary identities.
- `build/baseline-dos-profile.json`: opcode/phase/native-PC/guest-address/gate raw histograms.
- `build/baseline-dos-boot-first.json`, memory/video binaries: complete accepted baseline state and screen/input/disk history.
- `build/dispatch-dos-profile.json`, `build/dispatch-dos-boot-first.json`: corrected prototype proof.
- `build/dispatch-comparison.json`: explicit baseline/prototype identities and equality checks.
- `build/profile-summary.txt`, `build/baseline-profile-summary.json`: reduced baseline analysis.
- `dispatch-table.patch`: source patch against the frozen `src/cpu-baseline.s`; the only source difference is the dispatcher block and its tables.
- `prototype_dispatch.py`: reproduces the corrected private assembly/link using the frozen baseline source and copied modules. It does not touch the shared project.
- `instrument.py`: record of private instrumentation changes; it is an initial transformation, not an idempotent reapplication command.

From the private directory, the corrected prototype can be rebuilt with `python3 prototype_dispatch.py`, then executed with `/Users/karlprosserpp/dev/c64projects/zeropage-tooling/bin/zig build dos-boot --summary all`. Do not run the non-idempotent instrumentation transformation again over the already-instrumented copies. To repeat the baseline, restore `src/cpu-baseline.s` as `src/cpu.s`, rebuild its CPU object/link with the same copied modules, and use the same instrumented test executable. Preserve recorded baseline/prototype artifacts before repeating a run.
