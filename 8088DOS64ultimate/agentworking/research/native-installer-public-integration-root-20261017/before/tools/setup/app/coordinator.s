.setcpu "6502"
.macpack longbranch
.include "coordinator_internal.inc"
.importzp ptr1
.import _fw_run,_pw_run,_rc_retained
.import _bc_files_closed
.import runtime_init,_bc_init,_ps_init,_sl_install
.import _sc_begin,_sc_poll,_sc_cancel,_sc_ready,_sc_now,_sc_error
.import _ps_clock_poll,_ps_key_poll,_ps_key,_ps_ticks
.import _so_request,_so_prepare,_so_phase_request,_so_enter,_so_ui_ticket
.import _so_ticket,_so_leave,_so_bind_home,_so_begin,_so_poll,_so_cancel,_so_state,_so_now,_so_result
.import _su_timeout,_su_begin,_su_poll,_su_state,_su_error
.import _rc_capture,_rc_expected_ticket,_rc_source_ready
.export setup_boot,setup_loop,setup_boot_failed,_rc_begin,_rc_poll,_rc_state,_rc_error
.segment "BSS"
state: .res 1
error: .res 1
cancelled: .res 1
drain: .res 1
clock_ok: .res 1
ticket: .res 2
last_tick: .res 2
failure_shown: .res 1
failure_closed: .res 1
phase_verified: .res 1
.segment "BOOT"
setup_boot:
 sei
 cld
 ldx #$ff
 txs
 jsr runtime_init
 jsr _bc_init
 jsr _ps_init
 jsr _sl_install
 cmp #1
 jne setup_boot_failed
 jsr _rc_begin
setup_loop:
 jsr _rc_poll
 jmp setup_loop
setup_boot_failed:
 inc $d020
 jmp setup_boot_failed
.assert setup_boot=$080d,lderror,"BASIC SYS must enter real bootstrap"
.segment "HIGH_CODE"
_rc_state:
 lda state
 ldx #0
 rts
_rc_error:
 lda error
 ldx #0
 rts
; First cause persists; a failed coordinator never grants another phase.
fail:
 ldx error
 bne :+
 sta error
:
 ; Capture truthful closure while still in the failing operation. Terminal
 ; presentation never polls or switches FILES/UCI. Software-zero handles before
 ; successful startup CLOSE1/2 cannot certify firmware ownership.
 jsr _sc_ready
 tax
 beq :+
 jsr _bc_files_closed
:
 sta failure_closed
 lda #5
 sta state
 rts
_rc_begin:
 lda state
 bne @refuse
 lda #$a5
 jsr _sc_begin
 cmp #1
 bne @refuse
 lda #1
 sta state
 rts
@refuse:
 lda #0
 tax
 rts
; Fresh time before advancing a pending leaf. Missing/half-wrap time latches a
; coordinator error, then the same engine is cancelled/drained for <=256 polls.
sample:
 jsr _ps_clock_poll
 sta clock_ok
 beq @bad
 lda _ps_ticks
 sec
 sbc last_tick
 lda _ps_ticks+1
 sbc last_tick+1
 bmi @bad
 lda _ps_ticks
 sta last_tick
 sta _sc_now
 sta _so_now
 lda _ps_ticks+1
 sta last_tick+1
 sta _sc_now+1
 sta _so_now+1
 rts
@bad:
 lda #0
 sta clock_ok
 rts
clock_after:
 lda clock_ok
 bne :+
 lda #$e1
 jmp first
:
 rts
first:
 ldx error
 bne :+
 sta error
:
 rts
input:
 jsr _ps_key_poll
 beq @done
 lda _ps_key
 cmp #27
 bne @done
 lda #$e2
 jsr first
@done:
 rts
_rc_poll:
 lda state
 cmp #2
 jeq ui
 cmp #1
 jeq close_poll
 cmp #3
 jeq overlay_poll
 cmp #4
 jeq fat_run
 cmp #6
 jeq publish_run
 cmp #5
 bne @idle
 lda phase_verified
 jne rc_failure_screen
