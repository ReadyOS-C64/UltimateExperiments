.setcpu "6502"
.include "bundle.inc"
.if REU_ONLY
.import console_main
.export probe_main, row_start, print, putchar
.else
.import load_model_file, dos_stage, dos_status
.import uci_identity, uci_observed, uci_detail, uci_other_ids
.import verify_model_image, model_crc
.import clock_start, clock_read, clock_delta, clock_rate, clock_now, clock_since
.import clock_is_pal, clock_elapsed, turbo_start, turbo_restore, turbo_readback, turbo_sample
.import turbo_detail, clock_detail, clock_controls
.import model_open, model_reset, model_ingest, model_choose, token_pos, model_context
.importzp reu_banks
.import wide_a, wide_b, wide_divide, wide_remainder
.export probe_main, check_resident_model
.if INTERACTIVE
.import console_main
.export row_start, print, putchar, format_time
.endif
.if QUALIFY_REU
.import qualify_reu
.endif
.endif

; Mailbox addresses remain stable for independent host readback.
MAIL = $ce00
RECORD1 = $cc00
RECORD2 = $cd00
SCREEN = $0400
COLOR = $d800
cursor = $f0
message = $f2
result = $f4

.segment "PROBEBSS"
.if !REU_ONLY
question_id: .res 1
question_at: .res 1
answer_len:  .res 1
next_token:  .res 1
question_start: .res 4
first_ticks: .res 4
total_ticks: .res 4
digits: .res 6
.endif

.segment "PROBE"
.macro TEXT label
    lda #<(label)
    ldx #>(label)
    jsr print
.endmacro

.macro AT row
    lda #row
    jsr row_start
.endmacro

.macro COPY4 source, dest
    .repeat 4, I
        lda source+I
        sta dest+I
    .endrepeat
.endmacro

probe_main:
.if REU_ONLY
    jsr screen_init
    AT 2
    TEXT subtitle
    jmp console_main
.else
    lda #0
    ldx #$1f
clear_mail:
    sta MAIL,x
    dex
    bpl clear_mail
    sta RECORD1
    sta RECORD2
.if CONTEXT_TEST
    sta RECORD1+137
.endif
    lda #'T'
    sta MAIL
    lda #'6'
    sta MAIL+1
    lda #'4'
    sta MAIL+2
    lda #'P'
    sta MAIL+3
    lda #<RUN_NONCE
    sta MAIL+30
    lda #>RUN_NONCE
    sta MAIL+31
    jsr screen_init
    jsr clock_start
    lda clock_is_pal
    sta MAIL+5
    COPY4 clock_rate, MAIL+12
    jsr turbo_start
    php
    lda turbo_readback
    sta MAIL+6
    COPY4 turbo_sample, MAIL+16
    lda turbo_detail
    sta MAIL+26
    lda clock_detail
    sta MAIL+27
    lda clock_controls
    sta MAIL+28
    lda clock_controls+1
    sta MAIL+29
    plp
    bcc turbo_ok
    lda #$81
    jmp error
turbo_ok:
    AT 2
    TEXT subtitle
.if QUALIFY_REU
    jsr qualify_reu
    bcc :+
    lda #$87
    jmp error
:
.endif
    lda #32
    sta reu_banks
    AT 4
    TEXT checking
    jsr check_resident_model
    bcs disk_fallback
    COPY4 model_crc, MAIL+20
    lda #5                  ; CRC-verified image was already in REU
    sta MAIL+7
    AT 4
    TEXT preloaded
    jmp start_inference

disk_fallback:
    jsr clock_read
    bcc start_load
    jmp clock_error
start_load:
    COPY4 clock_now, question_start
    jsr load_model_file
    php
    lda dos_stage
    sta MAIL+7
    lda dos_status
    sta MAIL+24
    lda dos_status+1
    sta MAIL+25
    plp
    bcc load_ok
    lda uci_identity
    sta MAIL+8
    lda uci_observed
    sta MAIL+9
    lda uci_detail
    sta MAIL+10
    lda clock_detail
    sta MAIL+11
    lda uci_other_ids
    sta MAIL+20
    lda uci_other_ids+1
    sta MAIL+21
    AT 21
    TEXT load_hint
    lda #$82
    jmp error
