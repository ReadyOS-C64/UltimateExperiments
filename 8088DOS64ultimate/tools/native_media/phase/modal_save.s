.setcpu "6502"
.macpack longbranch
.include "runtime.inc"
.include "media_transaction.inc"
.export ms_begin,ms_poll,ms_state,ms_error,ms_drive,ms_path,ms_cancel
.segment "LOADADDR"
.word $ae00
.segment "BSS"
ms_drive:.res 1
ms_path:.res 128
ms_cancel:.res 1
.segment "CODE"
ms_state: lda ML_STATE
 ldx #0
 rts
ms_error: lda ML_ERROR
 ldx #0
 rts
ms_begin:
 lda ML_STATE
 cmp #1
 jeq bad
 lda dos64_native_diag
 cmp #8
 jne bad
 lda dos64_cache_limit
 ora dos64_cold_open
 ora sav_context_pending
 ora dos64_overlay_busy
 ora hdb_active
 ora hd_uncertain
 jne bad
 lda ms_drive
 cmp #2
 jcs bad
 jsr dos64_elapsed_poll
 jcs bad
 lda #0
 sta ML_VALID
 sta ML_PLAN
 sta ML_ERROR
 sta sav_error
 sta ms_cancel
 lda ms_drive
 sta sav_drive
 sta ML_DRIVE
 ldx #127
: lda ms_path,x
 sta dos64_export_path,x
 sta ML_PATH,x
 dex
 bpl :-
 ldx #0
@len: lda ML_PATH,x
 beq @end
 inx
 cpx #128
 bne @len
 jmp bad
@end:
 cpx #2
 bcc bad
 inx
 stx dos64_export_path_len
 lda #$a5
 sta dos64_export_owned
 sta dos64_export_paused
 jsr sav_capture_media
 bcs bad
 lda sav_selected_drive
 beq @a
 lda dos64_disk_b_descriptor+2
 jmp @bank
@a: lda dos64_disk_reu_base+2
@bank: sta dos64_export_bank
 jsr sav_validate_media
 bcs bad
 ldx #41
: lda sav_media_snapshot,x
 sta ML_SNAPSHOT,x
 dex
 bpl :-
 lda dos64_elapsed_now
 sta dos64_export_now
 lda dos64_elapsed_now+1
 sta dos64_export_now+1
 jsr sav_context_begin
 bcs failed
 lda #7
 sta dos64_native_diag+3
 lda #1
 sta ML_STATE
 ldx #0
 rts
bad: lda #0
 ldx #0
 rts
ms_poll:
 lda ML_STATE
 cmp #1
 bne @return
 lda ms_cancel
 beq :+
 lda #9
 sta dos64_native_diag+3
: jsr sav_dispatch
 lda dos64_native_diag+3
 bne @return
 lda dos64_native_diag+4
 cmp #$a5
 bne failed
 lda dos64_native_diag
 cmp #8
 bne failed
 lda dos64_cache_limit
 ora sav_context_pending
 ora sav_error
 bne failed
 lda dos64_export_verified
 cmp #1
 bne failed
 jsr sav_validate_media
 bcs failed
 ldx #3
: lda dos64_export_crc_raw,x
 eor #$ff
 sta ML_CRC,x
 dex
 bpl :-
 lda #2
 sta ML_STATE
 lda #$a5
 sta ML_VALID
@return: rts
failed:
 lda ML_ERROR
 bne :+
 lda #1
 sta ML_ERROR
: lda #0
 sta ML_VALID
 lda #3
 sta ML_STATE
 rts
.segment "SAVER"
 .byte "D64O",1,7
 .word save_end-save_body,$b010,0
 .byte "SAVE"
save_body:
 .include "selected_saver.inc"
save_end:
