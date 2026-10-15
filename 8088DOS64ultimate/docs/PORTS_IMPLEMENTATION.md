# PC port implementation

The linked original8088 CPU handles IN/OUT immediate-port and DX-port forms, byte and word (E4–E7, EC–EF). Reads update AL or AX; writes preserve guest registers. Guest FLAGS are unchanged. Immediate ports are zero-extended; DX ports retain 16 bits. Prefixes do not introduce repeated I/O. Failed or unsupported operations latch the CPU diagnostic and restore the instruction's starting IP. Fetch/cache failures remain terminal host errors.

`src/ports.s` supplies a bounded functional8259A PIC at20h/21h. It supports all ICW sequence lengths, interrupt masks, IRR/ISR read selection, specific/nonspecific EOI, priority rotation and special-mask programming. Defaults follow the original IBM XT BIOS: ICW1=13h, base08h, ICW4=09h and maskFCh. BIOS cold initialization resets this state. IRR/ISR remain explicit latches until the event dispatcher exists.

The descriptor is `dos64_io_port`/`dos64_io_value` little-endian words and `dos64_io_width` (0 byte,1 word). `dos64_io_read/write` preserve guest registers and native P except returned carry. Carry reports unsupported port/width/command. Word I/O preflights both consecutive ports, so only a word at20h currently succeeds. An unsupported second port cannot cause a partial first-port side effect. Byte reads preserve the descriptor's high byte.

Private BIOS OUT callbacks retain their exact initialized synthetic-ROM address whitelist. Arbitrary guest OUT F1/F2 is not privileged. The PIC fallback applies only when the private callback did not handle the operation and reported no fatal host error.

DEVICESTATE begins atEA00 and is constrained throughEEFF, preserving EF00–EFFF for future vectors/gateways. Frame metadata is separately constrained toE900–E9FF. PIC state occupies20 bytes. Tests reject metadata growth into devices and device placement in the vector reservation.

Accepted integration:172 Zig/Peddle tests,47 tooling checks and all2,555 previously selected hardware CPU cases. The PIC's independent suite covers all256 masks, all ICW lengths and2,048 EOI priority combinations; adapter tests cover all eight instruction forms, preserved registers/FLAGS, unsupported width/port with no partial effects, IP wrap and prefixes. IN/OUT hardware-generated vectors are not yet imported. [Source pins, tests, maps and DOS trace](../agentworking/evidence/pic-io-20261015.json).

Real IO.SYS progresses past OUT20h and now reaches absent serial BIOS INT14h after2,347 completed instructions. COMMAND.COM prompt is not accepted. No asynchronous IRQ/INTA delivery, PIC poll, hardware timing, PIT/keyboard/CGA ports or serial hardware is claimed.
