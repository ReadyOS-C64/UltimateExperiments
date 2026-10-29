# Packed GEOS BSW/9 glyph services

These are isolated measure/raster micromodules. They do not draw to a framebuffer,
choose tile colors, mutate a document, allocate, load overlays or switch modes.
They use the existing local English BSW/9 extraction without touching media.

`se_geos_measure` and `se_geos_glyph` take X/Y = low/high address of a caller-owned
77-byte frame from `api.inc`. A/X/Y/P and the two borrowed pointer pairs are
clobbered. The caller supplies aliases `se_gg_context` and `se_gg_pointer` to its
existing foreground pairs, owns the frame/fonts, and excludes competing users.
There is no resident BSS/ZP allocation. Calls are foreground-only/nonreentrant.
The isolated fixture aliases $F0/$F2; production may reuse text_ptr/screen_ptr.

The first14 frame bytes are immutable input: value, encoding, style, inverse
flag, pointers to packedfont/widths/native fallback, and a local half-open clip
rectangle. Horizontal clip endpoints are0..16; vertical endpoints0..9. Empty or
reversed windows succeed with empty raster masks; advance remains unchanged.
Arrays and frame must be valid accessible nonoverlapping RAM. This API is not a
general pointer/allocator service.

Native input calls the actual shared `se_petscii_screen`; raw-screen input uses
all128 indices and bit7 inverse. Explicit inverse and raw inverse are unioned.
The algorithmic screen-to-BSW mapping exactly preserves the existing extractor:
both cases, punctuation, @ and brackets map where available. All other graphics
use the caller's existing mixed-case128x8 native font at baseline6, with an empty
ninth row before inverse. There is no silent space substitution.

The profile is specifically the verified English BSW/9: baseline6, height9,
stride60, index offset8 and raster offset204, packed length744. Each measure
checks the eight-byte profile header and mapped width1..8; native fallback width
must be8. Raster checks packed index ordering, end<=480 and agreement with the
mapped width. It reads a second raster byte only when the glyph actually crosses
a byte boundary. The original raw97-character span includes unused wider glyphs;
this service intentionally preserves the existing mapped128-glyph profile.

Normal advance equals the mapped width. Bold ORs each row with a right shift by
one and adds1 to advance. Italic shifts rows0..2 by2, rows3..5 by1 and rows6..8
by0, adding2 to advance. Combined applies both and adds3. Baseline/line height
remain6/9, preserving descenders. Full glyph ink is clipped to its declared
cell and caller rectangle; adjacent glyph cells are never painted here.

Output valid0 means unusable; valid1 means metrics only; valid2 means raster and
metrics. Measure leaves both raster planes untouched. Successful raster returns
nine big-endian left-aligned16-bit ink words and nine corresponding coverage
words, clipped to the local rectangle. Coverage includes spaces and the styled
advance, so the compositor can apply selection/caret once to their union. It
owns absolute placement, damage scheduling, background/tile arbitration and
source hit testing. The glyph service cannot request a third tile color.

Success is C clear/A0; invalid input is C set/A$90; invalid profile/width/index is
C set/A$94, valid0. Other mutable outputs are undefined on refusal; immutable
inputs and all memory outside the caller frame/loaned pairs/CPU stack remain
unchanged. Font CRC/provenance verification belongs to the asset loader; the
profile checks are bounded structural checks, not a replacement for that seal.

Sizes from the isolated linker map: measure CODE340/RODATA8 =348 bytes; raster
CODE703/RODATA34 =737; packed744 + widths128 =872. Total1957 bytes, or2013 when
linking the existing56-byte shared PETSCII converter in the standalone fixture.
No2304-byte expanded font is linked. Measure-only links without raster. The
caller supplies its existing native fallback font; this module embeds no copy.

Run `python3 tests/test_geos_glyphs.py`. It independently decodes packed bits and
proves all128 normal glyphs equal the existing M1 expanded asset, then tests
every native/raw value, all four styles and inverse combinations, every local
horizontal/vertical boundary, corrupted profiles/widths/indices, full RAM guards,
the1024-byte ReadyOS shim and whole512KiB REU. Alternating frames cross a page
boundary without changing inactive state. A tiny native helper batches the
existing Peddle single-step API; no glyph result is substituted.

Measured maximum:194 instructions for measure and2485 for a complete glyph.
The wrapper cycle field does not advance; no cycle, VIC, readability, editor or
interactive timing claim is made. The live editor now links these services through R21 and its bounded page
controller. The original M1 display probes under `probes/side_views` remain
separate historical evidence. See [packet ABI2](editor-cache-README.md) for the
current editor cache and continuation contracts.
