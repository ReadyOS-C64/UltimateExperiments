# Canonical CGA cursor presentation

> Development note: see [current status](STATUS.md), [build instructions](BUILD.md) and [installation](INSTALL.md) for present qualification. Historical measurements below apply to their stated slice, not every current build.


The presenter adds foreground cursor scanlines to40/80-column text, with full14-bit absolute cursor address and80-column half-cell preservation. Direct CRTC writes leave DOS/BIOS BDA cursor shadows and guest VRAM unchanged. Hardware display start must match the presented BDA page; arbitrary direct start scrolling and visible inverted shapes explicitly refuse. Hidden cursors, clipped scanlines and offpage/high-address nonaliases are covered.

[Motorola MC6845](https://www.bitsavers.org/components/motorola/_dataSheets/6845.pdf), pages15–16, defines shape/address and internal16/32-field ON intervals. [IBM CGA logic](https://www.minuszerodegrees.net/oa/OA%20-%20IBM%20Color%20Graphics%20Monitor%20Adapter%20%28CGA%29.pdf), sheets1/3, supplies foreground cursor combination and external16-field full-period gating. Independent review corrects the candidate document's component name: **U12LS393 is the divider; U63LS02 is its reset gate.** The code's fieldbit3 external gate and fieldbits4/5 internal gates are unchanged. Virtual phase0 visibility is a functional model choice, not a physical reset-phase or analog claim.

Native text row0 samples the existing published48-bit PIT field once, before leasing TEXT. Rows1..24 reuse the cached phase; graphics4/5/6 bypass this sampler. Ordinary3DA reads do not overwrite the rendered-frame phase. Failed clock/ownership/lease/transfer retains the old phase byte but marks it staleFF; the renderer refuses stale state before writing output. No CIA read, guest retirement or change to IRQ/REP/STOP/debt cadence is introduced by sampling.

## Same-pause capture contract

Use native SNAPSHOT command2 and observe successful A5 acknowledgement, paused stage5 and completed render row0. Retain the same paused state's guest instruction counter, full source/overlay/font ownership checks, coherent256-byte BDA and16384-byte CGA,8000-byte bitmap and1000-byte matrix. Read exact labels from the matching native pair:

- `dos64_cga_registers`:18 bytes; `dos64_cga_control` and `dos64_cga_control_valid`:one byte each, validA5.
- `dos64_cursor_phase_valid`:A5 required; `dos64_cursor_field_phase`:low8 fieldquotient bits. FF is stale;0 unrequested is only for isolated fixtures.
- `dos64_render_text_request+1`:captured attribute blink0/1, never recomputed from host time.
- Installed narrow font1024 bytes at4400 and wide font2048 bytes at4800, checked against matching packaged metadata.

`build_support/cga_cursor_oracle.py:render_text_capture` takes these captured values and exact actual/expected native SHA. It has no device imports or current-time access. Compare all bitmap/matrix bytes; matching pixels alone do not establish installed source ownership. Graphics uses its separate oracle. The public ordinary A+C host's frozen older text oracle is insufficient for this new target; use an explicitly reviewed cursor adapter and fresh purpose-specific proof/guard.

## Cost and acceptance limits

Independent canonical80-column blank/q0 examples measured5712 modeled6510cycles/1480DMAbytes fromTEXT, or4471cycles/noDMA fromwarmFILE. Returning toTEXT adds1264bytes; an alreadyTEXT frame therefore incurs2744bytes/four commands plus ordinary cache traffic. These are examples, not worst-case or physical timing measurements. The bounded math uses the existing exclusive FILE overlay; original replacement-window callers are rejected before a nested call hides provenance.

Independent review passes69 focused group executions,24 direct tests including three new controls, four complete actualPeddle bitmap/matrix captures and the same old/new underline counterexample. Review c3250a03 and author cfec4485 remain immutable under agentworking/scratch. Combined ROOT validation is recorded separately in evidence/cga-cursor-root-20261016.json. OriginalTURBO, physical cursor/human acceptance and performance require fresh final-pair runs.