@idle:
 rts
close_poll:
 jsr sample
 jsr _sc_poll
 pha
 lda _sc_error
 beq :+
 lda #$e3
 jsr first
:
 jsr clock_after
 pla
 cmp #1
 jeq close_busy
 cmp #2
 jne close_failed
 lda error
 jne stop
 jsr _sc_ready
 cmp #1
 jne close_failed
 lda #$a5
 sta _so_request
 lda #0
 sta _so_request+1
 sta _so_request+2
 sta _so_request+4
 lda #$40
 sta _so_request+3
 lda #<$2710
 sta _so_request+5
 lda #>$2710
 sta _so_request+6
 jsr _so_prepare
 tax ; trusted boolean API returns A=0/1; C epilogues need not set NZ.
 jeq phase_failed
 inc phase_verified
 lda #1
 sta _so_phase_request
 jsr _so_enter
 tax ; trusted boolean API returns A=0/1; C epilogues need not set NZ.
 jeq phase_failed
 jsr _so_ui_ticket
 sta ticket
 sta _rc_expected_ticket
 stx ticket+1
 stx _rc_expected_ticket+1
 lda #<$2710
 sta _su_timeout
 lda #>$2710
 sta _su_timeout+1
 jsr _su_begin
 tax ; trusted boolean API returns A=0/1; C epilogues need not set NZ.
 jeq phase_failed
 lda #2
 sta state
 rts
close_busy:
 jsr input
 lda error
 jeq done
 lda cancelled
 jne drain_poll
 inc cancelled
 jsr _sc_cancel
 jmp drain_poll
close_failed:
 lda #$e3
 jmp fail
phase_failed:
 lda #$e4
 jmp fail
stop=fail
ui:
 jsr _su_poll
 jsr _su_state
 cmp #1
 jeq done
 cmp #2
 jne ui_failed
 jsr _rc_capture
 tax ; trusted boolean API returns A=0/1; C epilogues need not set NZ.
 jeq phase_failed
 jsr retire
 tax ; trusted boolean API returns A=0/1; C epilogues need not set NZ.
 jeq phase_failed
 jsr _so_bind_home
 tax ; trusted boolean API returns A=0/1; C epilogues need not set NZ.
 jeq phase_failed
 lda #2
replace:
 sta _so_phase_request
 jsr _ps_clock_poll
 jeq clock_failed
 lda _ps_ticks
 sta last_tick
 sta _so_now
 lda _ps_ticks+1
 sta last_tick+1
 sta _so_now+1
 jsr _so_begin
 tax ; trusted boolean API returns A=0/1; C epilogues need not set NZ.
 jeq phase_failed
 lda #3
 sta state
 rts
ui_failed:
 jsr _su_error
 jmp fail
clock_failed:
 lda #$e1
 jmp fail
overlay_poll:
 jsr sample
 jsr _so_poll
 jsr _so_state
 pha
 lda _so_result+2
 beq :+
 lda #$e4
 jsr first
:
 jsr clock_after
 pla
 cmp #1
 jeq overlay_busy
 cmp #2
 jne phase_failed
 lda error
 jne stop
 jsr _so_enter
 tax ; trusted boolean API returns A=0/1; C epilogues need not set NZ.
 jeq phase_failed
 lda _so_result+8
 sta ticket
 lda _so_result+9
 sta ticket+1
 ; Root alone replaces phases, after all overlaid frames have returned.
 ; Each worker admits against its authentic phase and internal retained facts.
 lda _so_phase_request
 cmp #3
 beq @pub
 lda #4
 bne @active
@pub:
 lda #6
@active:
 sta state
 rts
overlay_busy:
 jsr input
 lda error
 jeq done
 lda cancelled
 jne drain_poll
 inc cancelled
 jsr _so_cancel
drain_poll:
 inc drain
 jne done
 lda error
 jmp fail
done:
 rts

