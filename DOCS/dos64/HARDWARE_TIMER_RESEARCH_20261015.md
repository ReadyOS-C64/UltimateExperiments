# Native alarm hints: research only

> Development note: see [current status](STATUS.md), [build instructions](BUILD.md) and [installation](INSTALL.md) for present qualification. Historical measurements below apply to their stated slice, not every current build.


The accepted emulator continues full elapsed sampling and PIC arbitration at every eligible guest boundary. Standalone CIA experiments suggest a native one-shot alarm could eventually reduce this cost, but neither a safe deployed C64U latency bound nor a production layout has been proved.

The separate797-byte probe was executed in VICE with both CIA models, PAL and4MiBREU. Independent review rebuilt the executable byte-for-byte, decoded both captures and checked36 observations. Repeated masked TimerA events coalesce in ICR; IRQ notification waits through SEI; CIA2 NMI can notify under SEI while retaining registers and the tested status flags. One notification was observed after a4096-byte DMA. These are final RAM observations, not event timestamps or an all-DMA-seams bound. The probe is isolated startup code and does not establish arbitrary native takeover, other banking, stack headroom or competing NMI ownership.

The [MOS6526 datasheet](https://www.retrodocs.fr/wp-content/uploads/pdf/MOS-6526.pdf) and pinned [VICE CIA1](https://github.com/VICE-Team/svn-mirror/blob/495f6aea0b2ccc60a9051dd13ddb1ac82d5472a6/vice/src/c64/c64cia1.c#L496)/[CIA2](https://github.com/VICE-Team/svn-mirror/blob/495f6aea0b2ccc60a9051dd13ddb1ac82d5472a6/vice/src/c64/c64cia2.c#L315) sources support the tested mechanisms. ICR is a latch, not an elapsed-period counter. A handler increment must never substitute for exact elapsed conversion.

Independent rational arithmetic verifies all546,875 edges:464,908 intervals of54,115 raw ticks and81,967 intervals of54,116. A fixed rounded timer latch would lose phase. An early alarm formula is conditional on a conservative hardware overhead boundS, including load/start, source visibility and applicable interrupt/handler publication. No assembly arming sequence or such bound is established. When an edge is imminent, synchronous fallback guarantees full conversion at the next eligible software boundary; it does not promise flag visibility before an arbitrarily close physical edge.

The examined primary firmware trees include CIA components, but do not identify the complete deployed FPGA121/core1.47 CPU/CIA/bus integration needed to derive the bound. [Official turbo documentation](https://github.com/GideonZ/1541u-documentation/blob/master/config/turbo_mode.rst) confirms memory and external-bus timing depend on access/VIC behavior. A measured maximum alone would not prove a universal bound.

The next suitable experiment is observational: keep CIA2 elapsed sampling and all current software boundaries, arm a private CIA1 one-shot and record whether its source latch is visible whenever exact conversion detects an edge. The hint must not choose whether sampling runs. Preserve existing control-fault checks, pause/RUN and every DMA/HD return path. Keep an early hint sticky until exact conversion passes its edge; clearing it after an early poll can lose the later due boundary.

Any later production change needs actual assembled seam/race differentials, exact counter-to-latch semantics, both VICE CIA models, all successful and failed DMA paths, charged resident/vector/stack budgets, and root-owned physical calibration at1/16/64MHz. The essential invariant is at each eligible guest boundary: exact conversion sees an edge only when the hint is ready or an unconditional fallback performs that same conversion before PIC arbitration. No sampling policy or diagnostic change is accepted by this research. No physical speed/XT claim follows.

Retained evidence (local development record, not distributed), [current accepted optimization](BOUNDARY_PERFORMANCE_20261015.md).
