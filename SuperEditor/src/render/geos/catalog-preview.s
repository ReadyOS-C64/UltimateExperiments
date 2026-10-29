.setcpu "6502"
.macpack longbranch
.include "render/geos/catalog-glyph.inc"
.import se_petscii_screen
.export se_geos_catalog_measure,se_geos_catalog_glyph
.export se_geos_catalog_measure_preview,se_geos_catalog_glyph_preview
.import se_gf_fetch_preview,se_f_owner
.include "render/geos/font-store.inc"
P=212
R=214
S=216
B=218
ROW=220
SM=221
D=222
W=226
CELL=230
CLIP=234
COUNT=238
KIND=239
.segment "CODE"
; Isolated byte-decoder candidate. Public scalar/font/capability guards unchanged.
se_geos_catalog_measure:
    jsr measure_context
    jcs measure_failed
    lda #0
    beq measure_init
se_geos_catalog_measure_preview:
    lda se_f_owner
    cmp #4
    jne preview_busy
    jsr measure_context
    jcs measure_failed
    lda #1
measure_init:
    ldy #COUNT
    sta (se_gg_context),y
    lda #0
    ldy #CG_VALID
    sta (se_gg_context),y
    ldy #CG_ENCODING
    lda (se_gg_context),y
    cmp #3
    jcs argument
    iny
    lda (se_gg_context),y
    cmp #8
    jcs argument
    iny
    lda (se_gg_context),y
    cmp #2
    jcs argument
    ldy #CG_LEFT
    ldx #2
@horizontal:
    lda (se_gg_context),y
    cmp #33
    jcs argument
    iny
    dex
    bne @horizontal
    ldx #2
@vertical:
    lda (se_gg_context),y
    cmp #25
    jcs argument
    iny
    dex
    bne @vertical
    ldy #CG_NATIVE
    jsr pointer
    lda #0
    ldy #CLIP
    sta (se_gg_context),y
    lda #4
    iny
    sta (se_gg_context),y
    jsr span
    jcs argument
    lda #0
    ldy #KIND
    sta (se_gg_context),y
    ldy #CG_FONT
    lda (se_gg_context),y
    iny
    ora (se_gg_context),y
    iny
    ora (se_gg_context),y
    iny
    ora (se_gg_context),y
    bne @packed_font
    lda #8
    ldy #CG_HEIGHT
    sta (se_gg_context),y
    lda #6
    iny
    sta (se_gg_context),y
    lda #2
    ldy #KIND
    sta (se_gg_context),y
    jmp mapping
@packed_font:
    ldy #CG_LENGTH
    lda (se_gg_context),y
    ldy #CLIP
    sta (se_gg_context),y
    ldy #CG_LENGTH+1
    lda (se_gg_context),y
    cmp #$11
    jcs argument
    ldy #CLIP+1
    sta (se_gg_context),y
    cmp #0
    bne :+
    ldy #CLIP
    lda (se_gg_context),y
    cmp #202
    jcc argument
:   ;4210 is largest inventoried record; reject unrelated trailing memory.
    ldy #CG_LENGTH+1
    lda (se_gg_context),y
    cmp #$10
    bcc :+
    ldy #CLIP
    lda (se_gg_context),y
    cmp #$73
    jcs argument
:   ldy #CG_FONT
    jsr pointer
    jsr span
    jcs argument
    ldy #COUNT
    lda (se_gg_context),y
    beq :+
    jsr preview_authenticate
    jcs measure_failed
:   ldy #CG_FONT
    jsr pointer
    ldy #3
    lda (se_gg_pointer),y
    jeq format
    cmp #25
    jcs format
    ldy #CG_HEIGHT
    sta (se_gg_context),y
    ldy #0
    lda (se_gg_pointer),y
    ldy #CG_BASELINE
    sta (se_gg_context),y
    ldy #CG_HEIGHT
    cmp (se_gg_context),y
    jcs format
    ldy #4
    lda (se_gg_pointer),y
    cmp #8
    jne format
    iny
    lda (se_gg_pointer),y
    jne format
    ldy #6
    lda (se_gg_pointer),y
    cmp #202
    beq :+
    cmp #204
    jne format
