; R14 owns source access, so it also performs the bounded block-parser scan.
; One call consumes at most64 bytes or returns one completed logical event.
.setcpu "6502"
.macpack longbranch
.include "fold/source.inc"
.include "style/api.inc"
.include "supermark/api.inc"
.include "render/geos/edit-certificate.inc"
.import se_sm_init,se_sm_feed,se_sm_finish,se_sm_ready
.import se_sm_pos,se_sm_state,se_sm_fence,se_sm_language,se_sm_regions
.import se_e_draw_sequence,se_reu_epoch
.import st_budget,st_index,st_used,st_buffer,st_pos,st_finish,st_row,st_col,st_next
.export se_sb_init,se_sb_step
.segment "FOLD_SOURCE_CODE"

; Initialize a cold parser, or admit and restore the one exact visible edit
; described by the GEC.  A=1 is fast with st_row=start/st_col=end; A=0 is a
; clean cold parser.  Carry is always clear.
se_sb_init:
    lda se_st_cp_valid
    and GEC_VALID
    beq @reject_early
    ; The 40-column publisher still emits duplicate first-line events.
    lda se_st_key+ST_KEY_MODE
    cmp #2
    bcc @reject_early
    ldx #1
@sequence:
    lda GEC_SEQUENCE,x
    cmp se_e_draw_sequence,x
    bne @reject_early
    lda GEC_DOC_EPOCH,x
    cmp se_doc_epoch,x
    bne @reject_early
    lda GEC_REU_EPOCH,x
    cmp se_reu_epoch,x
    bne @reject_early
    dex
    bpl @sequence
    jmp @identity_begin
@reject_early:
    jmp sb_cold

    ; Source identity/generation and exact viewport presentation are unchanged.
@identity_begin:
    ldx #16
@identity:
    lda se_st_descriptor,x
    cmp se_st_key,x
    bne @reject_revision
    dex
    bpl @identity
    ldx #8
@view:
    lda se_st_descriptor+ST_KEY_TOP,x
    cmp se_st_key+ST_KEY_TOP,x
    bne @reject_revision
    dex
    bpl @view

    ; The GEC names the old published revision and length exactly.
    ldx #6
@old_publication:
    lda se_st_descriptor+17,x
    cmp GEC_REVISION,x
    bne @reject_revision
    dex
    bpl @old_publication

    ; Current revision minus old revision must be exactly one without wrap.
    sec
    lda se_st_key+17
    sbc GEC_REVISION
    sta st_next
    lda se_st_key+18
    sbc GEC_REVISION+1
    bne @reject_revision
    lda se_st_key+19
    sbc GEC_REVISION+2
    bne @reject_revision
    lda se_st_key+20
    sbc GEC_REVISION+3
    bne @reject_revision
    dec st_next
    bne @reject_revision
    jmp @operation
@reject_revision:
    jmp sb_cold

    ; Exactly one inserted/deleted non-CR byte and the matching length delta.
@operation:
    ldx GEC_OP
    cpx #2
    bcs @reject_length
    txa
    eor #1
    tax
    lda GEC_OLD,x
    beq @reject_length
    cmp #13
    beq @reject_length
    txa
    eor #1
    tax
    lda GEC_OLD,x
    bne @reject_length
    cpx #0
    beq @insert
    sec
    lda GEC_LENGTH
    sbc se_st_key+ST_KEY_LENGTH
    sta st_next
    lda GEC_LENGTH+1
    sbc se_st_key+ST_KEY_LENGTH+1
    bne @reject_length
    lda GEC_LENGTH+2
    sbc se_st_key+ST_KEY_LENGTH+2
    bne @reject_length
    jmp @length_one
@insert:
    sec
    lda se_st_key+ST_KEY_LENGTH
    sbc GEC_LENGTH
    sta st_next
    lda se_st_key+ST_KEY_LENGTH+1
    sbc GEC_LENGTH+1
    bne @reject_length
    lda se_st_key+ST_KEY_LENGTH+2
    sbc GEC_LENGTH+2
    bne @reject_length
@length_one:
    dec st_next
    bne @reject_length
    jmp @locate
@reject_length:
    jmp sb_cold

    ; Locate the physical row containing the edit in the current row anchors.
@locate:
    CMP24 GEC_POSITION,se_st_rows
    bcc @reject_map
    lda #0
    sta st_row
