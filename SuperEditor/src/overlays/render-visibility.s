; Source-only pending-wrap probe. Never writes pixels, row maps or publication
; state. Each iteration consumes a byte/CR, so at most22*40=880 source bytes.
; A validated old map starts at the earliest damaged row: ordinary last-row
; edits therefore inspect at most40 bytes rather than rescanning the viewport.
wrapped_visibility:
    lda #0
    sta se_l_need_wrap
    lda se_hot_pending
    jeq @visible
    lda #0
    sta se_v_row
    sta se_v_col
    COPY24 se_v_top,se_v_pos
    lda se_r_valid
    jeq @scan
    ldx #9
@tokens:
    lda se_doc_original,x
    cmp se_r_original,x
    jne @scan
    dex
    bpl @tokens
    ldx #1
@generation:
    lda se_doc_generation,x
    cmp se_r_generation,x
    jne @scan
    dex
    bpl @generation
    CMP24 se_v_top,se_r_top
    bne @scan
    lda se_r_damage_valid
    beq @scan
    COPY24 se_r_damage_from,se_r_first
    jsr locate
    bcs @top
    lda se_v_row
    asl
    clc
    adc se_v_row
    tax
    lda se_v_rows,x
    sta se_v_pos
    lda se_v_rows+1,x
    sta se_v_pos+1
    lda se_v_rows+2,x
    sta se_v_pos+2
    ; A caret before the damaged row is uncommon but may be supplied by a
    ; direct source-position client. Probe from top rather than assume it.
    CMP24 se_hot_caret,se_v_pos
    bcc @top
    lda #0
    sta se_v_col
    beq @scan
@top:
    lda #0
    sta se_v_row
    sta se_v_col
    COPY24 se_v_top,se_v_pos
@scan:
    lda se_v_row
    cmp #EDITOR_BODY_ROWS
    bcs @outside
    CMP24 se_v_pos,se_hot_caret
    beq @visible
    bcs @outside
    CMP24 se_v_pos,se_v_length
    bcs @outside
    jsr se_view_peek
    bcs @return
    pha
    jsr se_view_advance
    pla
    cmp #13
    beq @row
    inc se_v_col
    lda se_v_col
    cmp #40
    bcc @scan
@row:
    inc se_v_row
    lda #0
    sta se_v_col
    beq @scan
@outside:
    lda #1
    sta se_l_need_wrap
@visible:
    lda #0
    clc
@return:
    rts
