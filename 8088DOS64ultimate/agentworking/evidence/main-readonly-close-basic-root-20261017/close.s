.setcpu "6502"
.include "old.inc"
.export close_entry,close_halt,close_result
.segment "CODE"
close_entry:
 sei
 cld
 ldx #$ff
 txs
 jsr _ps_init
 jsr dos64_uci_init
 jsr dos64_files_init
 lda #0
 ldx #15
clear:
 sta close_result,x
 dex
 bpl clear
 lda #$43
 sta close_result
 lda #$4c
 sta close_result+1
 lda #$32
 sta close_result+2
 lda #1
 sta close_result+3
 lda #<30000
 sta dos64_uci_timeout
 lda #>30000
 sta dos64_uci_timeout+1
 lda #<500
 sta dos64_uci_recovery_timeout
 lda #>500
 sta dos64_uci_recovery_timeout+1
 lda #2
 sta dos64_files_handle
 sta dos64_files_target
 sta dos64_files_owned_target
 lda #1
 sta dos64_files_mode
 lda #3
 sta dos64_files_op
 jsr clock
 bcs failed
 jsr dos64_files_start
 bcs failed
poll:
 jsr clock
 bcs failed
 jsr dos64_files_poll
 lda dos64_files_state
 cmp #1
 beq poll
 ; Known closure must come from completed native CLOSE and exact parser.
 lda dos64_files_handle
 bne failed
 lda dos64_uci_state
 cmp #9
 bne failed
 lda dos64_files_state
 cmp #2
 beq ok_error
 cmp #3
 bne failed
 lda dos64_files_error
 cmp #3
 bne failed
 lda dos64_files_transport_error
 bne failed
 beq done
ok_error:
 lda dos64_files_error
 ora dos64_files_transport_error
 bne failed
done:
 lda #$a5
 bne publish
failed:
 lda #$e1
publish:
 sta close_result+3
 lda dos64_files_state
 sta close_result+4
 lda dos64_files_error
 sta close_result+5
 lda dos64_files_transport_error
 sta close_result+6
 lda dos64_files_handle
 sta close_result+7
 lda dos64_uci_state
 sta close_result+8
 lda dos64_uci_error
 sta close_result+9
 lda dos64_uci_recovery_failed
 sta close_result+10
close_halt:
 jmp close_halt
clock:
 jsr _ps_clock_poll
 cmp #1
 bne no_clock
 lda _ps_ticks
 sta dos64_files_now
 lda _ps_ticks+1
 sta dos64_files_now+1
 clc
 rts
no_clock:
 sec
 rts
.segment "STATE"
close_result: .res 16
