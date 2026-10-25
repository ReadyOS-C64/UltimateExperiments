; Private R29 candidate: unchanged reader plus page packet/map micromodule.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/geos/editor.inc"
.include "render/geos/source-line.inc"
.include "render/geos/semantic-lex.inc"
.include "render/geos/inline.inc"
.include "render/geos/fold-query.inc"
.include "render/geos/caret-cache.inc"
.include "render/geos/edit-cache.inc"
.include "document/math24.inc"
.import se_v_length
.import se_ef_valid
.import se_r_presentation
.import se_f_owner,se_i_ready,se_i_count,se_n_cache_count
.import se_l_valid,se_r_valid,se_st_request,se_st_cp_valid,se_l_mode,se_l_pan,se_l_manual
.import se_v_top,se_hot_caret,se_view_peek,se_view_advance,se_v_pos,se_v_rows
.import se_v_bottom,se_v_seen,se_v_caret_row,se_l_need_wrap
.export entry
P=GP_CONTROL
PS=P
REQUEST=P+1
OP=P+2
LINE=P+3
TOP=P+4
ANCHOR=P+5
INDEX=P+8
CANON=P+9
CHUNK=P+12
BASE=P+13
MAP_DONE=P+14
FOLD_END=P+16
FOLD_PENDING=P+19
FAST_PAINT=P+20
L=GEOS_LINE_FRAME
.import se_fs_begin,se_fs_guard,se_fs_read
.segment "GEOS_PAGE"
 OVL_BINDING
entry:
 lda se_f_owner
 cmp #4
 jne busy
 lda se_overlay_frame
 beq reader_begin
 cmp #1
 beq reader_guard
 cmp #2
 beq reader_read
 cmp #3
 jne argument
 jsr se_gp_cache_guard
 jcs failed
 lda PS
 cmp #1
 jeq source
 cmp #2
 jeq bytes
 cmp #3
 jeq canonical
 cmp #7
 jeq lexed
 cmp #8
 jeq inlined
 jmp argument
reader_begin:jmp se_fs_begin
reader_guard:jmp se_fs_guard
reader_read:jmp se_fs_read
source:
    lda L+GL_STATE
    cmp #2
    beq @ready
    lda #GP_LAYOUT_ID
    ldx #GS_STEP
    jmp request
@ready:
    lda L+GL_MAP_COUNT+1
    jne argument
    lda L+GL_MAP_COUNT
    cmp #GP_MAX_GLYPHS+1
    jcs argument
    sta GP_RECORD+GPR_COUNT
    lda L+GL_REASON
    sta GP_RECORD+GPR_REASON
    lda L+GL_CARET_VALID
    sta GP_RECORD+GPR_MEMBER
    ldx #2
@outputs:
    lda L+GL_END,x
    sta GP_RECORD+GPR_END,x
    lda L+GL_NEXT,x
    sta GP_RECORD+GPR_NEXT,x
    lda L+GL_MAP_FIRST,x
    sta GP_RECORD+GPR_FIRST,x
    dex
    bpl @outputs
    lda GP_RECORD+GPR_FLAGS
    bpl @fold_ready
    lda GP_RECORD+GPR_REASON
    cmp #GL_CR
    beq @fold_skip
    lda GP_RECORD+GPR_FLAGS
    and #$7F
    sta GP_RECORD+GPR_FLAGS
    bpl @fold_ready
@fold_skip:
    COPY24 FOLD_END,GP_RECORD+GPR_NEXT
@fold_ready:
    ldx #1
@raster:
    lda L+GL_RASTER_X,x
    sta GP_RECORD+GPR_RASTER_X,x
    dex
    bpl @raster
    ldx #GL_CARET_X
    jsr viewport_x
    jsr visible_x
    bcs @tail
    lda GP_RECORD+GPR_MEMBER
    beq @tail
    sta GP_RECORD+GPR_CARET_VALID
    lda CANON
    sta GP_RECORD+GPR_CARET_X
    lda CANON+1
    sta GP_RECORD+GPR_CARET_X+1
@tail:
    ldx #GL_X
    jsr viewport_x
    jsr visible_x
    bcc @tail_visible
    lda CANON+2
    and CANON+1
    cmp #$FF
    bne @geometry
    lda #$FC ;-4..-1 intersects the normal5px BSWspace
    bit GP_RECORD+GPR_FLAGS
    bpl :+
    lda #$FB ;-5..-1 intersects the6px foldedplus
:
    ldx GP_RECORD+GPR_KIND
    beq :+
    lda #$F9 ;-7..-1 intersects a native8space
