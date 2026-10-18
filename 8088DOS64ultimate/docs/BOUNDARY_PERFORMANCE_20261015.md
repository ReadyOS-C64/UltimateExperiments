# Clock and interrupt boundary optimization

> Development note: see [current status](STATUS.md), [build instructions](BUILD.md) and [installation](INSTALL.md) for present qualification. Historical measurements below apply to their stated slice, not every current build.


The reviewed combined target retains every existing guest interrupt sampling boundary, including HLT and eligible REP elements. It reduces work at those boundaries through an internal owned-clock entry and an early return when the fully validated PIC has no eligible request.

The internal clock entry is called only by the existing PIT path, with exclusive CIA2 ownership, RAM+I/O mapping, initialized copied shadow and synchronous non-reentrant execution. It preserves native status except returned carry; A/X/Y are caller-clobbered. Public clock and elapsed entries retain their banking-safe contracts and work with an uninitialized or poisoned shadow. Normal target linking selects separate owned objects; standalone helpers retain their original bytes.

The PIC change is a two-byte branch after complete configuration validation and unmasked request calculation. Empty eligible boundaries save313 modeled CPU cycles. Nonempty arbitration takes two extra cycles. No CIA access, instruction callback or IRQ sampling opportunity is removed.

The combined elapsed entry saves111 cycles. In independently compared32-instruction sequential tests, the combined saving is13,568 cycles,424 per empty eligible boundary. Full guest RAM, public CPU/PIC/PIT state and per-CIA-register access counts match at fixed clocks. Fault, ownership, shadow, busy-lease and due-IRQ cases retain their failure ordering.

| Workload | Accepted baseline modeled CPU cycles | Combined modeled CPU cycles |
| --- | ---: | ---: |
| Genuine native DOS startup, VER, DIR /P | 2,869,345,809 | 2,616,062,815 |
| Genuine MODE CO40/CO80 | 1,923,740,623 | 1,755,120,848 |

These diagnostic native workflows include development observation commands. Their clock derives from modeled CPU cost, so reducing that cost changes tick/IRQ counts and can change timing-dependent guest execution. The DOS workflow executes598,702 guest instructions in both runs; MODE changes377,062→377,078. This is functional evidence, not an exact long-run RAM differential at a fixed external clock.

The candidate runtime/unit hashes are22f82091/8a84329c, both42,497-byte PRGs. Copied shadow code grows2144→2361 bytes, leaving1223 zero-tail bytes in the unchanged3584-byte copy window. PIT grows1662→1664 bytes. MAIN115/114 and DEVICE22 headroom, zero page and resident state remain unchanged.

Root private gates421 default/597 quick/238 tooling,49 IRQ/PIT,3 startup and actual DOS/MODE pass. Independent review reproduces both PRGs, verifies all nine unchanged standalone helpers and executes12 distinct integration tests plus strict shadow/layout checks. Root production verification additionally includes the separately promoted HD evidence host tests.

The older full5701-case whole-PRG corpus proof remains tied to98fc/6eba. CPU ISA sources have not changed; no new full-corpus claim is made. Existing physical DOS/MODE acceptance also remains specific to98fc. New physical evidence is required before claiming performance or acceptance for this target. Peddle excludes real DMA/MMIO/VIC stalls, and the near4.77MHz XT objective remains unproved.

Evidence (local development record, not distributed), memory budget (local development record, not distributed), [guest timer](TIMER_IRQ_IMPLEMENTATION.md), [native clock](NATIVE_CLOCK_IMPLEMENTATION.md).
