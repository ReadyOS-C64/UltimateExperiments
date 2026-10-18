.include "abi.inc"
.include "host_clock.inc"
.import dos64_host_clock_init, dos64_host_clock_read
.import dos64_host_clock_claim, dos64_host_clock_status, dos64_host_clock_ticks
.import dos64_mailbox
.export dos64_host_clock_probe, dos64_host_clock_probe_record

; Destructive calibration fixture, caller owns CIA2 timer/NMI policy and has
; I/O visible with KERNAL out. No elapsed result is derived from CPU clocks.
; DCK1 record at $6000, 40 bytes: magic[4],version,status,error,profile,
; frames[2],target[2],max_raster[2],start[4],end[4],delta[4],retries[2],
; last_clock_error,phase,reserved[2],start_raster[2],end_raster[2],reserved[4].
; Record size 40. All words little-endian, delta modulo 2^32.
; Profile 1 is a 312-line candidate, observed at physical raster 311.
; Independent CIA delta verification distinguishes PAL 63 from PAL-N 65.
dos64_host_clock_probe_record = $6000
R = $6000
.segment "DEVICESTATE"
polls: .res 2
raster: .res 2
phase_high: .res 1
clock_attempts: .res 1
clock_ok: .res 1
.segment "CODE"
dos64_host_clock_probe:
    lda #0
    ldx #39
@clear:
    sta R,x
    dex
    bpl @clear
    lda #'D'
    sta R
    lda #'C'
    sta R+1
    lda #'K'
    sta R+2
    lda #'1'
    sta R+3
    lda #1
    sta R+4
    sta R+5
    lda #100
    sta R+10
    lda #3
    sta $dd0d                 ; only disable timer A/B NMI masks; never read ICR
    lda #HC_OWNED
    sta dos64_host_clock_claim
    jsr dos64_host_clock_init
    bcc @align
    lda #1
    jmp failed
@align:
    inc R+29
    jsr frame_boundary
    bcc @start
    jmp raster_failed
@start:
    inc R+29
    jsr clock_read
    bcc @copy_start
    jmp clock_failed
@copy_start:
    lda raster
    sta R+32
    lda #0
    sta R+33
    ldx #3
@copy:
    lda dos64_host_clock_ticks,x
    sta R+14,x
    dex
    bpl @copy
    inc R+29
@frame:
    jsr frame_boundary
    bcs raster_failed
    inc R+8
    lda R+8
    cmp #100
    bne @frame
    inc R+29
    jsr clock_read
    bcs clock_failed
    lda raster
    sta R+34
    lda #0
    sta R+35
    ldx #3
@end:
    lda dos64_host_clock_ticks,x
    sta R+18,x
    dex
    bpl @end
    sec
    lda R+18
    sbc R+14
    sta R+22
    lda R+19
    sbc R+15
    sta R+23
    lda R+20
    sbc R+16
    sta R+24
    lda R+21
    sbc R+17
    sta R+25
    lda R+13
    cmp #1
    bne profile_failed
    lda R+12
    cmp #55                  ; physical max raster $137 = 311
    bne profile_failed
    lda #1
    sta R+7
    lda #5
    sta R+29
    lda #STATUS_PASS         ; numerical delta acceptance belongs to verifier
    sta R+5
    sta dos64_mailbox+MB_STATUS
    lda #0
    sta dos64_mailbox+MB_ERROR
    lda #5
    sta $d020
    clc
    rts
raster_failed:
    lda #2
    bne failed
clock_failed:
    lda #3
    bne failed
profile_failed:
    lda #4
failed:
    sta R+6
    sta dos64_mailbox+MB_ERROR
    lda #STATUS_FAIL
    sta R+5
    sta dos64_mailbox+MB_STATUS
    lda #2
    sta $d020
    sec
    rts

; 128 complete bounded reads, plus raster-progress check after EVERY attempt.
; A successful or failed read beyond line 15 fails, limiting endpoint latency
; to less than 16 PAL lines (1008 raw CIA ticks). Never infer elapsed from CPU.
clock_read:
    lda #128
    sta clock_attempts
@try:
    lda #0
    sta clock_ok
    jsr dos64_host_clock_read
    bcs @bad
    inc clock_ok
    bne @check_raster
@bad:
    lda dos64_host_clock_status
    sta R+28
    inc R+26
    bne @check_raster
    inc R+27
@check_raster:
    jsr raster_read
    bcs @late
    lda raster+1
    bne @late
    lda raster
    cmp #16
    bcs @late
    lda clock_ok
    bne @ok
    dec clock_attempts
    bne @try
    sec
    rts
@late:
    lda #$fe
    sta R+28
    sec
    rts
@ok:
    clc
    rts

; Two bounded phases: observe raster bit8 high, then low. Each gets 65535
; stable/unstable sample attempts; frozen VIC and torn reads terminate.
frame_boundary:
    lda #$80
    sta phase_high
@phase:
    lda #$ff
    sta polls
    sta polls+1
@poll:
    jsr raster_read
    bcs @next
    lda raster+1
    cmp phase_high
    beq @matched
@next:
    lda polls
    bne @low
    dec polls+1
@low:
    dec polls
    lda polls
    ora polls+1
    bne @poll
    sec
    rts
@matched:
    lda phase_high
    beq @done
    lda #0
    sta phase_high
    beq @phase
@done:
    clc
    rts

; Stable bit8/low/bit8 sample; raster+1 holds $00 or $80. A torn edge
; consumes an attempt. Maximum is recorded as an ordinary 9-bit word.
raster_read:
    lda $d011
    and #$80
    sta raster+1
    lda $d012
    sta raster
    lda $d011
    and #$80
    cmp raster+1
    bne @torn
    asl a
    lda #0
    rol a
    cmp R+13
    bcc @ok
    bne @maximum
    lda raster
    cmp R+12
    bcc @ok
    beq @ok
    lda R+13
@maximum:
    sta R+13
    lda raster
    sta R+12
@ok:
    clc
    rts
@torn:
    sec
    rts
