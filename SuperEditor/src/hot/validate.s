valid:
    jsr se_doc_validate
    jcs return
    lda se_hot_ready
    ora se_hot_phase
    jeq state
    ldx #4
@tokens:
    lda se_hot_original,x
    cmp se_doc_original,x
    jne context
    lda se_hot_append,x
    cmp se_doc_append,x
    jne context
    dex
    bpl @tokens
    lda se_hot_command
    cmp #W_COMMIT
    bne @generation_start
    lda se_h_phase
    jne busy
    jmp se_h_validate
@generation_start:
    ldx #1
@generation:
    lda se_hot_generation,x
    cmp se_doc_generation,x
    jne context
    dex
    bpl @generation
    clc
    rts
