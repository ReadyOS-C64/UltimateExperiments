# Coherent native text row renderer

The TEXT overlay renders one bounded row for BIOS text modes 0–3, 40 or 80 columns. It reads mutable BDA/page/CGA data through the actual coherent guest cache, including dirty guest changes. Caller supplies row 0–24 and blink phase. Output is the 8,000-byte VIC bitmap at 6000 and 1,000-byte matrix at 4000; input is a caller-installed 256×8 font at 4800. The routine does not install a font or configure the VIC.

Forty columns retain all eight glyph pixels. Eighty columns OR adjacent pixel pairs into four-pixel glyphs and combine two characters into one VIC cell. The left character's attribute chooses the shared foreground/background; each character retains its own blink visibility. RGBI colors are approximated to the C64 palette. This explicit color compromise does not establish physical readability.

Each row validates mode/columns/page/row before output. Completed cell count advances only after all eight bitmap bytes and its color byte are committed. Cache/partial writeback failures report progress and allow retry without a stale REU bypass. The caller schedules complete rows between CPU calls; no IRQ or asynchronous renderer is provided.

Eight assembly tests execute 600 valid mode/page/row combinations, every attribute, blink, all output bytes/font/guards, dirty single-frame guest state and injected failures. Direct ABI tests run only with TEXT acquired and locked; runtime callers use resident `dos64_overlay_render_text_row`. Code/table size is 906 bytes and resident state 19 bytes, no additional ZP/E000 BSS. [Evidence](../agentworking/evidence/overlays-dispatch-20261015.json).

Font/VIC presentation and cursor remain private/unlinked. CGA graphics modes 4/5/6 have logical BIOS behavior but no accepted native graphics renderer. Physical display/input/latency are not implied by bitmap equality.
