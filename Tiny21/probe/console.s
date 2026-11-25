.setcpu "6502"
.macpack longbranch
.include "question.inc"
.include "bundle.inc"
.import row_start, print, putchar
.if !::REU_ONLY
    .import format_time, clock_read, clock_delta, clock_now, clock_since
.endif
.import question_text, question_length, question_position, question_char
.import question_append, question_delete, question_begin, question_step, question_cancel
.import keyboard_init, keyboard_input, keyboard_stop
.import model_context
.if ::DUAL_MODEL
    .import active_model
    .if ::REU_ONLY
        .import scan_reu_model
    .else
        .import select_model
    .endif
.endif
.export console_main, console_prepare, console_edit, run_answer, render_answer_char

MAIL_PHASE = $ce04
SCREEN = $0400
INPUT_ROW = 7
STATUS_ROW = 10
ANSWER_ROW = 12
.if ::DUAL_MODEL
TIME_ROW = 22
.else
TIME_ROW = 17
.endif
PROMPT_VIEW = 72
ANSWER_START = SCREEN + 40*ANSWER_ROW
ANSWER_END = SCREEN + 40*TIME_ROW
ANSWER_SHIFT = ANSWER_END-ANSWER_START-40
ANSWER_CLEAR = 40*(TIME_ROW-STATUS_ROW+1)
RUN_STOP = 3
DEL = 8
RETURN = 13
cursor = $f0
KERNAL_KEY_COUNT = $c6
KERNAL_KEY = $0277

.segment "PROBEBSS"
answer_cursor: .res 2
answer_column: .res 1
prompt_answered: .res 1
.if ::REU_ONLY
reu_target:      .res 1
.endif

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
    lda prompt_answered
    bne keep_prompt
    sta question_length
keep_prompt:
    jsr render_prompt
    lda #5
    sta $d020
.if !::REU_ONLY
    lda #4
    sta MAIL_PHASE
.endif
    jmp input
.endproc

.proc console_prepare
    jsr keyboard_init
    lda #0
    sta prompt_answered
.if ::CONSOLE_AUTOMATION
    sta KERNAL_KEY_COUNT
.endif
.if ::REU_ONLY
    lda #$ff
    sta reu_target
    LINE 23, reu_controls
    LINE 24, model_keys
    jmp rescan_reu
.else
    jsr render_prompt_label
.if ::DUAL_MODEL
    LINE 23, dual_controls
    LINE 24, model_keys
    jsr render_model
    LINE STATUS_ROW, model_ready
.else
    LINE 20, controls
    LINE 21, cancel_hint
.endif
    jsr render_prompt
    lda #4
    sta MAIL_PHASE
    lda #5
    sta $d020
    rts
.endif
.endproc

.proc render_prompt_label
.if ::THIRD_MODEL
    lda active_model
    cmp #2
    bne context
    LINE 6, ask_japanese
    rts
context:
.endif
    lda model_context
    cmp #129
    bcs extended
    LINE 6, ask
    rts
extended:
    LINE 6, ask_extended
    rts
.endproc

; Accept one ASCII event. Carry set when a nonempty question is submitted.
.proc console_edit
.if ::DUAL_MODEL
    cmp #KEY_F1
    jeq tiny
    cmp #KEY_F3
    jeq programmer
.if ::THIRD_MODEL
    cmp #KEY_F5
    jeq japanese
.endif
.endif
.if ::REU_ONLY
    ldx reu_target
    bpl reu_wait
    ldx active_model
    bpl accepted
reu_wait:
    cmp #RETURN
    jne waiting
    jsr rescan_reu
    jmp waiting
accepted:
.endif
    cmp #RETURN
    beq submit
    cmp #DEL
    beq erase
    cmp #RUN_STOP
    beq clear
    ldx prompt_answered
    beq append
    ; The first printable key replaces the completed prompt.
    cmp #' '
    bcc waiting
    cmp #$7f
    bcs waiting
    ldx #0
    stx prompt_answered
    stx question_length
append:
    jsr question_append
    bcc redraw
    bcs waiting
erase:
    lda prompt_answered
    bne waiting
    jsr question_delete
    bcc redraw
    bcs waiting
clear:
    lda #0
    sta prompt_answered
    sta question_length
redraw:
    jsr render_prompt
waiting:
    clc
    rts
submit:
    lda prompt_answered
    bne waiting
    jsr question_begin
    bcs waiting
    sec
    rts
.if ::DUAL_MODEL
tiny:
    lda #0
    beq select
programmer:
    lda #1
.if ::THIRD_MODEL
    bne select
japanese:
    lda #2
.endif
select:
.if ::REU_ONLY
    cmp active_model
    bne request_image
    ldx reu_target
    bmi waiting
request_image:
    sta reu_target
    lda #$ff
    sta active_model
    jsr reset_reu_prompt
    jsr render_model
    jsr render_reu_image
    LINE STATUS_ROW, reu_attach
    clc
    rts
