.setcpu "6502"
.macpack longbranch
.include "render/geos/style-typing/wide.inc"
.importzp gt_base,gt_bitmap
.export se_typing_patch,se_typing_validate,se_typing_dry,se_typing_color_patch,se_typing_color_validate
se_typing_validate:
 lda #0
 sta mode
 jmp validate
se_typing_color_validate:
 lda #1
 sta mode
 jmp validate
F=GT_FRAME
P=F+GT_PRIVATE
line=P
column=P+1
xb=P+2
xbit=P+3
bb=P+4
bp=P+5
nb=P+6
np=P+7
prefix=P+8
suffix=P+9
endmask=P+10
width=P+11
bound=P+13
carrybyte=P+15
value=P+16
work=P+17
glyphlo=P+18
carethi=P+19
caretlo=P+20
sy=P+21
glyphtail=P+22
carettail=P+23
carry2=P+24
mode=P+25 ;bit0 certifiedcolorentry,bit1 dry(noVIC)
.segment "CODE"
se_typing_patch:
    lda #0
    beq set_mode
se_typing_dry:
    lda #3
    bne set_mode
se_typing_color_patch:
    lda #1
set_mode:
    sta mode
    jsr validate
    bcc :+
    rts
:
    lda #0
    sta F+GT_VALID
    sta line
    lda #<GT_BASE
    sta gt_base
    lda #>GT_BASE
    sta gt_base+1
@row:
    ; One temporary byte per destination column. Source remains immutable.
    ; Copy whole unchanged prefix bytes without any bit shifts. Validation
    ; proves xb<=nb; the boundary byte still takes the exact masked path.
    ldy #0
    ldx xb
    beq @shift_begin
@copy_prefix:
    lda (gt_base),y
    sta GT_TEMP,y
    iny
    dex
    bne @copy_prefix
@shift_begin:
    sty column
    ; Select wide deletion once per row; the original narrow/insert loop
    ; retains its byte and bit paths without a per-byte width comparison.
    lda F+GT_OP
    beq @byte
    lda F+GT_ADVANCE
    cmp #8
    jcs @wide_byte
@byte:
    ldy column
    lda F+GT_OP
    bne @left
    lda #0
    sta carry2
    cpy #2
    bcc :+
    dey
    dey
    lda (gt_base),y
    sta carry2
    iny
    iny
:   tya
    beq @zero_prev
    dey
    lda (gt_base),y
    iny
    bne @prev
@zero_prev:
    lda #0
@prev:
    sta carrybyte
    lda (gt_base),y
    ldx F+GT_ADVANCE
@right_bits:
    lsr carry2
    ror carrybyte
    ror
    dex
    bne @right_bits
    beq @shifted
@left:
    lda #0
    sta carry2
    cpy #38
    bcs :+
    iny
    iny
    lda (gt_base),y
    sta carry2
    dey
    dey
:   cpy #39
    beq @zero_next
    iny
    lda (gt_base),y
    dey
    jmp @next
@zero_next:
    lda #0
@next:
    sta carrybyte
    lda (gt_base),y
    ldx F+GT_ADVANCE
@left_bits:
    asl carry2
    rol carrybyte
    rol
    dex
    bne @left_bits
@shifted:
    sta value
    ; Preserve only original pixels strictly before the edit.
    cpy xb
    bne @no_prefix
    lda (gt_base),y
    and prefix
    bcs @prefix_ready ;carry from CPY equality is stillset
@no_prefix:
    lda #0
@prefix_ready:
    sta work
    cpy bb
    bcc @merged
    lda value
    bne @suffix_test
    beq @merged
@suffix_test:
    cpy bb
    bne @whole_suffix
    and suffix
@whole_suffix:
    ora work
    sta work
@merged:
    ; Clear the vacated tail, independent of unused input-tail contents.
    lda work
    cpy nb
    bcc @store
    and endmask
@store:
    sta GT_TEMP,y
    inc column
    lda column
    cmp np
    jne @byte
    ; Unused tail is zeroed explicitly, including dirty old input-tail bits.
@zero_begin:
    tay
    cpy #40
    bcs @tail_done
    lda #0
@clear_tail:
    sta GT_TEMP,y
    iny
    cpy #40
    bcc @clear_tail
