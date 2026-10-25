; Resident published-row summary query shared by R1 and C16. No overlay call.
.setcpu "6502"
.macpack longbranch
.import se_ef_valid,se_ef_fold_rows,se_ef_paint_ends,se_v_rows,se_v_bottom
.import se_sel_mark,se_sel_length,se_sel_start,se_sel_end,se_r_color
.export se_ef_summary
.segment "CODE"
; A=row0..21. A0/Zset/Cclear ordinary; A1/Zclear folded, Cset iff selected.
; X/Y and existing foreground se_r_color scratch clobbered; no new state/ZP.
; Caller has refreshed the ordered selection range and published C11 row map.
; PAINT_END is CR+1; [CR,next canonical anchor) summarizes hidden bytes.
se_ef_summary:
    cmp #22
    jcs ordinary
    tax
    lda se_ef_valid
    jeq ordinary
    txa
    and #7
    tay
    lda masks,y
    pha
    txa
    lsr
    lsr
    lsr
    tay
    pla
    and se_ef_fold_rows,y
    beq ordinary
    lda se_sel_mark
    beq unselected
    lda se_sel_length
    ora se_sel_length+1
    ora se_sel_length+2
    beq unselected
    txa
    asl
    sta se_r_color
    txa
    clc
    adc se_r_color
    tay
    ; selection.end >CR iff selection.end >=paint_end on integer anchors.
    lda se_sel_end+2
    cmp se_ef_paint_ends+2,y
    bne :+
    lda se_sel_end+1
    cmp se_ef_paint_ends+1,y
    bne :+
    lda se_sel_end
    cmp se_ef_paint_ends,y
:
    bcc unselected
    cpx #21
    beq bottom
    ; selection.start must precede the following canonical anchor.
    lda se_sel_start+2
    cmp se_v_rows+5,y
    bne :+
    lda se_sel_start+1
    cmp se_v_rows+4,y
    bne :+
    lda se_sel_start
    cmp se_v_rows+3,y
:
    bcs unselected
selected:
    lda #1
    sec
    rts
bottom:
    lda se_sel_start+2
    cmp se_v_bottom+2
    bne :+
    lda se_sel_start+1
    cmp se_v_bottom+1
    bne :+
    lda se_sel_start
    cmp se_v_bottom
:
    bcc selected
unselected:
    lda #1
    clc
    rts
ordinary:
    lda #0
    clc
    rts
.segment "RODATA"
masks: .byte 1,2,4,8,16,32,64,128
