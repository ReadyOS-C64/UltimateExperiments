; Compact independentR30guard for a CRC-certified C6 readonly oldrow result.
.setcpu "6502"
.macpack longbranch
GP_CACHE_IMPLEMENTATION=1
.include "render/geos/typing-candidate/guard.inc"
.include "document/math24.inc"
.import se_mode,se_e_ui,se_r_presentation,se_l_mode,se_l_pan,se_sel_mark,se_ef_valid
.import se_e_error,se_h_fault,se_h_trimmed,se_e_draw_sequence
.import se_doc_meta,se_doc_generation,se_doc_epoch,se_doc_busy,se_r_revision
.import se_hot_ready,se_hot_phase,se_hot_pending,se_hot_delete,se_hot_command,se_hot_caret
.import se_view_init,se_v_length,se_v_top,se_object_id,se_object_validate
.import se_gc_handle,se_gc_width,se_gc_epoch,se_reu_epoch,se_reu_map
.import se_gp_cache_read,se_gp_cache_slot
.import se_crc_init,se_crc_byte,se_crc_value
.export se_gtt_admit,se_gtt_current
.segment "CODE"
se_gtt_admit:
 jmp @resume2
@miss2:
 lda #2
 clc
 rts
@resume2:
 lda GEC_VALID
 cmp #1
 bne @miss2
 lda GCC_VALID
 cmp #1
 bne @miss2
 lda GTC_VALID
 cmp #1
 bne @miss2
 ldx #46
@copy:
 lda GTC,x
 sta GTT_LOCAL,x
 dex
 bpl @copy
 lda #0
 sta GTC_VALID
 jsr se_crc_init
 ldy #1
 jmp @resume4
@miss4:
 lda #2
 clc
 rts
@resume4:
@crc:
 lda GTT_LOCAL,y
 jsr se_crc_byte
 iny
 cpy #45
 bcc @crc
 lda se_crc_value
 cmp GTT_LOCAL+45
 bne @miss4
 lda se_crc_value+1
 cmp GTT_LOCAL+46
 bne @miss4
 jsr se_gtt_current
 jcs return
 cmp #2
 beq @miss4
 lda #0
 sta GP_IO_OFFSET
 sta GP_IO_OFFSET+1
 lda #<GP_HEADER
 ldx #>GP_HEADER
 ldy #64
 jsr read
 jcs return
 lda GP_HEADER+GPH_VALID
 jmp @resume5
@miss5:
 lda #2
 clc
 rts
@resume5:
 cmp #1
 bne @miss5
 lda GP_HEADER+GPH_MAGIC
 cmp #$47
 bne @miss5
 lda GP_HEADER+GPH_VERSION
 cmp #3
 bne @miss5
 lda GP_HEADER+GPH_COUNT
 beq @miss5
 cmp #23
 bcs @miss5
 cmp GCC_COUNT
 bne @miss5
 cmp GTT_ROW
 bcc @miss5
 beq @miss5
 ldx #36
@key:
 lda GP_HEADER+GPH_KEY,x
 cmp GCC_KEY,x
 jne miss
 dex
 bpl @key
 ldx #2
 jmp @resume7
@miss7:
 lda #2
 clc
 rts
@resume7:
@fold:
 lda GP_HEADER+GPH_FOLD_VALID,x
 cmp GCC_FOLD,x
 bne @miss7
 lda GP_HEADER+GPH_TOP,x
 cmp se_v_top,x
 bne @miss7
 lda GP_HEADER+GPH_PAN,x
 bne @miss7
 dex
 bpl @fold
 lda GTT_ROW
 jsr se_gp_cache_slot
 jcs return
 lda GP_IO_OFFSET
 sta GTT_SLOT
 lda GP_IO_OFFSET+1
 sta GTT_SLOT+1
 lda #<GP_RECORD
 ldx #>GP_RECORD
 ldy #32
 jsr read
 jcs return
 ldx #31
 jmp @resume8
@miss8:
 lda #2
 clc
 rts
@resume8:
@prefix:
 lda GP_RECORD,x
 cmp GTT_PREFIX,x
 bne @miss8
 dex
 bpl @prefix
 ; Bounds areindependent evenif a malformedcertificate hasarecomputedCRC.
 lda GP_RECORD+GPR_COUNT+1
 ora GP_RECORD+GPR_KIND
 ora GP_RECORD+GPR_INLINE
 ora GP_RECORD+GPR_FLAGS
 bne @miss8
 lda GP_RECORD+GPR_COUNT
 beq @miss8
 cmp #161
 bcs @miss8
 cmp GTT_INDEX
 bcc @miss8
 lda GTT_INDEX
 beq @miss8
 lda GP_RECORD+GPR_TOP
 cmp #16
 bcc @miss8
 cmp #184
 bcs @miss8
 jmp @resume9
@miss9:
 lda #2
 clc
 rts
@resume9:
 lda GP_RECORD+GPR_HEIGHT
 cmp #9
 bne @miss9
 lda GP_RECORD+GPR_REASON
 beq @miss9
 cmp #3
 bcs @miss9
 lda #1
 clc
