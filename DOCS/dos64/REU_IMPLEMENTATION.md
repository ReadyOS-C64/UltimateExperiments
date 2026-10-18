# REU transfer slice

> Development note: see [current status](STATUS.md), [build instructions](BUILD.md) and [installation](INSTALL.md) for present qualification. Historical measurements below apply to their stated slice, not every current build.


Implemented 2026-10-14. This documents the current bounded primitive and mock, not the completed paging/storage system. Baseline capacity is **4 MiB**; the allocation is in [MEMORY.md](MEMORY.md).

## Assembly contract

`dos64_reu_transfer` consumes the exported ten-byte `dos64_reu_request` defined in `include/reu.inc`:

| Offset | Field | Meaning |
|---|---|---|
| 0–1 | host | Little-endian C64 RAM address |
| 2–4 | REU | Little-endian 24-bit REU address |
| 5–6 | length | Nonzero byte count |
| 7 | direction | 0 stores host to REU; 1 loads REU to host |
| 8 | status | Captured REU status on completion; zero before command |
| 9 | error | 0 success, 1 range, 2 direction, 3 zero count, 4 device status |

The primitive rejects host ranges outside `[0200,D000)` and requests that cross an REU 64 KiB bank. Ending exactly at a boundary is valid. The caller owns the buffer, request and REU allocation and must check capacity; this internal primitive does not enforce allocator ownership or probe expansion size. Larger range operations must split and explicitly reload the bank.

It preserves Y, processor flags except returned carry, and the 6510 DDR/port output bits; it clobbers A/X and ZP `20–23`. Carry clear indicates success. It saves P, disables interrupts and decimal arithmetic, enables RAM plus I/O **before reading its descriptor under KERNAL ROM**, clears stale status, disables REU IRQ/autoload/fixed addressing, programs DF02–DF08 and executes immediate command 90/91. Completion checks end-of-block and absence of verify error before restoring mapping. Exclusive REU ownership is required; prior REU register configuration is not preserved. NMI policy remains a system integration responsibility.

The current low-level host range is only a hardware guard: a caller could still overwrite resident code within it. Cache/storage ownership checks are required before exposing higher-level operations. A zero software count is rejected even though zero in the hardware count encodes 65,536 bytes.

## Mock and semantics

The independently authored C++ model is driven through the Peddle bus, while Zig calls **actual assembled routines**. Its reference is [VICE REU implementation at fa7f1e1](https://github.com/VICE-Team/svn-mirror/blob/fa7f1e1ec4f1b97d00c5b8117e12a592992f7262/vice/src/c64/cart/reu.c). No VICE source was copied into the model.

Supported semantics are immediate store/load, fixed address controls, autoload restoration, address increments, hardware zero count, count-one postcondition, command execute-bit clearing and status clear-on-read. Expanded REC address increments wrap the low 19-bit counter while preserving upper bank latches; splitting on 64 KiB boundaries avoids relying on cross-wrap behavior. Capacity models cover 4, 8 and 16 MiB; addresses alias to physical capacity as an expanded REU does.

Swap, compare, deferred FF00 execution and REU interrupts explicitly report unsupported access. No DMA bus stalls, VIC contention or physical timing is simulated. The C64 bus models relevant DDR/port banking with ROM sentinels, writes to RAM under ROM, and selected I/O. It is not executable C64 ROM or a complete CIA/VIC model; unknown device access fails rather than behaving like RAM.

## Evidence

`make test` passed 26 Zig/Peddle tests plus four linker-contract tests after the 4 MiB baseline change. Transfer vectors cover eight sizes from one byte to 4 KiB, unaligned buffers, separated banks, last-address access at 4/8/16 MiB, rejected ranges, flags/banking preservation and model postconditions. The same assembly integrity probe stores 4 KiB from 6000 to REU 180003, clears RAM, reloads and checks every byte, producing mailbox A5/error 00.

The standalone probe passed the established .NET VICE harness on run `vice_auto_20261014_222223`. Independent extraction verified all 4,096 returned bytes against `low_byte(index) XOR A7`, not only the success mailbox. See compact evidence (local development record, not distributed). The harness uses a 16 MiB REU and warp; this proves that configuration's functional round trip at an address below 4 MiB, not a physical 4 MiB configuration or 64 MHz speed. `make probe` prepares the image/plan; `make test-vice` runs the slower lane and verifies its captured bytes.

Still required: capacity/allocator enforcement above the primitive, coherent guest page cache, UCI bulk file operations, IEC backend, timer-based transfer measurements, and physical C64U execution. In particular, Ultimate bulk UCI capacity assumptions and the actual firmware must be checked; no larger-than-baseline range may be submitted merely because the wire address has 24 bits.
