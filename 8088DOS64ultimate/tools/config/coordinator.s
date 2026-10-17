.setcpu "6502"
.ifndef DOS64_ALL_FILE_DIAGNOSTICS
DOS64_ALL_FILE_DIAGNOSTICS=0
.endif
.if DOS64_ALL_FILE_DIAGNOSTICS
.import fd_show,_fd_closed,_fd_code
.importzp _fd_origin
.endif
.import _cg_poll,_cg_state,_cg_error,_cg_get,_cg_receipt,_cg_closed_quiet
.import _rm_begin,_rm_poll,_rm_state,_rm_error,_rm_request,_rm_closed_quiet
.import _cp_begin,_cp_poll,_cp_state,_cp_error,_cp_request,_cp_closed_quiet
.import _ps_clear
.importzp ptr1
.export _co_poll,_co_state,_co_error,_co_closed_quiet,co_poll_return
.segment "BSS"
co_state:.res 1 ;0CG,1RM,2CP,3DONE,4FAILED
co_error:.res 1 ;privatefirst cause, qualified by originating stage
co_stage:.res 1
.segment "CODE"
_co_poll:
 lda co_state
 beq selection
 cmp #1
 beq media
 cmp #2
 beq publication
 rts
selection:
 jsr _cg_poll
 jsr _cg_state
 cmp #7
 beq cg_failed
 cmp #6
 beq :+
 rts
:
 jsr _cg_get
 cmp #0
 beq owner_failed
 ; Capture the fresh private getter immediately, no intervening callback.
 ldx #127
@home:
 lda _cg_receipt+10,x
 sta _rm_request+5,x
 dex
 bpl @home
 lda _cg_receipt
 sta _rm_request+3
 lda _cg_receipt+1
 sta _rm_request+4
 lda #$a5
 sta _rm_request
 lda #$d0 ;2000ticks, same bounded native component policy
 sta _rm_request+1
 lda #$07
 sta _rm_request+2
 jsr _rm_begin
 cmp #0
 beq owner_failed
 lda #1
 bne transition
cg_failed:
 jsr _cg_error
 jmp failed
media:
 jsr _rm_poll
 jsr _rm_state
 cmp #3
 beq rm_failed
 cmp #2
 beq :+
 rts
:
 ; cp_begin independently refreshes CG and RM; no public media facts injected.
 lda #$a5
 sta _cp_request
 lda #$a0 ;4000ticks
 sta _cp_request+1
 lda #$0f
 sta _cp_request+2
 jsr _cp_begin
 cmp #0
 beq owner_failed
 lda #2
 bne transition
rm_failed:
 jsr _rm_error
 jmp failed
publication:
 jsr _cp_poll
 jsr _cp_state
 cmp #3
 beq cp_failed
 cmp #2
 beq :+
 rts
:
 lda #3
 bne transition
cp_failed:
 jsr _cp_error
 jmp failed
owner_failed:
 lda #2
failed:
 sta co_error
.if DOS64_ALL_FILE_DIAGNOSTICS=0
 lda co_state
 sta co_stage
.endif
 lda #4
transition:
 sta co_state
 jsr show
co_poll_return:
 rts
_co_state:
 lda co_state
 ldx #0
 rts
_co_error:
 lda co_error
 ldx #0
 rts
_co_closed_quiet:
 jsr _cg_closed_quiet
 cmp #0
 beq co_poll_return
 jsr _rm_closed_quiet
 cmp #0
 beq co_poll_return
 jmp _cp_closed_quiet
show:
.if DOS64_ALL_FILE_DIAGNOSTICS
 lda co_state
 cmp #4
 bne :+
 jsr _co_closed_quiet
 sta _fd_closed
 lda co_error
 sta _fd_origin
 lda _fd_code
 bne @display
 lda co_error
 sta _fd_code
@display:
 jmp fd_show
:
.endif
 jsr _ps_clear
 lda co_state
 asl
 tax
 lda messages,x
 sta ptr1
 lda messages+1,x
 sta ptr1+1
 ldy #0
@text:
 lda (ptr1),y
 beq @details
 and #$3f
 sta $04a0,y
 iny
 cpy #40
 bne @text
@details:
.if DOS64_ALL_FILE_DIAGNOSTICS
 rts
.else
 lda co_state
 cmp #4
 bne @done
 lda #5 ;E
 sta $04f0
 lda #18 ;R
 sta $04f1
 sta $04f2
 lda co_error
 lsr
 lsr
 lsr
 lsr
 jsr hex
 sta $04f4
 lda co_error
 and #15
 jsr hex
 sta $04f5
 jsr _co_closed_quiet
 cmp #0
 beq @unknown
 lda #<closed_message
 ldx #>closed_message
 bne @closure
@unknown:
 lda #<unknown_message
 ldx #>unknown_message
@closure:
 sta ptr1
 stx ptr1+1
 ldy #0
@line:
 lda (ptr1),y
 beq @done
 and #$3f
 sta $0540,y
 iny
 cpy #40
 bne @line
@done:
 rts
hex:
 cmp #10
 bcc @digit
 adc #6
@digit:
 adc #48
 and #$3f
 rts
 .endif
.segment "RODATA"
messages:.word 0,media_message,publish_message,done_message,failed_message
media_message:.asciiz "CHECKING EXISTING DISK IMAGES"
publish_message:.asciiz "WRITING NEW LAUNCH FOLDER"
done_message:.asciiz "CONFIG COMPLETE - NEW FOLDER READY"
.if DOS64_ALL_FILE_DIAGNOSTICS
failed_message=done_message
.else
failed_message:.asciiz "CONFIG FAILED - KEEP OLD INSTALL"
closed_message:.asciiz "FILES CLOSED. PARTIAL NEW FILES MAY REMAIN"
unknown_message:.asciiz "RESTART C64 - FILE OWNERSHIP UNKNOWN"

.endif
