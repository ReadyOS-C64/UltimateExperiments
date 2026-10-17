.setcpu "6502"
.macpack longbranch
.include "symbols.inc"
.include "products.inc"
.export bridge_entry,bridge_init,bridge_dispatch,bridge_load_controller,bridge_load_ui
.export br_intent,br_last,br_error,br_resume,br_success
.import __BSS_RUN__,__BSS_SIZE__
.segment "LOADADDR"
.word $6000
.segment "BSS"
br_busy:.res 1
br_intent:.res 133
br_last:.res 9
br_error:.res 1
br_resume:.res 1
br_success:.res 1
br_safe:.res 1
.segment "CODE"
bridge_entry: jmp bridge_dispatch
bridge_init:
 lda #0
 ldx #0
: sta __BSS_RUN__,x
 inx
 cpx #<__BSS_SIZE__
 bne :-
 rts
.assert __BSS_SIZE__ < 256,lderror,"bridge private state exceeds256"
bridge_dispatch:
 php
 sei
 cld
 lda br_busy
 jne reject
 lda modal_owned
 cmp #$a5
 jne reject
 lda modal_context
 cmp #1
 jne reject
 lda dos64_native_diag
 cmp #8
 jne reject
 lda dos64_cache_limit
 jne reject
 lda #1
 sta br_busy
 lda #0
 sta br_error
 sta br_resume
 sta br_success
 sta br_safe
 ldx #8
: sta br_last,x
 dex
 bpl :-
 jsr modal_ui_on
 jcs unavailable
 jsr _mu_capture
 pha
 jsr modal_ui_off
 bcc :+
 pla
 jmp unavailable
: pla
 cmp #1
 jne unavailable
 lda br_intent
 ora br_intent+1
 jeq unavailable
 lda br_intent+3
 cmp #2
 jcs unavailable
 lda br_intent+2
 cmp #7
 jeq finish_intent
 lda br_intent+4
 jne unavailable
 lda br_intent+2
 cmp #6
 jeq resume_intent
 cmp #2
 jne unsupported_intent
 ; No frontend frame remains live. Its code may now be replaced; its BSS,
 ; saved high96 and private WAIT ticket remain owned and unchanged.
 lda #0
 sta ui_ready
bridge_load_controller:
 ldx #0
 jsr copy_asset
 jcs bad_asset
 ldx #3
: lda controller_crc,x
 sta verify_expected,x
 dex
 bpl :-
 jsr modal_verify
 jcs bad_asset
 lda #$a5
 sta _ac_request
 lda #0
 sta _ac_request+1
 sta _ac_request+4
 sta _ac_request+5
 sta _ac_request+7
 lda #$40
 sta _ac_request+6
 ; CUI ticket belongs only to the private WAIT/reply protocol. Start readonly
 ; archive search at1; WIRE returns the private transaction sequence separately.
 lda #1
 sta _ac_request+2
 lda #0
 sta _ac_request+3
 lda br_intent+3
 sta _ac_request+8
 lda #2
 sta _ac_request+9
 ldx #127
: lda br_intent+5,x
 sta _ac_request+10,x
 dex
 bpl :-
 jsr ac_entry
 cmp #1
 bne :+
 lda #1
 sta br_success
: ldx #8
: lda _ac_result,x
 sta br_last,x
 dex
 bpl :-
 lda br_last+1
 sta br_error
 lda br_success
 beq @failed
 lda br_last
 cmp #2
 bne @invalid
 lda br_error
 bne @invalid
 lda br_last+4
 and br_last+5
 cmp #1
 bne @invalid
 lda dos64_native_diag
 cmp #8
 bne @invalid
 lda #1
 sta br_resume
 bne reload
@failed:
 lda br_error
 bne :+
 lda #$fd
 sta br_error
: lda br_last+5
 beq @blocked
 jsr modal_poll
 bcs @blocked
 lda #1
 sta br_resume
 bne reload
@invalid:
 lda #$fd
 sta br_error
@blocked:
 lda #0
 sta br_success
 lda #$e1
 sta dos64_native_diag
reload:
bridge_load_ui:
 ldx #8
 jsr copy_asset
 jcs bad_asset
 ldx #3