load_ok:
    jsr elapsed
    bcc store_load
    jmp clock_error
store_load:
    COPY4 clock_elapsed, MAIL+8

    AT 4
    TEXT checking
    lda #32
    sta reu_banks
    jsr verify_model_image
    php
    COPY4 model_crc, MAIL+20
    plp
    bcc verify_ok
    lda #$83
    jmp error
verify_ok:
    jsr model_open
    bcc admitted
    lda #$84
    jmp error
admitted:
    AT 4
    TEXT loaded
    COPY4 MAIL+8, clock_elapsed
    jsr format_time
    TEXT clear_load
start_inference:
.if INTERACTIVE
    jmp console_main
.else
    lda #0
    sta question_id
    jsr run_question
    bcc second
    jmp network_error
second:
    inc question_id
    jsr run_question
    bcc complete
    jmp network_error
complete:
    AT 22
    TEXT finished
    lda #3
    sta MAIL+4
    lda #5
    sta $d020
    jsr turbo_restore
.endif
park:
    jmp park

network_error:
    lda #$85
    bne error
clock_error:
    lda #$86
error:
    sta MAIL+4
    pha
    AT 22
    TEXT failure
    pla
    and #$0f
    ora #'0'
    jsr putchar
    lda #2
    sta $d020
    jsr turbo_restore
    jmp park

.proc check_resident_model
    ; Reject an empty or foreign REU quickly using the model header.
    jsr model_open
    bcs done
    jmp verify_model_image
done:
    rts
.endproc

elapsed:
    jsr clock_read
    bcs elapsed_failed
    COPY4 question_start, clock_since
    jsr clock_delta
    clc
elapsed_failed:
    rts

run_question:
    ldx question_id
    lda borders,x
    sta $d020
    txa
    clc
    adc #1
    sta MAIL+4
    lda question_rows,x
    jsr row_start
    ldx question_id
    ldy prompt_lo,x
    lda prompt_hi,x
    tax
    tya
    jsr print
    ldx question_id
    lda answer_rows,x
    jsr row_start

    lda #0
    sta answer_len
    sta question_at
    .repeat 4, I
        sta first_ticks+I
    .endrepeat
    jsr model_reset
    jsr clock_read
    bcc :+
    rts
:
    COPY4 clock_now, question_start
prefill:
    ldx question_id
    lda prompt_lo,x
    sta message
    lda prompt_hi,x
    sta message+1
    ldy question_at
    lda (message),y
    beq delimiter
    sec
    sbc #30
    ldx #0
    jsr model_ingest
    bcc :+
    rts
:
    inc question_at
    jmp prefill
delimiter:
    lda #1
    tax
    jsr model_ingest
    bcc answer
    rts
answer:
    lda token_pos
    cmp model_context
    bcs done
    jsr model_choose
    bcc :+
    rts
:
    cmp #2
    bcc done
    sta next_token
    lda answer_len
    bne emit
    jsr elapsed
    bcc :+
    rts
:
    COPY4 clock_elapsed, first_ticks
emit:
    lda #0
    sta result
    ldx question_id
    lda result_hi,x
    sta result+1
    lda answer_len
    clc
    adc #10
    tay
    lda next_token
    clc
    adc #30
    sta (result),y
    jsr putchar
    inc answer_len
    lda next_token
    ldx #1
    jsr model_ingest
    bcc answer
    rts
done:
    jsr elapsed
    bcc :+
    rts
:
    COPY4 clock_elapsed, total_ticks
.if CONTEXT_TEST
    lda question_id
    bne :+
    jsr certify_context
    bcc :+
    rts