@tail_done:
    ; Insert glyph isalreadygenuine/transformed, left-aligned andadvance-bounded.
    lda F+GT_OP
    bne @caret
    lda line
    asl
    tay
    lda #0
    sta glyphtail
    lda F+GT_GLYPH+1,y
    sta glyphlo
    lda F+GT_GLYPH,y
    ldx xbit
    beq @glyph_ready
@align:
    lsr
    ror glyphlo
    ror glyphtail
    dex
    bne @align
@glyph_ready:
    ldy xb
    cpy #40
    bcs @caret
    ora GT_TEMP,y
    sta GT_TEMP,y
    iny
    cpy #40
    bcs @caret
    lda glyphlo
    ora GT_TEMP,y
    sta GT_TEMP,y
    iny
    cpy #40
    bcs @caret
    lda glyphtail
    ora GT_TEMP,y
    sta GT_TEMP,y
@caret:
    ldy #39
@cache_base:
    lda GT_TEMP,y
    sta (gt_base),y
    dey
    bpl @cache_base
    ldy bb
    cpy #40
    bcs @bitmap
    lda carethi
    eor GT_TEMP,y
    sta GT_TEMP,y
    iny
    cpy #40
    bcs @bitmap
    lda caretlo
    eor GT_TEMP,y
    sta GT_TEMP,y
    iny
    cpy #40
    bcs @bitmap
    lda carettail
    eor GT_TEMP,y
    sta GT_TEMP,y
@bitmap:
    lda mode
    and #2
    bne @advance
    ; VIC hires tile layout, with only this nine-pixel logical band touched.
    lda F+GT_TOP
    clc
    adc line
    sta sy
    and #7
    sta gt_bitmap
    lda sy
    lsr
    lsr
    lsr
    tax
    and #3
    .repeat 6
    asl
    .endrepeat
    ora gt_bitmap
    sta gt_bitmap
    txa
    lsr
    lsr
    clc
    adc #$60
    stx sy
    adc sy
    sta gt_bitmap+1
    ldy #0
    ldx #0
@copy:
    lda GT_TEMP,x
    sta (gt_bitmap),y
    clc
    lda gt_bitmap
    adc #8
    sta gt_bitmap
    bcc :+
    inc gt_bitmap+1
:
    inx
    cpx #40
    bcc @copy
@advance:
    clc
    lda gt_base
    adc #40
    sta gt_base
    bcc :+
    inc gt_base+1
:
    inc line
    lda line
    cmp #9
    jcc @row
    lda #1
    sta F+GT_VALID
    lda #0
    clc
    rts
@wide_byte:
    ldy column
    lda #0
    sta carry2
    cpy #38
    bcs :+
    iny
    iny
    lda (gt_base),y
    sta carry2
    dey
    dey
:   cpy #39
    beq @wide_zero_next
    iny
    lda (gt_base),y
    dey
    jmp @wide_next
@wide_zero_next:
    lda #0
@wide_next:
    sta carrybyte
    lda F+GT_ADVANCE
    and #7
    tax
    lda carrybyte
    cpx #0
    beq @wide_shifted
@wide_bits:
    asl carry2
    rol
    dex
    bne @wide_bits
@wide_shifted:
    sta value
    ; Preserve only original pixels strictly before the edit.
    cpy xb
    bne @wide_no_prefix
    lda (gt_base),y
    and prefix
    bcs @wide_prefix_ready ;carry from CPY equality is stillset
@wide_no_prefix:
    lda #0
@wide_prefix_ready:
    sta work
    cpy bb
    bcc @wide_merged
    lda value
    bne @wide_suffix_test
    beq @wide_merged
@wide_suffix_test:
    cpy bb
    bne @wide_whole_suffix
    and suffix
@wide_whole_suffix:
    ora work
    sta work
@wide_merged:
    ; Clear the vacated tail, independent of unused input-tail contents.
    lda work
    cpy nb
    bcc @wide_store
    and endmask
@wide_store:
    sta GT_TEMP,y
    inc column
    lda column
    cmp np
    jne @wide_byte
    jmp @zero_begin
bad:
    lda #$90
    sec
    rts
