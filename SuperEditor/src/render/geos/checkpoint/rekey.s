; Private post-publication pair refresh. No parser inference/anchor rebasing.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/geos/caret-cache.inc"
.include "render/geos/edit-certificate.inc"
.include "document/math24.inc"
.ifndef GSR_C5
.import se_f_owner,se_mode,se_e_ui,se_r_presentation,se_ef_valid,se_l_mode,se_l_pan
.import se_e_draw_sequence
.import se_doc_meta,se_doc_generation,se_doc_epoch,se_r_revision,se_v_top,se_v_length
.import se_hot_pending,se_reu_epoch,se_reu_retired,se_gc_handle,se_gc_epoch,se_gc_width
.import se_reu_map,se_reu_logical_owner,se_reu_physical_owner
.import se_reu_logical,se_reu_offset,se_reu_c64,se_reu_length,se_reu_copy
.import se_crc_init,se_crc_byte,se_crc_value
.importzp text_ptr
.endif
.export se_gsr_refresh
R=$8880 ;two64B records; closed GEOS painter/FS source context only
OLD=$8900 ;28B expected oldkey
T=$891C ;4 arithmetic bytes
SLOT=$8920 ;0current/64previous
COUNT=$8921 ;1atBOF/2otherwise
.assert R>=$8880 .and COUNT+1<=$8B40,error,"refresh scratch must remain phaseowned"
.ifdef GSR_C5
.segment "CODE"
.else
.segment "FOLD_SOURCE_CODE"
.endif
se_gsr_refresh:
 lda se_f_owner
 cmp #4
 jne miss
 lda se_mode
 cmp #3
 jne miss
 lda se_e_ui
 ora se_r_presentation
 ora se_ef_valid
 ora se_l_mode
 ora se_l_pan
 ora se_l_pan+1
 ora se_l_pan+2
 ora $912C
 ora $912D
 ora GEC_VALID
 jne miss
 lda se_hot_pending
 cmp #1
 jne miss
 lda GCC_VALID
 cmp #1
 jne miss
 ldx #1
@sequence:
 lda GCC_SEQUENCE,x
 cmp se_e_draw_sequence,x
 jne miss
 dex
 bpl @sequence
 clc
 lda GEC_SEQUENCE
 adc #1
 sta T
 lda GEC_SEQUENCE+1
 adc #0
 jcs miss
 cmp se_e_draw_sequence+1
 jne miss
 lda T
 cmp se_e_draw_sequence
 jne miss
 ; Exact current fullkey.  The successful page publication has already
 ; refreshed the resident view; R19 owns this transaction and authenticates
 ; every source token/epoch/revision/length against the retained page key.
 ldx #14
@tokens:
 lda se_doc_meta,x
 cmp GCC_KEY,x
 jne cleanup
 dex
 bpl @tokens
 ldx #1
@epochs:
 lda se_doc_generation,x
 cmp GCC_KEY+15,x
 jne cleanup
 lda se_doc_epoch,x
 cmp GCC_KEY+26,x
 jne cleanup
 lda se_reu_epoch,x
 cmp GCC_KEY+24,x
 jne cleanup
 cmp GEC_REU_EPOCH,x
 jne cleanup
 cmp se_gc_epoch,x
 jne cleanup
 cmp GCC_EPOCH,x
 jne cleanup
 lda se_doc_epoch,x
 cmp GEC_DOC_EPOCH,x
 jne cleanup
 dex
 bpl @epochs
 ldx #3
@revision:
 lda se_r_revision,x
 cmp GCC_KEY+17,x
 jne cleanup
 dex
 bpl @revision
 ldx #2
@length:
 lda se_v_length,x
 cmp GCC_KEY+21,x
 jne cleanup
 lda se_v_top,x
 cmp GCC_KEY+28,x
 jne cleanup
 dex
 bpl @length
 ; Construct exact old key and prove one nonwrapping observer edit.
 ldx #27
@key:
 lda GCC_KEY,x
 sta OLD,x
 dex
 bpl @key
 clc
 .repeat 4,I
 lda GEC_REVISION+I
 sta OLD+17+I
 .if I=0
 adc #1
 .else
 adc #0
 .endif
 sta T+I
 .endrepeat
 jcs cleanup
 ldx #3
@newrev:
 lda T,x
 cmp GCC_KEY+17,x
 jne cleanup
 dex
 bpl @newrev
 ldx #2
@oldlen:
 lda GEC_LENGTH,x
 sta OLD+21,x
 sta T,x
 dex
 bpl @oldlen
 lda GEC_OP
 beq @insert
 cmp #1
 jne cleanup
 lda GEC_NEW
 jne cleanup
 sec
 lda T
 sbc #1
 sta T
 lda T+1
 sbc #0
 sta T+1
 lda T+2
 sbc #0
 sta T+2
 jcc cleanup
 jmp @newlen
@insert:
 lda GEC_OLD
 jne cleanup
 inc T
 bne @newlen
 inc T+1
 bne @newlen
 inc T+2
 jeq cleanup
@newlen:
 CMP24 T,se_v_length
 jne cleanup
 CMP24 GEC_POSITION,GEC_LENGTH
 jcc @bounds
 jne cleanup
 lda GEC_OP
 jne cleanup
