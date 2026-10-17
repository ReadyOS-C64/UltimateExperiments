.include "floppy_format.inc"
.if DOS64_FLOPPY_FORMAT
.include "overlays.inc"
.include "reu.inc"
.macpack longbranch
.import dos64_reu_request,dos64_reu_transfer,dos64_range_buffer,dos64_overlay_error,dos64_format_slot_crc
.export dos64_format_check_slot,dos64_format_check_cold
.segment "DEVICESTATE"
fc_crc:.res 4
fc_pages:.res 1
.macro CRCBYTE
.local bit,skip
 eor fc_crc
 sta fc_crc
 ldx #8
bit:
 lsr fc_crc+3
 ror fc_crc+2
 ror fc_crc+1
 ror fc_crc
 bcc skip
 lda fc_crc
 eor #$20
 sta fc_crc
 lda fc_crc+1
 eor #$83
 sta fc_crc+1
 lda fc_crc+2
 eor #$b8
 sta fc_crc+2
 lda fc_crc+3
 eor #$ed
 sta fc_crc+3
skip:
 dex
 bne bit
.endmacro
.macro INIT
 lda #$ff
 ldx #3
: sta fc_crc,x
 dex
 bpl :-
 lda #8
 sta fc_pages
.endmacro
.macro COMPARE
.local compare,bad
 ldx #3
compare:
 lda fc_crc,x
 eor #$ff
 cmp dos64_format_slot_crc,x
 bne bad
 dex
 bpl compare
 clc
 rts
bad:
 lda #9
 sta dos64_overlay_error
 sec
 rts
.endmacro
.segment "FORMATCHECKCODE"
dos64_format_check_slot:
 INIT
 lda #0
 sta dos64_reu_request+R_HOST
 sta dos64_reu_request+R_REU
 sta dos64_reu_request+R_LENGTH
 lda #$c0
 sta dos64_reu_request+R_HOST+1
 lda #$20
 sta dos64_reu_request+R_REU+1
 lda #$34
 sta dos64_reu_request+R_REU+2
 lda #1
 sta dos64_reu_request+R_DIRECTION
 sta dos64_reu_request+R_LENGTH+1
fc_live_page:
 jsr dos64_reu_transfer
 bcs fc_live_dma
 ldy #0
fc_live_byte:
 lda dos64_range_buffer,y
 CRCBYTE
 iny
 bne fc_live_byte
 inc dos64_reu_request+R_REU+1
 dec fc_pages
 bne fc_live_page
 COMPARE
fc_live_dma:
 lda #5
 sta dos64_overlay_error
 sec
 rts
.segment "COLDINIT"
dos64_format_check_cold:
 INIT
 lda #$90
 sta fc_cold_source+2
fc_cold_page:
 ldy #0
fc_cold_byte:
fc_cold_source:
 lda $9000,y
 CRCBYTE
 iny
 bne fc_cold_byte
 inc fc_cold_source+2
 dec fc_pages
 bne fc_cold_page
 COMPARE
.endif
