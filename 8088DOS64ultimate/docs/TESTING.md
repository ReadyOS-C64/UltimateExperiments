# Behavior tests and end-user acceptance

This document retains the original test design and utility matrix; individual planned cases are not completion claims. Current executed evidence is in [TEST_LOG](../agentworking/TEST_LOG.md) and [STATUS](../agentworking/STATUS.md). The [V1 endpoint](V1_ENDPOINT.md) defines the final matched-release acceptance run, including edited Turbo Pascal source, compilation to disk and restart persistence. Further speed improvement is post-V1.

## The ZeroPage pattern to retain

The user specifically wants both Peddle execution and **Zig tests/assertions of behavior**, like ZeroPage. Reuse that separation:

```text
Zig test case and assertions
    → fixture registers/memory + scheduled device events
    → small C ABI → Peddle MOS_6510
    → actual ca65/ld65 output + project device models
    → bounded completion / first failure
    → compare guest state, writes, device transcript, and persistent bytes
```

Inspect `../../zig64/src/emu_test_runner.zig`, its `Labels`/test hooks, fixture discovery, KERNAL LOAD tests, and `std.testing.expectEqual` assertions. Inspect `../../zig64/third_party/peddle/zeropage_peddle.{h,cpp}` and `../ReuSQL64/build.zig`, `tests/host/runner.zig`, and local Peddle shim. The C++ bridge exposes reset/load/step/registers/memory/clock operations; Zig owns cases, expected values, scheduling, assertions, reports, and corpus parsing. Pin Peddle commit `c23e34a7e6516b284750b8c7caaa8c41948a407a`, preserving its MIT license.

Use exported linker symbols rather than invented fixed addresses for test entry, guest state, and completion. A stable test mailbox carries ABI version, case ID, completion/error, and guest instruction count. The runner stops at a return sentinel or explicit yield; reaching a cycle limit is failure. Unit-test entry points call the **same assembly routines** shipped in the runtime; end-to-end cases start its actual entry point.

Illustrative Zig test shape (API to be implemented, not runnable now):

```zig
test "ADD AL sets carry, zero, parity, auxiliary carry without overflow" {
    var machine = try Fixture.loadAssembledRuntime();
    defer machine.deinit();
    try machine.seedGuest(.{ .ax = 0x12ff, .flags = 0x0002 });
    try machine.writeGuestCode(&.{ 0x04, 0x01 }); // ADD AL,1
    try machine.stepGuestWithinBudget(1, 100_000);
    const state = try machine.readGuestState();
    try std.testing.expectEqual(@as(u16, 0x1200), state.ax);
    try std.testing.expectEqual(@as(u16, 0x0055), state.flags & 0x08d5);
    try machine.expectOnlyAllowedWrites();
}
```

Also test assembly register preservation, stack depth, `$01` restoration, and prohibited writes. Do not make tests simply echo implementation tables. Independent expected arithmetic, hardware vectors, reference disks, and post-save extraction provide stronger evidence.

## Test layers

| Lane | System under test | Main proof | Does not prove |
|---|---|---|---|
| Host Zig unit/property | Fixture parsers, independent arithmetic/address models, image metadata, schedulers | Oracle/model correctness, malformed-input handling, deterministic seeds | Target assembly correctness |
| Peddle assembly unit | Linked 6510 routines | Flags/registers/bytes/ABI, exact modeled device operations, CPU-cycle counts | VIC raster quality, real turbo/DMA/UCI wall time |
| Peddle integration | Whole emulator in modeled C64 bus | CPU↔paging↔BIOS↔image↔devices; genuine DOS boot and commands | Physical bus behavior or ultimate persistence |
| PC reference | Supplied DOS image in DOSBox-X, selected original-CPU tests/MartyPC | Expected DOS behavior, output/files; CPU semantics from suitable sources | DOSBox built-in shell is not DOS 3.3; DOSBox cycles are not XT speed |
| VICE accelerated | Actual PRG, REU, KERNAL IEC, D81; traps/warp | C64 bank/screen/input/REU and disk integration | C64U 64 MHz timing or UCI |
| VICE serial | Small true-drive 1581 scenarios | IEC path without virtual traps | Ultimate firmware behavior |
| Physical C64U | Same PRG and owned image copies | REU/UCI, speed-dependent bugs, persistence, visual usability, elapsed performance | Arbitrary PC hardware compatibility |

Fast/default runs are deterministic subsets; scheduled/manual full CPU sweeps and larger DOS matrices report separate totals. A feature is not “tested” solely because its mock passed. Every lane emits pass/fail/skipped/not-run plus reason, test count, first failure, build/fixture hashes, seed, and configuration.

## Strengthen the mocks before trusting them

The existing ZeroPage/ReuSQL64 shims immediately execute a simplified REU transfer on a command write. They cover useful DMA modes and a zero count interpreted as 65,536, but inspection does not show complete autoload/post-transfer register handling, deferred `$FF00` triggering, DMA clock stalls, bus banking, or IRQ timing. One shim truncates at its REU end; the other wraps modulo configured capacity. These are different contracts, not interchangeable proof of hardware.

