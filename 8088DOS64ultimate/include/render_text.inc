.ifndef DOS64_RENDER_TEXT_INC
DOS64_RENDER_TEXT_INC = 1
; Native input: packed4x8 font4400–47FF for80 columns, full8x8 font4800–4FFF
; for40 columns. Caller owns released bitmap lifetime and held TEXT lock.
; One synchronous row; input row 0..24, blink 0=hidden / 1=visible.
; Native production samples dos64_cga_cursor_sample at frame row0 before TEXT.
; phase_valid A5 means captured field; FF stale refuses before pixel stores.
; phase_valid0 is only the unrequested isolated glyph-fixture contract.
; Hardware start must match BDA page. Visible inverted cursor shape refuses.
; Cursor ORs foreground after glyph blink; 80-column pairs keep left palette.
; done counts fully committed native 8x8 cells, 0..40 (two chars in 80 cols).
RT_ROW = 0
RT_BLINK = 1
RT_DONE = 2
RT_STATUS = 3
RT_ERROR = 4
RT_SIZE = 5
RT_OK = 1
RT_FAILED = 2
RT_ERR_ARGUMENT = 1
RT_ERR_CACHE = 2
RT_ERR_CURSOR = 3
.endif
