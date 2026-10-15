# Original XT guest clock BIOS

Updated 2026-10-15. `src/clock.s` implements original XT INT 1Ah guest-state behavior and explicit virtual tick advancement. This is separate from the [native CIA clock](NATIVE_CLOCK_IMPLEMENTATION.md), PIT/IRQ scheduling and physical elapsed-time calibration.

`dos64_clock_service` reads guest AH. AH=00 returns the coherent 32-bit BDA tick word at 046C–046F in CX:DX, returns the full overflow byte at 0470 in AL, then clears that byte. AH=01 writes CX:DX without normalizing it and clears overflow, preserving AL/CX/DX. Every nonzero function decrements AH, including unsupported later RTC probes: AH=02 returns AH=01, without pretending an AT RTC exists. Guest saved FLAGS and other registers remain unchanged. The owned F000:0190 `OUT F7h,AL; IRET` gate performs normal guest-frame routing, not interrupt-number interception. Cache failure is a distinct terminal host error.

`dos64_clock_advance` consumes at most 256 caller-supplied virtual ticks per invocation. The count word mutates to remaining work; DONE reports only this invocation. Exactly reaching 001800B0h resets ticks to zero and sets the overflow byte to one, following the original equality test even after an unnormalized set. A wrap from FFFFFFFF to zero alone is not midnight. Overflow is a flag, not an accumulated day count. Zero count performs no memory access.

All five clock BDA bytes share one coherent cache page. Initial acquisition failure leaves BDA/count unchanged and DONE zero; retry does not double-apply ticks. Once acquired, the routine performs no later eviction/transfer between its same-page writes. Native P except returned carry is preserved; A/X/Y and public memory scratch are clobbered. The synchronous service is non-reentrant and uses 13 DEVICESTATE bytes with no extra E000 BSS or zero page; linked DEVICECODE is 390 bytes.

Tests execute all 256 AH values, full overflow-byte semantics, unnormalized sets, exact midnight/32-bit wrap, zero work, one-frame dirty BDA authority, initial/eviction failures and retry, native flags and memory guards. The genuine DOS path passes its INT 1Ah startup calls and later reaches COMMAND.COM in the opt-in long lane.

No PIT programming, IRQ0/INT 1Ch delivery, motor timeout, host-time pacing or RTC hardware is implemented here. The long functional DOS run does not establish elapsed-time fidelity. Runtime integration must convert a validated elapsed clock into bounded guest ticks while retaining guest IF/event semantics.
