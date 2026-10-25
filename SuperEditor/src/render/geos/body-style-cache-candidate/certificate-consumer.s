.import se_fs_owned
; Parent fullsource/FE guard alreadyprotects the currentC20map. This certificate
; is an additional output of that exactjob, not a reusable validity-bitcache.
style_certificate:
    lda GP_RECORD+GPR_COUNT
    jeq @miss
    cmp #162
    jcs @miss
    lda SC_VALID
    cmp #2
    jne @miss
    lda GS_ACTIVE
    ora GS_CONTEXT_VALID
    jne @miss
    jsr style_check
    jcs @miss
    ldx #2
@start:
    lda GP_RECORD+GPR_START,x
    cmp SC_START,x
    jne @miss
    dex
    bpl @start
    sec
.repeat 3,I
    lda GP_RECORD+GPR_FIRST+I
    sbc SC_START+I
    sta SC_TEMP+I
.endrepeat
    jcc @miss
    lda SC_TEMP+1
    ora SC_TEMP+2
    jne @miss
    lda SC_TEMP
    clc
    adc GP_RECORD+GPR_COUNT
    jcs @miss
    cmp SC_COUNT
    bcc @ready
    jne @miss
@ready:
    ldy SC_TEMP
    ldx #0
@cell:
    lda SC_STYLES,y
    sta GI_OUTPUT_STYLES,x
    lda SC_ROLES,y
    cpx #160
    bne @ordinary
    sta GI_OUTPUT_ROLE_LAST
    jmp @next
@ordinary:
    sta GI_OUTPUT_ROLES,x
@next:
    iny
    inx
    cpx GP_RECORD+GPR_COUNT
    bcc @cell
    lda #0
    sta GI_ACTIVE ;GLmap alreadypublished; samephase as normalC26publication
    sta se_fs_owned ;inactive GL/map aliases FS: leave C26-compatible empty owner
    clc
    rts
@miss:
    sec
    rts

; Shared fullidentity/context comparator; no source authority is elided.
style_check:
    ldx #58
@key:
    lda GS_FS+27,x
    cmp SC_KEY,x
    bne @miss
    dex
    bpl @key
    ldx #9
@context:
    lda GSEM_FRAME+GSEM_START,x
    cmp SC_CONTEXT,x
    bne @miss
    dex
    bpl @context
    clc
    rts
@miss:
    sec
    rts
