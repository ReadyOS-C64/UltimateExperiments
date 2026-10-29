.setcpu "6502"
.macpack longbranch
.include "render/geos/api.inc"
.include "render/geos/row.inc"
; Private byte-flush experiment; original and proven pointer candidate unchanged.
.export se_geos_row
; The glyph service and compositor share the same two borrowed pointer pairs.
; The compiled frame address makes every continuation pointer-free.
F=GEOS_ROW_FRAME
G=F+GR_GLYPH
H=F+GR_HISTOGRAM
P=F+GR_PRIVATE
run=P
index=P+1
count=P+2
origin=P+3
xpos=P+4
role=P+6
flags=P+7
gy=P+8
sy=P+9
gx=P+10
pixel=P+11
tile=P+13
inkhi=P+14
inklo=P+15
base=P+16
rowbase=P+17
map=P+19
desc=P+21
best=P+23
weight=P+24
rank=P+25
work=P+26
span=P+28
ending=P+30
inkbyte=P+32
coverbyte=P+33
.segment "CODE"
se_geos_row:
    cpx #<F
    bne early_argument
    cpy #>F
    bne early_argument
    jsr validate
    bcc validated
 early_return:
    rts
 early_argument:
    jmp argument
 validated:
    lda #0
    sta F+GR_VALID
    ; Validate immutable font header before clearing any output.
    jsr glyph_setup
    lda #32
    sta G+GG_VALUE
    lda #0
    sta G+GG_STYLE
    sta G+GG_FLAGS
    jsr glyph
    bcs early_return
    ldx F+GR_ROW
    lda rowlo,x
    sta rowbase
    lda rowhi,x
    sta rowbase+1
    lda F+GR_RESET
    beq begin_runs
    lda #<H
    sta se_gg_pointer
    lda #>H
    sta se_gg_pointer+1
    ldx #2
    ldy #0
    lda #0
@page:
    sta (se_gg_pointer),y
    iny
    bne @page
    inc se_gg_pointer+1
    dex
    bne @page
    ldy #47
@tail:
    sta (se_gg_pointer),y
    dey
    bpl @tail
    ; Reclaim old padding and reuse existing helpers for tile-byte setup.
    ; CODE remains1719B: immutable packed font and width addresses stay fixed.
clear_slot:

    jsr row_clear
    jmp begin_runs
    .res $6-(*-clear_slot),$EA
    .assert *-clear_slot=$6,error,"candidate fixed font padding budget changed"
begin_runs:
    lda #0
    sta run
next_run:
    lda run
    cmp F+GR_RUNS
    jcs resolve
    jsr descriptor
    ldy #GRR_COUNT
    lda (se_gg_pointer),y
    sta count
    iny
    lda (se_gg_pointer),y
    sta origin
    iny
    lda (se_gg_pointer),y
    sta xpos
    iny
    lda (se_gg_pointer),y
    sta xpos+1
    ldy #GRR_BOUNDARIES
    lda (se_gg_pointer),y
    sta map
    iny
    lda (se_gg_pointer),y
    sta map+1
    lda #0
    sta index
    jsr boundary
next_glyph:
    lda index
    cmp count
    jcs run_done
    lda xpos
    sta pixel
    lda xpos+1
    sta pixel+1
    jsr clipped_right
    jcs run_done
    ldy #GRR_CHARACTERS
    jsr input
    sta G+GG_VALUE
    ldy #GRR_STYLES
    jsr input
    sta G+GG_STYLE
    ldy #GRR_ROLES
    jsr input
    sta role
    ldy #GRR_FLAGS
    jsr input
    sta flags
    and #1
    sta G+GG_FLAGS
    jsr glyph
    bcc :+
    rts
:
    lda #0
    sta gy
@glyph_y:
    lda origin
    clc
    adc gy
    ldx origin
    bpl @positive
    bcc @early_skip
@positive:
    cmp F+GR_TOP
    bcc @early_skip
    cmp F+GR_BOTTOM
    bcs @early_skip
    sta sy
    lda gy
    asl
    tay
    lda G+GG_INK,y
    sta inkhi
    lda G+GG_INK+1,y
    sta inklo
    lda xpos
    sta pixel
    lda xpos+1
    sta pixel+1
    lda #0
    sta gx
@left:
    jsr clipped_left
    bcs @visible
    asl inklo
    rol inkhi
    inc gx
    lda gx
    cmp G+GG_ADVANCE
    bcs @skip_y
    jsr next_pixel
    jmp @left
@early_skip:
    jmp @skip_y
@visible:
    jsr clipped_right
    bcs @skip_y
    jsr pixel_address
    jsr histogram_address
    lda #0
    sta inkbyte
    sta coverbyte
@glyph_x:
    asl inklo
    rol inkhi
    bcc @clear_ink
    lda inkbyte
    ora masks,x
    sta inkbyte
@clear_ink:
    lda coverbyte
    ora masks,x
    sta coverbyte
    inc gx
    lda gx
    cmp G+GG_ADVANCE
    bcs @flush_done
    jsr next_pixel
    jsr clipped_right
    bcs @flush_done
    inx
    cpx #8
    bcc @glyph_x
    jsr raster_flush
    jsr raster_next
    jmp @glyph_x
@flush_done:
    jsr raster_flush
@skip_y:
    inc gy
    lda gy
    cmp #9
    jcc @glyph_y
    clc
    lda xpos
    adc G+GG_ADVANCE
    sta xpos
    bcc :+
    inc xpos+1
:
    inc index
    jsr boundary
    jmp next_glyph
