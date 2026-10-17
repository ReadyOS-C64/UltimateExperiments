.setcpu "6502"
.macpack longbranch
.include "../phase/runtime.inc"
.include "../phase/media_transaction.inc"
.include "../phase/binding_receipt.inc"
.include "broker.inc"
.importzp sp,ptr1,sreg
.export _mb_get32
.import __BSS_RUN__,__BSS_SIZE__
.import _mb_cancel_seen,_mb_ledger_check
.export _mb_buffer:=$b800,_mb_compare:=$ba40,_mb_ledger:=$7f00,_mb_token:=MB_READY
.export _mb_block:=dos64_native_diag,_mb_uci_base:=dos64_uci_base
.export _mb_dma,_mb_dma_c64,_mb_dma_address,_mb_dma_count,_mb_dma_write
.export _mb_owner,_mb_clean,_mb_service,_mb_fixture_init
.segment "LOADADDR"
.word $a000
.segment "BSS"
_mb_dma_c64:.res 2
_mb_dma_address:.res 4
_mb_dma_count:.res 2
_mb_dma_write:.res 1
ports:.res 4
samples:.res 1
.segment "CODE"
_mb_fixture_init:
 lda #$ff
 sta sp
 lda #$bf
 sta sp+1
 lda #0
 ldx #<__BSS_SIZE__
: sta __BSS_RUN__-1,x
 dex
 bne :-
 rts
.assert __BSS_SIZE__>0 && __BSS_SIZE__<256,lderror,"binding init8bit bound"
.assert __BSS_RUN__+__BSS_SIZE__ <= $7dd0,lderror,"binding phase state must not alias wrapper"
; cc65 ABI: unaligned little-endian32 load, no external callback.
_mb_get32:
 sta ptr1
 stx ptr1+1
 ldy #3
 lda (ptr1),y
 sta sreg+1
 dey
 lda (ptr1),y
 sta sreg
 dey
 lda (ptr1),y
 tax
 dey
 lda (ptr1),y
 rts
_mb_dma:
 ldx #1
: lda _mb_dma_c64,x
 sta dos64_reu_request,x
 lda _mb_dma_count,x
 sta dos64_reu_request+5,x
 dex
 bpl :-
 ldx #2
: lda _mb_dma_address,x
 sta dos64_reu_request+2,x
 dex
 bpl :-
 lda _mb_dma_write
 eor #1
 sta dos64_reu_request+7
 jsr dos64_reu_transfer
 bcs bad
 lda #1
 ldx #0
 rts
bad:
 lda #0
 tax
 rts
; Exact current broker and saved C authority, no C callbacks/engine mutation.
_mb_owner:
 jsr _mb_ledger_check
 cmp #0
 jeq bad
 lda broker_owned
 cmp #$a5
 jne bad
 lda broker_context
 cmp #1
 beq :+
 cmp #2
 jne bad
: lda dos64_native_diag
 cmp #8
 jne bad
 lda dos64_overlay_reu_mib
 cmp #4
 jcc bad
 cmp #17
 jcs bad
 lda dos64_cache_ready
 cmp #$a5
 jne bad
 lda dos64_overlay_ready
 cmp #$a5
 jne bad
 lda dos64_cache_limit
 ora dos64_cold_open
 ora sav_context_pending
 ora sav_borrowed
 ora hdb_active
 ora hd_uncertain
 ora dos64_overlay_busy
 ora dos64_uci_recovery_failed
 jne bad
 lda dos64_uci_state
 beq :+
 cmp #9
 jne bad
: lda broker_online
 cmp hdb_online
 jne bad
 cmp MB_ONLINE
 jne bad
 lda broker_target
 cmp hdc_target
 jne bad
 ldx #24
: lda dos64_files_state_start,x
 cmp broker_files,x
 jne bad
 cmp MB_FILES,x
 jne bad
 dex
 bpl :-
 ldx #hd_state_end-hd_state_start-1
: lda hd_state_start,x
 cmp broker_hd,x
 jne bad
 dex
 bpl :-
 ldx #hdb_state_end-hdb_state_start-1
: lda hdb_state_start,x
 cmp broker_hdb,x
 jne bad
 dex
 bpl :-
 ldx #31
: lda dos64_cache_flags,x
 ora dos64_cache_pins,x
 jne bad
 dex
 bpl :-
 ldx #9
: lda dos64_disk_reu_base,x
 cmp ML_SNAPSHOT,x
 jne bad
 dex
 bpl :-
 ldx #31
: lda dos64_disk_b_descriptor,x
 cmp ML_SNAPSHOT+10,x
 jne bad
 dex
 bpl :-
 ldx #23
: lda dos64_disk_clean_mount,x
 cmp MB_TAIL,x
 jne bad
 dex
 bpl :-
 lda ML_DRIVE
 cmp #2
 jcs bad
 tax
 lda dos64_disk_exhausted,x
 jne bad
 lda #1
 ldx #0
 rts
_mb_clean:
 jsr _mb_service
 cmp #0
 jeq bad
 jsr _mb_owner
 cmp #0
 jeq bad
 lda #0
 ldx #26
: sta dos64_floppy_request,x
 dex
 bpl :-
 lda #5
 sta dos64_floppy_request
 lda ML_DRIVE
 sta dos64_floppy_request+1
 tax
 lda #$a5
 sta dos64_floppy_request+3
 lda $ba40+524
 cpx #0
 beq :+
 lsr
: and #1
 sta dos64_floppy_request+2
 txa
 asl
 asl
 tax
 ldy #0
: lda ML_SNAPSHOT+26,x
 sta dos64_floppy_request+15,y
 lda ML_SNAPSHOT+34,x
 sta dos64_floppy_request+19,y
 lda ML_CRC,y
 sta dos64_floppy_request+23,y
 inx
 iny
 cpy #4
 bne :-
 jsr dos64_overlay_floppy_control
 jcs bad
 lda dos64_overlay_error
 ora dos64_floppy_status
 jne bad
 lda #1
 ldx #0
 rts
; Cancellation is already past durable WIRE commit: record STOP, finish bounded
; binding. Clock errors still fail, no clock/CIA init or retry beyond256sample4.
_mb_service:
 lda #0
 sta samples
@clock:
 jsr dos64_elapsed_poll
 bcc @key
 lda dos64_host_clock_status
 cmp #4
 jne bad
 inc samples
 bne @clock
 jmp bad
@key:
 ldx #3
: lda $dc00,x
 sta ports,x
 dex
 bpl :-
 lda #$ff
 sta $dc02
 lda #0
 sta $dc03
 lda #$7f
 sta $dc00
 nop
 nop
 lda $dc01
 and #$80
 pha
 ldx #3
: lda ports,x
 sta $dc00,x
 dex
 bpl :-
 pla
 bne :+
 lda #1
 sta _mb_cancel_seen
: lda #1
 ldx #0
 rts