:   ldy #B
    sta (se_gg_context),y
    ldy #7
    lda (se_gg_pointer),y
    jne format
    ldy #1
    lda (se_gg_pointer),y
    ldy #S
    sta (se_gg_context),y
    ldy #2
    lda (se_gg_pointer),y
    cmp #2
    jcs format
    ldy #S+1
    sta (se_gg_context),y
    ldy #S
    ora (se_gg_context),y
    jeq format
    ; Exact end = bitmapoffset + stride*height, all16bit.
    ldy #B
    lda (se_gg_context),y
    ldy #CLIP
    sta (se_gg_context),y
    lda #0
    iny
    sta (se_gg_context),y
    ldy #CG_HEIGHT
    lda (se_gg_context),y
    tax
@extent:
    ldy #CLIP
    lda (se_gg_context),y
    clc
    ldy #S
    adc (se_gg_context),y
    ldy #CLIP
    sta (se_gg_context),y
    iny
    lda (se_gg_context),y
    ldy #S+1
    adc (se_gg_context),y
    ldy #CLIP+1
    sta (se_gg_context),y
    dex
    bne @extent
    ldy #CG_LENGTH
    lda (se_gg_context),y
    ldy #CLIP
    cmp (se_gg_context),y
    jne format
    ldy #CG_LENGTH+1
    lda (se_gg_context),y
    ldy #CLIP+1
    cmp (se_gg_context),y
    jne format
    ; Full index ordering and bounds; preserve selectedmetrics until validated.
    lda #0
    ldy #P
    sta (se_gg_context),y
    iny
    sta (se_gg_context),y
    ldy #S
    lda (se_gg_context),y
    ldy #R
    sta (se_gg_context),y
    ldy #S+1
    lda (se_gg_context),y
    ldy #R+1
    sta (se_gg_context),y
    ldx #3
@bits:
    ldy #R
    lda (se_gg_context),y
    asl
    sta (se_gg_context),y
    iny
    lda (se_gg_context),y
    rol
    sta (se_gg_context),y
    dex
    bne @bits
    ; Existing strict path retains its complete96/97-entry index validation.
    ldy #COUNT
    lda (se_gg_context),y
    jne mapping
    ldy #B
    lda (se_gg_context),y
    sec
    sbc #8
    lsr
    ldy #COUNT
    sta (se_gg_context),y
    lda #8
    ldy #ROW
    sta (se_gg_context),y
@index:
    ldy #ROW
    lda (se_gg_context),y
    tay
    lda (se_gg_pointer),y
    tax
    iny
    lda (se_gg_pointer),y
    ldy #CLIP+1
    sta (se_gg_context),y
    txa
    dey
    sta (se_gg_context),y
    ldy #ROW
    lda (se_gg_context),y
    cmp #8
    bne :+
    ldy #CLIP
    lda (se_gg_context),y
    iny
    ora (se_gg_context),y
    jne format
:   ; P<=current<=rowbits.
    jsr ordered
    jcs format
    ldy #R+1
    lda (se_gg_context),y
    ldy #CLIP+1
    cmp (se_gg_context),y
    jcc format
    bne :+
    ldy #R
    lda (se_gg_context),y
    ldy #CLIP
    cmp (se_gg_context),y
    jcc format
:   ldy #CLIP
    lda (se_gg_context),y
    ldy #P
    sta (se_gg_context),y
    ldy #CLIP+1
    lda (se_gg_context),y
    ldy #P+1
    sta (se_gg_context),y
    ldy #ROW
    lda (se_gg_context),y
    clc
    adc #2
    sta (se_gg_context),y
    ldy #COUNT
    lda (se_gg_context),y
    sec
    sbc #1
    sta (se_gg_context),y
    bne @index
mapping:
    ; Native screen conversion matches existing BSW measure exactly.
    ldy #CG_FLAGS
    lda (se_gg_context),y
    lsr
    lda #0
    ror
    ldy #KIND
    ora (se_gg_context),y
    sta (se_gg_context),y
    ldy #CG_ENCODING
    lda (se_gg_context),y
    beq @native
    cmp #2
    bne @raw_screen
    jsr raw_ascii
    bcc :+
    rts