.else
    cmp active_model
    beq waiting
    pha
    LINE STATUS_ROW, switching
    pla
    jsr select_model
    bcs unavailable
    jsr question_cancel
    lda #0
    sta prompt_answered
    sta question_length
    jsr clear_answer
    jsr render_model
    jsr render_prompt_label
    jsr render_prompt
    LINE STATUS_ROW, model_ready
    clc
    rts
unavailable:
    LINE STATUS_ROW, model_missing
    clc
    rts
.endif
.endif
.endproc

.if ::REU_ONLY
.proc reset_reu_prompt
    lda #0
    sta prompt_answered
    sta question_length
    jsr clear_answer
    ldx #79
    lda #' '
clear:
    sta SCREEN+40*INPUT_ROW,x
    dex
    bpl clear
    rts
.endproc

.proc render_reu_image
    lda #6
    jsr row_start
    ldy reu_target
    bmi choose
    lda reu_hint_lo,y
    ldx reu_hint_hi,y
    jmp print
choose:
    TEXT reu_choose
    rts
.endproc

.proc rescan_reu
    jsr reset_reu_prompt
    LINE STATUS_ROW, reu_checking
    jsr scan_reu_model
    pha
    jsr render_model
    pla
    bne failed
    lda reu_target
    bmi ready
    cmp active_model
    bne wrong
ready:
    lda #$ff
    sta reu_target
    jsr render_prompt_label
    jsr render_prompt
    LINE STATUS_ROW, model_ready
    lda #5
    sta $d020
    rts
wrong:
    lda #5
failed:
    pha
    jsr render_reu_image
    lda #STATUS_ROW
    jsr row_start
    pla
    tay
    lda reu_error_lo-1,y
    ldx reu_error_hi-1,y
    jsr print
    lda #8
    sta $d020
    rts
.endproc
.endif

.proc render_prompt
    lda #' '
    ldx #79
clear:
    sta SCREEN+40*INPUT_ROW,x
    dex
    bpl clear
    lda #INPUT_ROW
    jsr row_start
    lda question_length
    sec
    sbc #PROMPT_VIEW
    bcs :+
    lda #0
:
    tax
copy:
    cpx question_length
    beq prompt_cursor
    lda question_text,x
    jsr putchar
    inx
    bne copy
prompt_cursor:
    lda prompt_answered
    bne done
    ldy #0
    lda #$a0
    sta (cursor),y
done:
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
    jsr clear_answer
    lda #<(SCREEN+40*ANSWER_ROW+1)
    sta answer_cursor
    lda #>(SCREEN+40*ANSWER_ROW+1)
    sta answer_cursor+1
    lda #1
    sta answer_column
    LINE STATUS_ROW, reading
.if !::REU_ONLY
    jsr clock_read
    jcs failed
    .repeat 4, I
        lda clock_now+I
        sta clock_since+I
    .endrepeat
.endif
step:
    jsr keyboard_stop
    jne cancelled
    jsr question_step
    jcs failed
    cmp #QUESTION_PREFILL
    beq progress
    cmp #QUESTION_OUTPUT
    beq emit
    cmp #QUESTION_CONTEXT
    jeq context
    LINE STATUS_ROW, finished
    jmp keep_prompt
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
    cmp #40
    bcs step
    tay
    lda #'.'
    sta (cursor),y
    jmp step
emit:
.if !::REU_ONLY
    lda #2
    sta MAIL_PHASE
.endif
    lda #4
    sta $d020
    jsr render_answer_char
    jmp step
context:
    LINE STATUS_ROW, limit
keep_prompt:
    lda #1
    sta prompt_answered
.if ::REU_ONLY
    rts
.else
    jmp time
.endif
cancelled:
    jsr question_cancel
    LINE STATUS_ROW, stopped
.if ::REU_ONLY
    rts
.else
    jmp time
.endif
failed:
    jsr question_cancel
    lda #0
    sta prompt_answered
    LINE STATUS_ROW, error
    rts
.if !::REU_ONLY
time:
    jsr clock_read
    bcs failed
    jsr clock_delta
    LINE TIME_ROW, duration
    jmp format_time
.endif
.endproc

.proc render_answer_char
.if ::DUAL_MODEL
    lda question_char
    cmp #13
    beq newline
.endif
    lda answer_cursor+1
    cmp #>ANSWER_END
    bne show_char
    lda answer_cursor
    cmp #<ANSWER_END
    bne show_char
    jsr scroll_answer
show_char:
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
    inc answer_column
    lda answer_column
    cmp #40
    bne output_done
    lda #0
    sta answer_column
output_done:
    rts
.if ::DUAL_MODEL
newline:
    lda answer_column
    beq output_done
    lda #40
    sec
    sbc answer_column
    clc
    adc answer_cursor
    sta answer_cursor
    bcc :+
    inc answer_cursor+1
:
    lda #0
    sta answer_column
    rts
.endif
.endproc

.proc clear_answer
    lda #' '
    ldx #0
