map_cell:
.ifdef SE_EDITOR_GEOS_RENDERED
    jmp rendered_map_cell
.else
    lda L+GL_MAP_CLOSED
    jne @done
    lda L+GL_MODE
    beq @append
    lda L+GL_MAP_STARTED
    bne @append
    ; Only glyphs whose cell intersects the no-wrap viewport enter the map.
    ldx #2
@left:
    lda L+GL_PENDING_X,x
    cmp L+GL_PAN,x
    bcc @done
    bne @start
    dex
    bpl @left
    bmi @done
@start:
    ; The hit map is clamped, but raster needs the small negative first-glyph
    ; origin when PAN cuts through its cell. All advances are positive.
    sec
    lda L+GL_X
    sbc L+GL_PAN
    sta L+GL_RASTER_X
    lda L+GL_X+1
    sbc L+GL_PAN+1
    sta L+GL_RASTER_X+1
    lda #1
    sta L+GL_MAP_STARTED
    ldx #2
@source:
    lda L+GL_SCAN,x
    sta L+GL_MAP_FIRST,x
    dex
    bpl @source
    ldx #GL_X
    jsr clamp
    jsr store_map
@append:
    lda L+GL_MAP_COUNT+1
    cmp #1
    bcc @space
    jne argument
    lda L+GL_MAP_COUNT
    cmp #64
    jcs argument
@space:
    inc L+GL_MAP_COUNT
    bne :+
    inc L+GL_MAP_COUNT+1
:
    ldx #GL_PENDING_X
    jsr clamp
    jsr store_map
    lda L+GL_MODE
    beq @done
    ldx #2
@right:
    lda L+GL_PENDING_X,x
    cmp L+GL_RIGHT,x
    bcc @done
    bne @close
    dex
    bpl @right
@close:
    lda #1
    sta L+GL_MAP_CLOSED
@done:
    clc
    rts
 .endif
ensure_map:
.ifdef SE_EDITOR_GEOS_RENDERED
    jmp rendered_ensure_map
.else
    lda L+GL_MAP_STARTED
    bne @done
    lda #1
    sta L+GL_MAP_STARTED
    ldx #2
@source:
    lda L+GL_SCAN,x
    sta L+GL_MAP_FIRST,x
    dex
    bpl @source
    ldx #GL_X
    jsr clamp
    jsr store_map
@done:
    rts
 .endif
; source is X-relative field in L; viewport clamp is explicit and unsigned.
clamp:
    lda L+GL_MODE
    beq @wrap
    lda L+2,x
    cmp L+GL_PAN+2
    bcc @zero
    bne @subtract
    lda L+1,x
    cmp L+GL_PAN+1
    bcc @zero
    bne @subtract
    lda L,x
    cmp L+GL_PAN
    bcc @zero
@subtract:
    sec
    lda L,x
    sbc L+GL_PAN
    sta mapped
    lda L+1,x
    sbc L+GL_PAN+1
    sta mapped+1
    lda L+2,x
    sbc L+GL_PAN+2
    bne @width
    beq @limit
@wrap:
    lda L,x
    sta mapped
    lda L+1,x
    sta mapped+1
    lda L+2,x
    bne @width
@limit:
    lda mapped+1
    cmp L+GL_WIDTH+1
    bcc @done
    bne @width
    lda mapped
    cmp L+GL_WIDTH
    bcc @done
@width:
    lda L+GL_WIDTH
    sta mapped
    lda L+GL_WIDTH+1
    sta mapped+1
@done:
    rts
@zero:
    lda #0
    sta mapped
    sta mapped+1
    rts
store_map:
    lda L+GL_MAP_COUNT
    sta position
    lda L+GL_MAP_COUNT+1
    sta position+1
    jsr map_pointer
    ldy #0
    lda mapped
    sta (se_gg_pointer),y
    iny
    lda mapped+1
    sta (se_gg_pointer),y
    rts
map_pointer:
    lda position
    asl
    sta se_gg_pointer
    lda position+1
    rol
    sta se_gg_pointer+1
    clc
    lda se_gg_pointer
    adc #<M
    sta se_gg_pointer
    lda se_gg_pointer+1
    adc #>M
    sta se_gg_pointer+1
    rts
.export se_geos_line_hit
se_geos_line_hit:
    jsr context
    jcs return
    lda L+GL_STATE
    cmp #2
    jne state
 .ifdef SE_EDITOR_GEOS_RENDERED
    lda L+GL_MAP_COUNT+1
    jne argument
    lda L+GL_MAP_COUNT
    cmp #GL_RENDER_CAPACITY+1
    jcs argument
 .else
    lda L+GL_MAP_COUNT+1
    cmp #1
    bcc @count
    jne argument
    lda L+GL_MAP_COUNT
    cmp #65
    jcs argument
 .endif
@count:
    lda L+GL_HIT_X
    sta hitx
    lda L+GL_HIT_X+1
    sta hitx+1
    cmp L+GL_WIDTH+1
    bcc @init
    bne @clamp
    lda hitx
    cmp L+GL_WIDTH
    bcc @init
@clamp:
    lda L+GL_WIDTH
    sta hitx
    lda L+GL_WIDTH+1
    sta hitx+1
@init:
    lda #0
    sta position
    sta position+1
@scan:
    jsr map_pointer
    ldy #0
    lda (se_gg_pointer),y
    sta mapped
    iny
    lda (se_gg_pointer),y
    sta mapped+1
    cmp hitx+1
    bcc @below
    bne @candidate
    lda mapped
    cmp hitx
    bcc @below
@candidate:
    lda position
    ora position+1
    jeq @publish
    sec
    lda hitx
    sbc previous
    sta distance
    lda hitx+1
    sbc previous+1
    sta distance+1
    sec
    lda mapped
    sbc hitx
    sta mapped
    lda mapped+1
    sbc hitx+1
    cmp distance+1
    bcc @publish
    bne @previous
    lda mapped
    cmp distance
    bcc @publish
    beq @publish ;exact midpoint chooses the right source boundary
@previous:
    lda position
    bne :+
    dec position+1
:
    dec position
    jmp @publish
@below:
    lda position+1
    cmp L+GL_MAP_COUNT+1
    bne @advance
    lda position
    cmp L+GL_MAP_COUNT
    beq @publish
@advance:
    lda mapped
    sta previous
    lda mapped+1
    sta previous+1
    inc position
    jne @scan
    inc position+1
    jmp @scan
@publish:
.ifdef SE_EDITOR_GEOS_RENDERED
    lda position
    sta L+GL_HIT_BOUNDARY
    lda position+1
    sta L+GL_HIT_BOUNDARY+1
    jsr rendered_anchor_pointer
    ldy #2
@canonical:
    lda (se_gg_pointer),y
    sta L+GL_HIT_SOURCE,y
    dey
    bpl @canonical
    jmp zero
.else
    lda position
    sta L+GL_HIT_BOUNDARY
    clc
    adc L+GL_MAP_FIRST
    sta L+GL_HIT_SOURCE
    lda position+1
    sta L+GL_HIT_BOUNDARY+1
    adc L+GL_MAP_FIRST+1
    sta L+GL_HIT_SOURCE+1
    lda L+GL_MAP_FIRST+2
    adc #0
    sta L+GL_HIT_SOURCE+2
    jcs range
    jmp zero
.endif