:   jmp @mapped
@raw_screen:
    ldy #CG_VALUE
    lda (se_gg_context),y
    bpl :+
    lda #$80
    ldy #KIND
    ora (se_gg_context),y
    sta (se_gg_context),y
    ldy #CG_VALUE
    lda (se_gg_context),y
:   and #127
    jmp @screen
@native:
    ldy #CG_VALUE
    lda (se_gg_context),y
    jsr se_petscii_screen
@screen:
    ldy #CG_SCREEN
    sta (se_gg_context),y
    ldy #KIND
    lda (se_gg_context),y
    and #2
    jne @fallback
    ldy #CG_SCREEN
    lda (se_gg_context),y
    cmp #1
    bcc @at
    cmp #27
    bcc @lower
    beq @bracket
    cmp #29
    beq @bracket
    cmp #32
    bcc @fallback
    cmp #64
    bcc @ordinary
    cmp #65
    bcc @fallback
    cmp #91
    bcs @fallback
@ordinary:
    sec
    sbc #32
    jmp @mapped
@at:
    lda #32
    bne @mapped
@lower:
    clc
    adc #64
    bne @mapped
@bracket:
    clc
    adc #32
@mapped:
    asl
    clc
    adc #8
    tay
    lda (se_gg_pointer),y
    pha
    tya
    ldy #ROW
    sta (se_gg_context),y
    pla
    ldx #0
@copy_index:
    pha
    txa
    clc
    adc #P
    tay
    pla
    sta (se_gg_context),y
    inx
    cpx #4
    beq @width
    ldy #ROW
    lda (se_gg_context),y
    clc
    adc #1
    sta (se_gg_context),y
    tay
    lda (se_gg_pointer),y
    jmp @copy_index
@width:
    ldy #R
    lda (se_gg_context),y
    sec
    ldy #P
    sbc (se_gg_context),y
    tax
    ldy #R+1
    lda (se_gg_context),y
    ldy #P+1
    sbc (se_gg_context),y
    jne format
    txa
    cmp #25
    jcs format
    pha
    ldy #COUNT
    lda (se_gg_context),y
    beq :+
    jsr preview_selected_bounds
    bcs @selected_error
:   pla
    jmp @metrics
@selected_error:
    pla
    jmp format
@fallback:
    ldy #KIND
    lda (se_gg_context),y
    ora #1
    sta (se_gg_context),y
    ldy #CG_SCREEN
    lda (se_gg_context),y
    ldy #P
    sta (se_gg_context),y
    lda #0
    iny
    sta (se_gg_context),y
    ldx #3
@native_offset:
    ldy #P
    lda (se_gg_context),y
    asl
    sta (se_gg_context),y
    iny
    lda (se_gg_context),y
    rol
    sta (se_gg_context),y
    dex
    bne @native_offset
    ldy #P
    lda (se_gg_context),y
    clc
    ldy #CG_NATIVE
    adc (se_gg_context),y
    ldy #P
    sta (se_gg_context),y
    iny
    lda (se_gg_context),y
    ldy #CG_NATIVE+1
    adc (se_gg_context),y
    ldy #P+1
    sta (se_gg_context),y
    lda #8
@metrics:
    ldy #CG_WIDTH
    sta (se_gg_context),y
    ldy #KIND
    lda (se_gg_context),y
    and #2
    beq :+
    lda #0
    beq @style_advance
:   ldy #CG_STYLE
    lda (se_gg_context),y
    and #3
@style_advance:
    ldy #CG_WIDTH
    clc
    adc (se_gg_context),y
    iny
    sta (se_gg_context),y
    lda #1
    ldy #CG_VALID
    sta (se_gg_context),y
success:
    lda #0
    clc
    rts
bad_context:
argument:
    lda #CG_ARGUMENT
    sec
    rts
format:
    lda #CG_FORMAT
    sec
    rts
