; SE_EDITOR_GEOS_RENDERED hooks, included only inside actual line.s.
; Caller-loaned sparse24-bit ledger and three persistent phase-independent edges.
rendered_begin:
    ldx #2
@copy:
    lda L+GL_START,x
    sta GL_RENDER_LEFT0,x
    sta GL_RENDER_EDGE,x
    sta GL_RENDER_BREAK_EDGE,x
    sta GL_RENDER_ANCHORS,x
    dex
    bpl @copy
    rts
rendered_hidden:
    lda value
    cmp #13
    beq @visible ;a mask cannot erase the canonical CR delimiter
    lda L+GL_HIDDEN
    ora L+GL_HIDDEN+1
    beq @visible
    lda L+GL_HIDDEN
    sta se_gg_pointer
    lda L+GL_HIDDEN+1
    sta se_gg_pointer+1
    lda L+GL_USED
    lsr
    lsr
    lsr
    tay
    lda (se_gg_pointer),y
    sta advance
    lda L+GL_USED
    and #7
    tax
    lda rendered_bits,x
    and advance
    beq @visible
    lda L+GL_SCAN
    and L+GL_SCAN+1
    and L+GL_SCAN+2
    cmp #255
    jeq range
    jsr consumed
    lda L+GL_MAP_STARTED
    beq @hidden
    lda L+GL_MAP_CLOSED
    cmp #2
    beq @hidden
    jsr rendered_count_position
    jsr rendered_anchor_pointer
    ldy #2
@boundary:
    lda L+GL_SCAN,y
    sta (se_gg_pointer),y
    dey
    bpl @boundary
@hidden:
    lda #1
    clc
    rts
@visible:
    lda #0
    clc
    rts
rendered_bits:
    .byte $80,$40,$20,$10,$08,$04,$02,$01
rendered_count_position:
    lda L+GL_MAP_COUNT
    sta position
    lda #0
    sta position+1
    rts
rendered_anchor_pointer:
    ; At most161: three-byte multiplication cannot exceed483.
    lda position
    asl
    sta se_gg_pointer
    lda #0
    rol
    sta se_gg_pointer+1
    clc
    lda se_gg_pointer
    adc position
    sta se_gg_pointer
    lda se_gg_pointer+1
    adc #0
    sta se_gg_pointer+1
    clc
    lda se_gg_pointer
    adc #<GL_RENDER_ANCHORS
    sta se_gg_pointer
    lda se_gg_pointer+1
    adc #>GL_RENDER_ANCHORS
    sta se_gg_pointer+1
    rts
rendered_store_scan:
    jsr rendered_count_position
    jsr rendered_anchor_pointer
    ldy #2
@copy:
    lda L+GL_SCAN,y
    sta (se_gg_pointer),y
    dey
    bpl @copy
    rts
rendered_edge:
    clc
    lda L+GL_SCAN
    adc #1
    sta GL_RENDER_EDGE
    lda L+GL_SCAN+1
    adc #0
    sta GL_RENDER_EDGE+1
    lda L+GL_SCAN+2
    adc #0
    sta GL_RENDER_EDGE+2
    rts
rendered_map_cell:
    lda L+GL_MAP_CLOSED
    beq @open
    cmp #2
    beq @offscreen
    jsr rendered_store_scan ;next visible glyph certifies final sparse RIGHT
    lda #2
    sta L+GL_MAP_CLOSED
@offscreen:
    jsr rendered_edge
    clc
    rts
@open:
    lda L+GL_MODE
    beq @append
    lda L+GL_MAP_STARTED
    bne @append
    ldx #2
@left:
    lda L+GL_PENDING_X,x
    cmp L+GL_PAN,x
    bcc @offscreen
    bne @start
    dex
    bpl @left
    bmi @offscreen
@start:
    sec
    lda L+GL_X
    sbc L+GL_PAN
    sta L+GL_RASTER_X
    lda L+GL_X+1
    sbc L+GL_PAN+1
    sta L+GL_RASTER_X+1
    ldx #2
@left0:
    lda GL_RENDER_EDGE,x
    sta GL_RENDER_LEFT0,x
    lda L+GL_SCAN,x
    sta L+GL_MAP_FIRST,x
    dex
    bpl @left0
    lda #1
    sta L+GL_MAP_STARTED
    ldx #GL_X
    jsr clamp
    jsr store_map
@append:
    lda L+GL_MAP_COUNT
    bne :+
    ldx #2
@first:
    lda L+GL_SCAN,x
    sta L+GL_MAP_FIRST,x
    dex
    bpl @first
:
    lda L+GL_MAP_COUNT+1
    jne argument
    lda L+GL_MAP_COUNT
    cmp #GL_RENDER_CAPACITY
    jcs argument
    jsr rendered_store_scan ;actual glyph source, not MAP_FIRST+ordinal
    jsr rendered_edge
    inc L+GL_MAP_COUNT
    jsr rendered_count_position
    jsr rendered_anchor_pointer
    ldy #2
@right:
    lda GL_RENDER_EDGE,y
    sta (se_gg_pointer),y
    dey
    bpl @right
    ldx #GL_PENDING_X
    jsr clamp
    jsr store_map
    lda L+GL_MODE
    beq @done
    ldx #2
@close:
    lda L+GL_PENDING_X,x
    cmp L+GL_RIGHT,x
    bcc @done
    bne @closed
    dex
    bpl @close
@closed:
    lda #1
    sta L+GL_MAP_CLOSED
@done:
    clc
    rts
rendered_ensure_map:
    lda L+GL_MAP_STARTED
    bne @done
    lda #1
    sta L+GL_MAP_STARTED
    ldx #2
@source:
    lda L+GL_SCAN,x
    sta L+GL_MAP_FIRST,x
    lda GL_RENDER_EDGE,x
    sta GL_RENDER_LEFT0,x
    dex
    bpl @source
    jsr rendered_store_scan
    ldx #GL_X
    jsr clamp
    jsr store_map
@done:
    rts
rendered_ready:
    lda L+GL_MAP_COUNT
    ora L+GL_MAP_COUNT+1
    bne :+
    ldx #2
@empty:
    lda L+GL_END,x
    sta L+GL_MAP_FIRST,x
    dex
    bpl @empty
:
    lda L+GL_REASON
    cmp #GL_WORD
    bne @normal
    ldx #2
@rewind:
    lda GL_RENDER_BREAK_EDGE,x
    sta GL_RENDER_EDGE,x
    dex
    bpl @rewind
    jsr rendered_count_position
    jsr rendered_anchor_pointer
    ldy #2
@break:
    lda L+GL_BREAK_SOURCE,y
    sta (se_gg_pointer),y
    dey
    bpl @break
    rts
@normal:
    lda L+GL_MAP_CLOSED
    cmp #2
    beq @done
    jsr rendered_count_position
    jsr rendered_anchor_pointer
    ldy #2
@end:
    lda L+GL_END,y
    sta (se_gg_pointer),y
    dey
    bpl @end
@done:
    rts
