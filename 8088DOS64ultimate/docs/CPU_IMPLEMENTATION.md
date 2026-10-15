# Original-8088 execution checkpoint

Updated 2026-10-15 in `src/cpu.s`, `src/alu.s`, `src/operands.s`, `src/stack.s`, `src/strings.s`, `src/shifts.s`, `src/control.s`, `src/math.s`, `src/indirect.s`, `src/fetch.s`, `src/ports.s` and `src/adjust.s`. This is a functional execution checkpoint, not a complete 8088 or full native DOS machine. Target code is independently authored 6502 assembly and executes guest bytes through the coherent memory bus.

## Current interface and instructions

`dos64_cpu_init` initializes the existing register ABI and clears core status/counters. `dos64_cpu_step` executes one guest instruction, a bounded prefix/REP slice or a bounded owned-BIOS wait attempt. It requires the normal RAM/I/O mapping and initialized memory cache, preserves host P except returned carry, and clobbers A/X/Y. It does not implement a guest-cycle timing model.

| Opcodes | Implemented behavior |
|---|---|
| 00–3D (six arithmetic forms per family) | Byte/word ADD, OR, ADC, SBB, AND, SUB, XOR, CMP with register/memory/accumulator operands |
| 40–4F, 80–85 | Word register INC/DEC, immediate ALU groups (including signed 83), TEST register/memory |
| 88–8E, C4–C7 | General/segment MOV, LEA, LES/LDS and immediate MOV; C6/C7 extension aliases follow hardware vectors |
| 50–5F, 06/07/0E/16/17/1E/1F | General and segment PUSH/POP, including original PUSH SP and POP SP ordering |
| 9A, 9C–9F, E8, C2/C3/CA/CB | Direct far/near CALL and RET with optional stack cleanup, PUSHF/POPF, SAHF/LAHF |
| 60–7F, E0–E3 | All Jcc conditions including original aliases, LOOPNE/LOOPE/LOOP/JCXZ with signed relative offsets |
| A4–A7, AA–AF | MOVS/CMPS/STOS/LODS/SCAS byte/word, DF, source override, fixed ES destination, bounded REP |
| D0–D3 | Rotate/shift through all CL counts, original SETMO/SETMOC extension 6 |
| CC–CF | INT3, INT imm8, INTO and IRET through ordinary guest IVT/stack |
| B0–BF | Immediate MOV to all byte/word general registers |
| 90–97 | AX/register XCHG, including NOP |
| A0–A3 | Accumulator/moffs loads and stores, byte/word, DS or segment override |
| E9, EA, EB | Near-relative, far-absolute and short-relative jumps |
| 86/87, 8F /0, 98/99, A8/A9 | General XCHG, POP r/m16, CBW/CWD and accumulator TEST |
| FE /0–1, FF /0–7 | Byte/word INC/DEC; word indirect near/far CALL/JMP and PUSH, including /7 PUSH alias; far register forms excluded |
| 27/2F, 37/3F, D4–D7 | Original DAA/DAS/AAA/AAS, immediate-base AAM/AAD, SALC and coherent XLAT |
| F6/F7 | TEST (/0 and /1 alias), NOT, NEG, MUL, IMUL, DIV and IDIV |
| E4–E7, EC–EF | Byte/word IN/OUT with immediate/DX ports; PIC 20h/21h and whitelisted private BIOS callbacks |
| F4 | Halt latch; subsequent steps wait without advancing IP/count |
| F5, F8–FD | CMC, CLC, STC, CLI, STI, CLD, STD guest flags |
| 26, 2E, 36, 3E, F0, F2, F3 | Recognized prefixes; last segment override wins, REP executes on strings, LOCK retained without bus-lock timing |

Status 0 is running, 1 halted, 2 unsupported instruction and 3 host memory failure. Errors return carry set and latch; initialization is required to resume. Unsupported instructions restore IP to the instruction's first prefix/opcode for diagnostics and are **not** implemented as a guest invalid-opcode exception. A host memory error may leave partial memory writes; it is not a guest CPU exception either.

