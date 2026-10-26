.setcpu "6502"
.macpack longbranch
.include "render/geos/api.inc"
.include "render/geos/row.inc"
; Incremental bitmap/histogram tile pointers; sealed R21 font ABI unchanged.
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
byte_ok=P+32
covhi=P+33
covlo=P+34
covtail=P+35
fragment=P+36
subtotal=P+37
attrbase=P+30 ;validation ending is dead before resolve
roles_seen=P+39 ;bit7 forbids append shortcut, lowbits accumulate actualpaintroles
.assert GR_PRIVATE+40<=GR_SIZE,error,"private role witness exceeds frame"
.segment "CODE"
se_geos_row:
    cpx #<F
    jne argument
    cpy #>F
    jne argument
    jsr validate
    jcs return
    lda #0
    sta F+GR_VALID
    sta P+38 ;font-header witness is local to this single non-yielding call
    lda F+GR_RESET ;only reset1 can prove no previous nonzero-role votes
    eor #1
    lsr
    ror
    sta roles_seen
    ; Validate immutable font header before clearing any output.
    jsr glyph_setup
    lda #32
    sta G+GG_VALUE
    lda #0
    sta G+GG_STYLE
    sta G+GG_FLAGS
    jsr glyph
    jcs return
    ; Validated row0..24: high=$60+row+floor(row/4), low=row*64.
    lda F+GR_ROW
    lsr
    lsr
    clc
    adc F+GR_ROW
    adc #$60
    sta rowbase+1
    lda F+GR_ROW
    .repeat 6
        asl
    .endrepeat
    sta rowbase
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
    ; Reclaim thirteen bytes of former padding for incremental tile setup.
    ; CODE remains1719B: immutable packed font and width addresses stay fixed.
clear_slot:
    .assert clear_slot-se_geos_row=$7E,error,"GEOS clear call slot moved"
    jsr row_clear
    jmp begin_runs
    .assert *-clear_slot=6,error,"candidate clear slot changed"
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
    ora roles_seen
    sta roles_seen
    ldy #GRR_FLAGS
    jsr input
    sta flags
    and #1
    sta G+GG_FLAGS
    jsr glyph
    jcs return
    lda #0
    sta byte_ok
    lda F+GR_LEFT
    ora F+GR_LEFT+1
    bne @slow
    lda F+GR_RIGHT
    cmp #<320
    bne @slow
    lda F+GR_RIGHT+1
    cmp #>320
    bne @slow
    lda xpos+1
    beq @fast
    cmp #1
    bne @slow
    lda xpos
    clc
    adc G+GG_ADVANCE
    cmp #65
    bcs @slow
@fast:
    ; The validation work word is dead until the next entry. Keep the
    ; aligned first bitmap-byte base; sy0..7 is added by OR, without carry.
    lda #0
    sta sy
    jsr pixel_address
    lda se_gg_pointer
    sta work
    lda se_gg_pointer+1
    sta work+1
    inc byte_ok
    ; Horizontal cell coverage is identical for every scanline of this glyph.
    lda #0
    sta covtail
    lda G+GG_CELL_HI
    sta covhi
    lda G+GG_CELL_LO
    sta covlo
    lda xpos
    and #7
    tax
    beq @slow
@coverage_shift:
    lsr covhi
    ror covlo
    ror covtail
    dex
    bne @coverage_shift
@slow:
    lda #0
    sta gy
@glyph_y:
    lda origin
    clc
    adc gy
    ldx origin
    bpl @positive
    jcc @skip_y
@positive:
    cmp F+GR_TOP
    jcc @skip_y
    cmp F+GR_BOTTOM
    jcs @skip_y
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
    jcs @skip_y
    jsr next_pixel
    jmp @left
@visible:
    lda byte_ok
    beq @slow_address
    lda work
    ora sy
    sta se_gg_pointer
    lda work+1
    sta se_gg_pointer+1
    lda xpos
    and #7
    tax
    jmp @address_ready
@slow_address:
    jsr clipped_right
    bcs @skip_y
    jsr pixel_address
@address_ready:
    jsr histogram_address
    lda byte_ok
    beq @glyph_x
    jsr byte_row
    jmp @skip_y
@glyph_x:
    asl inklo
    rol inkhi
    lda #0
    rol
    sta base
    beq @invert
    ; Histogram pointer remains on this role until the next VIC tile.
    ldy #0
    lda (se_gg_context),y
    cmp #255
    beq @invert
    clc
    adc #1
    sta (se_gg_context),y
@invert:
    lda flags
    and #6
    beq @normal
    lda base
    eor #1
    bne @paint
    beq @skip_x
@normal:
    lda base
    beq @skip_x
