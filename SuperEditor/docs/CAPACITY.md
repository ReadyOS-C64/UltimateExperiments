# Capacity and tested limits

The current combined63-overlay package also passes a bounded native smoke with
an actual2MiB REU:32 detected banks, exact2,097,152-byte dumps and14 occupied
banks for the422-byte diverse document. All63 images and the complete fontpack,
source40/80/GEOS, formatted preview and paged Help are checked. This proves that
small-document workflow, not maximum source/append quota or all2MiB workloads.


The full development configuration uses a 16 MiB REU. A bounded CPU test of the
1612523 engine reaches exactly **1,048,576 source bytes**, with a separate
16-bank append object. It verifies BOF/middle/EOF edits, Undo/Redo, copy/paste,
replacement at the limit and refusal above it. It uses Plain rendering, modeled
ROM/source import and real hot-window APIs for far placement. It does not prove
1 MiB disk I/O, Full-mode speed or global navigation speed.

| Resource | Current limit or behavior |
| --- | --- |
| Original source object | 1–16 banks of 64 KiB |
| Append object | Separate finite allocation; old source extents remain immutable |
| Source quota | Derived from the original object's allocation; up to 1 MiB |
| Small file opened from disk | Original quota rounds up to the next 64 KiB bank; a tiny file normally gets a 64 KiB quota |
| Object slots | 8; optional analysis may be retired to admit required work |
| Piece storage | 2,048 entries, with at most 32 active leaves |
| History record arenas | 45,056 active bytes plus 20,480 staging bytes; finite linear history |
| Overlay catalog | 62 registered images, capacity 64; four REU code banks |
| GEOS font pack | 74,432 bytes across two checked REU banks |

At source quota, an extra byte is refused before modifying the source, pending
edit, caret/selection, history or observer. Equal-length replacement and Undo
remain usable. A copy or append/history allocation can independently exhaust
its own resource; free physical REU space alone does not guarantee admission.
Opening another file starts a new history. The current program does not offer
a quota-setting dialog or unlimited history.

A D81 image is only 819,200 bytes including its filesystem. It cannot contain a
1 MiB document. Editor overlays, fonts and samples further reduce free disk
space. Save replacement also needs space for the staged file while retaining
the previous file until promotion. A nearly full disk can therefore refuse a
save even when the final document itself would fit after replacement.

The full font configuration does not support a 512 KiB REU. Historical native
cold-boot/edit/save tests cover 1 MiB and 2 MiB REUs; they are workload-specific,
not universal capacity promises for every history/clipboard/cache combination.
The current bounded 1 MiB document test uses a 16 MiB provider. Source import,
rendering, navigation and IEC transfer costs must be measured separately.

Reproduce the bounded engine proof with
`tests/test_supereditor_capacity_limits.py --fixture FROZEN_FIXTURE --out NEW_OUTPUT`.
Its recorded release is `build/capacity-limits-current/release/manifest.json`.
The test includes full 16 MiB typed-DMA comparisons, all immutable original
banks, a retained foreign bank, independent pixels and source/history/observer
checks. A separately preserved public LEFT operation in a huge logical line
took 45.47 million CPU instructions; this capacity result is not a performance
claim. Exhaustive piece/history exhaustion and final-cohort lower-memory native
acceptance remain separate gates.
