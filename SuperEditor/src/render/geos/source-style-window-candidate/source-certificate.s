; Accumulate outputs alreadycomputed by actualC26, only for currentC20job.
; It neither prefetches nor skips a source guard/query. First161 canonical
; sourcebytes cover normal wrapped rows; positivepan beyond it safelymisses.
style_remember:
    sec
.repeat 3,I
    lda L+GL_SCAN+I
    sbc L+GL_START+I
    sta SC_TEMP+I
.endrepeat
    jcc @invalid
    lda SC_TEMP+1
    ora SC_TEMP+2
    bne @return
    lda SC_TEMP
    cmp #161
    bcs @return
    cmp SC_COUNT
    bne @first
    lda SC_VALID
    cmp #1
    bne @first
    ldx #58
@key:
    lda GS_FS+27,x
    cmp SC_KEY,x
    bne @invalid
    dex
    bpl @key
    ldx #9
@context:
    lda GSEM_FRAME+GSEM_START,x
    cmp SC_CONTEXT,x
    bne @invalid
    dex
    bpl @context
    jmp @copy
@first:
    lda SC_TEMP
    bne @invalid
    lda SC_VALID
    bne @invalid
    ldx #58
@save_key:
    lda GS_FS+27,x
    sta SC_KEY,x
    dex
    bpl @save_key
    ldx #2
@save_start:
    lda L+GL_START,x
    sta SC_START,x
    dex
    bpl @save_start
    ldx #9
@save_context:
    lda GSEM_FRAME+GSEM_START,x
    sta SC_CONTEXT,x
    dex
    bpl @save_context
@copy:
    ldy SC_TEMP
    ldx #0
@cell:
    lda GI_OUTPUT_STYLES,x
    sta SC_STYLES,y
    lda GI_OUTPUT_ROLES,x
    sta SC_ROLES,y
    iny
    inx
    cpy #161
    beq @publish
    cpx L+GL_PACKET_COUNT
    bcc @cell
@publish:
    sty SC_COUNT
    lda #1
    sta SC_VALID
@return:
    rts
@invalid:
    lda #0
    sta SC_VALID
    rts