raw_ascii:
    ldy #KIND
    lda (se_gg_context),y
    and #2
    jne argument
    ldy #CG_VALUE
    lda (se_gg_context),y
    cmp #32
    jcc argument
    cmp #128
    bcc :+
    jne argument
    ldy #B
    lda (se_gg_context),y
    cmp #204
    jne argument
    lda #128
:   ldy #CG_SCREEN
    sta (se_gg_context),y
    sec
    sbc #32
    clc
    rts
; P<=CLIP? no stores.
ordered:
    ldy #P+1
    lda (se_gg_context),y
    ldy #CLIP+1
    cmp (se_gg_context),y
    bcc @yes
    bne @no
    ldy #P
    lda (se_gg_context),y
    ldy #CLIP
    cmp (se_gg_context),y
    bcc @yes
    beq @yes
@no:
    sec
    rts
@yes:
    clc
    rts
pointer:
    lda (se_gg_context),y
    sta se_gg_pointer
    iny
    lda (se_gg_context),y
    sta se_gg_pointer+1
    rts
; Validate [pointer,pointer+CLIPword) and disjoint caller frame.
span:
    lda se_gg_pointer+1
    cmp #$10
    bcc @no
    cmp #$C6
    bcs @no
    lda se_gg_pointer
    clc
    ldy #CLIP
    adc (se_gg_context),y
    ldy #R
    sta (se_gg_context),y
    lda se_gg_pointer+1
    ldy #CLIP+1
    adc (se_gg_context),y
    cmp #$C6
    bcc :+
    bne @no
    ldy #R
    pha
    lda (se_gg_context),y
    tax
    pla
    cpx #0
    bne @no
:   ldy #R+1
    sta (se_gg_context),y
    ; End<=context permits the span.
    cmp se_gg_context+1
    bcc @yes
    bne @after
    ldy #R
    lda (se_gg_context),y
    cmp se_gg_context
    bcc @yes
    beq @yes
@after:
    ; Start>=context+240 permits it; otherwise overlapping.
    lda se_gg_context
    clc
    adc #CG_SIZE
    tax
    lda se_gg_context+1
    adc #0
    cmp se_gg_pointer+1
    bcc @yes
    bne @no
    txa
    cmp se_gg_pointer
    bcc @yes
    beq @yes
@no:
    sec
    rts
@yes:
    clc
    rts

.export se_geos_catalog_ink_preview
; Explicit new internal contract: owner4, frame8800 only; metrics plus INK rows
; 0..height-1. Coverage and INK afterheight stay untouched. Full APIs unaffected.
; KIND bit2 is caller-owned raster scratch, reset by every actual measure_init.
se_geos_catalog_ink_preview:
    lda se_f_owner
    cmp #4
    jne preview_busy
    cpx #0
    bne @argument
    cpy #$88
    bne @argument
    jsr se_geos_catalog_measure_preview
    jcs measure_failed
    ldy #KIND
    lda (se_gg_context),y
    ora #4
    sta (se_gg_context),y
    jmp catalog_raster
@argument:
    jmp argument
se_geos_catalog_glyph_preview:
    jsr se_geos_catalog_measure_preview
    jcs measure_failed
    jmp catalog_raster
se_geos_catalog_glyph:
    jsr se_geos_catalog_measure
    bcc catalog_raster
measure_failed:
    rts
catalog_raster:
    ; Full APIs retain192B clearing. New explicit ink-only entry never promises
    ; coverage or ink beyondheight, so clears only the liveheight ink rows.
    ldy #KIND
    lda (se_gg_context),y
    and #4
    beq @full_clear
    ldy #CG_HEIGHT
    lda (se_gg_context),y
    asl
    asl
    clc
    adc #CG_INK
    sta $8800+COUNT
    ldy #CG_INK
    lda #0
@ink_clear:
    sta (se_gg_context),y
    iny
    cpy $8800+COUNT
    bne @ink_clear
    beq @cleared
@full_clear:
    lda #0
    ldy #CG_INK
@clear:
    sta (se_gg_context),y
    iny
    cpy #CG_SCRATCH
    bne @clear
