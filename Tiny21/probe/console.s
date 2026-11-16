.setcpu "6502"
.macpack longbranch
.include "question.inc"
.include "bundle.inc"
.import row_start, print, putchar, format_time
.import clock_read, clock_delta, clock_now, clock_since
.import question_text, question_length, question_position, question_char
.import question_append, question_delete, question_begin, question_step, question_cancel
.import keyboard_init, keyboard_input, keyboard_stop
.export console_main, console_prepare, console_edit, run_answer

MAIL_PHASE = $ce04
SCREEN = $0400
INPUT_ROW = 7
STATUS_ROW = 10
ANSWER_ROW = 12
TIME_ROW = 17
RUN_STOP = 3
DEL = 8
RETURN = 13
cursor = $f0
KERNAL_KEY_COUNT = $c6
KERNAL_KEY = $0277

.segment "PROBEBSS"
answer_cursor: .res 2

.segment "PROBE"
.macro TEXT label
    lda #<(label)
    ldx #>(label)
    jsr print
.endmacro

.macro LINE row, label
    lda #row
    jsr row_start
    TEXT label
.endmacro

.proc console_main
    jsr console_prepare
input:
    jsr wait_frame
    jsr keyboard_input
.if ::CONSOLE_AUTOMATION
    bne edit
    lda KERNAL_KEY_COUNT
    beq input
    lda KERNAL_KEY
    ldx #0
    stx KERNAL_KEY_COUNT
    ; Defer injected RETURN one frame after acknowledging its queue entry.
    cmp #RETURN
    bne edit
    pha
    jsr wait_frame
    pla
edit:
.endif
    jsr console_edit
    bcc input
    jsr run_answer
    lda #0
    sta question_length
    jsr render_prompt
    lda #5
    sta $d020
    lda #4
    sta MAIL_PHASE
    jmp input
.endproc

.proc console_prepare
    jsr keyboard_init
.if ::CONSOLE_AUTOMATION
    lda #0
    sta KERNAL_KEY_COUNT
.endif
    LINE 6, ask
    LINE 20, controls
    LINE 21, cancel_hint
    jsr render_prompt
    lda #4
    sta MAIL_PHASE
    lda #5
    sta $d020
    rts
.endproc

; Accept one ASCII event. Carry set when a nonempty question is submitted.
.proc console_edit
    cmp #RETURN
    beq submit
    cmp #DEL
    beq erase
    cmp #RUN_STOP
    beq clear
    jsr question_append
    bcc redraw
    bcs waiting
erase:
    jsr question_delete
    bcc redraw
    bcs waiting
clear:
    lda #0
    sta question_length
redraw:
    jsr render_prompt
waiting:
    clc
    rts
submit:
    jsr question_begin
    bcs waiting
    sec
    rts
.endproc

.proc render_prompt
    lda #' '
    ldx #79
clear:
    sta SCREEN+40*INPUT_ROW,x
    dex
    bpl clear
    lda #INPUT_ROW
    jsr row_start
    ldx #0
copy:
    cpx question_length
    beq prompt_cursor
    lda question_text,x
    jsr putchar
    inx
    bne copy
prompt_cursor:
    ldy #0
    lda #$a0
    sta (cursor),y
    rts
.endproc

; D011 bit 7 is the high raster bit. Sample the matrix once per frame.
.proc wait_frame
high:
    bit $d011
    bpl high
low:
    bit $d011
    bmi low
    rts
.endproc

.proc run_answer
    lda #1
    sta MAIL_PHASE
    lda #3
    sta $d020
    lda #' '
    ldx #239
clear_old:
    sta SCREEN+40*STATUS_ROW,x
    dex
    cpx #$ff
    bne clear_old
    ldx #39
clear_time:
    sta SCREEN+40*TIME_ROW,x
    dex
    bpl clear_time
    lda #<(SCREEN+40*ANSWER_ROW+1)
    sta answer_cursor
    lda #>(SCREEN+40*ANSWER_ROW+1)
    sta answer_cursor+1
    LINE STATUS_ROW, reading
    jsr clock_read
    jcs failed
    .repeat 4, I
        lda clock_now+I
        sta clock_since+I
    .endrepeat
step:
    jsr keyboard_stop
    bne cancelled
    jsr question_step
    jcs failed
    cmp #QUESTION_PREFILL
    beq progress
    cmp #QUESTION_OUTPUT
    beq emit
    cmp #QUESTION_CONTEXT
    beq context
    LINE STATUS_ROW, finished
    jmp time
progress:
    lda question_position
    and #7
    bne step
    lda #STATUS_ROW
    jsr row_start
    ldx question_position
    txa
    lsr
    lsr
    lsr
    clc
    adc #16
    tay
    lda #'.'
    sta (cursor),y
    jmp step
emit:
    lda #2
    sta MAIL_PHASE
    lda #4
    sta $d020
    lda answer_cursor
    sta cursor
    lda answer_cursor+1
    sta cursor+1
    lda question_char
    jsr putchar
    lda cursor
    sta answer_cursor
    lda cursor+1
    sta answer_cursor+1
    jmp step
context:
    LINE STATUS_ROW, limit
    jmp time
cancelled:
    jsr question_cancel
    LINE STATUS_ROW, stopped
    jmp time
failed:
    jsr question_cancel
    LINE STATUS_ROW, error
    rts
time:
    jsr clock_read
    bcs failed
    jsr clock_delta
    LINE TIME_ROW, duration
    jmp format_time
.endproc

ask:         .asciiz "Question (72 characters)"
controls:    .asciiz "RETURN ask   DEL erase   RUN/STOP clear"
cancel_hint: .asciiz "Hold RUN/STOP to cancel an answer"
reading:     .asciiz "Reading question"
finished:    .asciiz "Answer complete. Ready.                "
limit:       .asciiz "Context full. Ready.                   "
stopped:     .asciiz "Cancelled. Ready.                      "
error:       .asciiz "Answer failed. Ready.                  "
duration:    .asciiz "Elapsed "
.assert cancel_hint-controls <= 40, error, "controls must fit one screen row"
.assert reading-cancel_hint <= 40, error, "cancel hint must fit one screen row"
