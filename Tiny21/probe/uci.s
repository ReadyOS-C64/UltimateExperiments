.setcpu "6502"
.include "bundle.inc"
.import clock_read, clock_delta, clock_now, clock_since, clock_elapsed
.export load_model_file, dos_stage, dos_status
.export uci_identity, uci_observed, uci_detail, uci_other_ids
.if DUAL_MODEL
    .import requested_model
.endif

UCI_CONTROL = $df1c
UCI_COMMAND = $df1d
UCI_DATA    = $df1e
UCI_STATUS  = $df1f
command_ptr = $f0

.segment "PROBEBSS"
command_length: .res 1
reply_state:    .res 1
more_pending:   .res 1
last_status:    .res 1
data_count:     .res 1
status_count:   .res 1
reply_data:     .res 32
dos_status:     .res 2
dos_stage:      .res 1
file_open:      .res 1
failed_status:  .res 2
uci_identity:  .res 1
uci_observed:  .res 1
uci_detail:    .res 1
uci_other_ids: .res 2

.segment "PROBE"
; Ultimate DOS instance 2. Use an explicit path and read-only attributes.
; Validate the opened byte count before LOAD_REU and close on every exit.
load_model_file:
    lda #0
    sta file_open
    sta dos_status
    sta dos_status+1
    lda #1
    sta dos_stage
    sta uci_detail
    lda UCI_CONTROL
    sta uci_observed
    lda $de1d
    sta uci_other_ids
    lda $dffd
    sta uci_other_ids+1
    lda UCI_COMMAND
    sta uci_identity
    cmp #$c9
    beq :+
    sec
    rts
:
.if DUAL_MODEL
    ldy requested_model
    lda open_command_low,y
    ldx open_command_high,y
    pha
    lda open_command_length,y
    tay
    pla
.else
    lda #<open_cmd
    ldx #>open_cmd
    ldy #open_end-open_cmd
.endif
    jsr exchange
    bcs loader_failed
    inc file_open
    inc dos_stage
    lda #<info_cmd
    ldx #>info_cmd
    ldy #2
    jsr exchange
    bcs loader_failed
    lda data_count
    cmp #4
    bcc loader_failed
    ldx #3
.if DUAL_MODEL
    lda requested_model
    asl
    asl
    ora #3
    tay
.endif
check_size:
    lda reply_data,x
.if DUAL_MODEL
    cmp model_size,y
    bne loader_failed
    dey
.else
    cmp model_size,x
    bne loader_failed
.endif
    dex
    bpl check_size
    inc dos_stage
.if DUAL_MODEL
    ldy requested_model
    lda load_command_low,y
    ldx load_command_high,y
.else
    lda #<load_cmd
    ldx #>load_cmd
.endif
    ldy #10
    jsr exchange
    bcs loader_failed
    inc dos_stage
    jmp close_file

loader_failed:
    lda dos_status
    sta failed_status
    lda dos_status+1
    sta failed_status+1
    lda file_open
    beq :+
    jsr close_file
:
    lda failed_status
    sta dos_status
    lda failed_status+1
    sta dos_status+1
    sec
    rts

close_file:
    lda #0
    sta file_open
    lda #<close_cmd
    ldx #>close_cmd
    ldy #2
    jmp exchange

; A/X points to command bytes and Y carries the nonzero length.
; Timer-derived deadline covers idle sync, a busy interval, and all
; response blocks. CLK reads destroy X, so command bytes are sent together.
exchange:
    sta command_ptr
    stx command_ptr+1
    sty command_length
    lda #0
    sta data_count
    sta status_count
    sta dos_status
    sta dos_status+1
    sta more_pending
    lda #2
    sta uci_detail
    jsr clock_read
    bcc :+
    sec
    rts
:
    .repeat 4, I
        lda clock_now+I
        sta clock_since+I
    .endrepeat
    lda #3
    sta uci_detail
    lda #$08                   ; clear any earlier push-state error
    sta UCI_CONTROL
wait_idle:
    lda UCI_CONTROL
    sta uci_observed
    bne idle_pending
    jmp send
idle_pending:
    jsr in_time
    bcc wait_idle
    jmp abort
send:
    lda #4
    sta uci_detail
    ldy #0
