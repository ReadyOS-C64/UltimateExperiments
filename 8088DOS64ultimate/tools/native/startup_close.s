.setcpu "6502"
.macpack longbranch
.import dos64_files_start,dos64_files_poll
.import dos64_files_state,dos64_files_error,dos64_files_transport_error
.import dos64_files_handle,dos64_files_target,dos64_files_owned_target
.import dos64_files_op,dos64_files_now
.import dos64_uci_state,dos64_uci_error,dos64_uci_recovery_failed
.export _sc_now,_sc_state,_sc_error,_sc_transport,_sc_target,_sc_closed,_sc_cleanup
.export _sc_begin,_sc_poll,_sc_cancel,_sc_ready
.segment "BSS"
_sc_now: .res 2
sc_private:
state: .res 1
error: .res 1
transport: .res 1
target: .res 1
closed: .res 1
cleanup: .res 1
sc_observed:
_sc_state: .res 1
_sc_error: .res 1
_sc_transport: .res 1
_sc_target: .res 1
_sc_closed: .res 1
_sc_cleanup: .res 1
.segment "CODE"
quiet:
 lda dos64_uci_state
 beq @yes
 cmp #9
 beq @yes
 cmp #10
 bne @no
 lda dos64_uci_recovery_failed
 bne @no
 lda dos64_uci_error
 cmp #3
 bcc @no
@yes: clc
 rts
@no: sec
 rts
publish:
 ldx #5
@copy:
 lda sc_private,x
 sta sc_observed,x
 dex
 bpl @copy
 rts
clock:
 lda _sc_now
 sta dos64_files_now
 lda _sc_now+1
 sta dos64_files_now+1
 rts
leaf_error:
 lda error
 beq @first
 cmp #1
 bne @return
 lda cleanup
 bne @return
 lda dos64_files_error
 bne @clean
 lda #2
@clean: sta cleanup
@return: rts
@first:
 lda dos64_files_error
 bne @save_file
 lda #2
 sta error
 lda dos64_uci_error
 jmp @save_transport
@save_file:
 sta error
 lda dos64_files_transport_error
@save_transport:
 sta transport
 rts
start:
 lda target
 sta dos64_files_target
 sta dos64_files_owned_target
 lda #2
 sta dos64_files_handle
 lda #3
 sta dos64_files_op
 jsr clock
 jsr dos64_files_start
 bcc @return
 jsr leaf_error
 lda #3
 sta state
@return: rts
_sc_begin:
 cmp #$a5
 bne rejected
 lda state
 ora dos64_files_handle
 bne rejected
 lda dos64_files_state
 cmp #1
 beq rejected
 jsr quiet
 bcs rejected
 lda #1
 sta state
 sta target
 jsr start
 jsr publish
 lda #1
 ldx #0
 rts
rejected:
 jsr publish
false:
 lda #0
 ldx #0
 rts
_sc_poll:
 lda state
 cmp #1
 jne return_state
 jsr clock
 jsr dos64_files_poll
 lda dos64_uci_state
 cmp #8
 bne @terminal
 jsr leaf_error
@terminal:
 lda dos64_files_state
 cmp #1
 beq return_state
 lda dos64_files_handle
 bne @failed
 jsr quiet
 bcs @failed
 lda dos64_files_state
 cmp #2
 beq @closed
 cmp #3
 bne @failed
 lda dos64_files_error
 cmp #3
 bne @failed
 lda dos64_files_transport_error
 bne @failed
 lda dos64_uci_state
 cmp #9
 bne @failed
@closed:
 lda closed
 ora target
 sta closed
 lda target
 cmp #1
 bne @finish
 inc target
 jsr start
 jmp return_state
@finish:
 lda error
 beq @success
 lda #3
 bne @set
@success: lda #2
@set: sta state
 jmp return_state
@failed:
 jsr leaf_error
 lda #3
 sta state
return_state:
 jsr publish
 lda state
 ldx #0
 rts
_sc_cancel:
 lda state
 cmp #1
 beq @mark
 cmp #2
 bne @return
 lda #3
 sta state
@mark:
 lda error
 bne @return
 lda #1
 sta error
@return: jmp publish
_sc_ready:
 lda state
 cmp #2
 bne @no
 lda error
 ora dos64_files_handle
 bne @no
 lda closed
 cmp #3
 bne @no
 jsr quiet
 bcs @no
 lda #1
 ldx #0
 rts
@no:
 lda #0
 ldx #0
 rts