@cleared:
    ; Packed start bit -> bytepointer plus initial source mask.
    ldy #KIND
    lda (se_gg_context),y
    and #1
    bne @native_setup
    ldy #P
    lda (se_gg_context),y
    and #7
    ldy #SM
    sta (se_gg_context),y
    ldx #3
@byteoffset:
    ldy #P+1
    lda (se_gg_context),y
    lsr
    sta (se_gg_context),y
    dey
    lda (se_gg_context),y
    ror
    sta (se_gg_context),y
    dex
    bne @byteoffset
    ldy #P
    lda (se_gg_context),y
    clc
    ldy #B
    adc (se_gg_context),y
    ldy #P
    sta (se_gg_context),y
    iny
    lda (se_gg_context),y
    adc #0
    sta (se_gg_context),y
    ldy #P
    lda (se_gg_context),y
    clc
    ldy #CG_FONT
    adc (se_gg_context),y
    ldy #R
    sta (se_gg_context),y
    ldy #P+1
    lda (se_gg_context),y
    ldy #CG_FONT+1
    adc (se_gg_context),y
    ldy #R+1
    sta (se_gg_context),y
    jmp @mask_setup
@native_setup:
    ldy #P
    lda (se_gg_context),y
    ldy #R
    sta (se_gg_context),y
    ldy #P+1
    lda (se_gg_context),y
    ldy #R+1
    sta (se_gg_context),y
    lda #1
    ldy #S
    sta (se_gg_context),y
    lda #0
    iny
    sta (se_gg_context),y
    lda #0
    ldy #SM
    sta (se_gg_context),y
@mask_setup:
    ; P is dead after R receives the source pointer: retain only bit phase.
    ldy #SM
    lda (se_gg_context),y
    ldy #P
    sta (se_gg_context),y
    ; Build full cell and horizontal clip masks once.
    ldx #7
    lda #0
@zero_masks:
    ldy #CELL
    jsr indexed_store
    dex
    bpl @zero_masks
    jsr dest_mask
    ldx #0
@cell:
    ldy #CG_ADVANCE
    txa
    cmp (se_gg_context),y
    bcs @rows
    ldy #CELL
    jsr or_dest
    ldy #CG_LEFT
    txa
    cmp (se_gg_context),y
    bcc @nextcell
    iny
    cmp (se_gg_context),y
    bcs @nextcell
    ldy #CLIP
    jsr or_dest
@nextcell:
    jsr shift_dest
    inx
    bne @cell
@rows:
    ; Prepare exact source-byte count and final raw-width mask once per glyph.
    ; Every row reads ceil((phase+rawWidth)/8), at most4; width0 reads nothing.
    ldy #CG_WIDTH
    lda (se_gg_context),y
    lsr
    lsr
    lsr
    ldy #P+1
    sta (se_gg_context),y
    ldy #CG_WIDTH
    lda (se_gg_context),y
    and #7
    tax
    lda end_masks,x
    ldy #B
    sta (se_gg_context),y
    ldy #CG_WIDTH
    lda (se_gg_context),y
    clc
    ldy #P
    adc (se_gg_context),y
    adc #7
    lsr
    lsr
    lsr
    ldy #SM
    sta (se_gg_context),y
    lda #0
    ldy #ROW
    sta (se_gg_context),y
@row:
    ldy #R
    jsr pointer
    ; Explicit operation-frame specialization; every other legal CG frame
    ; retains the generic byte decoder below. No input/guard semantics change.
    lda se_gg_context
    bne @generic_row
    lda se_gg_context+1
    cmp #$88
    bne @generic_row
    jsr preview_byte_row_fast
    jmp @styled
@generic_row:
    lda #0
    ldx #3
@zero_word:
    ldy #W
    jsr indexed_store
    dex
    bpl @zero_word
    ldy #KIND
    lda (se_gg_context),y
    and #1
    beq @read
    ldy #ROW
    lda (se_gg_context),y
    cmp #8
    jcs @styled
@read:
    ldy #CG_WIDTH
    lda (se_gg_context),y
    jeq @styled
    ldy #SM
    lda (se_gg_context),y
    ldy #COUNT
    sta (se_gg_context),y
    ldx #0
