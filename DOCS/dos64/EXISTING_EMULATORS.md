# Existing emulator references

> Development note: see [current status](STATUS.md), [build instructions](BUILD.md) and [installation](INSTALL.md) for present qualification. Historical measurements below apply to their stated slice, not every current build.


Inspected 2026-10-14. The user clarified that the target is the **original 8088 / IBM PC XT**, implemented on the C64U's 6502/6510. References inform techniques; their capabilities never narrow the project's requirements. No code from the projects below has been incorporated into the runtime.

## Closest host-CPU match: NES86

[NES86](https://github.com/decrazyo/nes86/tree/d72debaa0a5daed533d994e087fa2963e1793820) implements an 8086 on the NES in 6502 assembly, built with ca65/ld65. This is a real example of the direction we need: 6502 **executing an x86 interpreter**. It is not a C emulator of both processors, nor an emulator running on an 8088. Pin: `d72debaa0a5daed533d994e087fa2963e1793820`. Repository LICENSE is GPLv3; any source adaptation must retain notices and meet that license, rather than being treated as newly authored code.

Inspected modules provide these concrete references:

| Module | Useful technique | Adaptation boundary |
|---|---|---|
| [x86.s](https://github.com/decrazyo/nes86/blob/d72debaa0a5daed533d994e087fa2963e1793820/src/x86.s) | Separate fetch/decode/execute/write stages and explicit single-step entry | Benchmark stage overhead; preserve our test ABI and bounded scheduler |
| [decode.s](https://github.com/decrazyo/nes86/blob/d72debaa0a5daed533d994e087fa2963e1793820/src/x86/decode.s) | Shared operand forms, opcode-indexed tables and split low/high dispatch tables | Preserve original-8088 opcode profile and prefix semantics |
| [reg.s](https://github.com/decrazyo/nes86/blob/d72debaa0a5daed533d994e087fa2963e1793820/src/x86/reg.s) | Byte/word register maps and ModR/M register maps in zero page | Account for our limited ZP ownership and existing register layout |
| [alu.s](https://github.com/decrazyo/nes86/blob/d72debaa0a5daed533d994e087fa2963e1793820/src/x86/alu.s), [execute.s](https://github.com/decrazyo/nes86/blob/d72debaa0a5daed533d994e087fa2963e1793820/src/x86/execute.s) | 8/16-bit arithmetic on an 8-bit host; separate flag computation | Verify independently against hardware-generated 8088 cases, especially shifts, divide and decimal-adjust |
| [mem.s](https://github.com/decrazyo/nes86/blob/d72debaa0a5daed533d994e087fa2963e1793820/src/x86/mem.s) | Segmented-address interface separates operands from host memory mapping | MMC5 maps cartridge RAM directly; REU requires DMA and coherent cached host pages. Replace mapping, do not port its mapper assumptions |

The [linker layout](https://github.com/decrazyo/nes86/blob/d72debaa0a5daed533d994e087fa2963e1793820/conf/ld.cfg) allocates 128 KiB guest RAM and cartridge ROM. The [BIOS](https://github.com/decrazyo/nes86/blob/d72debaa0a5daed533d994e087fa2963e1793820/data/bios/src/bios.asm) is tailored to ELKS and a serial console; it is not a DOS disk/CGA BIOS to drop in. Neither the project's advertised operation nor source inspection proves original-8088 conformance or our performance goal. Do not import reset defaults, segment-edge behavior, instruction timing, or undocumented-opcode behavior without tests. On the 6510, explicitly keep host decimal mode clear during binary arithmetic; NES code runs on a CPU whose decimal behavior differs.

Searches also returned Appler, PCjs and multi-CPU desktop emulators. Appler runs a 6502 emulator **on an 8088**, the opposite direction. The searches did not establish a separate, explicitly 8088/XT-focused 6502/6510 core. This is a search result, not proof that none exists.

## Other useful references

| Project and inspected pin | License evidence | Intended use and limits |
|---|---|---|
| [8086tiny](https://github.com/adriancable/8086tiny/tree/c79ca2a34d96931d55ef724c815b289d0767ae3a), `c79ca2a34d96931d55ef724c815b289d0767ae3a` | MIT in `license.txt` and BIOS source header | Compact C interpreter and NASM BIOS. Useful BIOS contracts, boot/INT 13h flow and decoder structure. C implementation is not our target runtime or a hardware oracle |
| [XTulator](https://github.com/mikechambers84/XTulator/tree/211791d9b41871fb18079e37e696f6b95d2c3f88), `211791d9b41871fb18079e37e696f6b95d2c3f88` | CPU source header: GPLv2 or later | Readable C flags/ModR/M/peripheral reference. Includes 80186 extensions; filter those out. GitHub's missing license metadata does not supersede the source header |
| [emu2](https://github.com/dmsc/emu2/tree/9d8698d06e67359bc8b230c2d19d5b1503e60819), `9d8698d06e67359bc8b230c2d19d5b1503e60819` | GPLv2 LICENSE | CPU/console reference; native DOS API emulation is a different architecture from our real DOS boot |
| [MartyPC](https://github.com/dbalsom/martypc) and [SingleStepTests/8088](https://github.com/SingleStepTests/8088) | Pin and audit exact corpus/license when importing | Prefer original-CPU evidence for correctness; desktop emulator performance does not predict C64U performance |

8086tiny's [BIOS source](https://github.com/adriancable/8086tiny/blob/c79ca2a34d96931d55ef724c815b289d0767ae3a/bios_source/bios.asm) uses private `0F 00` through `0F 03` services and carries decoder lookup tables. Its BIOS/emulator coupling and memory layout differ from ours. If BIOS code is adapted later, record exact source ranges, modifications and MIT notices; do not adopt private instructions as generally executable guest opcodes. Our proposed native BIOS entry callbacks must still allow guest interrupt-vector hooks.

## Historical 6502-hosted CP/M work

Dann McCreary's original [8080 Simulator for the 6502, KIM-1 Version](https://www.pagetable.com/docs/8080sim/An%208080%20Simulator%20for%20the%206502,%20KIM-1%20Version.pdf) and [1979 design article](https://www.pagetable.com/docs/8080sim/8080%20Simulation%20with%20a%206502.pdf) are author-provided scans. They illustrate compact opcode grouping and register simulation. Publication of scans does not establish a reusable open-source license; treat them as historical design reading.

Michael Steil's [source-level examination of Roßmöller's C64 CP/M emulator](https://www.pagetable.com/213) traces it to McCreary's size-focused 8080 simulator. Its extra address translation and wrapper overhead are useful cautionary examples for a fast interpreter. It is not a full Z80 or x86 core, and its licensing history makes it unsuitable for unexamined copying. [CP/M-65](https://github.com/davidgiven/cpm65) is instead a native 6502 OS port, not execution of 8080 programs.

## Implementation policy

1. Implement the required original-8088 behavior, genuine DOS 3.3 boot and our PC device subset whether or not a reference provides it. The latest user clarification explicitly confirms this priority.
2. Keep our CPU-state ABI, REU/cache/storage interfaces and Zig/Peddle behavior tests. Inspect useful routines before designing the next slice; do not make progress depend on finding reusable code.
3. Use hardware-generated original-8088 cases and independently calculated defined flags as acceptance evidence. Comparing two emulators is supplementary evidence; they can share a bug.
4. Before substantial code reuse, pin it, preserve its license/attribution, identify modifications and measure linked code/ZP/stack costs. No blanket project license choice is made by this research document.
5. Keep downloads in project-local ignored scratch. The inspected NES86 file hashes are retained in the inspection record (local development record, not distributed); no upstream source is vendored by this research pass.
