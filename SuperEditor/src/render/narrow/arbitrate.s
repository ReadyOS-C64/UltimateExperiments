.setcpu "6502"
.include "render/narrow/api.inc"
.export se_narrow_resolve_tile
.segment "CODE"
; Resolve one current physical tile from unselected, clipped ink counts.
; All-zero tiles use normal; otherwise majority wins, then documented priority,
; then the lower semantic ID. Selection never changes this decision.
se_narrow_resolve_tile:
    lda #0
    ldy #NR_BEST_WEIGHT
    sta (se_nr_context),y
    iny
    sta (se_nr_context),y
    iny
    sta (se_nr_context),y
    ldx #0
@role:
    txa
    clc
    adc #NR_HISTOGRAM
    tay
    lda (se_nr_context),y
    beq @next
    ldy #NR_BEST_WEIGHT
    cmp (se_nr_context),y
    bcc @next
    bne @choose
    lda priority,x
    ldy #NR_BEST_RANK
    cmp (se_nr_context),y
    bcc @next
    beq @next
@choose:
    txa
    clc
    adc #NR_HISTOGRAM
    tay
    lda (se_nr_context),y
    ldy #NR_BEST_WEIGHT
    sta (se_nr_context),y
    lda priority,x
    iny
    sta (se_nr_context),y
    txa
    iny
    sta (se_nr_context),y
@next:
    inx
    cpx #14
    bcc @role
    ldy #NR_PALETTE
    lda (se_nr_context),y
    sta se_nr_pointer
    iny
    lda (se_nr_context),y
    sta se_nr_pointer+1
    ldy #NR_BEST_ROLE
    lda (se_nr_context),y
    tay
    lda (se_nr_pointer),y
    and #15
    asl
    asl
    asl
    asl
    ldy #NR_TEMP
    sta (se_nr_context),y
    ldy #NR_BACKGROUND
    lda (se_nr_context),y
    and #15
    ldy #NR_TEMP
    ora (se_nr_context),y
    sta (se_nr_context),y
    ldy #NR_ATTRIBUTE_PTR
    lda (se_nr_context),y
    sta se_nr_pointer
    iny
    lda (se_nr_context),y
    sta se_nr_pointer+1
    ldy #NR_TEMP
    lda (se_nr_context),y
    ldy #0
    sta (se_nr_pointer),y
    rts
.segment "RODATA"
; normal,emphasis,strong,both,code,reserved,reserved,keyword,number,string,
; comment,directive,label,operator. Same-rank ties retain lower ID.
priority: .byte 0,6,7,8,0,0,0,5,3,4,1,5,2,0
