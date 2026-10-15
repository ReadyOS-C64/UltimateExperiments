# Original-8088 execution checkpoint

Implemented 2026-10-14 in `src/cpu.s`. This is the first functional execution slice, not a complete 8088 or DOS boot. Target code is independently authored 6502 assembly and executes guest bytes through the coherent memory bus.

## Current interface and instructions

`dos64_cpu_init` initializes the existing register ABI and clears core status/counters. `dos64_cpu_step` executes one guest instruction or a bounded prefix slice. It requires the normal RAM/I/O mapping and initialized memory cache, preserves host P except returned carry, and clobbers A/X/Y. It does not implement a guest-cycle timing model.

| Opcodes | Implemented behavior |
|---|---|
| B0–BF | Immediate MOV to all byte/word general registers |
| 90–97 | AX/register XCHG, including NOP |
| A0–A3 | Accumulator/moffs loads and stores, byte/word, DS or segment override |
| E9, EA, EB | Near-relative, far-absolute and short-relative jumps |
| F4 | Halt latch; subsequent steps wait without advancing IP/count |
| F5, F8–FD | CMC, CLC, STC, CLI, STI, CLD, STD guest flags |
| 26, 2E, 36, 3E, F0, F2, F3 | Recognized prefixes; last segment override wins, LOCK/REP retained for future relevant instructions |

Status 0 is running, 1 halted, 2 unsupported instruction and 3 host memory failure. Errors return carry set and latch; initialization is required to resume. Unsupported instructions restore IP to the instruction's first prefix/opcode for diagnostics and are **not** implemented as a guest invalid-opcode exception. A host memory error may leave partial memory writes; it is not a guest CPU exception either.

Original 8088 prefixes have no modern 15-byte instruction limit. After 64 prefixes the step routine yields with pending state and IP advanced through those prefixes, without completing/counting the guest instruction. A subsequent step continues it. STI records an interrupt shadow through the following complete instruction; actual interrupt/trap delivery and halt wake-up remain unimplemented.

Instruction fetch wraps IP as a 16-bit register before translating each byte. It sees dirty cached code, including tested self-modification followed by a jump. There is no instruction prefetch-queue emulation or fast span fetch yet.

## Word boundary policy

Word helpers preserve segment/offset inputs, transfer low then high byte, wrap the temporary **16-bit offset** for the second byte, and translate each byte independently with 20-bit physical wrap and PC RAM/ROM/hole protection. Failed high-byte stores can leave a committed low byte; failures propagate rather than report false success.

This policy follows the original-8088 path in [MartyPC's byte-bus word implementation at 05c0d088](https://github.com/dbalsom/martypc/blob/05c0d088e84ad6bbfac9b3f0d051e7eadefd9f44/crates/lib/marty_core/src/cpu_808x/biu.rs), which recalculates the second address from a wrapping offset. No MartyPC code was copied. Hand-authored tests distinguish offset FFFF→0000 from linear physical increment, and separately test physical FFFFF→00000, page eviction, RAM/hole boundaries and high-byte failure recovery.

The imported hardware A3 case at index 9570 covers offset FFFE→FFFF. The audited A1/A3 corpus contained no offset-FFFF word case. Do not claim those random hardware cases prove that specific corner; the corner policy currently rests on the pinned reference implementation plus independent tests. Broader original-hardware corner/event evidence remains an open research item.

## Independent verification

The pinned [SingleStepTests 8088](https://github.com/SingleStepTests/8088/tree/aea84484abc79d09639d855b7b0ab32bc9e4dbeb) projection contains **481 cases** across 20 selected opcode files. [Upstream pin/selection/hashes](../third_party/sst8088/UPSTREAM.json) and the MIT license are retained. Import script: `build_support/fetch_8088_subset.py`; network is only needed when explicitly importing, not for routine tests. The manifest rejects changes to the pinned fixture or license without regeneration.

Tests load each case's initial registers/RAM and logical instruction bytes into a fresh 1 MiB ALL_RAM guest, execute the assembled core, and compare every guest register under the declared flag mask. After coherent flush, they compare **all 1 MiB** against an independent expected RAM buffer, including unchanged bytes. Cycles and instruction queues are intentionally excluded; this is functional verification, not timing or prefetch conformance.

`make test` passes 55 Zig/Peddle tests plus 15 tooling tests, including 41 hardware cases and boundary/guest-program tests, around six seconds warm. `make test-cpu-corpus` runs all 481 pinned cases and passes, around 26 seconds. Hand tests include all supported instruction families, reset-ROM far jump, loop budgets, fetch wrap, prefix continuation, STI shadow, self-modification and latched errors. The fast/full distinction keeps routine feedback short without redefining the broader conformance gate.

## What remains

Arithmetic/flags, general ModR/M operands, stack/call/return, strings/REP execution, divide/multiply, I/O, interrupt/trap handling and most other instructions are not implemented. Synthetic BIOS/ROM initialization, boot-sector execution, real DOS kernel boot, native display/keyboard, storage/UCI/IEC, calibrated speed and optimized fetch are also unfinished. The runtime initializes state and waits; it does not automatically execute a supplied DOS image yet.

The supplied disk-1 boot sector is also an initial integration fixture: the core executes its entry jump and CLI, then explicitly reports the currently unsupported XOR at 0000:7C37. This is an entry-path check with a host-loaded sector, not a BIOS/DOS boot result. It identifies arithmetic/ModR/M and segment/stack execution as the next concrete work.