@bounds:
 CMP24 GEC_POSITION,se_v_top
 jcc cleanup
 ; Exact typed FE capability before any backing read/write.
 lda se_gc_width
 cmp #$FF
 jne cleanup
 lda se_reu_retired
 jne cleanup
 lda se_reu_epoch
 ora se_reu_epoch+1
 jeq cleanup
 ldx se_gc_handle
 jeq cleanup
 cpx GCC_HANDLE
 jne cleanup
 lda se_reu_logical_owner,x
 cmp #$FE
 jne cleanup
 ldy se_reu_map,x
 jeq cleanup
 cpy GCC_PHYSICAL
 jne cleanup
 lda se_reu_physical_owner,y
 cmp #$FE
 jne cleanup
 stx se_reu_logical
 lda #0
 sta se_reu_offset
 sta se_reu_length+1
 lda #6
 sta se_reu_offset+1
 lda #<R
 sta se_reu_c64
 lda #>R
 sta se_reu_c64+1
 lda #128
 sta se_reu_length
 lda #1
 jsr se_reu_copy
 jcs cleanup
 lda #1
 sta COUNT
 lda se_v_top
 ora se_v_top+1
 ora se_v_top+2
 beq :+
 inc COUNT
: lda #0
 sta SLOT
@validate:
 jsr pointer
 jsr record
 jcs cleanup
 lda SLOT
 bne @validated
 lda COUNT
 cmp #2
 bne @validated
 lda #64
 sta SLOT
 bne @validate
@validated:
 lda #0
 sta SLOT
@publish:
 jsr pointer
 ldy #24
 ldx #17
@visible:
 lda GCC_KEY,x
 sta (text_ptr),y
 inx
 iny
 cpy #31
 bcc @visible
 jsr checksum
 ldy #62
 lda se_crc_value
 sta (text_ptr),y
 iny
 lda se_crc_value+1
 sta (text_ptr),y
 ldy #3
 lda #0
 sta (text_ptr),y
 lda SLOT
 sta se_reu_offset
 lda text_ptr
 sta se_reu_c64
 lda #64
 sta se_reu_length
 lda #0
 jsr se_reu_copy
 jcs cleanup
 ; Trust is published only by the final single VALID1 byte.
 jsr pointer
 ldy #3
 lda #1
 sta (text_ptr),y
 lda SLOT
 clc
 adc #3
 sta se_reu_offset
 lda text_ptr
 clc
 adc #3
 sta se_reu_c64
 lda #1
 sta se_reu_length
 lda #0
 jsr se_reu_copy
 jcs cleanup
 lda SLOT
 bne success
 lda COUNT
 cmp #2
 bne success
 lda #64
 sta SLOT
 bne @publish
success:
cleanup:
miss:
 lda #0
 clc
 rts
pointer:
 lda SLOT
 clc
 adc #<R
 sta text_ptr
 lda #>R
 sta text_ptr+1
 rts
checksum:
 jsr se_crc_init
 ldy #0
@byte:
 lda (text_ptr),y
 jsr se_crc_byte
 iny
 cpy #62
 bcc @byte
 rts
record:
 ldy #0
@header:
 lda (text_ptr),y
 cmp header,y
 jne bad
 iny
 cpy #3
 bcc @header
 ; A refused final VALID1 leaves a complete body whose stored CRC covers the
 ; intended VALID value. Authenticate that pending record by hashing it as
 ; VALID1 in phase-owned scratch. Other values are corrupt.
 ldy #3
 lda (text_ptr),y
 cmp #2
 jcs bad
 lda #1
 sta (text_ptr),y
 jsr checksum
 ldy #62
 lda (text_ptr),y
 cmp se_crc_value
 jne bad
 iny
 lda (text_ptr),y
 cmp se_crc_value+1
 jne bad
 ; Each fullkey must be exactly OLD or NEW, never an unproved revision gap.
 ldy #7
 ldx #0
@old:
 lda (text_ptr),y
 cmp OLD,x
 bne @newstart
 iny
 inx
 cpx #28
 bcc @old
 beq @TOP
@newstart:
 ldy #7
 ldx #0
@new:
 lda (text_ptr),y
 cmp GCC_KEY,x
 jne bad
 iny
 inx
 cpx #28
 bcc @new
@TOP:
 ldy #41
 ldx #0
@bound:
 lda (text_ptr),y
 cmp se_v_top,x
 jne bad
 iny
 inx
 cpx #3
 bcc @bound
 ldy #4
 ldx #0
@anchor:
 lda (text_ptr),y
 sta T,x
 iny
 inx
 cpx #3
 bcc @anchor
 CMP24 T,se_v_top
 lda SLOT ;LDA preserves carry from24bit comparison
 beq @current
 jcs bad
 clc
 rts
@current:
 ; Carry set plus zero means currentSTART exactlyTOP.
 jcc bad
 lda T
 cmp se_v_top
 jne bad
 lda T+1
 cmp se_v_top+1
 jne bad
 lda T+2
 cmp se_v_top+2
 jne bad
 clc
 rts
bad:
 sec
 rts
header:.byte $53,2,64,1
