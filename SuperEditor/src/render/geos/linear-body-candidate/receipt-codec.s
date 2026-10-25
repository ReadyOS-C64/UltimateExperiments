.setcpu "6502"
.macpack longbranch
.include "render/geos/receipt-codec.inc"
.import se_si_kind,se_si_style,se_si_width,se_si_open,se_si_close,se_f_owner
.export se_ecr_pack,se_ecr_take
.segment "CODE"
; Pack only actual already-emitted PAIR/ESCAPE fields, preserve parser fields.
; A0 accepted/A1 fullbatch, Cset90argument/B2foreignowner. No source/REU writes.
se_ecr_pack:
    jsr owner
    jcs return
    lda ECR_BATCH
    cmp #8
    jcs bad
    ldx #8
@input:
    lda se_si_kind,x ;kind/style/width/open3/close3 are contiguous parser ABI
    sta ECR_TEMP,x
    dex
    bpl @input
    jsr valid
    jcs return
    lda ECR_BATCH
    jsr times10
    ldy #0
@copy:
    lda ECR_TEMP,y
    sta ECR_DATA,x
    inx
    iny
    cpy #9
    bcc @copy
    lda #0
    sta ECR_DATA,x
    inc ECR_BATCH
    lda ECR_BATCH
    cmp #8
    lda #0
    bcc return
    lda #1
    clc
return:
    rts
; The input batch is untrusted derived data; stage/validate before publication.
se_ecr_take:
    jsr owner
    jcs return
    lda ECR_BATCH
    cmp #9
    jcs bad
    lda ECR_NEXT
    cmp ECR_BATCH
    jeq done
    jcs bad
    jsr times10
    ldy #0
@read:
    lda ECR_DATA,x
    sta ECR_TEMP,y
    inx
    iny
    cpy #10
    bcc @read
    lda ECR_TEMP+9
    jne bad
    jsr valid
    jcs return
    ldx #8
@publish:
    lda ECR_TEMP,x
    sta se_si_kind,x
    dex
    bpl @publish
    inc ECR_NEXT
    lda #1
    clc
    rts
; Actual parser fields are contiguous. Match their declared source coordinates.
valid:
    lda ECR_TEMP
    cmp #1
    beq @pair
    cmp #2
    jne bad
    lda ECR_TEMP+1
    jne bad
    lda ECR_TEMP+2
    cmp #1
    jne bad
    beq @bounds
@pair:
    lda ECR_TEMP+1
    cmp #4
    beq @code
    cmp #1
    jcc bad
    cmp #4
    jcs bad
    cmp ECR_TEMP+2
    jne bad
    beq @bounds
@code:
    lda ECR_TEMP+2
    cmp #2
    jne bad
@bounds:
    ldx #2
@open:
    lda ECR_TEMP+3,x
    cmp ECR_BODY,x
    jcc bad
    bne @interior
    dex
    bpl @open
@interior:
    clc
    lda ECR_TEMP+3
    adc ECR_TEMP+2
    sta ECR_LIMIT
    lda ECR_TEMP+4
    adc #0
    sta ECR_LIMIT+1
    lda ECR_TEMP+5
    adc #0
    sta ECR_LIMIT+2
    jcs bad
    ldx #2
@close:
    lda ECR_TEMP+6,x
    cmp ECR_LIMIT,x
    jcc bad
    bne @tail
    dex
    bpl @close
@tail:
    clc
    lda ECR_TEMP+6
    adc ECR_TEMP+2
    sta ECR_LIMIT
    lda ECR_TEMP+7
    adc #0
    sta ECR_LIMIT+1
    lda ECR_TEMP+8
    adc #0
    sta ECR_LIMIT+2
    jcs bad
    ldx #2
@end:
    lda ECR_BODY_END,x
    cmp ECR_LIMIT,x
    jcc bad
    bne done
    dex
    bpl @end
done:
    lda #0
    clc
    rts
times10:
    asl
    sta ECR_LIMIT
    asl
    asl
    clc
    adc ECR_LIMIT
    tax
    rts
owner:
    lda se_f_owner
    cmp #4
    jeq done
    lda #$B2
    sec
    rts
bad:
    lda #$90
    sec
    rts
.assert se_si_style=se_si_kind+1,lderror,"parserstyle receipt ABI moved"
.assert se_si_width=se_si_kind+2,lderror,"parserwidth receipt ABI moved"
.assert se_si_open=se_si_kind+3,lderror,"parseropen receipt ABI moved"
.assert se_si_close=se_si_kind+6,lderror,"parserclose receipt ABI moved"