@load_byte:
    txa
    tay
    lda (se_gg_pointer),y
    pha
    txa
    clc
    adc #W
    tay
    pla
    sta (se_gg_context),y
    inx
    ldy #COUNT
    lda (se_gg_context),y
    sec
    sbc #1
    sta (se_gg_context),y
    bne @load_byte
    ldy #P
    lda (se_gg_context),y
    beq @trim
    ldy #COUNT
    sta (se_gg_context),y
    ldy #CG_WIDTH
    lda (se_gg_context),y
    cmp #9
    bcs @wide_shift
@narrow_shift:
    ldy #W+1
    lda (se_gg_context),y
    asl
    sta (se_gg_context),y
    dey
    lda (se_gg_context),y
    rol
    sta (se_gg_context),y
    ldy #COUNT
    lda (se_gg_context),y
    sec
    sbc #1
    sta (se_gg_context),y
    bne @narrow_shift
    beq @trim
@wide_shift:
    ldy #W+3
    lda (se_gg_context),y
    asl
    sta (se_gg_context),y
    .repeat 3
        dey
        lda (se_gg_context),y
        rol
        sta (se_gg_context),y
    .endrepeat
    ldy #COUNT
    lda (se_gg_context),y
    sec
    sbc #1
    sta (se_gg_context),y
    bne @wide_shift
@trim:
    ; Alignment may expose the following glyph: remove every bit beyond raw
    ; width BEFORE bold/italic/underline. Width8/16/24 mask the next byte0.
    ldy #P+1
    lda (se_gg_context),y
    tax
    ldy #B
    lda (se_gg_context),y
    pha
    txa
    clc
    adc #W
    tay
    pla
    and (se_gg_context),y
    sta (se_gg_context),y
    inx
    cpx #4
    beq @styled
    lda #0
@trim_rest:
    ldy #W
    jsr indexed_store
    inx
    cpx #4
    bne @trim_rest
@styled:
    lda #0
    ldy #COUNT
    sta (se_gg_context),y
    ldy #CG_STYLE
    lda (se_gg_context),y
    and #CG_BOLD
    beq @italic
    ; D=word>>1, thenOR into originalword.
    ldx #0
    clc
@bold:
    txa
    clc
    adc #W
    tay
    lda (se_gg_context),y
    ; Carry from previous byte must survive address calculation.
    ldy #COUNT
    pha
    lda (se_gg_context),y
    lsr
    pla
    ror
    pha
    lda #0
    rol
    sta (se_gg_context),y
    pla
    ldy #D
    jsr indexed_store
    txa
    clc
    adc #W
    tay
    lda (se_gg_context),y
    pha
    txa
    clc
    adc #D
    tay
    pla
    ora (se_gg_context),y
    pha
    txa
    clc
    adc #W
    tay
    pla
    sta (se_gg_context),y
    inx
    cpx #4
    bne @bold
@italic:
    ldy #CG_STYLE
    lda (se_gg_context),y
    and #CG_ITALIC
    beq @underline
    ldy #ROW
    lda (se_gg_context),y
    asl
    clc
    adc (se_gg_context),y
    ldy #CG_HEIGHT
    cmp (se_gg_context),y
    bcc @twice
    ldy #COUNT
    sta (se_gg_context),y
    ldy #CG_HEIGHT
    lda (se_gg_context),y
    asl
    ldy #COUNT
    cmp (se_gg_context),y
    bcc @underline
    beq @underline
    lda #1
    bne @shiftword
@twice:
    lda #2
@shiftword:
    ldy #COUNT
    sta (se_gg_context),y
@shift_again:
    ldy #W
    lda (se_gg_context),y
    lsr
    sta (se_gg_context),y
    .repeat 3
        iny
        lda (se_gg_context),y
        ror
        sta (se_gg_context),y
    .endrepeat
    ldy #COUNT
    lda (se_gg_context),y
    sec
    sbc #1
    sta (se_gg_context),y
    bne @shift_again
@underline:
    ldy #CG_STYLE
    lda (se_gg_context),y
    and #CG_UNDERLINE
    beq @publish
    ldy #CG_BASELINE
    lda (se_gg_context),y
    clc
    adc #1
    ldy #ROW
    cmp (se_gg_context),y
    bne @publish
    ldx #3