send_byte:
    lda (command_ptr),y
    sta UCI_COMMAND
    iny
    cpy command_length
    bne send_byte
    lda #1
    sta UCI_CONTROL
wait_reply:
    lda UCI_CONTROL
    sta last_status
    sta uci_observed
    and #$08
    beq :+
    jmp abort
:
    lda last_status
    and #$30
    cmp #$20
    bcs consider
    lda #0
    sta more_pending
    jmp reply_pending
consider:
    sta reply_state
    lda last_status
    and #$02                   ; previous acknowledgement still pending
    bne reply_pending
    lda more_pending
    beq drain
    lda reply_state
    cmp #$20
    beq drain
    lda last_status
    and #$c0                   ; same DATA_MORE state, new bytes available
    bne drain
reply_pending:
    jsr in_time
    bcc wait_reply
    jmp abort
drain:
    lda #5
    sta uci_detail
    lda UCI_CONTROL
    sta uci_observed
    asl
    bcc drain_status
    lda UCI_DATA
    ldx data_count
    cpx #32
    bcs drain_budget
    sta reply_data,x
    inc data_count
drain_budget:
    jsr in_time
    bcc drain
    bcs abort
drain_status:
    bpl accept                  ; shifted STAT_AV is bit 7
    lda UCI_STATUS
    ldx status_count
    cpx #2
    bcs drain_budget
    sta dos_status,x
    inc status_count
    jmp drain_budget
accept:
    lda #2
    sta UCI_CONTROL
    lda reply_state
    cmp #$20
    beq wait_final
    lda #1
    sta more_pending
    jmp wait_reply
wait_final:
    lda #6
    sta uci_detail
    lda UCI_CONTROL
    sta uci_observed
    beq validate
    jsr in_time
    bcc wait_final
    bcs abort
validate:
    lda #7
    sta uci_detail
    lda status_count
    cmp #2
    bne status_error
    lda dos_status
    cmp #'0'
    bne status_error
    lda dos_status+1
    cmp #'0'
    bne status_error
    lda #0
    sta uci_detail
    clc
    rts
status_error:
    sec
    rts
abort:
    lda #$0c                    ; abort + clear state error
    sta UCI_CONTROL
    sec
    rts

in_time:
    jsr clock_read
    bcs :+
    jsr clock_delta
    lda clock_elapsed+3
    cmp #2                      ; about 33 seconds at PAL or NTSC
:
    rts

open_cmd:
    .byte $02,$02,$01, MODEL_PATH
open_end:
.assert open_end-open_cmd < 256, error, "UCI command exceeds byte count"
info_cmd:
    .byte $02,$07
load_cmd:
    .byte $02,$21
    .dword 0,MODEL_SIZE
close_cmd:
    .byte $02,$03
model_size:
    .dword MODEL_SIZE
.if DUAL_MODEL
    .dword SECOND_MODEL_SIZE
.if THIRD_MODEL
    .dword THIRD_MODEL_SIZE
.endif
second_open_cmd:
    .byte $02,$02,$01, SECOND_MODEL_PATH
second_open_end:
.assert second_open_end-second_open_cmd < 256, error, "UCI command exceeds byte count"
second_load_cmd:
    .byte $02,$21
    .dword $100000,SECOND_MODEL_SIZE
.if THIRD_MODEL
third_open_cmd:
    .byte $02,$02,$01, THIRD_MODEL_PATH
third_open_end:
.assert third_open_end-third_open_cmd < 256, error, "UCI command exceeds byte count"
third_load_cmd:
    .byte $02,$21
    .dword $200000,THIRD_MODEL_SIZE
.endif
open_command_low:
    .byte <open_cmd, <second_open_cmd
.if THIRD_MODEL
    .byte <third_open_cmd
.endif
open_command_high:
    .byte >open_cmd, >second_open_cmd
.if THIRD_MODEL
    .byte >third_open_cmd
.endif
open_command_length:
    .byte open_end-open_cmd, second_open_end-second_open_cmd
.if THIRD_MODEL
    .byte third_open_end-third_open_cmd
.endif
load_command_low:
    .byte <load_cmd, <second_load_cmd
.if THIRD_MODEL
    .byte <third_load_cmd
.endif
load_command_high:
    .byte >load_cmd, >second_load_cmd
.if THIRD_MODEL
    .byte >third_load_cmd
.endif
.endif