:
    cmp CANON
    bcc @tail_visible
    bne @geometry
@tail_visible:
    lda #1
    sta GP_RECORD+GPR_TAIL_VALID
    lda CANON
    sta GP_RECORD+GPR_TAIL_X
    lda CANON+1
    sta GP_RECORD+GPR_TAIL_X+1
@geometry:
    lda #6
    sta GP_RECORD+GPR_BACKGROUND
    lda TOP
    sta GP_RECORD+GPR_TOP
    lda #<GPR_X
    jsr field
    inc GP_IO_OFFSET+1
    inc GP_IO_OFFSET+1
    lda #< (L+GL_MAP)
    sta GP_IO_POINTER
    lda #> (L+GL_MAP)
    sta GP_IO_POINTER+1
    lda GP_RECORD+GPR_COUNT
    clc
    adc #1
    asl
    sta GP_IO_LENGTH
    lda #0
    rol
    sta GP_IO_LENGTH+1
    jsr se_gp_cache_write
    jcs failed
    lda #0
    sta INDEX
    ldx #GP_MAX_GLYPHS-1
@styles:
    sta GP_ROLES,x
    dex
    cpx #$FF ;160 entries: sign flag cannot terminate a >128-byte loop
    bne @styles
    lda #2
    sta PS
    jmp own_pending
bytes:
    lda INDEX
    cmp GP_RECORD+GPR_COUNT
    beq @write
    ldx #2
@pos:
    lda GP_RECORD+GPR_FIRST,x
    sta se_v_pos,x
    dex
    bpl @pos
    clc
    lda se_v_pos
    adc INDEX
    sta se_v_pos
    bcc :+
    inc se_v_pos+1
    bne :+
    inc se_v_pos+2
:
    lda #32
    sta CHUNK
@read:
    jsr se_view_peek
    jcs failed
    ldx INDEX
    sta GP_SOURCE,x
    inc INDEX
    jsr se_view_advance
    lda INDEX
    cmp GP_RECORD+GPR_COUNT
    beq @write
    dec CHUNK
    bne @read
    jmp own_pending
@write:
    lda GP_RECORD+GPR_COUNT
    jeq begin_maps
    sta GP_IO_LENGTH
    lda #0
    sta GP_IO_LENGTH+1
    lda #<GP_SOURCE
    sta GP_IO_POINTER
    lda #>GP_SOURCE
    sta GP_IO_POINTER+1
    lda #GPR_CHARS
    jsr field
    jsr se_gp_cache_write
    jcs failed
    lda #<GP_ROLES
    sta GP_IO_POINTER
    lda #>GP_ROLES
    sta GP_IO_POINTER+1
    lda #GPR_STYLES
    jsr field
    jsr se_gp_cache_write
    jcs failed
    lda GP_RECORD+GPR_KIND
    beq @roles
    COPY24 GP_RECORD+GPR_FIRST,GSEM_FRAME+GSEM_QUERY
    lda GSEM_FRAME+GSEM_LANG
    sta GSEM_FRAME+GSEM_LANGUAGE
    lda GP_RECORD+GPR_COUNT
    sta GSEM_FRAME+GSEM_COUNT
    lda #7
    sta PS
    lda #GLEX_ID
    ldx #GLEX_BEGIN
    jmp request
@roles:
    lda GSEM_FRAME+GSEM_KIND
    cmp #4
    bcs @plain_roles
    lda GSEM_FRAME+GSEM_INLINE
    beq @plain_roles
    COPY24 GP_RECORD+GPR_FIRST,GSEM_FRAME+GSEM_QUERY
    lda GP_RECORD+GPR_COUNT
    sta GSEM_FRAME+GSEM_COUNT
    lda #8
    sta PS
    lda #GI_ID
    ldx #GI_BEGIN
    jmp request
@plain_roles:
    lda GSEM_FRAME+GSEM_ROLE
    ldx #GP_MAX_GLYPHS-1
@fill:
    sta GP_ROLES,x
    dex
    cpx #$FF
    bne @fill
    jsr write_roles
    jcs failed
begin_maps:
    lda #0
    sta INDEX
    ldx #2
@first:
    lda GP_RECORD+GPR_FIRST,x
    sta CANON,x
    dex
    bpl @first
    lda #3
    sta PS
    jmp own_pending
lexed:
    lda GLEX_ACTIVE
    beq @ready
    lda #GLEX_ID
    ldx #GLEX_STEP
    jmp request
@ready:
    jsr write_roles
    jcs failed
    jmp begin_maps
inlined:
    lda GI_ACTIVE
    beq @ready
    lda #GI_ID
    ldx #GI_STEP
    jmp request