@containing:
    clc
    lda st_row
    adc #1
    cmp se_st_cp_count
    bcs @backward
    sta st_col
    asl
    clc
    adc st_col
    tax
    lda se_st_rows+2,x
    cmp GEC_POSITION+2
    bcc @advance
    bne @backward
    lda se_st_rows+1,x
    cmp GEC_POSITION+1
    bcc @advance
    bne @backward
    lda se_st_rows,x
    cmp GEC_POSITION
    bcc @advance
    bne @backward
@advance:
    inc st_row
    bne @containing

    ; Walk to the old incoming logical-start marker.
@backward:
    lda st_row
    jsr sb_carry_index
    lda se_st_cp_rows+2,x
    bmi @start
    lda st_row
    beq @reject_map
    dec st_row
    bne @backward
    beq @backward
@reject_map:
    jmp sb_cold

    ; The following marked row is the expected outgoing logical boundary.
@start:
    lda st_row
@forward:
    clc
    adc #1
    cmp se_st_cp_count
    bcs @reject_forward
    sta st_col
    jsr sb_carry_index
    lda se_st_cp_rows+2,x
    bpl @next
    lda st_row
    jsr sb_carry_index
    jsr se_sm_init
    jsr sb_carry_restore
    bcs @reject_forward
    jmp @restore
@reject_forward:
    jmp sb_cold

    ; Restore the current row anchor after semantic carry validation.
@restore:
    lda st_row
    asl
    clc
    adc st_row
    tax
    ldy #0
@position:
    lda se_st_rows,x
    sta st_pos,y
    sta se_sm_pos,y
    sta se_sm_state+20,y
    inx
    iny
    cpy #3
    bcc @position
    lda #0
    sta st_index
    sta st_used
    sta se_st_cp_valid
    lda #1
    clc
    rts
@next:
    lda st_col
    bne @forward

sb_cold:
    jsr se_sm_init
    lda #0
    clc
    rts

; A=row, X=row*6.  st_next is scratch after admission arithmetic is complete.
sb_carry_index:
    asl
    sta st_next
    asl
    adc st_next
    tax
    rts

; X indexes a six-byte incoming-carry record. Validate while restoring; the
; cold exit reinitializes the parser if any later field is corrupt.
sb_carry_restore:
    lda se_st_cp_rows,x
    tay
    beq :+
    cmp #3
    bcc @bad
    cmp #15
    bcs @bad
:   sta se_sm_fence
    lda se_st_cp_rows+1,x
    cmp #3
    bcs @bad
    cpy #0
    bne :+
    cmp #0
    bne @bad
:   sta se_sm_language
    lda se_st_cp_rows+2,x
    and #$1f
    cmp #17
    bcs @bad
    sta se_sm_regions
    lda se_st_cp_rows+3,x
    sta se_sm_state+76
    lda se_st_cp_rows+4,x
    sta se_sm_state+77
    lda se_st_cp_rows+5,x
    sta se_sm_state+78
    clc
    rts
@bad:
    sec
    rts

se_sb_step:
    lda #64
    sta st_budget
@loop:
    CMP24 st_pos,se_fs_length
    bcc @byte
    lda st_finish
    and #1                  ;bit7 marks a bounded fast job; bit0 owns EOF finish
    bne @complete
    inc st_finish
    jsr se_sm_finish
    lda se_sm_ready
    bne @event
@complete:
    lda #2
    clc
    rts
@byte:
    lda st_index
    cmp st_used
    bcc @cached
    COPY24 st_pos,se_fs_offset
    lda #128
    sta se_fs_count
    lda #<st_buffer
    sta se_fs_buffer
    lda #>st_buffer
    sta se_fs_buffer+1
    jsr se_fs_read
    bcs @return
    lda se_fs_done
    beq @bad
    cmp #129
    bcs @bad
    sta st_used
    lda #0
    sta st_index
@cached:
    ldx st_index
    lda st_buffer,x
    inc st_index
    pha
    SM_INC24 st_pos
    pla
    jsr se_sm_feed
    lda se_sm_ready
    bne @event
    dec st_budget
    jne @loop
    lda #0
    clc
    rts
@event:
    lda #1
    clc
@return:
    rts
@bad:
    lda #FS_BAD
    sec
    rts