: lda ui_crc,x
 sta verify_expected,x
 dex
 bpl :-
 jsr modal_verify
 jcs bad_asset
 lda #1
 sta ui_ready
 jsr modal_view_refresh
 jcs bad_asset
 lda br_resume
 sta _mu_view+258
 lda br_success
 bne bridge_present
 lda br_last+6
 beq bridge_present
 ldx #0
 lda br_intent+3
 beq :+
 ldx #129
: lda _mu_view,x
 ora #8
 sta _mu_view,x
bridge_present:
 jsr modal_ui_on
 jcs bad_asset
 jsr _mu_refresh
 lda br_resume
 ora br_safe
 bne @reply
 lda br_error
 sta _mu_block_error
 jsr _mu_block
 jmp @return
@reply:
 lda br_intent
 sta _mu_reply_ticket
 lda br_intent+1
 sta _mu_reply_ticket+1
 lda br_error
 sta _mu_reply_error
 lda br_safe
 sta _mu_reply_safe
 jsr _mu_reply
 cmp #1
 bne @reply_bad
@return:
 jsr modal_ui_off
 jcs bad_asset
 lda #0
 sta br_busy
 lda br_safe
 beq :+
 lda #7
: plp
 clc
 rts
@reply_bad:
 jsr modal_ui_off
 jmp bad_asset
resume_intent:
 lda #0
 sta br_busy
 plp
 clc
 lda #6
 rts
unsupported_intent:
 lda #254
 sta br_error
 lda #1
 sta br_resume
 jsr modal_view_refresh
 jcs bad_asset
 jmp bridge_present
; The UI has returned completely. Finish lives atA000 and retains the UI
; at8000; no C frames or controller overlays survive this exchange.
finish_intent:
 lda br_intent+4
 and #$fc
 jne unavailable
 ldx #16
 jsr copy_asset
 jcs bad_asset
 ldx #3
: lda finish_crc,x
 sta verify_expected,x
 dex
 bpl :-
 jsr modal_verify
 jcs bad_asset
 lda #0
 ldx #(fn_private_end-fn_enable-1)
: sta fn_enable,x
 dex
 bpl :-
 lda #$a5
 sta fn_enable
 lda br_intent+4
 sta fn_discard
 lda #<30000
 sta fn_limit
 lda #>30000
 sta fn_limit+1
 jsr fn_begin
 cmp #1
 bne finish_refused
finish_wait:
 jsr fn_poll
 jsr fn_state
 cmp #1
 beq finish_wait
 jsr fn_take_restart
 cmp #1
 bne finish_refused
 lda #1
 sta br_safe
 jmp finish_present
finish_refused:
 jsr fn_error
 cmp #0
 bne :+
 lda #$fc
: sta br_error
finish_present:
 ; C is closed or its ownership is uncertain. Resume remains permanently
 ; fenced. Verify retained frontend bytes before any frontend call.
 lda #$e1
 sta dos64_native_diag
 ldx #8
 jsr copy_request
 ldx #3
: lda ui_crc,x
 sta verify_expected,x
 dex
 bpl :-
 jsr modal_verify
 jcs bad_asset
 jsr modal_view_refresh
 jcs bad_asset
 lda #0
 sta _mu_view+258
 jmp bridge_present
unavailable:
 lda #0
 sta br_busy
 lda #$e1
 sta dos64_native_diag
 plp
 sec
 rts
bad_asset:
 lda #0
 sta br_safe
 sta br_resume
 lda #$e2
 sta modal_error
 lda #0
 sta ui_ready
 sta br_busy
 lda #$e1
 sta dos64_native_diag
 plp
 sec
 rts
reject:
 plp
 sec
 rts
copy_asset:
 jsr copy_request
 jmp dos64_reu_transfer
copy_request:
 ldy #7
: lda requests,x
 sta dos64_reu_request,y
 inx
 dey
 bpl :-
 rts
.segment "RODATA"
requests:
 .byte 1,>CONTROLLER_BYTES,<CONTROLLER_BYTES,$3f,$00,$00,$80,$00
 .byte 1,>UI_BYTES,<UI_BYTES,$3d,$aa,$00,$80,$00
 .byte 1,>FINISH_BYTES,<FINISH_BYTES,$3f,$38,$00,$a0,$00
finish_crc:.dword FINISH_CRC
controller_crc:.dword CONTROLLER_CRC
ui_crc:.dword UI_CRC
