# Separate terminal-byte correctness fix

This fix is independent of the unregistered R29/CR rendering prototype. Only
the current C33 paragraph controller changes. It adds no CR fast path.

Actual public Plain Return at the end of a short logical row reproduced wrong
pixels in both immutable original946 and released geometry fit11: source bytes
were correct, but route2 left following rows unmoved. The old validation loop
tested `LS_COL>=LS_COUNT` before checking the insertion position. At a terminal
insertion it therefore never consumed/authenticated the inserted byte; the new
CR could be mistaken for the existing line-ending CR.

The loop now tests the insertion position first, then checks the old-byte bound
before reading an old byte. Deletion still checks its bound before `P,x` access.
An inserted terminal CR reaches the existing `long_alnum` refusal, so the normal
renderer handles its geometry. Ordinary terminal glyphs are consumed and staged
correctly. No source/packet/provider/CRC/semantic guard is removed.

Seven local same-condition long-branch macros can use assembler-range-checked
short branches (four emitted expansions shrink). This recovers12 bytes; the
correct loop costs8, yielding CODE+RODATA through BEF9 inclusive,6 bytes before
the unchanged BF00 font. The padded C33 remains4096. R25 is byte-identical to
each supplied frozen product, with its actual native-font CRC witnesses.

Current source-matched build:

```
python3 src/render/grid/probes/row-geometry-extend/cr/terminal-fix.py build/UNIQUE build/geometry-current/20261026T194808512494Z/fixture
python3 tests/test_grid_cr_terminal.py --fixture build/UNIQUE/fixture --out build/UNIQUE-proof
```

The builder first reconstructs actual current C33 and R25 SEO bytes exactly,
then applies only range-proven short branches and the terminal loop reorder.
No shared build/labels are read or written. The exact complete controller delta
is `build/grid-cr-terminal-current/controller.patch`; its generated canonical
controller is under `tree/src/render/grid/paragraph/controller.inc`.

Current candidate SHA256:
`5dac796bd1d81907be37ddd51d9acc7a984ab7c4304427502cb77a720a9c919c`.
The old946-linked candidate is
`15a4f42875b7c66fcba74f19814169b430b1fc8cfc886c758c09d2c282ec4d0d`.

Receipts distinguish these facts:

- `build/grid-cr-legacy-end-{original946,probe}/result.json`: both original and
  released geometry reproduce the bug at both widths.
- `build/grid-cr-terminal-fixed-{old,current}/result.json`: both linked fixes
  repair the exact terminal-CR case through safe fallback.
- `build/grid-cr-terminal-current-proof/result.json`:108 public frames and10
  prewrite/refusal/repair cases. Plain/Full,60/80, empty/short/full/wrapped row,
  CR/glyph insertion and BACK, real Undo/Redo, exact independent bitmap/attrs,
  Plain packets/anchors/NC, source/history and checked whole16MiB protection.
- `build/grid-cr-terminal-current-stack/proof/result.json`:all59 actual images,
  foreground52 plus one IRQ/NMI16, relative combined68.

These are CPU instruction/IEC fixture proofs. They are not native VICE, disk
registration, physical keyboard or CR performance claims. True CR split/merge
acceleration remains separate unfinished work under the R29 prototype.
