# Original XT keyboard BIOS and bounded waiting

Updated 2026-10-15. `src/keyboard.s` implements the original-sized BDA keyboard ring and INT 16h services, with an independently callable enqueue routine. It consumes already translated XT ASCII/scancode words; native C64 scanning and key translation remain unfinished.

The fixed ring is 041E–043D, 16 word slots with 15 usable. Head/tail at 041A/041C must be even, in range and have zero high bytes. Later BIOS relocatable ring fields at 0480/0482 and AT extended functions are unsupported. `dos64_keyboard_enqueue` reads the caller's key word, stores both bytes coherently, then publishes tail. A full queue leaves keys/pointers unchanged. Malformed state is rejected explicitly. Dirty guest BDA bytes remain authoritative.

| INT 16h function | Implemented original XT behavior |
|---|---|
| AH=00 | Consume the head word into AX and advance head; empty ring sets waiting without inventing input or changing AX/head |
| AH=01 | Load the head word into AX even when empty; expose exact CMP(head,tail) arithmetic flags, IF=1 and TF=0 through the saved return frame |
| AH=02 | Return mutable shift byte 0417 in AL and AH=0; preserve caller saved FLAGS |

The service leaves guest FLAGS untouched and exports mask/value words for the owned BIOS wrapper to patch only on handled completion. AH=01 uses mask 0BD5h; other services preserve the original IRET flags. Unsupported/full/bad-state/cache outcomes have separate status values, and only cache failure sets host_error. Native P except carry is preserved; A/X/Y and memory scratch are clobbered. State is 18 DEVICESTATE bytes, linked CODE 464 bytes, no new E000 BSS or zero page.

The owned F000:0180 `OUT F6h,AL; IRET` gate preserves normal mutable IVT/stack hooks. During an empty AH=00 call, the wrapper enables guest IF, leaves the ordinary interrupt frame intact and marks BIOS waiting. CPU stepping restores IP to that owned OUT, sets host yield and does not increment the completed-instruction count. The next bounded call retries after input is enqueued; the actual IRET executes only after completion. This is a BIOS wait protocol, not fabricated input, guest asynchronous IRQ delivery or a CPU halt. Cache failures remain terminal.

Actual-assembly tests cover empty waits, unsupported functions, repeated 15-entry FIFO wrap/full rejection, all mutable shift bytes, exact AH=01 register/flag behavior including empty queues, malformed pointers, one-frame dirty authority, failure/retry, native ABI and write guards. Integration tests retain the frame across repeated CPU yields and enqueue keys through the real assembly routine. The long DOS lane uses ten such keys for date/time Enter, VER and DIR; it never writes DOS input buffers directly.

Native C64 matrix/USB key polling, scan mapping/chords, typematic, IRQ1/PIC delivery and interactive host input remain required work. Successful scripted Peddle input is functional backend acceptance, not a physical C64 keyboard test.