:
.endif
    lda #0
    sta result
    ldx question_id
    lda result_hi,x
    sta result+1
    ldy #1
    lda answer_len
    sta (result),y
    .repeat 4, I
        iny
        lda first_ticks+I
        sta (result),y
    .endrepeat
    .repeat 4, I
        iny
        lda total_ticks+I
        sta (result),y
    .endrepeat
    ldy #0
    lda #$a5
    sta (result),y

    ldx question_id
    lda timing_rows,x
    jsr row_start
    TEXT first_label
    COPY4 first_ticks, clock_elapsed
    jsr format_time
    TEXT total_label
    COPY4 total_ticks, clock_elapsed
    jsr format_time
    clc
    rts

.if CONTEXT_TEST
.proc certify_context
    lda token_pos
    cmp #128
    bne failed
    lda #2
    ldx #0
    jsr model_ingest
    bcc failed
    lda token_pos
    cmp #128
    bne failed
    sta RECORD1+137
    clc
    rts
failed:
    sec
    rts
.endproc
.endif

; Render SSS.mmm from raw PHI2 ticks. Keep raw values in the mailbox.
format_time:
    lda #0
    ldx #11
clear_div:
    sta wide_a,x
    sta wide_b,x
    dex
    bpl clear_div
    COPY4 clock_elapsed, wide_a
    COPY4 clock_rate, wide_b
    jsr wide_divide
    lda wide_a
    sta digits
    lda wide_a+1
    sta digits+1
    ; (remainder * 1000) / F. First form remainder * 125, then shift.
    lda #0
    ldx #3
clear_scaled:
    sta wide_a,x
    dex
    bpl clear_scaled
    ldx #125
multiply_ms:
    clc
    .repeat 4, I
        lda wide_a+I
        adc wide_remainder+I
        sta wide_a+I
    .endrepeat
    dex
    bne multiply_ms
    .repeat 3
        asl wide_a
        rol wide_a+1
        rol wide_a+2
        rol wide_a+3
    .endrepeat
    jsr wide_divide
    lda wide_a
    sta digits+2
    lda wide_a+1
    sta digits+3
    ldx #0
    jsr decimal3
    lda #'.'
    jsr putchar
    ldx #2
    jsr decimal3
    lda #'S'
    jmp putchar

; Input number 0..999 in digits+X. UCI timeout and attention probe limit
; keep observed elapsed time well below 1000 seconds per question.
decimal3:
    ldy #'0'
hundreds:
    lda digits+1,x
    bne subtract100
    lda digits,x
    cmp #100
    bcc print100
subtract100:
    sec
    lda digits,x
    sbc #100
    sta digits,x
    lda digits+1,x
    sbc #0
    sta digits+1,x
    iny
    bne hundreds
print100:
    tya
    jsr putchar
    ldy #'0'
tens:
    lda digits,x
    cmp #10
    bcc print10
    sbc #10
    sta digits,x
    iny
    bne tens
print10:
    tya
    jsr putchar
    lda digits,x
    ora #'0'
    jmp putchar
.endif

screen_init:
    lda $dd02
    ora #3
    sta $dd02
    lda $dd00
    ora #3
    sta $dd00
    lda #$1b
    sta $d011
    lda #$08
    sta $d016
    lda #$16                  ; lowercase ROM character set
    sta $d018
    lda #0
    sta $d015
    sta $d01a
    lda #8
    sta $d020
    lda #11
    sta $d021
    ldx #0
fill:
    lda #' '
    .repeat 4, I
        sta SCREEN+256*I,x
    .endrepeat
    lda #1
    .repeat 4, I
        sta COLOR+256*I,x
    .endrepeat
    inx
    bne fill
    ldx #39
accent:
    lda #3
    sta COLOR+40,x
    sta COLOR+40*2,x
    lda #7
    sta COLOR+40*7,x
.if INTERACTIVE
    sta COLOR+40*8,x
