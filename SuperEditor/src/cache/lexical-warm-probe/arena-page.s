.setcpu "6502"
.macpack longbranch
.include "cache/arena/api.inc"
.include "object/api.inc"
.import se_crc_init,se_crc_byte,se_crc_value
.import bca_owner,bca_guard,bca_transfer,bca_pending,bca_done,bca_bad,bca_stale,bca_corrupt
.export se_bc_page_begin,bca_page_step,se_bc_arena_read
; BCA_OUTER_VALIDATED may be enabled only for the R36/R37 lexical profiles:
; link_guard/guard has just completed for this same uninterrupted entry.
; Page request, range, directory/header/payload CRC and checked DMA stay live.
.segment "CODE"
; Caller supplies PAGE/KIND/GENERATION. STEP validates directory,64B header,
; then at most128 payload bytes per call. No record exposed before fullCRC.
se_bc_page_begin:
 jsr bca_owner
 jcs @done
 lda BCA_PHASE
 jne @busy
 lda #0
 sta BCA_PROOF
.ifndef BCA_OUTER_VALIDATED
 jsr bca_guard
 jcs @done
.endif
 lda BCA_PAGE
 jeq bca_bad
 ; page /16 < actual allocated bank count, handles 16-bank max safely.
 lsr
 lsr
 lsr
 lsr
 cmp BCA_BANKS
 jcs bca_bad
 lda BCA_KIND
 beq @bad
 cmp #8
 bcs @bad
 lda BCA_GENERATION
 and BCA_GENERATION+1
 cmp #$FF
 beq @bad
 ldy #3
@capture:lda BCA_PAGE,y
 sta BCA_TEMP+4,y
 dey
 bpl @capture
 lda #7
 sta BCA_PHASE
 jmp bca_pending
@busy:lda #BCA_BUSY
 sec
@done:rts
@bad:jmp bca_bad
bca_page_step:
 jsr page_request_guard
 jcs @done
.ifndef BCA_OUTER_VALIDATED
 jsr bca_guard
 jcs @done
.endif
 lda BCA_PHASE
 cmp #7
 jeq @directory
 cmp #8
 jeq @header
 cmp #9
 jne bca_bad
 ; Every chunk uses preserved running CRC, never global CRC across yields.
 lda BCA_CRC
 sta se_crc_value
 lda BCA_CRC+1
 sta se_crc_value+1
 ldy #2
@cursor:lda BCA_CURSOR,y
 sta BCA_OFFSET,y
 dey
 bpl @cursor
 lda #128
 ldx BCA_LEFT+1
 bne @length
 cmp BCA_LEFT
 bcc @length
 lda BCA_LEFT
@length:sta BCA_LENGTH
 lda #1
 jsr bca_transfer
 jcs @done
 ldy #0
@bytes:lda BC_IO,y
 jsr se_crc_byte
 iny
 cpy BCA_LENGTH
 bne @bytes
 lda se_crc_value
 sta BCA_CRC
 lda se_crc_value+1
 sta BCA_CRC+1
 clc
 lda BCA_CURSOR
 adc BCA_LENGTH
 sta BCA_CURSOR
 bcc @subtract
 inc BCA_CURSOR+1
 bne @subtract
 inc BCA_CURSOR+2
@subtract:sec
 lda BCA_LEFT
 sbc BCA_LENGTH
 sta BCA_LEFT
 lda BCA_LEFT+1
 sbc #0
 sta BCA_LEFT+1
 ora BCA_LEFT
 jne bca_pending
@finish:lda BCA_CRC
 cmp BCA_EXPECT
 jne bca_corrupt
 lda BCA_CRC+1
 cmp BCA_EXPECT+1
 jne bca_corrupt
 lda #$A5
 sta BCA_PROOF
 lda #0
 sta BCA_PHASE
 jmp bca_done
@directory:
 ; offset0100+page*8, independent checked directory entryCRC.
 lda BCA_PAGE
 ldx #0
 stx BCA_OFFSET+2
 asl
 rol BCA_OFFSET+2
 asl
 rol BCA_OFFSET+2
 asl
 rol BCA_OFFSET+2
 sta BCA_OFFSET
 lda BCA_OFFSET+2
 clc
 adc #1
 sta BCA_OFFSET+1
 lda #0
 sta BCA_OFFSET+2
 lda #8
 sta BCA_LENGTH
 lda #1
 jsr bca_transfer
 jcs @done
 ldy #7
@capture:lda BC_IO,y
 sta BCA_DIRECTORY,y
 dey
 bpl @capture
 lda BC_IO
 cmp BCA_GENERATION
 jne bca_corrupt
 lda BC_IO+1
 cmp BCA_GENERATION+1
 jne bca_corrupt
 lda BC_IO+2
 cmp BCA_KIND
 jne bca_corrupt
 lda BC_IO+3
 cmp #1
 jne bca_corrupt
 lda BC_IO+6
 ora BC_IO+7
 jne bca_corrupt
 jsr se_crc_init
 ldy #0
@dir_crc:cpy #4
 beq @skip
 cpy #5
 beq @skip
 lda BC_IO,y
 jsr se_crc_byte
