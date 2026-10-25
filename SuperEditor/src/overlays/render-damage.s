; C6-only bookkeeping: mutation occurs at hot_caret; delete is0/1.
render_damage:
    jsr se_ef_journal_local
    inc se_r_revision
    bne @range
    inc se_r_revision+1
    bne @range
    inc se_r_revision+2
    bne @range
    inc se_r_revision+3
    bne @range
    lda #0
    sta se_r_valid
@range:
    lda se_r_damage_valid
    bne @existing
    COPY24 se_hot_caret,se_r_damage_from
    COPY24 se_hot_caret,se_r_damage_to
    lda #1
    sta se_r_damage_valid
    jmp @tail
@existing:
    CMP24 se_hot_caret,se_r_damage_from
    bcs :+
    COPY24 se_hot_caret,se_r_damage_from
:
    CMP24 se_hot_caret,se_r_damage_to
    bcc @shift
    COPY24 se_hot_caret,se_r_damage_to
@tail:
    lda se_hot_delete
    bne @done
@increment:
    inc se_r_damage_to
    bne @done
    inc se_r_damage_to+1
    bne @done
    inc se_r_damage_to+2
    rts
@shift:
    lda se_hot_delete
    beq @increment
    lda se_r_damage_to
    bne :+
    lda se_r_damage_to+1
    bne :++
    dec se_r_damage_to+2
:
    dec se_r_damage_to
    rts
:
    dec se_r_damage_to+1
    dec se_r_damage_to
@done:
    rts
; A hot flush publishes exactly the already-visible gap bytes. Advance only a
; cache which describes that complete pre-flush view; other publications miss.
render_commit:
    lda se_r_valid
    beq @done
    ldx #9
@source:
    lda se_hot_original,x
    cmp se_r_original,x
    bne @done
    dex
    bpl @source
    ldx #1
@generation:
    lda se_hot_generation,x
    cmp se_r_generation,x
    bne @done
    dex
    bpl @generation
    ldx #3
@revision:
    lda se_r_revision,x
    cmp se_r_saved_revision,x
    bne @done
    dex
    bpl @revision
    CMP24 se_doc_length,se_r_length
    bne @done
    lda se_doc_generation
    sta se_r_generation
    lda se_doc_generation+1
    sta se_r_generation+1
@done:
    rts