return:
 rts
miss:
 lda #2
 clc
 rts
se_gtt_current:
 jmp @resume12
@miss12:
 lda #2
 clc
 rts
@resume12:
 lda se_mode
 cmp #3
 bne @miss12
 lda se_e_ui
 ora se_r_presentation
 ora se_l_mode
 ora se_l_pan
 ora se_l_pan+1
 ora se_l_pan+2
 ora se_sel_mark
 ora se_ef_valid
 ora se_e_error
 ora se_h_fault
 ora se_h_trimmed
 ora se_h_trimmed+1
 ora se_doc_busy
 ora se_hot_phase
 ora $912C
 ora $912D
 bne @miss12
 lda se_hot_ready
 cmp #1
 bne @miss12
 lda se_hot_pending
 jmp @resume13
@miss13:
 lda #2
 clc
 rts
@resume13:
 cmp #1
 bne @miss13
 lda GEC_OP
 cmp #2
 bcs @miss13
 cmp se_hot_delete
 bne @miss13
 lda se_hot_command
 ldx GEC_OP
 bne @delete
 cmp #3
 bne @miss13
 jmp @source
@delete:
 cmp #4
 beq @source
 cmp #5
 jne miss
@source:
 jsr se_view_init
 jcs return
 .repeat 3,T
 ldx #4
: lda se_doc_meta+T*5,x
 sta se_object_id,x
 dex
 bpl :-
 jsr se_object_validate
 jcs return
 .endrepeat
 ldx #14
 jmp @resume17
@miss17:
 lda #2
 clc
 rts
@resume17:
@graph:
 lda se_doc_meta,x
 cmp GCC_KEY,x
 bne @miss17
 dex
 bpl @graph
 lda se_gc_width
 cmp #$FF
 bne @miss17
 lda se_gc_handle
 beq @miss17
 cmp GCC_HANDLE
 bne @miss17
 tax
 lda se_reu_map,x
 cmp GCC_PHYSICAL
 bne @miss17
 ldx #1
 jmp @resume18
@miss18:
 lda #2
 clc
 rts
@resume18:
@epoch:
 lda se_reu_epoch,x
 cmp se_gc_epoch,x
 bne @miss18
 cmp GEC_REU_EPOCH,x
 bne @miss18
 cmp GCC_EPOCH,x
 bne @miss18
 cmp GCC_KEY+24,x
 bne @miss18
 lda se_doc_epoch,x
 cmp GEC_DOC_EPOCH,x
 bne @miss18
 cmp GCC_KEY+26,x
 bne @miss18
 lda se_doc_generation,x
 cmp GCC_KEY+15,x
 bne @miss18
 lda se_e_draw_sequence,x
 cmp GEC_SEQUENCE,x
 bne @miss18
 cmp GCC_SEQUENCE,x
 bne @miss18
 dex
 bpl @epoch
 jmp @resume19
@miss19:
 lda #2
 clc
 rts
@resume19:
 ; Exactly one nonwrapping canonicalrevision increment.
 clc
 .repeat 4,I
 lda GEC_REVISION+I
 cmp GCC_KEY+17+I
 bne @miss19
 cmp GTT_REVISION+I
 bne @miss19
 .endrepeat
 clc
 .repeat 4,I
 lda GEC_REVISION+I
 .if I=0
 adc #1
 .else
 adc #0
 .endif
 sta GTT_TEMP+I
 .endrepeat
 bcs @miss19
 ldx #3
@revision:
 lda GTT_TEMP,x
 cmp se_r_revision,x
 jne miss
 dex
 bpl @revision
 ldx #2
@oldlength:
 lda GEC_LENGTH,x
 cmp GCC_KEY+21,x
 jne miss
 sta GTT_TEMP,x
 dex
 bpl @oldlength
 lda GEC_OP
 bne @minus
 jsr plus1
 jcs miss
 jmp @length
@minus:
 lda GTT_TEMP
 ora GTT_TEMP+1
 ora GTT_TEMP+2
 jeq miss
 lda GTT_TEMP
 bne :+
 lda GTT_TEMP+1
 bne @mid
 dec GTT_TEMP+2
@mid:
 dec GTT_TEMP+1
: dec GTT_TEMP
@length:
 CMP24 GTT_TEMP,se_v_length
 jne miss
 COPY24 GEC_POSITION,GTT_TEMP
 lda GEC_OP
 bne @caret
 jsr plus1
 jcs miss
@caret:
 CMP24 GTT_TEMP,se_hot_caret
 jne miss
 lda #0
 clc
 rts
plus1:
 inc GTT_TEMP
 bne :+
 inc GTT_TEMP+1
 bne :+
 inc GTT_TEMP+2
 bne :+
 sec
 rts
: clc
 rts
read:
 sta GP_IO_POINTER
 stx GP_IO_POINTER+1
 sty GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 jmp se_gp_cache_read
