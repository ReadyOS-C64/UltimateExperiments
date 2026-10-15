# Native CGA presentation

Accepted in the five-overlay Peddle target on 2026-10-15. `src/render_graphics.s` is a real 6510 renderer loaded through GFX, not a host image substitute. [Evidence](../agentworking/evidence/timer-graphics-integration-20261015.json) pins the target. No physical graphics acceptance is claimed.

Coherent BIOS/BDA modes 4/5/6 select graphics presentation. Guest CGA storage is read through cache authority and remains exact. Modes 4/5 reduce 320 pixels to 160 by foreground-preserving adjacent pairs; mode 6 reduces 640 to 320 by pair OR. C64 cell color and palette restrictions cause documented approximations. Direct CGA 3D8h/3D9h/CRTC programming remains unsupported.

The runtime draws eight graphics scanlines, or one text row, per interval of at least four elapsed units. Each unit is 4096 PAL phi2 ticks. The ideal graphics cadence floor is approximately 416 ms per frame before rendering/CPU/DMA costs. A coherent development SNAPSHOT renders all 200 scanlines (25 text rows), flushes cache and publishes PAUSED only after completion. GFX shares the exclusive C900–CFFF window and releases its lease before any guest CPU work.

Initial TEXT setup saves the original VIC owner once. Returning from graphics reapplies TEXT settings without replacing that saved owner. GFX changes CIA2 VIC bank pins but does not touch the owned CIA timers. All display calls occur after irreversible cold release; initial startup graphics assets must be committed before cache use.

Seventeen focused Peddle blocks cover all 600 mode scanlines, 768 palette controls, 256 reduction inputs, coherent guest BIOS transitions, full-frame ownership, flags/banking/guards and injected failures. Independent host oracles inspect actual native bitmap/matrix/color output. Full frame CPU-cycle costs are 6,821,353 / 6,813,916 / 6,699,116 for modes 4/5/6; a bounded input/eight-line/16-HLT-call tick measures 268,170. DMA stalls and physical elapsed time are excluded. Human keyboard, display/readability and full new-target physical tests remain open.