@paint:
    ldy #0
    lda masks,x
    ora (se_gg_pointer),y
    sta (se_gg_pointer),y
@skip_x:
    inc gx
    lda gx
    cmp G+GG_ADVANCE
    bcs @skip_y
    jsr next_pixel
    jsr clipped_right
    bcs @skip_y
    jsr raster_next
    jmp @glyph_x
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
argument:
    lda #GR_ARGUMENT
    sec
    rts
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
    clc
    adc rowbase
    sta se_gg_pointer
    lda pixel+1
    adc rowbase+1
    sta se_gg_pointer+1
    clc
    lda se_gg_pointer
    adc sy
    sta se_gg_pointer
    bcc :+
    inc se_gg_pointer+1
:
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
; Full-horizontal clip and complete glyph only. Signed/partial glyphs retain
; the original bit path. Base ink contributes votes before selection XOR.
byte_row:
    lda #0
    sta base
    sta fragment
    cpx #0
    beq @fragment
@shift:
    lsr inkhi
    ror inklo
    ror base
    dex
    bne @shift
@fragment:
    ldy fragment
    lda covhi,y
    beq @done
    lda inkhi,y
    beq @no_ink_vote ;adding zero cannot change a saturating role histogram
    pha
    and #15
    tax
    lda popcount,x
    sta subtotal
    pla
    lsr
    lsr
    lsr
    lsr
    tax
    lda popcount,x
    clc
    adc subtotal
    ldy #0
    clc
    adc (se_gg_context),y
    bcc :+
    lda #255
:   sta (se_gg_context),y
@no_ink_vote:
    ldy fragment
    lda flags
    and #6
    beq @plain
    lda inkhi,y
    eor covhi,y
    jmp @paint
@plain:
    lda inkhi,y
@paint:
    ldy #0
    ora (se_gg_pointer),y
    sta (se_gg_pointer),y
    inc fragment
    lda fragment
    cmp #3
    beq @done
    ldx #7
    jsr raster_next
    jmp @fragment
@done:
    rts
.include "render/geos/row-validate.s"
resolve:
    lda F+GR_TOP
    cmp F+GR_BOTTOM
    jeq complete
    ; Derive the one attribute-row base from the already certified bitmap
    ; rowbase: $4000 + (($6000 + row*320 - $6000) >> 3).
    lda rowbase
    sta attrbase
    lda rowbase+1
    and #$1F
    sta attrbase+1
    ldx #3
@attribute_shift:
    lsr attrbase+1
    ror attrbase
    dex
    bne @attribute_shift
    lda attrbase+1
    ora #$40
    sta attrbase+1
    lda #0
    sta tile
@tile:
    lda tile
    asl
    asl
    asl
    sta pixel
    lda tile
    lsr
    lsr
    lsr
    lsr
    lsr
    sta pixel+1
    jsr clipped_right
    jcs @next
    clc
    lda pixel
    adc #8
    sta pixel
    bcc :+
    inc pixel+1
:
    jsr clipped_left
    jcc @next
    jeq @next
    lda #0
    sta best
    lda roles_seen
    beq @palette ;only actual role0 ink since reset; complete histogram retained
    lda #0
    sta role
    sta weight
    sta rank
    jsr histogram_address
    ldy #0
@role:
    lda (se_gg_context),y
    beq @skip ;zero can never replace the initialized/default winner
    cmp weight
    bcc @skip
    bne @choose
    lda priorities,y
    cmp rank
    bcc @skip
    beq @skip
@choose:
    lda (se_gg_context),y
    sta weight
    lda priorities,y
    sta rank
    sty best
@skip:
    iny
    cpy #14
    bcc @role
@palette:
    lda F+GR_PALETTE
    sta se_gg_pointer
    lda F+GR_PALETTE+1
    sta se_gg_pointer+1
    ldy best
    lda (se_gg_pointer),y
    asl
    asl
    asl
    asl
    ora F+GR_BACKGROUND
    pha
    lda attrbase
    clc
    adc tile
    sta se_gg_pointer
    lda attrbase+1
    adc #0
    sta se_gg_pointer+1
    pla
    ldy #0
    sta (se_gg_pointer),y
@next:
    inc tile
    lda tile
    cmp #40
    jcc @tile
complete:
    lda #1
    sta F+GR_VALID
    lda #0
    clc
    rts
.segment "RODATA"
priorities: .byte 0,6,7,8,0,0,0,5,3,4,1,5,2,0
.segment "CODE"

.segment "RODATA"
popcount: .byte 0,1,1,2,1,2,2,3,1,2,2,3,2,3,3,4
masks: .byte $80,$40,$20,$10,8,4,2,1
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
    inx
    cpx #8
    bne @done
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
.assert *-row_clear<=165,error,"candidate tail overflow"

