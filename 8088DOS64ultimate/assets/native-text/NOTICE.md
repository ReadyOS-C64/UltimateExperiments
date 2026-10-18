# Native CP437-compatible font

`cp437-unscii8.bin` is 256 glyphs × eight scanlines, MSB at the left. It is remapped from the **8-pixel Unscii** font by Ville-Matias “Viznut” Heikkilä and contributors. This is a usable CP437-compatible face, not an assertion of byte-identical IBM CGA ROM shapes.

Primary source: [viznut/unscii](https://github.com/viznut/unscii/tree/257b4dfeb50651510fe8b9cf4f151a148a4490e4), commit `257b4dfeb50651510fe8b9cf4f151a148a4490e4`. The vendored `README.md` is the exact upstream notice: Public Domain or CC0, except specifically identified Unifont-derived files. Only `fontfiles/unscii-8.hex` is used here; no Unifont, `unscii-16-full`, or GPL conversion program is used.

Normal CP437 bytes 20–7E and 80–FF use Python’s stable CP437 mapping. Bytes 01–1F and 7F use the familiar PC graphics symbols rather than Unicode controls. NUL is blank. Unscii lacks U+263C (sun), U+2302 (house), U+2310 (reversed not), and U+2219 (bullet operator). These four small replacement glyphs and the explicit blank NUL were drawn specifically for this project. They are dedicated to the public domain under CC0 1.0. Exact mapping, replacements and source/derived SHA-256 identities are in `provenance.json`.

Rebuild offline with `python3 build_support/native_text_font.py`; check with `--check`. Attribution is retained even though the upstream dedication does not require it. The binary’s SHA-256 is `94fb2992461e7b79fcb3514d077727f33e5ee4f9d993f40f0aaeabf9c8f1ac30`.
