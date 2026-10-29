.ifndef SE_NARROW_API
SE_NARROW_API=1
; X/Y -> caller-owned NR_SIZE-byte frame. Neither pointer pair is allocated by
; these modules: the foreground caller loans two existing zero-page pairs.
.importzp se_nr_context,se_nr_pointer
.global se_narrow_row,se_narrow_resolve_tile
NR_MODE=0                 ;60 or80
NR_ROW=1                  ;physical logical row0..24
NR_COUNT=2                ;input cells; clipped to mode width
NR_ENCODING=3             ;0=shared native PETSCII converter,1=raw screen codes
NR_BACKGROUND=4           ;low nibble, normally ReadyOS blue6
NR_BITMAP=5               ;full framebuffer base, aligned8KiB,$2000..$A000
NR_ATTRIBUTES=7           ;1KiB-aligned matrix,$0400..$C000
NR_FONT=9                 ;existing128x8 narrow5/narrow4 font
NR_CHARACTERS=11          ;caller arrays, at least min(count,width) bytes each
NR_ROLES=13               ;SuperMark IDs0..13; unknown maps to normal0
NR_FLAGS=15               ;bit0 inverse; bit1 selection; bit2 caret
NR_PALETTE=17             ;14 caller-supplied foreground colors, low nibbles
NR_INPUT_SIZE=19
; Mutable scratch, entirely caller-owned. Do not alias inputs or output here.
NR_BITMAP_PTR=19
NR_ATTRIBUTE_PTR=21
NR_FONT_PTR=23
NR_LIMIT=25
NR_INDEX=26
NR_PITCH=27
NR_MASK=28
NR_OFFSET=29
NR_REVERSE=30
NR_SELECT=31
NR_ROLE=32
NR_NEXT=33
NR_SHIFT=34
NR_SIDE=35
NR_Y=36
NR_INK=37
NR_PAINT=38
NR_TILE=39
NR_BEST_WEIGHT=40
NR_BEST_RANK=41
NR_BEST_ROLE=42
NR_TEMP=43
NR_HISTOGRAM=44            ;14 one-byte ink counts, each<=64
NR_CACHE=58                ;8 base glyph rows before selection/caret
NR_GLYPH=66
NR_FRAGMENT_MASK=67
NR_SIZE=68
NR_INVERSE=1
NR_SELECTED=2
NR_CARET=4
NR_ARGUMENT=$90
.endif
