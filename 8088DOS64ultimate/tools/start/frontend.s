.setcpu "6502"
.macpack longbranch
.import _ps_init,_ps_put,_ps_key_poll,_ps_clock_poll
.import _ps_row,_ps_col,_ps_ascii,_ps_key,_ps_ticks
.import _lc_init,_lc_validate_start,_lc_begin,_lc_poll,_lc_cancel
.ifdef D64_START_OPTIONS
.if D64_START_OPTIONS
.import _lc_clock_fail
.endif
.endif
.import _lc_prepare_handoff,_lc_result,_lc_control,_lc_now,_sf_handoff
.import _sc_begin,_sc_poll,_sc_cancel,_sc_ready,_sc_now
.export _sf_main,_sf_status,_sf_error,sf_sample,sf_drain
.segment "ZEROPAGE"
sf_text: .res 2
.segment "BSS"
_sf_status: .res 1
_sf_error: .res 1
sf_shown: .res 1
sf_index: .res 1
.segment "RODATA"
title: .asciiz "DOS64 START"
setup: .asciiz "Run SETUP."
clock_error: .asciiz "Clock failed."
settings_error: .asciiz "Bad settings."
recovery_error: .asciiz "Recovery failed."
loading: .asciiz "Loading DOS..."
stop_hint: .asciiz "STOP: cancel"
phase: .asciiz "Phase "
cancelled: .asciiz "Canceled."
load_error: .asciiz "Cannot load. Check folder."
handoff_error: .asciiz "Handoff failed"
starting: .asciiz "Starting DOS"
.segment "CODE"
.macro DRAW row,text
 lda #<text
 ldx #>text
 ldy #row
 jsr line
.endmacro
line:
 sta sf_text
 stx sf_text+1
 sty _ps_row
 lda #0
 sta _ps_col
 sta sf_index
@next:
 ldy sf_index
 lda (sf_text),y
 beq @done
 sta _ps_ascii
 jsr _ps_put
 inc sf_index
 inc _ps_col
 lda _ps_col
 cmp #40
 bcc @next
@done: rts
copy_ticks:
 lda _ps_ticks
 sta _lc_now
 lda _ps_ticks+1
 sta _lc_now+1
 rts
copy_sc:
 lda _lc_now
 sta _sc_now
 lda _lc_now+1
 sta _sc_now+1
 rts
cancel:
 lda _sf_status
 beq @startup
 jmp _lc_cancel
@startup: jmp _sc_cancel
sf_sample:
 jsr _ps_clock_poll
 cmp #0
 beq @bad_clock
 jsr copy_ticks
 jmp @key
@bad_clock:
 lda _sf_error
 bne :+
 lda #1
 sta _sf_error
:
.ifdef D64_START_OPTIONS
.if D64_START_OPTIONS
 lda _sf_status
 beq :+
 jsr _lc_clock_fail
 jmp @key
:
.endif
.endif
 jsr cancel
@key:
 jsr _ps_key_poll
 cmp #0
 beq @return
 lda _ps_key
 cmp #27
 bne @return
 lda _sf_error
 bne :+
 lda #2
 sta _sf_error
: jmp cancel
@return: rts
sf_drain:
 jsr _lc_cancel
@loop:
 jsr sf_sample
 jsr _lc_poll
 lda _lc_result
 cmp #1
 beq @loop
 rts
_sf_main:
 jsr _ps_init
 jsr _lc_init
 DRAW 0,title
 lda _lc_control
 cmp #$a5
 beq @configured
 DRAW 2,setup
 jmp stopped
@configured:
 jsr _ps_clock_poll
 cmp #0
 bne @clock_ok
 lda #1
 sta _sf_error
 DRAW 2,clock_error
 jmp stopped
@clock_ok:
 jsr copy_ticks
 jsr _lc_validate_start
 cmp #1
 beq sf_settings_ok
bad_settings:
 DRAW 2,settings_error
 jmp stopped
sf_settings_ok:
 ; Ultimate root is a browser location, never an owned installation folder.
 lda _lc_control+4
 beq bad_settings
 jsr copy_sc
 lda #$a5
 jsr _sc_begin
 cmp #1
 jne bad_recovery
@recover:
 jsr _sc_poll
 cmp #1
 bne @recovered
 jsr sf_sample
 jsr copy_sc
 jmp @recover
@recovered:
 jsr _sc_ready
 cmp #1
 jne bad_recovery
 lda _sc_now
 sta _lc_now
 lda _sc_now+1
 sta _lc_now+1
 jsr _lc_begin
 cmp #1
 bne bad_settings
 lda #1
 sta _sf_status
 lda #$ff
 sta sf_shown
 DRAW 2,loading
 DRAW 4,stop_hint
@load:
 jsr sf_sample
 jsr _lc_poll
 lda _lc_result+3
 cmp sf_shown
 beq @same_phase
 sta sf_shown
 DRAW 6,phase
 lda sf_shown
 clc
 adc #'0'
 sta _ps_ascii
 jsr _ps_put
@same_phase:
 lda _lc_result
 cmp #1
 beq @load
 cmp #2
 bne failed_load
 lda _lc_result+1
 ora _lc_result+2
 bne failed_load
 jsr _lc_prepare_handoff
 cmp #1
 bne bad_handoff
 lda #2
 sta _sf_status
 DRAW 8,starting
 jsr _sf_handoff
bad_handoff:
 jsr sf_drain
 DRAW 8,handoff_error
 jmp stopped
failed_load:
 jsr sf_drain
 lda _sf_error
 cmp #2
 bne @other
 DRAW 8,cancelled
 jmp stopped
@other:
 DRAW 8,load_error
 jmp stopped
bad_recovery:
 DRAW 2,recovery_error
stopped:
 lda #3
 sta _sf_status
 rts