; Return values are private worker decisions, never observation bytes. A failure
; leaves the active phase reserved; it cannot authorize replacement or success.
fat_run:
 jsr _fw_run
 tax ; trusted boolean API returns A=0/1; C epilogues need not set NZ.
 jeq phase_failed
 jsr retire
 tax ; trusted boolean API returns A=0/1; C epilogues need not set NZ.
 jeq phase_failed
 lda #3
 jmp replace
publish_run:
 jsr _pw_run
 tax ; trusted boolean API returns A=0/1; C epilogues need not set NZ.
 jeq phase_failed
 lda _rc_retained+RC_OUTPUT_MASK
 cmp #31
 jne phase_failed
 jsr retire
 tax ; trusted boolean API returns A=0/1; C epilogues need not set NZ.
 jeq phase_failed
 lda #7
 sta state
 rts
retire:
 lda ticket
 sta _so_ticket
 lda ticket+1
 sta _so_ticket+1
 jmp _so_leave

.segment "AUX_CODE"
; Permanent copied code, independent of UI/FAT/PUB residency. All text is
; bounded at assembly time. The display is informational, never job authority.
rc_failure_screen:
 lda failure_shown
 bne @done
 inc failure_shown
 ldx #159
@clear:
 lda #32
 sta $0748,x
 lda #1
 sta $db48,x
 dex
 cpx #$ff
 bne @clear
 lda #<rc_failed_common
 sta ptr1
 lda #>rc_failed_common
 sta ptr1+1
 ldy #0
 ldx #0
 jsr rc_draw_line
 ldx #40
 iny
 jsr rc_draw_line
 lda error
 pha
 lsr
 lsr
 lsr
 lsr
 jsr rc_hex_glyph
 sta $0748+(rc_error_digits-rc_failed_common)
 pla
 and #15
 jsr rc_hex_glyph
 sta $0749+(rc_error_digits-rc_failed_common)
 lda failure_closed
 beq @unknown
 lda #<rc_failed_closed
 ldx #>rc_failed_closed
 bne @message
@unknown:
 lda #<rc_failed_unknown
 ldx #>rc_failed_unknown
@message:
 sta ptr1
 stx ptr1+1
 ldy #0
 ldx #80
 jsr rc_draw_line
 ldx #120
 iny
 jmp rc_draw_line
@done:
 rts
rc_draw_line:
 lda (ptr1),y
 beq @done
 and #$3f ; fixed uppercase ASCII/punctuation -> platform text glyphs
 sta $0748,x
 inx
 iny
 bne rc_draw_line
@done:
 rts
rc_hex_glyph:
 cmp #10
 bcc :+
 adc #6 ; carry from CMP makes A..F after the following ASCII addition
:
 adc #48
 and #$3f
 rts
.segment "AUX_RO"
rc_failed_common:
 .byte "SETUP STOPPED - ERROR "
rc_error_digits:
 .byte "00",0
rc_common_second:
 .byte "NEW FILES MAY REMAIN IN THE HOME FOLDER.",0
rc_failed_closed:
 .byte "FILES CLOSED.",0
rc_closed_second:
 .byte "RELOAD SETUP; CHOOSE A NEW FOLDER.",0
rc_failed_unknown:
 .byte "FILE CLEANUP NOT CONFIRMED.",0
rc_unknown_second:
 .byte "KEEP THIS SCREEN. DO NOT RETRY.",0
rc_failed_text_end:
.assert rc_common_second-rc_failed_common<=41,error,"failure row21 bounds"
.assert rc_failed_closed-rc_common_second<=41,error,"failure row22 bounds"
.assert rc_closed_second-rc_failed_closed<=41,error,"failure row23 closed bounds"
.assert rc_failed_unknown-rc_closed_second<=41,error,"failure row24 closed bounds"
.assert rc_unknown_second-rc_failed_unknown<=41,error,"failure row23 unknown bounds"
.assert rc_failed_text_end-rc_unknown_second<=41,error,"failure row24 unknown bounds"
