.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "editor/api.inc"
.include "search/api.inc"
.include "document/api.inc"
.include "document/math24.inc"
.include "hot/api.inc"
.segment "CODE"
    OVL_BINDING
entry:
    lda se_overlay_frame
    cmp #S_BEGIN
    jeq begin
    cmp #S_STEP
    jne state
    lda se_s_active
    jeq state
    jsr se_view_init
    jcs return
    lda #128
    sta se_s_budget
    lda se_e_command
    cmp #E_WORDLEFT
    jeq word_left
    cmp #E_WORDRIGHT
    jeq word_right
    jmp find_step
state:
    lda #$70
    sec
return:
    rts
pending:
    lda #1
    clc
    rts
begin:
    lda se_s_active
    ora se_hot_phase
    ora se_hot_pending
    jne busy
    jsr se_view_init
    bcs return
    lda se_e_command
    cmp #E_WORDLEFT
    beq @ready
    cmp #E_WORDRIGHT
    beq @ready
    lda se_s_length
    jeq bad_pattern
    cmp #27
    jcs bad_pattern
    jsr prefix
@ready:
    jsr se_doc_read_acquire
    bcs return
    lda #1
    sta se_s_owned
    sta se_s_active
    lda se_doc_epoch
    sta se_s_epoch
    lda se_doc_epoch+1
    sta se_s_epoch+1
    lda #0
    sta se_s_stage
    sta se_s_match
    sta se_s_wrapped
    sta se_s_found
    COPY24 se_hot_caret,se_s_position
    COPY24 se_v_length,se_s_limit
    lda se_e_command
    cmp #E_FINDNEXT
    bne @origin
    CMP24 se_s_position,se_v_length
    beq @origin
    COPY24 se_s_position,se_v_pos
    jsr se_view_advance
    COPY24 se_v_pos,se_s_position
@origin:
    COPY24 se_s_position,se_s_origin
    jmp pending
busy:
    lda #$7A
    sec
    rts
bad_pattern:
    lda #$7C
    sec
    rts
; Only letters fold. PETSCII graphics/punctuation retain every bit.
fold:
    ldx se_s_insensitive
    beq @return
    cmp #$C1
    bcc @alias
    cmp #$DB
    bcs @return
    and #$7F
    rts
@alias:
    cmp #$61
    bcc @return
    cmp #$7B
    bcs @return
    and #$5F
@return:
    rts
; KMP prefix construction, at most26 input bytes; original query retained.
prefix:
    lda #0
    sta se_s_prefix
    sta se_s_match
    lda #1
    sta se_s_index
@next:
    lda se_s_index
    cmp se_s_length
    bcs @done
@compare:
    ldy se_s_index
    lda se_s_pattern,y
    jsr fold
    sta se_s_byte
    ldy se_s_match
    lda se_s_pattern,y
    jsr fold
    cmp se_s_byte
    beq @equal
    lda se_s_match
    beq @store
    tay
    dey
    lda se_s_prefix,y
    sta se_s_match
    jmp @compare
@equal:
    inc se_s_match
@store:
    ldy se_s_index
    lda se_s_match
    sta se_s_prefix,y
    inc se_s_index
    bne @next
@done:
    rts
find_step:
@compare:
    CMP24 se_s_position,se_s_limit
    jeq wrap
    COPY24 se_s_position,se_v_pos
    jsr se_view_peek
    jcs return
    jsr fold
    sta se_s_byte
    ldy se_s_match
    lda se_s_pattern,y
    jsr fold
    cmp se_s_byte
    beq @equal
    lda se_s_match
    beq @advance
    tay
    dey
    lda se_s_prefix,y
    sta se_s_match
    jmp @budget
@equal:
    inc se_s_match
@advance:
    jsr se_view_advance
    COPY24 se_v_pos,se_s_position
    lda se_s_match
    cmp se_s_length
    beq @found
@budget:
    dec se_s_budget
    jne @compare
    jmp pending
@found:
    lda se_s_length
    sta se_s_temp
    lda #0
    sta se_s_temp+1
    sta se_s_temp+2
    SUB24 se_s_position,se_s_temp,se_s_position
    jmp found
wrap:
    lda se_s_wrapped
    bne not_found
    lda #1
    sta se_s_wrapped
    lda #0
    sta se_s_match
    sta se_s_position
    sta se_s_position+1
    sta se_s_position+2
    lda se_s_length
    sec
    sbc #1
    sta se_s_temp
    lda #0
    sta se_s_temp+1
    sta se_s_temp+2
    ADD24 se_s_origin,se_s_temp,se_s_limit
    CMP24 se_s_limit,se_v_length
    bcc :+
    COPY24 se_v_length,se_s_limit
:
    ; A new segment never joins suffix bytes to the start of the document.
    dec se_s_budget
    jeq pending
    jmp find_step
not_found:
    lda #$7E
    sec
    rts
; Carry set for native letters, digits and source identifier byte5F.
is_word:
    cmp #$30
    bcc @no
    cmp #$3A
    bcc @yes
    cmp #$5F
    beq @yes
    cmp #$41
    bcc @no
    cmp #$5B
    bcc @yes
    cmp #$61
    bcc @upper
    cmp #$7B
    bcc @yes
@upper:
    cmp #$C1
    bcc @no
    cmp #$DB
    bcc @yes
@no:
    clc
    rts
@yes:
    sec
    rts
word_right:
@next:
    CMP24 se_s_position,se_v_length
    jeq found
    COPY24 se_s_position,se_v_pos
    jsr se_view_peek
    jcs return
    jsr is_word
    bcc @separator
    lda se_s_stage
    jne found
    jmp @advance
@separator:
    lda #1
    sta se_s_stage
@advance:
    jsr se_view_advance
    COPY24 se_v_pos,se_s_position
    dec se_s_budget
    bne @next
    jmp pending
word_left:
@next:
    lda se_s_position
    ora se_s_position+1
    ora se_s_position+2
    jeq found
    COPY24 se_s_position,se_v_pos
    jsr se_view_retreat
    jsr se_view_peek
    jcs return
    jsr is_word
    bcs @word
    lda se_s_stage
    jne found ;position still follows the preceding separator
    beq @advance
@word:
    lda #1
    sta se_s_stage
@advance:
    COPY24 se_v_pos,se_s_position
    dec se_s_budget
    bne @next
    jmp pending
found:
    COPY24 se_s_position,se_e_target
    lda #1
    sta se_s_found
    jsr se_search_cancel
    lda #0
    clc
    rts
