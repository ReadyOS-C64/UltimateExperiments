; C8-only logical line and view controls. Source positions remain24-bit.
logical_up:
    lda se_n_line
    ora se_n_line+1
    ora se_n_line+2
    bne @previous
    lda #0
    sta se_n_target
    sta se_n_target+1
    sta se_n_target+2
    jmp complete
@previous:
    COPY24 se_n_line,se_n_query
    sec
    lda se_n_query
    sbc #1
    sta se_n_query
    lda se_n_query+1
    sbc #0
    sta se_n_query+1
    lda se_n_query+2
    sbc #0
    sta se_n_query+2
    lda #N_LOOK_UP
    sta se_n_lookup_action
    jmp lookup_start
layout_command:
    lda se_l_mode
    sta se_n_remaining ;old layout, used only until reveal starts
    lda se_e_command
    cmp #E_WRAP
    bne @explicit
    lda se_l_mode
    eor #1
    jmp @set
@explicit:
    cmp #E_WRAP_ON
    bne @off
    lda #0
    beq @set
@off:
    lda #1
@set:
    sta se_l_mode
    lda #0
    sta se_l_valid
    sta se_r_valid
    sta se_n_preferred_valid
    lda se_e_command
    cmp #E_PANLEFT
    beq @left
    cmp #E_PANRIGHT
    beq @right
    lda #0
    sta se_l_manual
    sta se_l_pan
    sta se_l_pan+1
    sta se_l_pan+2
    jmp @finish
@left:
    lda se_l_pan+2
    ora se_l_pan+1
    bne @subtract
    lda se_l_pan
    cmp #20
    bcs @subtract
    lda #0
    sta se_l_pan
    beq @manual
@subtract:
    sec
    lda se_l_pan
    sbc #20
    sta se_l_pan
    lda se_l_pan+1
    sbc #0
    sta se_l_pan+1
    lda se_l_pan+2
    sbc #0
    sta se_l_pan+2
    jmp @manual
@right:
    clc
    lda se_l_pan
    adc #20
    sta se_l_pan
    lda se_l_pan+1
    adc #0
    sta se_l_pan+1
    lda se_l_pan+2
    adc #0
    sta se_l_pan+2
    bcs @clamp
    CMP24 se_l_pan,se_v_length
    bcc @manual
@clamp:
    COPY24 se_v_length,se_l_pan
@manual:
    lda #1
    sta se_l_manual
@finish:
    lda #E_POSITION ;root skips unnecessary hot reload for a view-only command
    sta se_e_command
    COPY24 se_n_target,se_e_target
    lda se_l_mode
    cmp se_n_remaining
    beq @unchanged
    jmp reveal ;rebuild top from true rows when changing layout
@unchanged:
    jmp release
