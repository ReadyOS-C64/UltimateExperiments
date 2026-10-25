.setcpu "6502"
.macpack longbranch
GP_CACHE_IMPLEMENTATION=1
.include "render/geos/editor.inc"
.import se_f_owner,se_gc_epoch,se_reu_epoch,se_reu_retired,se_gc_handle
.import se_reu_logical_owner,se_reu_map,se_reu_physical_owner
.import se_reu_logical,se_reu_offset,se_reu_length,se_reu_c64,se_reu_copy
.import se_doc_invalidate
.export se_gp_cache_read,se_gp_cache_write,se_gp_cache_slot
.segment "CODE"
zero:
 lda #0
 clc
return:
 rts
stale:
 lda #$18
 sec
 rts
bad:
 lda #$90
 sec
 rts
owner:
 lda se_f_owner
 cmp #4
 beq zero
 lda #$B2
 sec
 rts
; Never free/reuse a foreign allocation. OPEN alone may replace a stale handle.
owned:
 lda se_reu_retired
 bne stale
 lda se_gc_epoch
 cmp se_reu_epoch
 bne stale
 lda se_gc_epoch+1
 cmp se_reu_epoch+1
 bne stale
 lda se_reu_epoch
 ora se_reu_epoch+1
 beq stale
 ldx se_gc_handle
 beq stale
 lda se_reu_logical_owner,x
 cmp #GP_CACHE_OWNER
 bne stale
 ldy se_reu_map,x
 beq stale
 lda se_reu_physical_owner,y
 cmp #GP_CACHE_OWNER
 bne stale
 clc
 rts
se_gp_cache_slot:
 pha
 jsr owner
 bcs @pop
 pla
 cmp #GP_MAX_LINES
 jcs bad
 asl
 asl
 asl
 clc
 adc #>GP_SLOT_BASE
 sta GP_IO_OFFSET+1
 lda #0
 sta GP_IO_OFFSET
 jmp zero
@pop:
 tax
 pla
 txa
 sec
 rts
se_gp_cache_read:
.ifdef SE_GP_CACHE_READ_ONLY
 jsr owner
 bcs @error
 jsr owned
 bcs @error
 jsr request
 bcs @error
 jsr se_doc_invalidate
 lda #1
 jmp se_reu_copy
@error:
 sec
 rts
.else
 lda #1
 bne transfer
se_gp_cache_write:
 lda #0
transfer:
 pha
 jsr owner
 bcs @error
 jsr owned
 bcs @error
 jsr request
 bcs @error
 jsr se_doc_invalidate ;checked host staging may alias document packet/leaf
 pla
 jmp se_reu_copy
@error:
 tax
 pla
 txa
 sec
 rts
.endif
request:
 lda GP_IO_LENGTH
 ora GP_IO_LENGTH+1
 jeq bad
 ; Exact bank-end is legal; no address wraps to a second physical bank.
 clc
 lda GP_IO_OFFSET
 adc GP_IO_LENGTH
 sta se_reu_offset
 lda GP_IO_OFFSET+1
 adc GP_IO_LENGTH+1
 sta se_reu_offset+1
 bcc :+
 ora se_reu_offset
 jne bad
:
 ; Host span exclusively8000..9133, except protected diag/VIEW holes.
 lda GP_IO_POINTER+1
 cmp #$80
 bcc @bad_span
 clc
 lda GP_IO_POINTER
 adc GP_IO_LENGTH
 sta se_reu_c64
 lda GP_IO_POINTER+1
 adc GP_IO_LENGTH+1
 bcs @bad_span
 sta se_reu_c64+1
 cmp #$91
 bcc :+
 bne @bad_span
 lda se_reu_c64
 cmp #$35
 bcs @bad_span
:
 ; Intersecting8800..887F is forbidden; ending at8800 is legal.
 lda GP_IO_POINTER+1
 cmp #$88
 bcc @diag_end
 bne @view
 lda GP_IO_POINTER
 cmp #$80
 bcc @bad_span
 bcs @view
@diag_end:
 lda se_reu_c64+1
 cmp #$88
 bcc @view
 bne @bad_span
 lda se_reu_c64
 bne @bad_span
@view:
 lda GP_IO_POINTER+1
 cmp #$8D
 bcs @copy
 cmp #$8C
 beq @bad_span
 lda se_reu_c64+1
 cmp #$8C
 bcc @copy
 bne @bad_span
 lda se_reu_c64
 bne @bad_span
@copy:
 lda se_gc_handle
 sta se_reu_logical
 ldx #1
@fields:
 lda GP_IO_OFFSET,x
 sta se_reu_offset,x
 lda GP_IO_POINTER,x
 sta se_reu_c64,x
 lda GP_IO_LENGTH,x
 sta se_reu_length,x
 dex
 bpl @fields
 clc
 rts
@bad_span:
 jmp bad