validate:
    lda F+GT_OP
    cmp #2
    jcs bad
    lda F+GT_FLAGS
    jne bad
    lda F+GT_TOP
    cmp #16
    jcc bad
    cmp #184
    jcs bad
    lda F+GT_ADVANCE
    beq bad
    cmp #12
    jcs bad
    lda F+GT_CARET_WIDTH
    beq bad
    cmp #12
    jcs bad
    ; Both half-open spans arebounded by320 before any output writes.
    lda F+GT_OLD_WIDTH
    sta width
    lda F+GT_OLD_WIDTH+1
    sta width+1
    jsr max320
    jcs bad
    lda F+GT_X+1
    cmp width+1
    bcc @position
    jne bad
    lda F+GT_X
    cmp width
    beq @position
    jcs bad
@position:
    lda F+GT_X
    sta bound
    lda F+GT_X+1
    sta bound+1
    lda F+GT_OP
    bne @delete
    clc
    lda width
    adc F+GT_ADVANCE
    sta width
    bcc :+
    inc width+1
:
    jsr max320
    jcs bad
    clc
    lda bound
    adc F+GT_ADVANCE
    sta bound
    bcc :+
    inc bound+1
:
    ; Confirm every supplied row of ink fits the explicit advance.
    ldx F+GT_ADVANCE
    lda highmask,x
    eor #255
    sta value
    lda lowmask,x
    eor #255
    sta work
    ldy #0
@glyph:
    lda F+GT_GLYPH,y
    and value
    jne bad
    lda F+GT_GLYPH+1,y
    and work
    jne bad
    iny
    iny
    cpy #18
    bcc @glyph
    jmp @geometry
@delete:
    sec
    lda width
    sbc F+GT_ADVANCE
    sta width
    lda width+1
    sbc #0
    sta width+1
    jcc bad
    lda bound+1
    cmp width+1
    bcc @geometry
    jne bad
    lda bound
    cmp width
    beq @geometry
    jcs bad
@geometry:
    lda F+GT_X
    and #7
    sta xbit
    tax
    lda highmask,x
    sta prefix
    lda F+GT_X+1
    lsr
    lda F+GT_X
    ror
    lsr
    lsr
    sta xb
    lda bound
    and #7
    sta bp
    tax
    lda highmask,x
    eor #255
    sta suffix
    lda bound+1
    lsr
    lda bound
    ror
    lsr
    lsr
    sta bb
    lda width
    and #7
    tax
    lda highmask,x
    sta endmask
    lda width+1
    lsr
    lda width
    ror
    lsr
    lsr
    sta nb
    sta np
    inc np ;exclusive shift-loop end, at most40 after validation
    ldx F+GT_CARET_WIDTH
    lda lowmask,x
    sta caretlo
    lda #0
    sta carettail
    lda highmask,x
    ldx bp
    beq @caret_ready
@caret_shift:
    lsr
    ror caretlo
    ror carettail
    dex
    bne @caret_shift
@caret_ready:
    sta carethi
    lda mode
    and #1
    bne @certified
    ; Outputattribute guard only. Caller MUST separately certify actualrole0
    ; ink for every glyph intersecting these bands; oldattributes alone
    ; cannot prove absenceofminoritycoloredvotes (see NEIGHBOR_PROOF.md).
    lda F+GT_TOP
    lsr
    lsr
    lsr
    sta sy
    ldx sy
    lda attrlo,x
    sta gt_bitmap
    lda attrhi,x
    sta gt_bitmap+1
    ldy #79
@attributes:
    lda (gt_bitmap),y
    cmp F+GT_ATTRIBUTE
    jne bad
    dey
    bpl @attributes
@certified:
    clc
    rts
max320:
    lda width+1
    beq @ok
    cmp #1
    bne @bad
    lda width
    cmp #64 ; exact320 changes the C20 break/reflow witness: decline
    rts
@bad:
    sec
    rts
@ok:
    clc
    rts
.segment "RODATA"
highmask:.byte 0,$80,$C0,$E0,$F0,$F8,$FC,$FE,$FF,$FF,$FF,$FF
lowmask:.byte 0,0,0,0,0,0,0,0,0,$80,$C0,$E0
attrlo:
.repeat 24,I
.byte <($4000+I*40)
.endrepeat
attrhi:
.repeat 24,I
.byte >($4000+I*40)
.endrepeat
