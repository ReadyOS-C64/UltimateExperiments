.ifndef SE_GEOS_GLYPH_API
SE_GEOS_GLYPH_API=1
.importzp se_gg_context,se_gg_pointer
.global se_geos_measure,se_geos_glyph
GG_VALUE=0
GG_ENCODING=1             ;0 native PETSCII,1 raw screen code with bit7 inverse
GG_STYLE=2                ;bit0 bold,bit1 italic
GG_FLAGS=3                ;bit0 inverse, unioned with raw inverse
GG_FONT=4                 ;verified existing packed BSW9,744 bytes
GG_WIDTHS=6               ;verified existing mapped widths,128 bytes
GG_NATIVE=8               ;existing mixed-case128x8 PETSCII fallback font
GG_CLIP_LEFT=10           ;local half-open clip, horizontal0..16,vertical0..9
GG_CLIP_RIGHT=11
GG_CLIP_TOP=12
GG_CLIP_BOTTOM=13
GG_INPUT_SIZE=14
GG_VALID=14               ;0 invalid,1 metrics,2 raster+metrics
GG_SCREEN=15
GG_KIND=16                ;0 packed BSW,1 native fallback
GG_WIDTH=17
GG_ADVANCE=18
GG_BASELINE=19            ;6
GG_HEIGHT=20              ;9-pixel common line cell, native ninth row blank
GG_INK=21                 ;9 big-endian,left-aligned16-bit clipped ink rows
GG_COVERAGE=39            ;9 corresponding clipped cell masks
GG_INDEX=57
GG_START=58
GG_END=60
GG_ROW_POINTER=62
GG_ROW=64
GG_PHASE=65
GG_WORD_HI=66
GG_WORD_LO=67
GG_CELL_HI=68
GG_CELL_LO=69
GG_CLIP_HI=70
GG_CLIP_LO=71
GG_REVERSE=72
GG_TEMP=73
GG_SHIFT=74
GG_COVER_HI=75
GG_COVER_LO=76
GG_SIZE=77
GG_BOLD=1
GG_ITALIC=2
GG_ARGUMENT=$90
GG_FORMAT=$94
.endif