@under_copy:
    txa
    clc
    adc #CELL
    tay
    lda (se_gg_context),y
    ldy #W
    jsr indexed_store
    dex
    bpl @under_copy
@publish:
    ; Per-rowclip; output wascleared, so vertical miss skips publication.
    ldy #ROW
    lda (se_gg_context),y
    ldy #CG_TOP
    cmp (se_gg_context),y
    bcc @advance
    iny
    cmp (se_gg_context),y
    bcs @advance
    ldy #KIND
    lda (se_gg_context),y
    and #4
    beq @full_output
    jsr preview_ink_publish
    jmp @advance
@full_output:
    ldx #0
@output_byte:
    txa
    clc
    adc #W
    tay
    lda (se_gg_context),y
    ldy #KIND
    pha
    lda (se_gg_context),y
    bpl :+
    pla
    pha
    txa
    clc
    adc #CELL
    tay
    pla
    eor (se_gg_context),y
    pha
:   txa
    clc
    adc #CLIP
    tay
    pla
    and (se_gg_context),y
    pha
    lda (se_gg_context),y
    pha
    ldy #ROW
    lda (se_gg_context),y
    asl
    asl
    clc
    adc #CG_COVERAGE
    sta se_gg_pointer
    txa
    clc
    adc se_gg_pointer
    tay
    pla
    sta (se_gg_context),y
    tya
    sec
    sbc #CG_COVERAGE-CG_INK
    tay
    pla
    sta (se_gg_context),y
    inx
    cpx #4
    bne @output_byte
@advance:
    ldy #R
    lda (se_gg_context),y
    clc
    ldy #S
    adc (se_gg_context),y
    ldy #R
    sta (se_gg_context),y
    iny
    lda (se_gg_context),y
    ldy #S+1
    adc (se_gg_context),y
    ldy #R+1
    sta (se_gg_context),y
    ldy #ROW
    lda (se_gg_context),y
    clc
    adc #1
    sta (se_gg_context),y
    ldy #CG_HEIGHT
    cmp (se_gg_context),y
    jcc @row
    lda #2
    ldy #CG_VALID
    sta (se_gg_context),y
    jmp success
 ; Newentryonly: context8800, full guardedmetrics, one clippedvisible row.
preview_ink_publish:
    lda $8800+ROW
    asl
    asl
    clc
    adc #CG_INK
    tay
    ldx #0
    lda $8800+KIND
    bmi @inverse
@plain:
    lda $8800+W,x
    and $8800+CLIP,x
    sta $8800,y
    inx
    iny
    cpx #4
    bne @plain
    rts
@inverse:
    lda $8800+W,x
    eor $8800+CELL,x
    and $8800+CLIP,x
    sta $8800,y
    inx
    iny
    cpx #4
    bne @inverse
    rts
 ; Only called after full measure/FD/context admission, context exactly8800.
; Same caller-owned scratch; source pointer already R. Reads the exact selected
; row-byte span, aligns MSB-left, removes adjacent-font bits before styles.
preview_byte_row_fast:
    lda #0
    sta $8800+W
    sta $8800+W+1
    sta $8800+W+2
    sta $8800+W+3
    lda $8800+KIND
    and #1
    beq @read
    lda $8800+ROW
    cmp #8
    bcs @done
@read:
    lda $8800+CG_WIDTH
    beq @done
    ldy #0
@load:
    lda (se_gg_pointer),y
    sta $8800+W,y
    iny
    cpy $8800+SM
    bne @load
    ldx $8800+P
    beq @trim
    lda $8800+CG_WIDTH
    cmp #9
    bcs @wide
@narrow:
    asl $8800+W+1
    rol $8800+W
    dex
    bne @narrow
    beq @trim
@wide:
    asl $8800+W+3
    rol $8800+W+2
    rol $8800+W+1
    rol $8800+W
    dex
    bne @wide
@trim:
    ldx $8800+P+1
    lda $8800+B
    and $8800+W,x
    sta $8800+W,x
    inx
    cpx #4
    beq @done
    lda #0