.endif
    sta COLOR+40*14,x
    lda #13
    sta COLOR+40*11,x
    sta COLOR+40*18,x
    dex
    bpl accent
.if !REU_ONLY
    ; Passive video identity. A reverse space fills its whole cell, so
    ; an out-of-band observer can establish that this PRG owns the screen.
    ldx #11
video_marker:
    lda #$a0
    sta SCREEN+1,x
    lda marker_colors,x
    sta COLOR+1,x
    dex
    bpl video_marker
.endif
    AT 1
    TEXT title
.if !REU_ONLY
    AT 4
    TEXT loading
.endif
    rts

row_start:
    tay
    lda row_low,y
    sta cursor
    lda row_high,y
    sta cursor+1
    rts

print:
    sta message
    stx message+1
    ldy #0
print_next:
    lda (message),y
    beq print_done
    jsr putchar
    iny
    bne print_next
print_done:
    rts

; ASCII through the C64 lowercase character set. Unsupported wide ASCII
; punctuation is represented as a question mark on screen only.
putchar:
    cmp #'a'
    bcc upper
    cmp #'z'+1
    bcs unsupported
    sec
    sbc #$60
    bcs glyph
upper:
    cmp #'A'
    bcc glyph
    cmp #'Z'+1
    bcs check_punctuation
    jmp glyph                  ; uppercase screen codes equal ASCII A-Z
check_punctuation:
    cmp #$60
    bcc glyph
unsupported:
    lda #'?'
glyph:
    sty saved_y
    ldy #0
    sta (cursor),y
    inc cursor
    bne :+
    inc cursor+1
:
    ldy saved_y
    rts

.segment "PROBEBSS"
saved_y: .res 1

.segment "PROBE"
.if !REU_ONLY
marker_colors: .byte RUN_MARKER
.endif
row_low:
    .repeat 25, I
        .byte <(SCREEN+I*40+1)
    .endrepeat
row_high:
    .repeat 25, I
        .byte >(SCREEN+I*40+1)
    .endrepeat
.if REU_ONLY
title: .asciiz "C64 LLM - Little Language Model"
subtitle: .asciiz "REU edition - 1 MiB or more"
.else
question_rows: .byte 7,14
.if CONTEXT_TEST
answer_rows: .byte 9,15
timing_rows: .byte 12,18
.else
answer_rows: .byte 8,15
timing_rows: .byte 11,18
.endif
borders: .byte 3,4
result_hi: .byte >RECORD1,>RECORD2
prompt_lo: .byte <prompt1,<prompt2
prompt_hi: .byte >prompt1,>prompt2
.if INTERACTIVE
title: .asciiz "C64 LLM - Little Language Model"
subtitle: .asciiz "64 MHz checked, 16 MiB REU"
.else
title: .byte "TINY 2.1 / ULTIMATE INFERENCE PROBE",0
subtitle: .byte "64 MHz checked | 16 MiB REU",0
.endif
loading: .byte "Ultimate DOS is loading MODEL.BIN...",0
checking: .byte "Verifying the REU image CRC32...    ",0
loaded: .byte "Ultimate DOS load ",0
preloaded: .asciiz "Preloaded REU model verified         "
.if DUAL_MODEL
load_hint: .asciiz "Check USB folder and model files"
.else
load_hint: .asciiz "Load MODEL.REU in the Ultimate menu"
.endif
clear_load: .byte "            ",0
.if CONTEXT_TEST
finished: .byte "CONTEXT LIMIT / RECOVERY PASSED",0
.else
finished: .byte "COMPLETE / TWO NATIVE RUNS",0
.endif
failure: .byte "PROBE ERROR ",0
first_label: .byte "FIRST ",0
total_label: .byte "  TOTAL ",0
.if CONTEXT_TEST
prompt1: .byte CONTEXT_PROMPT,0
.else
prompt1: .byte "what is 7 times 8",0
.endif
prompt2: .byte "what is the capital of peru",0
.endif