run_done:
    lda desc
    sta se_gg_pointer
    lda desc+1
    sta se_gg_pointer+1
    ldy #GRR_DONE
    lda index
    sta (se_gg_pointer),y
    iny
    lda xpos
    sta (se_gg_pointer),y
    iny
    lda xpos+1
    sta (se_gg_pointer),y
    inc run
    jmp next_run
return:
    rts
.segment "GEOS_ROW_FAST"
argument:
    lda #GR_ARGUMENT
    sec
    rts
.segment "CODE"
; Map entries are untrimmed x; after clipping, later entries remain untouched.
boundary:
    lda map
    sta se_gg_pointer
    lda map+1
    sta se_gg_pointer+1
    ldy #0
    lda xpos
    sta (se_gg_pointer),y
    iny
    lda xpos+1
    sta (se_gg_pointer),y
    clc
    lda map
    adc #2
    sta map
    bcc :+
    inc map+1
:
    rts
; Return the selected input byte, no persistent executable pointer.
input:
    lda desc
    sta se_gg_pointer
    lda desc+1
    sta se_gg_pointer+1
    lda (se_gg_pointer),y
    pha
    iny
    lda (se_gg_pointer),y
    sta se_gg_pointer+1
    pla
    sta se_gg_pointer
    ldy index
    lda (se_gg_pointer),y
    rts
descriptor:
    lda F+GR_RUN_POINTER
    sta desc
    lda F+GR_RUN_POINTER+1
    sta desc+1
    lda run
    beq :+
    clc
    lda desc
    adc #GRR_SIZE
    sta desc
    bcc :+
    inc desc+1
:
    lda desc
    sta se_gg_pointer
    lda desc+1
    sta se_gg_pointer+1
    rts
glyph_setup:
    ldx #5
@copy:
    lda F+GR_FONT,x
    sta G+GG_FONT,x
    dex
    bpl @copy
    lda #0
    sta G+GG_ENCODING
    sta G+GG_CLIP_LEFT
    sta G+GG_CLIP_TOP
    lda #16
    sta G+GG_CLIP_RIGHT
    lda #9
    sta G+GG_CLIP_BOTTOM
    rts
glyph:
    ldx #<G
    ldy #>G
    jmp se_geos_glyph
clipped_left:
    lda pixel+1
    cmp #$FF
    bne @unsigned
    lda pixel
    cmp #$F1 ;onlyFFF1..FFFF are signed origins/pixels-15..-1
    bcs @negative
    lda pixel+1
@unsigned:
    cmp F+GR_LEFT+1
    bne :+
    lda pixel
    cmp F+GR_LEFT
:
    rts
@negative:
    clc ;left rejects before address arithmetic;right keeps the run alive
    rts
clipped_right:
    lda pixel+1
    cmp #$FF
    bne @unsigned
    lda pixel
    cmp #$F1 ;onlyFFF1..FFFF are signed origins/pixels-15..-1
    bcs @negative
    lda pixel+1
@unsigned:
    cmp F+GR_RIGHT+1
    bne :+
    lda pixel
    cmp F+GR_RIGHT
:
    rts
@negative:
    clc ;left rejects before address arithmetic;right keeps the run alive
    rts
; Returns bitmap pointer,Y0,Xbit and tile0..39, preserving base.
pixel_address:
    lda pixel
    and #7
    tax
    lda pixel
    and #$F8
    ora sy
    clc
    adc rowbase
    sta se_gg_pointer
    lda pixel+1
    adc rowbase+1
    sta se_gg_pointer+1
    lda pixel+1
    lsr
    lda pixel
    ror
    lsr
    lsr
    sta tile
    ldy #0
    rts
histogram_address:
    ldy tile
    lda histlo,y
    clc
    adc role
    sta se_gg_context
    lda histhi,y
    adc #0
    sta se_gg_context+1
    rts
.include "render/geos/raster-candidate/row-blit-validate.s"
.include "render/geos/raster-candidate/row-blit-resolve.s"
.segment "RODATA"
masks: .byte $80,$40,$20,$10,8,4,2,1
rowlo:
.repeat 25,I
.byte <($6000+I*320)
.endrepeat
rowhi:
.repeat 25,I
.byte >($6000+I*320)
.endrepeat
histlo:
.repeat 40,I
.byte <(H+I*14)
.endrepeat
histhi:
.repeat 40,I
.byte >(H+I*14)
.endrepeat

.include "render/geos/row-fast.s"
next_pixel:
    inc pixel
    bne :+
    inc pixel+1
:
    rts
; Increment borrowed tile pointers only at the eight-pixel boundary.
raster_next:
    ldx #0
    clc
    lda se_gg_pointer
    adc #8
    sta se_gg_pointer
    bcc :+
    inc se_gg_pointer+1
:
    clc
    lda se_gg_context
    adc #14
    sta se_gg_context
    bcc @done
    inc se_gg_context+1
@done:
    rts
; One destination bitmap OR and one saturating vote update per covered tile.
; Popcount uses only A/Y, preserving the current bit index in X.
 .segment "CODE"
raster_flush:
    lda inkbyte
    ldy #0
@pop:
    lsr
    bcc :+
    iny
:
    bne @pop
    tya
    beq @paint
    ldy #0
    clc
    adc (se_gg_context),y
    bcc :+
    lda #255
:
    sta (se_gg_context),y
@paint:
    lda flags
    and #6
    beq @normal
    lda coverbyte
    eor inkbyte
    bne @store
    beq @done
@normal:
    lda inkbyte
    beq @done
@store:
    ldy #0
    ora (se_gg_pointer),y
    sta (se_gg_pointer),y
@done:
    lda #0
    sta inkbyte
    sta coverbyte
    rts
 .segment "GEOS_ROW_FAST"
.assert *=$B000,lderror,"byte flush candidate must end exactly atB000"