@rest:
    sta $8800+W,x
    inx
    cpx #4
    bne @rest
@done:
    rts
; Indexed private store: baseY+X, preserving value A andX.
indexed_store:
    pha
    txa
    pha
    tya
    tsx
    clc
    adc $0101,x
    tay
    pla
    tax
    pla
    sta (se_gg_context),y
    rts
; OR current32bit destination mask into baseY. PreserveX.
or_dest:
    tya
    ldy #B+1
    sta (se_gg_context),y
    txa
    pha
    ldx #0
@or:
    txa
    clc
    adc #D
    tay
    lda (se_gg_context),y
    pha
    txa
    clc
    ldy #B+1
    adc (se_gg_context),y
    tay
    pla
    ora (se_gg_context),y
    sta (se_gg_context),y
    inx
    cpx #4
    bne @or
    pla
    tax
    rts
dest_mask:
    lda #128
    ldy #D
    sta (se_gg_context),y
    lda #0
    iny
    sta (se_gg_context),y
    iny
    sta (se_gg_context),y
    iny
    sta (se_gg_context),y
    rts
shift_dest:
    ldy #D
    lda (se_gg_context),y
    lsr
    sta (se_gg_context),y
    .repeat 3
        iny
        lda (se_gg_context),y
        ror
        sta (se_gg_context),y
    .endrepeat
    rts
.segment "RODATA"
end_masks: .byte $00,$80,$c0,$e0,$f0,$f8,$fc,$fe

; Context admission precedes even VALID/scratch writes. Shared by strict and
; preview entries; this helper changes no frame byte on a malformed pointer.
measure_context:
    stx se_gg_context
    sty se_gg_context+1
    ; Establish legal full frame before even clearing VALID.
    cpy #$10
    jcc bad_context
    cpy #$C6
    jcs bad_context
    txa
    clc
    adc #CG_SIZE
    tax
    tya
    adc #0
    cmp #$C6
    bcc :+
    jne bad_context
    cpx #0
    jne bad_context
:
    clc
    rts

; No packed trusted entry can bypass the actual FD/window guard. Font store
; borrows both GG pointer loans, so retain the already validated context.
preview_authenticate:
    ldy #CG_FONT
    lda (se_gg_context),y
    bne preview_argument
    iny
    lda (se_gg_context),y
    cmp #>GF_BUFFER
    bne preview_argument
    lda se_gg_context
    pha
    lda se_gg_context+1
    pha
    jsr se_gf_fetch_preview
    tay
    pla
    sta se_gg_context+1
    pla
    sta se_gg_context
    tya
    bcs preview_return
    ldy #CG_LENGTH
    lda (se_gg_context),y
    cmp se_gf_state+GF_LENGTH
    bne preview_argument
    iny
    lda (se_gg_context),y
    cmp se_gf_state+GF_LENGTH+1
    bne preview_argument
    clc
preview_return:
    rts
preview_argument:
    lda #CG_ARGUMENT
    sec
    rts

; Selected P=start,R=end were copied only from the CRC-authenticated index.
; The normal width subtraction already proves ordering/width<=24. Independently
; enforce end<=stride*8, without relying on the omitted global index scan.
preview_selected_bounds:
    ldy #S
    lda (se_gg_context),y
    ldy #D
    sta (se_gg_context),y
    ldy #S+1
    lda (se_gg_context),y
    ldy #D+1
    sta (se_gg_context),y
    ldx #3
@bits:
    ldy #D
    lda (se_gg_context),y
    asl
    sta (se_gg_context),y
    iny
    lda (se_gg_context),y
    rol
    sta (se_gg_context),y
    dex
    bne @bits
    ldy #D+1
    lda (se_gg_context),y
    ldy #R+1
    cmp (se_gg_context),y
    bcc @bad
    bne @good
    ldy #D
    lda (se_gg_context),y
    ldy #R
    cmp (se_gg_context),y
    bcc @bad
@good:
    clc
    rts
@bad:
    sec
    rts

preview_busy:
    lda #$B2
    sec
    rts