@skip:iny
 cpy #8
 bne @dir_crc
 lda se_crc_value
 cmp BC_IO+4
 jne bca_corrupt
 lda se_crc_value+1
 cmp BC_IO+5
 jne bca_corrupt
 inc BCA_PHASE
 jmp bca_pending
@header:
 jsr page_offset
 lda #64
 sta BCA_LENGTH
 lda #1
 jsr bca_transfer
 jcs @done
 lda BC_IO
 cmp #$42
 jne bca_corrupt
 lda BC_IO+1
 cmp #$50
 jne bca_corrupt
 lda BC_IO+2
 cmp #BC_ABI
 jne bca_corrupt
 lda BC_IO+3
 cmp #1
 jne bca_corrupt
 lda BC_IO+4
 cmp BCA_PAGE
 jne bca_corrupt
 lda BC_IO+5
 cmp BCA_KIND
 jne bca_corrupt
 ldy #1
@gen:lda BC_IO+6,y
 cmp BCA_GENERATION,y
 jne bca_corrupt
 dey
 bpl @gen
 ldy #3
@inc:lda BC_IO+8,y
 cmp BCA_INC,y
 jne bca_corrupt
 dey
 bpl @inc
 ldy #4
@token:lda BC_IO+12,y
 cmp BCA_BOUND,y
 jne bca_corrupt
 dey
 bpl @token
 lda BC_IO+22
 cmp #16
 jcs bca_corrupt
 cmp #15
 bne @used_ok
 lda BC_IO+21
 cmp #193                     ;4032 maximum
 jcs bca_corrupt
@used_ok:lda BC_IO+21
 sta BCA_USED
 sta BCA_LEFT
 lda BC_IO+22
 sta BCA_USED+1
 sta BCA_LEFT+1
 lda BC_IO+39
 sta BCA_EXPECT
 lda BC_IO+40
 sta BCA_EXPECT+1
 ldy #63
@reserved:lda BC_IO,y
 jne bca_corrupt
 dey
 cpy #41
 bne @reserved
 jsr se_crc_init
 ldy #0
@head_crc:cpy #3
 beq @head_skip
 cpy #37
 beq @head_skip
 cpy #38
 beq @head_skip
 lda BC_IO,y
 jsr se_crc_byte
@head_skip:iny
 cpy #64
 bne @head_crc
 lda se_crc_value
 cmp BC_IO+37
 jne bca_corrupt
 lda se_crc_value+1
 cmp BC_IO+38
 jne bca_corrupt
 jsr page_offset
 lda #64
 sta BCA_CURSOR
 lda BCA_OFFSET+1
 sta BCA_CURSOR+1
 lda BCA_OFFSET+2
 sta BCA_CURSOR+2
 jsr se_crc_init
 lda se_crc_value
 sta BCA_CRC
 lda se_crc_value+1
 sta BCA_CRC+1
 inc BCA_PHASE
 lda BCA_LEFT
 ora BCA_LEFT+1
 jeq @finish
 jmp bca_pending
@done:rts
page_offset:
 lda #0
 sta BCA_OFFSET
 lda BCA_PAGE
 lsr
 lsr
 lsr
 lsr
 sta BCA_OFFSET+2
 lda BCA_PAGE
 asl
 asl
 asl
 asl
 sta BCA_OFFSET+1
 rts
; Absolute read request restricted to certified page payload, not headers or
; arbitrary arena contents. Revalidate live typed ownership before everyDMA.
se_bc_arena_read:
 jsr bca_owner
 jcs @done
 lda BCA_PROOF
 cmp #$A5
 jne bca_bad
 lda BCA_PHASE
 jne bca_bad
 jsr page_request_guard
 jcs @done
.ifndef BCA_OUTER_VALIDATED
 jsr bca_guard
 jcs @done
.endif
 ; Compute requested relative offset from page base without losing request.
 lda BCA_PAGE
 lsr
 lsr
 lsr
 lsr
 cmp BCA_OFFSET+2
 jne bca_bad
 lda BCA_PAGE
 asl
 asl
 asl
 asl
 sta BCA_TEMP
 sec
 lda BCA_OFFSET+1
 sbc BCA_TEMP
 jcc bca_bad
 cmp #16
 jcs bca_bad
 sta BCA_TEMP+1
 sec
 lda BCA_OFFSET
 sbc #64
 sta BCA_TEMP
 lda BCA_TEMP+1
 sbc #0
 sta BCA_TEMP+1
 jcc bca_bad
 lda BCA_LENGTH
 jeq bca_bad
 cmp #129
 jcs bca_bad
 clc
 adc BCA_TEMP
 sta BCA_TEMP
 lda BCA_TEMP+1
 adc #0
 cmp BCA_USED+1
 bcc @read
 jne bca_bad
 lda BCA_TEMP
 cmp BCA_USED
 bcc @read
 jne bca_bad
@read:lda #1
 jmp bca_transfer
@done:rts

page_request_guard:
 ldy #3
@check:lda BCA_PAGE,y
 cmp BCA_TEMP+4,y
 jne bca_stale
 dey
 bpl @check
 clc
 rts
