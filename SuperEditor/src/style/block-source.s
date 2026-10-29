; R14 owns source access, so it also performs the bounded block-parser scan.
; One call consumes at most64 bytes or returns one completed logical event.
.setcpu "6502"
.macpack longbranch
.include "fold/source.inc"
.include "style/api.inc"
.include "supermark/api.inc"
.import se_sm_init,se_sm_feed,se_sm_finish,se_sm_ready,se_sm_at_line
.import se_sm_pos,se_sm_state,se_sm_fence,se_sm_language,se_sm_regions
.import st_budget,st_index,st_used,st_buffer,st_pos,st_finish,st_row,st_col
.export se_sb_init,se_sb_step
.segment "FOLD_SOURCE_CODE"

; Consume the authenticated persistent ticket written by R25. The ticket check
; covers bytes1..19 and reduces to the published phase. Both the checksum and
; phase must name ADMITTED; INVALID and READY therefore cannot restart work.
; C6 owns checkpoint CRC, geometry and mode identity before ADMITTED, and every
; foreground input retires that phase. C14 owns the current source/epoch checks
; before this no-yield restore. A=1 is fast with st_row=start/st_col=end.
se_sb_init:
    jsr se_sm_init
    lda #ST_TX_CHECK_SEED
    ldx #ST_TX_BYTES-1
@check:
    eor se_st_tx,x
    dex
    bne @check
    cmp se_st_tx+ST_TX_PHASE
    bne sb_cold
    cmp #ST_TX_ADMITTED
    bne sb_cold
    lda se_st_tx+ST_TX_ROW_MODE
    and #ST_TX_ROW_MASK
    sta st_row
    lda se_st_tx+ST_TX_COUNT_KIND
    and #ST_TX_COUNT_MASK
    clc
    adc st_row
    sta st_col
    jmp sb_carry

sb_cold:
    lda #0
    clc
    rts

; C14 has authenticated the ticket and R25 has normalized its referenced carry.
; The two ASLs cannot set carry for a row <=21, giving X=row*5 without scratch.
sb_carry:
    lda st_row
    asl
    asl
    adc st_row
    tax
    lda se_st_cp_rows,x
    bpl sb_cold
    and #STYLE_CARRY_FENCE_MASK
    sta se_sm_fence
    lda se_st_cp_rows,x
    lsr
    lsr
    lsr
    lsr
    and #3
    sta se_sm_language
    lda se_st_cp_rows+1,x
    sta se_sm_regions
    lda se_st_cp_rows+2,x
    sta se_sm_state+76
    lda se_st_cp_rows+3,x
    sta se_sm_state+77
    lda se_st_cp_rows+4,x
    sta se_sm_state+78
    ldx #2
@position:
    lda se_st_tx+ST_TX_START,x
    sta st_pos,x
    sta se_sm_pos,x
    dex
    bpl @position
    jsr se_sm_at_line
    lda #0
    sta st_index
    sta st_used
    lda #1
    clc
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