clear:
    .repeat ::ANSWER_CLEAR / 256, I
        sta SCREEN+40*STATUS_ROW+256*I,x
    .endrepeat
    inx
    bne clear
    ldx #(<ANSWER_CLEAR)-1
tail:
    sta SCREEN+40*STATUS_ROW+(ANSWER_CLEAR / 256)*256,x
    dex
    bpl tail
    rts
.endproc

.if ::DUAL_MODEL
.proc render_model
    lda active_model
.if ::REU_ONLY
    bpl known
    LINE 5, reu_unknown
    rts
known:
.endif
    bne programmer
    LINE 5, model_tiny
    rts
programmer:
.if ::THIRD_MODEL
    cmp #2
    beq japanese
.endif
    LINE 5, model_prog
    rts
.if ::THIRD_MODEL
japanese:
    LINE 5, model_japanese
    rts
.endif
.endproc
.endif

.proc scroll_answer
    ldx #0
.if ::ANSWER_SHIFT >= 256
shift_page:
    lda ANSWER_START+40,x
    sta ANSWER_START,x
    inx
    bne shift_page
.endif
shift:
    lda ANSWER_START+40+(ANSWER_SHIFT / 256)*256,x
    sta ANSWER_START+(ANSWER_SHIFT / 256)*256,x
    inx
    cpx #<ANSWER_SHIFT
    bne shift
    ldx #39
    lda #' '
clear:
    sta ANSWER_END-40,x
    dex
    bpl clear
    lda #<(ANSWER_END-40)
    sta answer_cursor
    lda #>(ANSWER_END-40)
    sta answer_cursor+1
    rts
.endproc

ask:         .asciiz "Question (72 characters)               "
ask_extended:.asciiz "Question (long input scrolls left)     "
.if ::THIRD_MODEL
ask_japanese:.asciiz "Type an English sentence to translate  "
.endif
controls:    .asciiz "RETURN ask   DEL erase   RUN/STOP clear"
cancel_hint: .asciiz "Hold RUN/STOP to cancel an answer"
reading:     .asciiz "Reading question"
finished:    .asciiz "Answer complete. Ready.                "
limit:       .asciiz "Context full. Ready.                   "
stopped:     .asciiz "Cancelled. Ready.                      "
error:       .asciiz "Answer failed. Ready.                  "
duration:    .asciiz "Elapsed "
.if ::DUAL_MODEL
dual_controls: .asciiz "RETURN ask  DEL erase  RUN/STOP cancel"
.if ::THIRD_MODEL
model_keys:    .asciiz "F1 Tiny 2.1  F3 C64PROGINFO  F5 Romaji"
model_japanese:.asciiz "Model: English to Japanese (romaji)    "
.else
model_keys:    .asciiz "F1 Tiny 2.1   F3 C64PROGINFO"
.endif
model_tiny:    .asciiz "Model: Tiny 2.1                         "
model_prog:    .asciiz "Model: C64PROGINFO                      "
switching:     .asciiz "Checking selected model...              "
model_ready:   .asciiz "Model ready.                            "
model_missing: .asciiz "Load failed. Current model kept.       "
.endif
.if ::REU_ONLY
.macro SCREEN_TEXT text
    .byte text
    .res 39-.strlen(text), ' '
    .byte 0
.endmacro
reu_controls: SCREEN_TEXT "RETURN ask/recheck   DEL   RUN/STOP"
reu_unknown:  SCREEN_TEXT "Model: awaiting a valid REU image"
reu_choose:   SCREEN_TEXT "F1/F3/F5 show the model image name"
reu_attach:   SCREEN_TEXT "Attach image, then press RETURN."
reu_checking: SCREEN_TEXT "Checking REU image..."
reu_absent:   SCREEN_TEXT "REU missing. Enable it, then RETURN."
reu_small:    SCREEN_TEXT "Need at least 1 MiB REU. Then RETURN."
reu_foreign:  SCREEN_TEXT "Unknown image. Attach it, then RETURN."
reu_corrupt:  SCREEN_TEXT "Image failed check. Reload, then RETURN"
reu_wrong:    SCREEN_TEXT "Different model. Swap it, then RETURN."
reu_tiny:     SCREEN_TEXT "Use TINY21.REU at REU address 0"
reu_prog:     SCREEN_TEXT "Use C64PROGINFO.REU at REU address 0"
reu_japanese: SCREEN_TEXT "Use E2JROMAJI.REU at REU address 0"
reu_hint_lo:  .byte <reu_tiny, <reu_prog, <reu_japanese
reu_hint_hi:  .byte >reu_tiny, >reu_prog, >reu_japanese
reu_error_lo: .byte <reu_absent, <reu_small, <reu_foreign, <reu_corrupt, <reu_wrong
reu_error_hi: .byte >reu_absent, >reu_small, >reu_foreign, >reu_corrupt, >reu_wrong
.endif
.assert cancel_hint-controls <= 40, error, "controls must fit one screen row"
.assert reading-cancel_hint <= 40, error, "cancel hint must fit one screen row"