Build a project-owned mock with a versioned supported-register contract. Implement all semantics the runtime uses and explicitly reject unsupported model paths. For the used subset verify command bits, fixed addresses, auto-increment/reload, clear-on-read status, completion, wrapping, bank masks, host address wrap, and transfer direction. Test unused modes independently only if they are implemented. Separate CPU cycles from a configurable DMA cost model; calibrate that model with physical measurements. Model `$00/$01` RAM/ROM/I/O selection and IRQ/NMI gates needed by the program; keep CPU-only all-RAM mode distinct.

The UCI mock must sit at the actual register interface so target assembly performs the real handshake. It owns two target contexts, files, offsets, lengths, REU bytes, output queues, and states. Script delayed BUSY, immediate post-PUSH IDLE, MORE/LAST transitions, partial data, long status, empty reply, bad seek, short read/write, missing file, read-only file, full storage, abort pending, timeout, and uncertain close. Test serialization of simultaneous logical requests. For faster pure storage tests a high-level fake is acceptable, but it cannot replace this register-level integration lane.

Device models must have tests of their own, plus shared test vectors replayed in VICE/hardware. Never alter a mock to satisfy broken target code without evidence that the new behavior matches the device.

## CPU and memory suite

- Hardware-generated [SingleStepTests/8088](https://github.com/SingleStepTests/8088) is the primary functional corpus; [8086](https://github.com/SingleStepTests/8086) helps investigate shared/different semantics. Pin release/commit/hash and record imported opcode groups.
- Initialize registers/RAM exactly, execute one guest instruction or defined REP unit, reconstruct sparse expected final state, compare all unchanged and changed registers and touched memory. Apply only per-instruction undefined-flag masks from corpus metadata.
- Do not assert bus-cycle/prefetch equivalence for this functional interpreter. Corpus docs permit ignoring queue fields for functional validation; explicitly exclude/track cases whose semantics actually depend on stale prefetched bytes. IF/TF/HLT/WAIT/LOCK gaps need additional hand-authored event tests rather than a misleading “full corpus means full CPU” claim.
- Exhaust 8-bit ADD/SUB and carry-in variants (all input pairs), test 16-bit boundaries/random values, and independently compute parity/auxiliary carry. Test all ModR/M and segment-default forms. Keep random seeds and minimize failures into stable regressions.
- Run identical cases with a flat host-memory reference and the target pager, warm/cold cache, varied page sizes, aliases, forced eviction, and one-/two-byte boundary splits. Compare CPU state and memory changes, not eviction order unless testing the pager itself.
- Additional assembly fixtures cover flag materialization, IRET and interrupt shadows, divide return IP, PUSH SP, high shift counts, REP overlap/interrupt restart, ROM protection, B800 writes, code invalidation, and BIOS disk transfer coherence.
- Test repeated cold boot, warm reboot, cancellation, media swaps, interrupted save, and recovery. First failure captures recent guest instructions, host PC/registers, cache tags, REU registers, UCI transcript, dirty ranges, and relevant disk sectors; tracing is bounded and optional in release builds.

## Supplied-image reference baseline

DOSBox-X 2026.01.02 SDL2 exists at `/opt/homebrew/bin/dosbox-x`; NASM, x64sc and c1541 are also present. Use a project-local configuration with CGA, an appropriate real-mode CPU setting, fixed comparison settings, and **BOOT from a copied raw disk**. Merely selecting a reported DOS version or running commands in the DOSBox Z: shell is not a reference boot.

First observe unmodified disk 1: its CONFIG.SYS refers to `C:\DOS\ANSI.SYS` and includes an invalid-looking `c:` line. Record actual diagnostics. Create a separate minimal-config variant for early boot, a driver-enabled variant with corrected paths, and a writable work disk. Record exact transformations/hashes; originals stay unchanged. Disk 2 lacks system files and is a utility data disk. Disk 3 contains matching DOS binaries but a nonstandard OEM boot field and different config; do not infer corruption or a DOS version from that field alone. Use its GWBASIC file under the established disk-1 OS before treating disk 3 as an alternate boot baseline.

Capture boot output, `VER`, disk directories, free space, command results, and independent output-file hashes. Record prompts and OEM-specific differences. Boot/version remains **unverified at planning completion**.

## DOS-first acceptance matrix

“Required” below means required by the relevant milestone, not already passed. Resolve exact command syntax/prompts against the supplied binaries; use the [Microsoft command reference](https://msarchive.pcjs.org/mspl13/msdos/encyclopedia/section3/) and observed reference behavior. Do not introduce DOS 5/6-only commands such as EDIT or MEM into baseline scripts.

| Group | Commands / binaries | Acceptance |
|---|---|---|
| Boot/shell — required M5/M7 | COMMAND.COM, VER, DIR, TYPE, CLS, DATE, TIME, VOL | Actual DOS version, valid prompt, stable clock/date semantics, directories/files and 40/80 presentation |
| Files/directories — required M7 | COPY, REN, DEL/ERASE, MD, CD/CHDIR, RD | Empty/binary/text files, nested paths, wildcards, names, read-only/full disk errors, persistence |
| Batch/control — required M7 | ECHO, SET, PATH, PROMPT, IF, FOR, GOTO, CALL, SHIFT, PAUSE, REM, BREAK, VERIFY, EXIT, command `/C`, redirection/pipes, CTTY CON | Deterministic output and ERRORLEVEL behavior; nested scripts and temporary-file cleanup; keyboard/cancellation; no serial CTTY endpoint |
| Text/filter — required M7 | FIND.EXE, SORT.EXE, MORE.COM, EDLIN.COM | Compare text content; EDLIN insert/edit/write/reopen; MORE keyboard/paging; input/output redirection |
| Filesystem utilities — required M7/M8 | CHKDSK.COM, ATTRIB.EXE, TREE.COM, COMP.COM, FC.EXE, LABEL.COM, XCOPY.EXE, REPLACE.EXE | Expected listing/comparison/attributes, cluster/free-space checks, copy results; CHKDSK repairs only disposable corruption fixtures |
| Media — required M6/M8/M9 | DISKCOPY.COM, DISKCOMP.COM, FORMAT.COM, SYS.COM, FDISK.COM | Two-drive and swap flows, BIOS format/verify calls, bootable outputs, MBR/partition checks, clean restart and independent bytes |
| CPU/debug — required M7 | DEBUG.COM | Assemble/run/trace tiny 8086 programs, inspect registers/memory, INT 3/TF behavior, read/write scratch files |
| Console/config — required subset M7 | MODE.COM CO40/CO80, ANSI.SYS | Width switches, cursor movement, clear/color, keyboard editing; MODE serial/printer modes excluded |
| Memory/process helpers — staged M7/M9 | ASSIGN.COM, SUBST.EXE, APPEND.EXE, JOIN.EXE, SHARE.EXE, FASTOPEN.EXE | Path/drive semantics, resident installation and hooked vectors, reopen behavior; promote each after basic shell/media stability |
| Backup — staged M9 | BACKUP.COM, RESTORE.COM | Owned multi-disk backups/restores with prompts, independent restored data; no real-media source |
| Development — staged M7/M9 | EXE2BIN.EXE, LINK.EXE | Small source-controlled object/executable fixtures, output hashes/semantics and error paths |
| Locale/drivers — conditional | KEYB.COM, KEYBOARD.SYS, NLSFUNC.EXE, COUNTRY.SYS, DISPLAY.SYS, DRIVER.SYS, RAMDRIVE.SYS | Add only configurations compatible with declared CGA/640 KiB/no EMS/XMS profile; US keyboard baseline first; record unsupported configuration explicitly |
| CGA/included BASIC — M10 | GRAFTABL.COM, GWBASIC.EXE | Font/pixel behavior and small generated BASIC graphics programs; no third-party apps needed |
| Excluded peripheral/OEM operations | PRINT.COM, GRAPHICS.COM printing, PRINTER.SYS, 4201/5202.CPI, EGA.CPI/LCD.CPI-only display features, HDFORM.EXE, HDPARK.EXE, SELECT.COM OEM install flow | Printer/EGA/LCD and hardware-specific setup/parking outside v1; do not claim pass; ordinary guest absence/error handling may be tested |
| Repair — staged M9 | RECOVER.COM | Separately specified disposable damaged-image experiment with reference results and independent extraction; never original media |

Each binary receives a manifest status: required/planned, conditional, excluded with reason, or verified with evidence. An excluded peripheral operation does not exclude the relevant supported part of a multi-purpose utility. Long-tail helpers may expose missing BIOS/ports; they are traced and triaged before any third-party-app compatibility work.

## Physical acceptance and evidence

Use the existing .NET Ultimate harness and the repository's proven Terminal-owned network wrappers as development controls. Determine the actual device/configuration at test time, capture its firmware/turbo/REU/PAL-NTSC/drive state, create only owned test roots, and restore prior settings/media afterwards. Do not use a stale device address from another project's sample file.

Required physical checks: actual 640 KiB report/use across segments; keyboard at 40/80; scrolling/editor readability; A/B copy and save/reload after restart; UCI failures/recovery; small-HD creation/boot; 20 MiB extent eviction/offsets; CGA test cards; stopwatch/host-clock measurements with display active at 64 MHz. Also repeat the transport and REU probes at 1/16 MHz to catch timeouts that only fail when turbo changes.

Acceptance has two kinds of output: machine assertions (registers, sectors, hashes, error codes) and human-visible evidence (screens/video, font readability, useful keyboard mapping). Capture both. Screenshots alone cannot establish data integrity; passing CPU vectors cannot establish usability.