@ready:
    lda GP_RECORD+GPR_COUNT
    sta GP_IO_LENGTH
    lda #0
    sta GP_IO_LENGTH+1
    lda #<GI_OUTPUT_STYLES
    sta GP_IO_POINTER
    lda #>GI_OUTPUT_STYLES
    sta GP_IO_POINTER+1
    lda #GPR_STYLES
    jsr field
    jsr se_gp_cache_write
    jcs failed
    lda #<GI_OUTPUT_ROLES
    sta GP_IO_POINTER
    lda #>GI_OUTPUT_ROLES
    sta GP_IO_POINTER+1
    lda #<GPR_ROLES
    jsr field
    inc GP_IO_OFFSET+1
    jsr se_gp_cache_write
    jcs failed
    jmp begin_maps
write_roles:
    lda GP_RECORD+GPR_COUNT
    sta GP_IO_LENGTH
    lda #0
    sta GP_IO_LENGTH+1
    lda #<GP_ROLES
    sta GP_IO_POINTER
    lda #>GP_ROLES
    sta GP_IO_POINTER+1
    lda #<GPR_ROLES
    jsr field
    inc GP_IO_OFFSET+1
    jmp se_gp_cache_write
canonical:
    lda INDEX
    sta BASE
    lda #0
    sta CHUNK
    sta MAP_DONE
    tay
@map:
    ldx #0
@three:
    lda CANON,x
    sta GP_CANONICAL,y
    iny
    inx
    cpx #3
    bne @three
    inc CHUNK
    lda INDEX
    cmp GP_RECORD+GPR_COUNT
    beq @last
    inc INDEX
    inc CANON
    bne :+
    inc CANON+1
    bne :+
    inc CANON+2
:
    lda CHUNK
    cmp #32
    bcc @map
    bcs @stash
@last:
    lda #1
    sta MAP_DONE
@stash:
    sty GP_IO_LENGTH
    lda #0
    sta GP_IO_LENGTH+1
    lda #<GP_CANONICAL
    sta GP_IO_POINTER
    lda #>GP_CANONICAL
    sta GP_IO_POINTER+1
    lda LINE
    jsr slot
    clc
    lda GP_IO_OFFSET
    adc #<GPR_LEFT
    sta GP_IO_OFFSET
    lda GP_IO_OFFSET+1
    adc #>GPR_LEFT
    sta GP_IO_OFFSET+1
    lda BASE
    jsr add_index3
    jsr se_gp_cache_write
    jcs failed
    clc
    lda GP_IO_OFFSET
    adc #<(GPR_RIGHT-GPR_LEFT)
    sta GP_IO_OFFSET
    lda GP_IO_OFFSET+1
    adc #>(GPR_RIGHT-GPR_LEFT)
    sta GP_IO_OFFSET+1
    jsr se_gp_cache_write
    jcs failed
    lda MAP_DONE
    jeq own_pending
    lda #4
    sta PS
    jmp own_pending
slot:
    jmp se_gp_cache_slot
field:
    pha
    lda LINE
    jsr slot
    pla
    clc
    adc GP_IO_OFFSET
    sta GP_IO_OFFSET
    bcc :+
    inc GP_IO_OFFSET+1
:
    rts
; X selects a logical24bit metric. Wrap has no horizontal origin. The signed
; result is only exposed after the caller has checked its viewport range.
viewport_x:
    lda L+GL_MODE
    bne @subtract
    lda L,x
    sta CANON
    lda L+1,x
    sta CANON+1
    lda L+2,x
    sta CANON+2
    rts
@subtract:
    sec
    lda L,x
    sbc L+GL_PAN
    sta CANON
    lda L+1,x
    sbc L+GL_PAN+1
    sta CANON+1
    lda L+2,x
    sbc L+GL_PAN+2
    sta CANON+2
    rts
visible_x:
    lda CANON+2
    bne @no
    lda CANON+1
    beq @yes
    cmp #1
    bne @no
    lda CANON
    cmp #64
    bcs @no
@yes:
    clc
    rts
@no:
    sec
    rts
add_index3:
    tax
    beq @done
@add:
    clc
    lda GP_IO_OFFSET
    adc #3
    sta GP_IO_OFFSET
    bcc :+
    inc GP_IO_OFFSET+1
:
    dex
    bne @add
@done:
    rts
own_pending:
 lda #GP_PAGE_ID
 ldx #1
request:
 sta REQUEST
 stx OP
 lda #1
 clc
 rts
failed:
 sec
 rts
busy:
 lda #$B2
 sec
 rts
argument:
 lda #$90
 sec
 rts
