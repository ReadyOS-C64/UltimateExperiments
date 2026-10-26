# Complete native-row descriptor, private release

This is a C33-only space recovery. It changes neither source admission nor the
native renderer. `descriptor.py` first rebuilds the terminal-corrected C33 and
R25 exactly, then replaces repeated constant stores and the68-byte zero loop
with one19-byte input template. Width/count and physical row are overwritten
with their authenticated live values. Every public NR input is initialized.

`render/narrow/api.inc` declares inputs0..18 and worker-owned mutable scratch
19..67. No scratch byte is a public input. The actual packaged R16/R17 leaves
are tested with all256 glyph values at both widths, including inverse,
selection/caret combinations, plus16 mixed/partial rows per width. Scratch00
andA7 runs give identical independent per-pixel/color-vote results and identical
instruction counts:544 vectors,1088 actual6510 calls. All input bytes remain
exact. Full64KiB outside-row/frame/borrowed-pointer/stack guards and whole16MiB
REU equality pass. This component uses explicit input packets, not fabricated
editor source/cache authority.

Build:

```
python3 src/render/grid/probes/row-geometry-extend/cr/descriptor.py \
  build/grid-nr-descriptor-fit build/grid-cr-terminal-current/tree \
  build/grid-cr-terminal-current/fixture
python3 tests/test_grid_nr_descriptor.py \
  --fixture build/grid-cr-terminal-current/fixture \
  --out build/grid-nr-descriptor-poison-retry
python3 tests/test_grid_cr_terminal.py \
  --fixture build/grid-nr-descriptor-fit/fixture \
  --out build/grid-nr-descriptor-public
```

The control C33 matches committed454396b fixture
`build/terminal-committed/20261026T203908556792Z/fixture` byte for byte.
Candidate C33 SHA256:
`fb3e6a86c658bb5bc345167403e4b9137a94a47d12faefeae26e8a84ed629c3b`.
Actual CODE/RODATA end movesBEF9→BED1:40 bytes recovered,46 bytes beforeBF00.
Payload4096 includes fixed native/status font; R25 is byte-identical. No new
overlay calls, BSS, zero page, asset or resident code. Actual public108 frames
and10 prewrite/refusal/repair cases pass, including Plain/Full60/80 terminal
CR and glyph insertion/BACK, Undo/Redo, exact pixels, Plain packets/anchors/NC,
source/history/shim and checked whole16MiB. Of96 measured ordinary edit
intervals, savings are0..153 instructions (2142 total), with no regression.

This is not a CR acceleration or native timing claim. The R29 complete CR
transaction remains separate unfinished work; no new asset is registered here.
