# PC port implementation

Current timer integration adds only the exact owned F8h BIOS clock gate. Guest8253ports40h–43h and directCGA3D8h/3D9h/CRTC remain unsupported. Fixed PIT scheduling and BDA-selected presentation are described in [timer](TIMER_IRQ_IMPLEMENTATION.md) and [graphics](CGA_RENDERER_IMPLEMENTATION.md).

The linked original 8088 CPU handles immediate-port and DX-port IN/OUT forms, byte and word (E4–E7, EC–EF). Reads update AL or AX; writes preserve guest registers. Guest FLAGS are unchanged. Immediate ports are zero-extended; DX ports retain 16 bits. Prefixes do not introduce repeated I/O. Failed or unsupported operations latch the CPU diagnostic and restore the instruction's starting IP. Fetch/cache failures remain terminal host errors.

`src/ports.s` supplies a bounded functional 8259A PIC at 20h/21h. It supports all ICW sequence lengths, interrupt masks, IRR/ISR read selection, specific/nonspecific EOI, priority rotation and special-mask programming. Defaults follow the original IBM XT BIOS: ICW1=13h, base 08h, ICW4=09h and mask FCh. BIOS cold initialization resets this state. IRR/ISR remain explicit latches; the current event dispatcher accepts eligible requests through the guest IVT.

The descriptor is `dos64_io_port`/`dos64_io_value` as little-endian words, and `dos64_io_width` (0 byte, 1 word). `dos64_io_read/write` preserve guest registers and native P except returned carry. Carry reports an unsupported port/width/command. Word I/O preflights both consecutive ports, so only a word at 20h currently succeeds. An unsupported second port cannot cause a partial first-port side effect. Byte reads preserve the descriptor's high byte.

Private BIOS OUT callbacks retain their exact initialized synthetic-ROM address whitelist. Arbitrary guest OUT F1/F2 is not privileged. The PIC fallback applies only when the private callback did not handle the operation and reported no fatal host error.

DEVICESTATE begins at EA00 and is constrained through EEFF, preserving EF00–EFFF for future vectors/gateways. Frame metadata is separately constrained to E900–E9FF. PIC state occupies 20 bytes; other device modules share the explicitly bounded DEVICESTATE allocation. Tests reject metadata growth into devices and device placement in the vector reservation.

The accepted PIC checkpoint passes 172 Zig/Peddle tests, 47 tooling checks and all 2,555 previously selected hardware CPU cases. The PIC's independent suite covers all 256 masks, all ICW lengths and 2,048 EOI priority combinations; adapter tests cover all eight instruction forms, preserved registers/FLAGS, unsupported width/port without partial effects, IP wrap and prefixes. IN/OUT hardware-generated vectors are not yet imported. [Source pins, tests, maps and DOS trace](../agentworking/evidence/pic-io-20261015.json).

At this checkpoint real IO.SYS progresses past OUT 20h and reaches absent serial BIOS INT 14h after 2,347 completed instructions. COMMAND.COM prompt is not accepted. No asynchronous IRQ/INTA delivery, PIC poll, hardware timing, PIT/keyboard/CGA ports or serial hardware is claimed. The later verified BIOS/video/adjust slice passes 205 tests, 57 tooling checks and all 5,701 hardware cases, and reaches absent INT 1Ah after 2,542 instructions. [Combined evidence](../agentworking/evidence/video-adjust-bios-20261015.json). PIC event-delivery and other port limitations remain unchanged.


## DOS 3.30 shared-interrupt rearm broadcasts

The generic port adapter now accepts arbitrary byte writes to exactly 02F2h–02F7h as DOS GLOBAL REARM broadcasts for shared IRQ levels 2–7. The XT profile has no attached shared-interrupt boards, so these writes preserve PIC/device state, guest registers and FLAGS. Reads, word forms, neighboring/unrelated ports remain explicitly unsupported; this is not a blanket unknown-port success policy or a new interrupt controller.

The genuine stop at 9DFD:0A53 was original relocated SYSINIT code, not evidence of a fetch failure. The [pinned primary-source and binary audit](../agentworking/research/dos-trace-audit-20261015.md) identifies the inherited DOS 3.30 six-port sequence and arbitrary-byte meaning. Microsoft v4 source documents the purpose, while the supplied 3.3 binary remains authoritative. Independent tests cover all six ports/byte values, preserved flags/state and rejected reads/words/adjacent ports. This narrow addition lets genuine DOS continue to COMMAND.COM; asynchronous shared-IRQ delivery remains unimplemented.
