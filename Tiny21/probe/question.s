.setcpu "6502"
.include "question.inc"
.import model_reset, model_ingest, model_choose, token_pos
.export question_text, question_length, question_position, question_char
.export question_append, question_delete, question_begin, question_step, question_cancel

.segment "PROBEBSS"
question_text:     .res QUESTION_LIMIT
question_length:   .res 1
question_position: .res 1
question_char:     .res 1
question_end:      .res 1
question_lower:    .res 1
question_active:   .res 1
pending_token:     .res 1

.segment "PROBE"
; Input editor accepts ASCII. Carry set if a character was ignored.
.proc question_append
    cmp #' '
    bcc ignored
    cmp #$7f
    bcs ignored
    ldx question_length
    cpx #QUESTION_LIMIT
    bcs ignored
    sta question_text,x
    inc question_length
    clc
    rts
ignored:
    sec
    rts
.endproc

.proc question_delete
    lda question_length
    beq empty
    dec question_length
    clc
    rts
empty:
    sec
    rts
.endproc

; Trim trailing spaces without rewriting the displayed buffer. Lowercase
; ASCII letters as they are ingested if the prompt has no lowercase letters.
.proc question_begin
    jsr question_cancel
    ldx question_length
trim:
    beq empty
    lda question_text-1,x
    cmp #' '
    bne trimmed
    dex
    bne trim
empty:
    sec
    rts
trimmed:
    stx question_end
    lda #1
    sta question_lower
    sta question_active
case_scan:
    dex
    lda question_text,x
    cmp #'a'
    bcc next
    cmp #'z'+1
    bcs next
    dec question_lower
    clc
    rts
next:
    cpx #0
    bne case_scan
    clc
    rts
.endproc

; This entry is called only between complete token ingests. Reset invalidates
; stale history and logits without touching weights or clearing REU memory.
.proc question_cancel
    jsr model_reset
    lda #0
    sta question_position
    sta question_active
    sta pending_token
    rts
.endproc

; At most one complete native token ingest per call. A reports the event and
; question_char contains the emitted ASCII byte for QUESTION_OUTPUT.
.proc question_step
    lda question_active
    beq idle
    lda pending_token
    bne decode
    ldy question_position
    cpy question_end
    beq delimiter
    lda question_text,y
    ldx question_lower
    beq token
    cmp #'A'
    bcc token
    cmp #'Z'+1
    bcs token
    ora #$20
token:
    sec
    sbc #30
    ldx #0
    jsr model_ingest
    bcs failure
    inc question_position
    lda #QUESTION_PREFILL
    clc
    rts
delimiter:
    lda #1
decode:
    ldx #1
    jsr model_ingest
    bcs failure
    lda token_pos
    cmp #128
    beq context
    jsr model_choose
    bcs failure
    cmp #2
    bcc eos
    sta pending_token
    clc
    adc #30
    sta question_char
    lda #QUESTION_OUTPUT
    rts
idle:
    lda #QUESTION_IDLE
    clc
    rts
context:
    lda #QUESTION_CONTEXT
    bne finish
eos:
    lda #QUESTION_EOS
finish:
    ldx #0
    stx question_active
    clc
    rts
failure:
    jsr question_cancel
    sec
    rts
.endproc
