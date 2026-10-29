; PRIVATE nonview guard: TOP is a separately authenticated memo query.
.include "render/presentation.inc"
.setcpu "6502"
.macpack longbranch
GP_CACHE_IMPLEMENTATION=1
.include "render/geos/editor.inc"
.include "editor-api.inc"
.import se_gc_handle,se_gc_epoch,se_gc_width,se_gc_valid
.import se_reu_alloc,se_reu_copy,se_reu_epoch,se_reu_retired
.import se_reu_map,se_reu_logical_owner,se_reu_physical_owner
.import se_reu_c64,se_reu_offset,se_reu_length,se_reu_logical
.import se_f_owner,se_view_init,se_v_length,se_v_top,se_l_pan,se_r_presentation
.import se_doc_meta,se_doc_original,se_doc_append,se_doc_generation,se_doc_epoch
.import se_ef_valid,se_ef_generation
.import se_r_revision,se_object_id,se_object_validate,se_doc_invalidate
.assert se_doc_original=se_doc_meta+5,lderror,"GEOS source token graph must be contiguous"
.assert se_doc_append=se_doc_meta+10,lderror,"GEOS source token graph must be contiguous"
.export se_gp_cache_guard,se_gp_cache_read,se_gp_cache_slot
.ifndef SE_GP_CACHE_READ_ONLY
.export se_gp_cache_write
.endif
.ifndef SE_GP_CACHE_WARM_ONLY
.export se_gp_cache_open
.endif
.segment "CODE"
.macro KEY_FIELDS action
 action se_doc_meta,0,15
 action se_doc_generation,15,2
 action se_r_revision,17,4
 action se_v_length,21,3
 action se_reu_epoch,24,2
 action se_doc_epoch,26,2
.endmacro
.macro CAPTURE source,offset,size
 ldx #size-1
: lda source,x
 sta GP_HEADER+GPH_KEY+offset,x
 dex
 bpl :-
.endmacro
.macro COMPARE source,offset,size
 ldx #size-1
: lda source,x
 cmp GP_HEADER+GPH_KEY+offset,x
 jne changed
 dex
 bpl :-
.endmacro
; Source key exactly matches the28B fold/view graph identity. No phase scratch.
.ifndef SE_GP_CACHE_WARM_ONLY
se_gp_cache_open:
 jsr owner
 jcs return
 jsr refresh
 jcs return
 jsr owned
 bcc @ready
 lda se_reu_epoch
 ora se_reu_epoch+1
 jeq stale
 lda se_reu_retired
 jne stale
 lda #GP_CACHE_OWNER
 jsr se_reu_alloc
 jcs return
 sta se_gc_handle
 lda se_reu_epoch
 sta se_gc_epoch
 lda se_reu_epoch+1
 sta se_gc_epoch+1
@ready:
 jsr se_doc_invalidate ;8500 aliases the checked document leaf scratch
 lda se_r_presentation
 eor #GP_CACHE_WIDTH
 sta se_gc_width
 lda #0
 sta se_gc_valid
 sta se_gc_valid+1
 sta se_gc_valid+2
 ldx #GP_HEADER_SIZE-1
@clear:
 sta GP_HEADER,x
 dex
 bpl @clear
 lda #$47
 sta GP_HEADER+GPH_MAGIC
 lda #GP_CACHE_VERSION
 sta GP_HEADER+GPH_VERSION
 KEY_FIELDS CAPTURE
 jsr se_ef_visible
 sta GP_HEADER+GPH_FOLD_VALID
 ldx #1
@fold:
 lda se_ef_generation,x
 sta GP_HEADER+GPH_FOLD_GENERATION,x
 dex
 bpl @fold
 ldx #2
@view:
 lda se_v_top,x
 sta GP_HEADER+GPH_TOP,x
 lda se_l_pan,x
 sta GP_HEADER+GPH_PAN,x
 dex
 bpl @view
 jsr header_request
 lda #0
 jmp se_reu_copy
.endif
se_gp_cache_guard:
 jsr owner
 jcs return
 jsr owned
 jcs return
 lda se_r_presentation
 eor #GP_CACHE_WIDTH
 cmp se_gc_width
 jne changed
 jsr refresh
 jcs return
 jsr header_request
 lda #1
 jsr se_reu_copy
 jcs return
 lda GP_HEADER+GPH_MAGIC
 cmp #$47
 jne changed
 lda GP_HEADER+GPH_VERSION
 cmp #GP_CACHE_VERSION
 jne changed
 lda GP_HEADER+GPH_VALID
 cmp #2
 jcs changed
 lda GP_HEADER+GPH_COUNT
 cmp #GP_MAX_LINES+1
 jcs changed
 KEY_FIELDS COMPARE
 jsr se_ef_visible
 cmp GP_HEADER+GPH_FOLD_VALID
 jne changed
 ldx #1
@fold:
 lda se_ef_generation,x
 cmp GP_HEADER+GPH_FOLD_GENERATION,x
 jne changed
 dex
 bpl @fold
 ldx #2
@view:
 lda se_l_pan,x
 cmp GP_HEADER+GPH_PAN,x
 jne changed
 dex
 bpl @view
zero:
 lda #0
 clc
return:
 rts
changed:
 lda #$74
 sec
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
refresh:
 jsr se_view_init
 bcs return
 ; Object validation does not DMA or touch the source phase.
 ldx #4
@meta:
 lda se_doc_meta,x
 sta se_object_id,x
 dex
 bpl @meta
 jsr se_object_validate
 bcs return
 ldx #4
@original:
 lda se_doc_original,x
 sta se_object_id,x
 dex
 bpl @original
 jsr se_object_validate
 bcs return
 ldx #4
@append:
 lda se_doc_append,x
 sta se_object_id,x
 dex
 bpl @append
 jmp se_object_validate
header_request:
 jsr se_doc_invalidate ;header DMA replaces bytes in DOC_LEAF8400..87FF
 lda se_gc_handle
 sta se_reu_logical
 lda #0
 sta se_reu_offset
 sta se_reu_offset+1
 sta se_reu_c64
 sta se_reu_length+1
 lda #>GP_HEADER
 sta se_reu_c64+1
 lda #GP_HEADER_SIZE
 sta se_reu_length
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
 jcc bad
 clc
 lda GP_IO_POINTER
 adc GP_IO_LENGTH
 sta se_reu_c64
 lda GP_IO_POINTER+1
 adc GP_IO_LENGTH+1
 jcs bad
 sta se_reu_c64+1
 cmp #$91
 bcc :+
 jne bad
 lda se_reu_c64
 cmp #$35
 jcs bad
:
 ; Intersecting8800..887F is forbidden; ending at8800 is legal.
 lda GP_IO_POINTER+1
 cmp #$88
 bcc @diag_end
 bne @view
 lda GP_IO_POINTER
 cmp #$80
 jcc bad
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
