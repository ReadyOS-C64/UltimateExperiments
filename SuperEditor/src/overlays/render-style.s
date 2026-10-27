.include "render/presentation.inc"
; R1-private source-color plan consumer. No phase-union or source-buffer reads.
; All capability/context comparisons precede cache admission and pixel writes.
.macro ST_COMPARE source,offset,count
    .local loop,same
    ldx #count-1
loop:
    lda source,x
    cmp se_st_descriptor+offset,x
    beq same
    iny ;at most 33 changed key bytes, so the mismatch count cannot wrap
same:
    dex
    bpl loop
.endmacro
style_context:
    lda se_render_caps
    beq @raw
    jsr style_damage
    jsr style_matches
    bcc @same
    lsr se_st_valid ;published-valid is a strict 0/1 flag
    lda #1
    sta se_st_request
    rts
@same:
    lda se_st_valid
    ora se_st_request
    bne @done ;valid, pending, or failed exact context needs no new request
    inc se_st_request ;both flags are strict 0/1, with $80 the only failure
@done:
    rts
@raw:
    sta se_st_valid
    sta se_st_request
    rts
style_matches:
    ldy #0
    ST_COMPARE se_doc_meta,0,15
    ST_COMPARE se_doc_generation,15,2
    ST_COMPARE se_r_revision,17,4
    ST_COMPARE se_v_length,21,3
    ST_COMPARE se_v_top,24,3
    ST_COMPARE se_l_pan,27,3
    ST_COMPARE se_reu_epoch,30,2
    lda se_mode
    asl
    ora se_l_mode ;bit0 wrap policy, bits1/2 grid mode:40/60/80
    cmp se_st_descriptor+32
    beq :+
    iny
:   tya
    cmp #1 ;Y0 matching/Cclear; Y1..33 rebound current context/Cset
    rts

; Capture mutation proof before cache_save clears R1's damage. Compare against
; last painted revision so later cursor-only frames do not revoke a saved proof
; merely because an optional style job has not caught up with the current key.
style_damage:
    ldx #3
@revision:
    lda se_r_revision,x
    cmp se_r_saved_revision,x
    bne @changed
    dex
    bpl @revision
    rts
@changed:
    lda se_r_damage_valid
    bne @done ;an exact one-edit certificate may still consume the old carry
    lsr se_st_cp_valid ;checkpoint-valid is a strict 0/1 flag
@done:
    rts

.ifndef SE_STYLE_CONTEXT_ONLY
style_cell:
    lda se_st_valid
    beq @done
    ldx se_v_row
    lda style_row_low,x
    sta text_ptr
    lda style_row_high,x
    sta text_ptr+1
    ldy se_v_col
    lda (text_ptr),y
    pha
    and #15
    sta tui_color
    pla
    and #$80
    eor se_v_cell
    sta se_v_cell
@done:
    rts
style_row_low:
.repeat STYLE_ROWS,R
    .byte <(STYLE_PLAN+40*R)
.endrepeat
style_row_high:
.repeat STYLE_ROWS,R
    .byte >(STYLE_PLAN+40*R)
.endrepeat
.endif
