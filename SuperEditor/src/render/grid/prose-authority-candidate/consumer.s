; R25 exact old C14-publication authority. B is only scratch until row fetch.
.include "prose.inc"
sc_check:
 jsr sc_fetch
 jcs invalid
 jsr sc_crc
 ldx #1
@crc:
 lda se_crc_value,x
 cmp B+SC_CRC,x
 jne invalid
 dex
 bpl @crc
 lda B
 cmp #'S'
 jne invalid
 lda B+1
 cmp #'P'
 jne invalid
 lda B+2
 cmp #1
 jne invalid
 lda B+3
 cmp #$A5
 jne invalid
 ldx #32
@key:
 lda B+SC_KEY,x
 cmp H+N_STYLE,x
 jne invalid
 dex
 bpl @key
 ldx #1
@binding:
 lda B+SC_EPOCH,x
 cmp H+N_KEY+26,x
 jne invalid
 lda B+SC_GEN,x
 cmp H+N_STYLE+33,x
 jne invalid
 dex
 bpl @binding
 lda B+SC_WIDTH
 cmp W
 jne invalid
 ldx #68
@rows:
 lda B+SC_ROWS,x
 cmp H+N_ROWS,x
 jne invalid
 dex
 bpl @rows
 jsr row_bit
 lda B+SC_PLAIN,x
 and BITMASK
 jeq invalid
 clc
 rts

; Earlier sc_check is valid through this uninterrupted owner4 transaction.
; R16 only paints and status is C33-local; no source/FE/certificate writer can
; run between phases. Re-fetch/checkCRC, then derive the exact rekeyed witness.
sc_rekey:
 jsr sc_fetch
 jcs invalid
 jsr sc_crc
 ldx #1
@crc:
 lda se_crc_value,x
 cmp B+SC_CRC,x
 jne invalid
 dex
 bpl @crc
 ldx #32
@key:
 lda H+N_STYLE,x
 sta B+SC_KEY,x
 dex
 bpl @key
 ldx #68
@rows:
 lda H+N_ROWS,x
 sta B+SC_ROWS,x
 dex
 bpl @rows
 jsr sc_crc
 lda se_crc_value
 sta B+SC_CRC
 lda se_crc_value+1
 sta B+SC_CRC+1
 jsr sc_request
 lda #0
 jmp se_reu_copy
sc_fetch:
 jsr sc_request
 lda #1
 jmp se_reu_copy
sc_request:
 lda se_gc_handle
 sta se_reu_logical
 lda #<SC_REU
 sta se_reu_offset
 lda #>SC_REU
 sta se_reu_offset+1
 lda #<B
 sta se_reu_c64
 lda #>B
 sta se_reu_c64+1
 lda #128
 sta se_reu_length
 lda #0
 sta se_reu_length+1
 rts
sc_crc:
 jsr se_crc_init
 ldy #0
@byte:
 lda B,y
 jsr se_crc_byte
 iny
 cpy #SC_CRC
 bcc @byte
 rts
