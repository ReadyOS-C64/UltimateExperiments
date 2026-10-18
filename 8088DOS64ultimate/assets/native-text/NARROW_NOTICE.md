# Packed 4×8 font for 80-column text

The 95 printable ASCII glyphs, sixteen CP437 single-line/block glyphs and blank NUL are original drawings for this project, dedicated to the public domain under CC0 1.0. The ordinary text shapes occupy three pixels plus a blank separating column. 0/O and 1/I/l have deliberately different shapes.

Other extended CP437 glyphs use an explicitly recorded fallback: adjacent pairs from the licensed 8×8 Unscii-derived font are combined by OR. Its upstream attribution, pinned provenance and license remain in [NOTICE.md](NOTICE.md). The fallback is not a claim of improved readability for every extended symbol.

`build_support/narrow_font.py` reproduces all 1,024 bytes offline; `--check` verifies the binary, row table and source provenance without modifying them. `narrow-provenance.json` pins every original glyph, fallback identity, generator identity and packed asset hash. Each character uses four bytes, even scanline in the high nibble, odd scanline in the low nibble; bit 3 is leftmost.

This font is loaded at 4400–47FF as non-executable startup data. The unchanged full 8×8 font remains at 4800–4FFF for 40-column text.