Original 8088 prefixes have no modern 15-byte instruction limit. After 64 prefixes the step routine yields with pending state and IP advanced through those prefixes, without completing/counting the guest instruction. A subsequent step continues it. STI, loading SS, and POPF changing IF from zero to one record an interrupt shadow through the following complete instruction; asynchronous hardware interrupt/trap delivery and halt wake-up remain unimplemented. Software INT/IRET routing is implemented.

Instruction fetch wraps IP as a 16-bit register before translating each byte. It sees dirty cached code, including tested self-modification followed by a jump. The linked fetch helper reuses a validated coherent span; there is no original-8088 prefetch-queue emulation.

## Word boundary policy

Word helpers preserve segment/offset inputs, transfer low then high byte, wrap the temporary **16-bit offset** for the second byte, and translate each byte independently with 20-bit physical wrap and PC RAM/ROM/hole protection. Failed high-byte stores can leave a committed low byte; failures propagate rather than report false success.

This policy follows the original-8088 path in [MartyPC's byte-bus word implementation at 05c0d088](https://github.com/dbalsom/martypc/blob/05c0d088e84ad6bbfac9b3f0d051e7eadefd9f44/crates/lib/marty_core/src/cpu_808x/biu.rs), which recalculates the second address from a wrapping offset. No MartyPC code was copied. Hand-authored tests distinguish offset FFFF→0000 from linear physical increment, and separately test physical FFFFF→00000, page eviction, RAM/hole boundaries and high-byte failure recovery.

The imported hardware A3 case at index 9570 covers offset FFFE→FFFF. The audited A1/A3 corpus contained no offset-FFFF word case. Do not claim those random hardware cases prove that specific corner; the corner policy currently rests on the pinned reference implementation plus independent tests. Broader original-hardware corner/event evidence remains an open research item.

## Arithmetic, operands and stack

The independent assembly ALU eagerly computes CF/PF/AF/ZF/SF/OF for arithmetic and preserves control flags. INC/DEC preserve CF. Logical AF is undefined on the original CPU; this implementation clears it and applies upstream defined-flag masks in conformance comparisons. The host 6502 decimal flag is cleared inside execution and restored on return.

ModR/M decoding covers all 16-bit addressing forms, signed displacement bytes, wrapping displacement words, default SS for BP forms and DS for the direct displacement form, and the last segment override. The descriptor retains segment/offset values rather than an evictable host pointer; immediate fetching cannot invalidate its destination. LES/LDS read both words before committing registers. LEA/LES/LDS register forms remain explicit unsupported diagnostics pending an audited undocumented-behavior policy. Segment-register fields use the original two-bit alias selection. C6/C7 ignore their reg extension, as exercised by hardware rows for every extension.

Stack helpers wrap SP and each byte's offset. PUSH SP stores the decremented SP; POP SP finishes with the popped word. POPF normalizes FLAGS with `(value & 0x0FD5) | 0xF002`; PUSHF/SAHF/LAHF retain original reserved-bit policy. Evidence: pinned [MartyPC stack implementation](https://github.com/dbalsom/martypc/blob/05c0d088e84ad6bbfac9b3f0d051e7eadefd9f44/crates/lib/marty_core/src/cpu_808x/stack.rs) and imported original-hardware vectors. No source was copied. Trap delivery is not implemented even when TF is set. Opcode 0F POP CS remains unfinished. POP r/m16 and word FF near/far control/PUSH forms are implemented; undefined far register pointers and unaudited FE control/stack forms remain explicit unsupported diagnostics.

A failed push can leave SP decremented and a low byte written. Pop advances only after a complete word succeeds; a far return can consume its first word before a later read fails. ALU flags may commit before a destination write fails. These are terminal host-memory diagnostics, not retryable guest exceptions.

## Independent verification

Current default quick acceptance passes **258 Zig/Peddle tests**, including **597 selected hardware rows**, with **72 in-scope tooling checks**. The separate long lane passes **1/1** genuine COMMAND.COM/VER/exact-DIR test. The pinned **5,701-case** full corpus remains the prior video/adjust acceptance; no new full rerun is claimed for this non-ISA slice. [Current slice](../agentworking/evidence/clock-keyboard-uci-20261015.json) and [long DOS proof](../agentworking/evidence/dos-command-builtins-20261015.json) retain the new identities.

The historical video/adjust slice passed **205 Zig/Peddle behavior tests and 57 tooling checks**. Its full lane passed **205 tests including all 5,701 selected hardware cases** in 59.26 host seconds, maximum eight scheduling slices. The quick gate took 29.12 seconds and executed the earlier 581-row quick projection; the subsequently expanded fixture designates 597 quick rows, all covered by the final full run, without a separate quick rerun. [Current evidence](../agentworking/evidence/video-adjust-bios-20261015.json) pins tools, source, maps, fixtures and artifacts. The 5,701 cases preserve all prior 2,555 rows and add 3,146 adjust rows; all 47 selected AAM-zero saved-FLAGS frames compare exactly in RAM without new masks. Historical math/storage/fetch/PIC checkpoints retain their individual evidence. Host command durations are not guest emulation rates.

The pinned [SingleStepTests 8088](https://github.com/SingleStepTests/8088/tree/aea84484abc79d09639d855b7b0ab32bc9e4dbeb) projection and exact selection are recorded in [upstream hashes](../third_party/sst8088/UPSTREAM.json). The MIT license is retained. Import script: `build_support/fetch_8088_subset.py`; network is only needed for explicit import, not routine tests. The manifest checks fixture and license identity.

Each case seeds a fresh 1 MiB ALL_RAM guest, executes the actual assembly, compares every register under the declared flag mask, coherently flushes, and compares all 1 MiB against an independent expected buffer. Cycles and instruction queues are intentionally excluded. Additional tests include 3,200 ALU edge/seed cases, 720 effective-address combinations, all register operand widths/high bytes, eviction across immediate fetching, stack wrap/order/flags, failure injection and guest programs.

The test runner batches bounded native Peddle stepping in C++, caches linker symbols and compiles the host engine with optimization while Zig assertions remain Debug. Three regressions compare the old and new loop's results, clocks, failure order, stack diagnostics and complete host RAM/write bitmap. Host test acceleration does not change target assembly or establish emulator throughput.

## Strings, shifts and software interrupt routing

Each step handles one ordinary string instruction or at most 16 REP iterations. CX=0 performs no string access or flag change. MOVS/STOS/LODS repeat for either F2/F3; CMPS/SCAS test the actual comparison's ZF after the first iteration and stop on the requested REPE/REPNE condition. SI/DI wrap with DF and element width; destination ES is fixed. Pending host yields preserve opcode/prefixes, leave IP after the decoded opcode, and increment the guest instruction counter once on completion. Tests include 65 prefixes before REP, forced eviction, overlap/self-overwrite, multi-slice comparisons and terminal failures after prior iterations.

These host yields are scheduling boundaries, not asynchronous guest interrupts. Original-8088 REP interrupt restart (including multiple-prefix loss), traps and per-iteration hardware event sampling remain unimplemented; a future event dispatcher must implement their policy explicitly. Software INT cannot be fetched until the current REP completes.

D0–D3 use the full 8-bit CL, without a modern 31 mask. Count zero preserve destination and flags. Rotates preserve SZP; shifts update SZP with undefined AF deterministically cleared. OF follows the final single-bit operation where checked by the original vectors. Extension 6 is original SETMO/SETMOC, setting all operand bits for nonzero counts; its undefined arithmetic flags are masked by upstream metadata. Independent closed-form integer/ring tests include counts 0/1/8/9/16/17/31/32/255.

Software INT reads both IVT words at segment 0 before pushing normalized FLAGS, CS and return IP; clears guest IF/TF; then transfers to the captured target. This preserves mutable guest hooks and a reference-derived IVT/stack alias ordering. INTO only routes vector 4 when OF is set. IRET pops IP/CS/FLAGS and applies the same normalized flags-load IF transition policy as POPF. Event timing is not proven by these state tests. Partial host errors can consume stack words or commit prior state and remain terminal. No native INT 21h replacement exists.

Tests exercise normal guest handlers editing saved return flags, IVT overwritten by the interrupt stack, stack/address wrap, the last IVT entry, conditional INTO, and IVT-load failure. Hardware vectors compare complete functional registers/RAM, not interrupt-controller behavior.

## Math and indirect control

F6/F7 executes byte/word TEST (including /1 alias), NOT, NEG, unsigned/signed multiplication and division in actual assembly. Multiplication is bounded by 8/16 shifts and restoring division by 8/16 steps. Independent integer oracles cover edge values, seeded inputs, both widths and F2/F3 cases. CF/OF report multiplication overflow; undefined flags are compared only under the pinned metadata masks. Divide faults use ordinary guest vector 0 and stack routing, preserving original post-instruction return IP rather than later-CPU fault restart semantics. The original signed minimum quotient magnitude 80h/8000h faults; signed REP division negates the quotient. Pinned hardware rows cover zero divisor, minimum signed quotient and successful/error REP IDIV. The selected MUL/IMUL/unsigned DIV sources have no REP prefixes: those additional cases are independent/source-derived evidence, not hardware-corpus coverage. No reference implementation code was copied.

General XCHG writes the decoded memory destination before replacing a base register. POP r/m16 retains its decoded destination across stack access and eviction. FF CALL/JMP captures target words before overlapping pushes; far memory pointers wrap their 16-bit offset. PUSH SP uses its decremented value, including the /7 alias. Independent tests cover aliases, all register widths, stack overlap, wrap, flags and unsupported forms.

## What remains

PC devices beyond the functional PIC, original POP CS, hardware interrupt/trap handling, halt wake-up and further original-CPU corners remain unfinished. Native C64 renderer/font/keyboard, Ultimate/IEC file loading and persistence, complete DOS boot and calibrated speed remain ahead. Coherent fetch, adjust instructions, logical video and accurate absent serial/printer BIOS are now linked and verified. Guest clock/keyboard, generic UCI and native CIA clock routines are now linked; runtime scheduling, physical key scanning and the file-command layer are unfinished. Startup initializes state and waits; it does not automatically execute a DOS image.

The [synthetic BIOS](BIOS_IMPLEMENTATION.md) and [disk primitive](DISK_IMPLEMENTATION.md) now execute reset at FFFF:0000, load the original sector at 0000:7C00 and let that sector load IO.SYS into 0070:0000. The full 22,398-byte file and 51 raw sectors, including padding and bootloader overread, match the unchanged floppy. The video/adjust checkpoint took 392 completed guest instructions and 11,860,775 native CPU step cycles to handoff, excluding setup. The storage baseline previously stopped at PIC OUT 20h after 2,335 instructions, and PIC integration reached INT 14h after 2,347. That logical video/absent-device checkpoint reached missing clock BIOS INT 1Ah after 2,542 completed instructions. Subsequent clock/keyboard/shared-rearm integration now accepts the actual COMMAND.COM prompt, VER and exact DIR in the explicit long Peddle lane below; native full-system integration remains unfinished.

## Coherent fetch span checkpoint

`src/fetch.s` accelerates instruction byte reads without pinning a cache frame across operand accesses. Each dereference validates expected CS/IP, cache mode/readiness/capacity, frame validity/tag and generation. The 512-byte span ends at a frame boundary or 16-bit IP wrap; holes never create a span. Every refill uses the normal guest-memory API. `cpu_fetch8_slow` retains the previous assembled helper for independent differential tests, including self-modification, one-frame eviction, redirects, aliases, initialization and failure.

The fetch checkpoint quick/full lanes pass 161 tests and 2,555 selected hardware cases, with 45 tooling checks. The cycle profile preserves all final registers and the full 1 MiB memory oracle. See [measured comparison](../agentworking/evidence/fetch-optimization-20261015.json). This is functional fetching, without an 8088 prefetch queue or bus timing.

## Decimal/ASCII adjust implementation

`src/adjust.s` adds original 8088 DAA/DAS (27/2F), AAA/AAS (37/3F), AAM/AAD with immediate base (D4/D5), SALC (D6) and XLAT (D7). Adjust scratch uses six DEVICESTATE bytes with no extra pre-map BSS or zero page. DAA/DAS uses the AF-sensitive high-digit threshold 99h/9Fh; DAS low correction alone does not force CF. AAA/AAS correct AL by six and AH independently by one, avoiding later-CPU AX-wide carry behavior. Undefined flag bits retain the explicitly tested policy and are masked only where the hardware metadata declares them undefined.

AAM/AAD use the actual immediate byte, including nondecimal bases. AAM base zero preserves AX, updates SZP to the original hardware-observed zero result and enters ordinary guest INT 0 with IP following the immediate. AAD base zero is valid. REP has no sign effect on AAM/AAD; this policy is source/microcode-derived because the pinned adjust hardware inputs contain no REP cases. SALC sets AL to 00h/FFh from CF without changing flags. XLAT wraps BX+AL at 16 bits, honors the source segment override and reads through the coherent bus, including dirty data, holes and physical wrap.

Private checks passed 10 native test blocks covering 80,946 executed guest instructions and 3,146 selected additional hardware cases, with register/defined-flag and full 1 MiB RAM comparison. The 3,146 cases are now integrated into the normal 5,701-case full projection, preserving all earlier 2,555 cases. Offline model comparison over all 10,000 rows in each BCD source file is also separate from actual target execution. AAM-zero saved FLAGS bytes were compared without masking. The global linked quick/full/profile gates passed; this is functional coverage, not physical execution or original-CPU bus timing.


## Owned keyboard wait and genuine DOS continuation

When the exact initialized keyboard ROM gate reports an empty AH=00 ring, CPU stepping restores the instruction IP to that owned OUT, returns carry clear with yield and leaves the completed count unchanged. The ordinary guest interrupt frame remains on the stack. The BIOS enables guest IF while waiting, retries after a real enqueue and executes normal IRET on completion. This is a bounded BIOS callback wait, not an asynchronous IRQ implementation or a new guest opcode. Tests exercise repeated empty retries, frame/flags preservation, enqueue and completion.

The normal full hardware corpus remains the 5,701-case source-pinned projection last passed in the video/adjust slice; no new ISA forms are introduced here. Default quick tests now use its 597-row selection and stop the DOS acceptance lane at kernel handoff. `make test-dos-boot` explicitly executes genuine COMMAND.COM with scripted assembly keyboard input, validates VER and complete DIR filename/size/free-byte output and requires the final prompt. It passes after 588,937 completed guest instructions and 592,171 scheduling calls; [built-ins evidence](../agentworking/evidence/dos-command-builtins-20261015.json) retains exact scope.

A separate [fast/slow fetch comparison](../agentworking/evidence/dos-fetch-differential-20261015.json) at the previously unsupported DOS shared-IRQ broadcast matched all 55,583 calls/53,861 instructions, every guest register state and complete coherent 640 KiB RAM plus 16 KiB CGA. [Primary trace audit](../agentworking/research/dos-trace-audit-20261015.md) establishes that the code/relocation/port access is genuine; that comparison rules out a regression relative to the retained slow path, not every possible CPU semantic defect.
