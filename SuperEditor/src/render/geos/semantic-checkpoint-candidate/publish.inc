; C21-only producer. Call at classified/@ready before C20/C25 phase reuse.
; Existing C21 STEP has just passed actual cache_guard (source graph + typedFE).
; Only row0 with a real logical START==TOP publishes; softwrap TOP declines.
.include "render/geos/semantic-checkpoint-candidate/codec.inc"
.import se_crc_init,se_crc_byte,se_crc_value
.segment "GEOS_PAGE"
gsc_publish:
 lda LINE
 jne @skip
 lda GSC_CAPTURED
 cmp #1
 jne @skip
 CMP24 GSC_INCOMING,se_v_top
 jne @skip
 ldx #27
@identity:
 lda GSC_CURRENT,x
 cmp GP_HEADER+GPH_KEY,x
 jne @skip
 dex
 bpl @identity
 lda #0
 ldx #63
@zero:
 sta GSC_RECORD,x
 dex
 bpl @zero
 lda #$53
 sta GSC_RECORD
 lda #1
 sta GSC_RECORD+1
 sta GSC_RECORD+3
 lda #64
 sta GSC_RECORD+2
 COPY24 GSC_INCOMING,GSC_RECORD+4
 ldx #27
@key:
 lda GSC_CURRENT,x
 sta GSC_RECORD+7,x
 dex
 bpl @key
 ldx #5
@carry:
 lda GSC_INCOMING+3,x
 sta GSC_RECORD+35,x
 dex
 bpl @carry
 jsr se_crc_init
 ldy #0
@crc:
 lda GSC_RECORD,y
 jsr se_crc_byte
 iny
 cpy #62
 bcc @crc
 lda se_crc_value
 sta GSC_RECORD+62
 lda se_crc_value+1
 sta GSC_RECORD+63
 ; Commit VALID-last. A failed partial record can never be a cache hit.
 lda #0
 sta GSC_RECORD+3
 jsr @request
 jsr se_gp_cache_write
 bcs @skip
 lda #1
 sta GSC_RECORD+3
 lda #3
 sta GP_IO_OFFSET
 lda #<(GSC_RECORD+3)
 sta GP_IO_POINTER
 lda #1
 sta GP_IO_LENGTH
 jsr se_gp_cache_write
 jmp @skip
@request:
 lda #0
 sta GP_IO_OFFSET
 sta GP_IO_POINTER
 sta GP_IO_LENGTH+1
 lda #6
 sta GP_IO_OFFSET+1
 lda #>GSC_RECORD
 sta GP_IO_POINTER+1
 lda #64
 sta GP_IO_LENGTH
 rts
@skip:
 lda #0
 clc
 rts
