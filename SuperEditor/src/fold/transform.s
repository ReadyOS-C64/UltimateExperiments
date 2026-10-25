.setcpu "6502"
.macpack longbranch
SE_FOLD_TRANSFORM_IMPLEMENTATION=1
.include "fold/transform.inc"
.include "object/api.inc"
.import se_reu_epoch,se_reu_map
.export se_ft_begin,se_ft_begin_log,se_ft_step,se_ft_cancel
.export se_ft_input,se_ft_output,se_ft_count,se_ft_length
.export se_ft_position,se_ft_delete,se_ft_insert,se_ft_busy,se_ft_error
.export se_ft_valid,se_ft_index,se_ft_written,se_ft_dropped,se_ft_changed
.export se_ft_new_length,se_ft_delete_end,se_ft_epoch,se_ft_bound,se_ft_record
.export se_ft_parents,se_ft_old_indices,se_ft_ends,se_ft_hidden,se_ft_last
.export se_ft_previous_depth,se_ft_disposition,se_ft_temp,se_ft_in_banks
.export se_ft_out_banks,se_ft_outer,se_ft_inner,se_ft_physical
.export se_ft_current_parent,se_ft_frame_end
.export se_ft_in_logical,se_ft_out_logical,se_ft_in_physical,se_ft_out_physical
.export se_ft_map_counts
.export se_ft_log_pointer,se_ft_log_count,se_ft_log_mode,se_ft_phase
.export se_ft_log_bound,se_ft_log_cursor,se_ft_log_event,se_ft_log_byte
.export se_ft_work_length,se_ft_final_length
.segment "FOLD_TRANSFORM"
se_ft_begin:
    lda se_ft_busy
    jne ft_busy
    lda #0
    sta se_ft_log_mode
    jmp ft_begin
se_ft_begin_log:
    lda se_ft_busy
    jne ft_busy
    lda #1
    sta se_ft_log_mode
ft_begin:
    lda #0
    sta se_ft_valid
    sta se_ft_error
    sta se_ft_index
    sta se_ft_index+1
    sta se_ft_written
    sta se_ft_written+1
    sta se_ft_dropped
    sta se_ft_dropped+1
    sta se_ft_disposition
    sta se_ft_changed
    SF_COPY se_ft_length,se_ft_work_length,3
    lda se_ft_log_mode
    beq @single
    jsr ft_log_admit
    jcs ft_fail
    jmp ft_count
@single:
    lda se_ft_delete
    ora se_ft_delete+1
    ora se_ft_delete+2
    ora se_ft_insert
    ora se_ft_insert+1
    ora se_ft_insert+2
    beq :+
    lda #1
:   sta se_ft_changed
    jsr ft_edit
    jcs ft_fail
    lda #FT_READ
    sta se_ft_phase
ft_count:
    lda se_ft_count+1
    cmp #$80
    jcc @tokens
    jne ft_bad
    lda se_ft_count
    jne ft_bad
@tokens:
    ldx #4
@distinct:
    lda se_ft_input,x
    cmp se_ft_output,x
    bne @admit
    dex
    bpl @distinct
    jmp ft_bad
@admit:
    jsr ft_objects
    jcs ft_fail
    lda #0
    jsr ft_maps
    jcs ft_fail
    ; Both logical objects may share a type, never a physical bank.
    lda #0
    sta se_ft_outer
@outer:
    lda se_ft_input
    asl
    asl
    asl
    asl
    clc
    adc se_ft_outer
    tax
    lda object_extents,x
    tax
    lda se_reu_map,x
    sta se_ft_physical
    lda #0
    sta se_ft_inner
@inner:
    lda se_ft_output
    asl
    asl
    asl
    asl
    clc
    adc se_ft_inner
    tax
    lda object_extents,x
    tax
    lda se_reu_map,x
    cmp se_ft_physical
    jeq ft_bad
    inc se_ft_inner
    lda se_ft_inner
    cmp se_ft_out_banks
    bcc @inner
    inc se_ft_outer
    lda se_ft_outer
    cmp se_ft_in_banks
    bcc @outer
    SF_COPY se_ft_input,se_ft_bound,FT_INPUT_SIZE
    SF_COPY se_ft_log_pointer,se_ft_log_bound,3
    lda se_ft_log_mode
    sta se_ft_log_bound+3
    SF_COPY se_reu_epoch,se_ft_epoch,2
    lda #1
    sta se_ft_busy
    clc
    rts
se_ft_step:
    lda se_ft_busy
    jeq ft_bad
    lda se_ft_log_mode
    cmp se_ft_log_bound+3
    jne ft_stale
    ldx #FT_INPUT_SIZE-1
    lda se_ft_log_mode
    beq @bound
    ldx #2
@log_bound:
    lda se_ft_log_pointer,x
    cmp se_ft_log_bound,x
    jne ft_stale
    dex
    bpl @log_bound
    ldx #14
@bound:
    lda se_ft_input,x
    cmp se_ft_bound,x
    jne ft_stale
    dex
    bpl @bound
    ldx #1
@epoch:
    lda se_reu_epoch,x
    cmp se_ft_epoch,x
    jne ft_stale
    dex
    bpl @epoch
    jsr ft_objects
    jcs ft_fail
    lda #1
    jsr ft_maps
    jcs ft_fail
    lda se_ft_phase
    cmp #FT_VALIDATE_LOG
    jeq ft_log_validate
    cmp #FT_APPLY
    jeq ft_log_apply
    cmp #FT_READ
    jne ft_bad
    lda se_ft_index
    cmp se_ft_count
    bne @read
    lda se_ft_index+1
    cmp se_ft_count+1
    bne @read
    lda se_ft_log_mode
    beq @complete
    SF_COPY se_ft_final_length,se_ft_new_length,3
@complete:
    lda #0
    sta se_ft_busy
    sta se_ft_error
    lda #1
    sta se_ft_valid
    lda #0
    clc
    rts
@read:
    SF_COPY se_ft_input,se_object_id,5
    SF_COPY se_ft_index,se_object_offset,2
    jsr ft_offset
    lda #1
    jsr se_object_copy
    jcs ft_fail
    jsr ft_record_check
    jcs ft_fail
    lda #0
    sta se_ft_disposition
    ; An already dropped parent makes its complete subtree ineligible.
    lda se_ft_record+SF_DEPTH
    beq ft_record_mode
    asl
    tax
    lda se_ft_parents-2,x
    and se_ft_parents-1,x
    cmp #$FF
    jeq ft_drop
ft_record_mode:
    lda se_ft_log_mode
    beq ft_transform
    SF_COPY se_ft_log_pointer,se_ft_log_cursor,2
    SF_COPY se_ft_length,se_ft_work_length,3
    lda #0
    sta se_ft_log_event
    lda #FT_APPLY
    sta se_ft_phase
    jmp ft_pending
ft_transform:
    ; Deletion intersects opener iff p<hidden and q>summary. A pure insert
    ; exactly at summary is before the fold; strictly inside opener is unsafe.
    lda se_ft_delete
    ora se_ft_delete+1
    ora se_ft_delete+2
    beq @insertion
    SF_GE se_ft_position,se_ft_record+SF_HIDDEN,@end
    SF_GE se_ft_record+SF_SUMMARY,se_ft_delete_end,@end
    jmp ft_drop
@insertion:
    lda se_ft_insert
    ora se_ft_insert+1
    ora se_ft_insert+2
    beq @end
    SF_GE se_ft_record+SF_SUMMARY,se_ft_position,@end
    SF_LT se_ft_position,se_ft_record+SF_HIDDEN,ft_drop
@end:
    ; [p,q) crossing the exclusive END invalidates identity. q==end is
    ; a body deletion; potential closure changes require fresh parse anyway.
    SF_GE se_ft_position,se_ft_record+SF_END,@transform
    SF_LT se_ft_record+SF_END,se_ft_delete_end,ft_drop
@transform:
    ; SUMMARY is right-affine; HIDDEN/END left-affine for pure insertion.
    SF_LT se_ft_record+SF_SUMMARY,se_ft_position,@hidden
    ldy #SF_SUMMARY
    jsr ft_shift
    jcs ft_drop
    lda se_ft_disposition
    ora #FT_SHIFTED
    sta se_ft_disposition
@hidden:
    SF_GE se_ft_position,se_ft_record+SF_HIDDEN,@end_shift
    ldy #SF_HIDDEN
    jsr ft_shift
    jcs ft_drop
@end_shift:
    SF_GE se_ft_position,se_ft_record+SF_END,@geometry
    ldy #SF_END
    jsr ft_shift
    jcs ft_drop
    lda se_ft_disposition
    ora #FT_CONTAINING
    sta se_ft_disposition
@geometry:
    SF_GE se_ft_record+SF_SUMMARY,se_ft_record+SF_HIDDEN,ft_drop
    SF_GE se_ft_record+SF_HIDDEN,se_ft_record+SF_END,ft_drop
    SF_LT se_ft_new_length,se_ft_record+SF_END,ft_drop
    lda se_ft_log_mode
    beq ft_write
    SF_COPY se_ft_new_length,se_ft_work_length,3
    jsr ft_log_advance
    jcc ft_pending
ft_write:
    ; Parent identity uses the dense output index, never the old ordinal.
    lda se_ft_record+SF_DEPTH
    beq @root
    asl
    tax
    lda se_ft_parents-2,x
    sta se_ft_record+SF_PARENT
    lda se_ft_parents-1,x
    sta se_ft_record+SF_PARENT+1
    jmp @parent_saved
@root:
    lda #$FF
    sta se_ft_record+SF_PARENT
    sta se_ft_record+SF_PARENT+1
@parent_saved:
    lda se_ft_record+SF_DEPTH
    asl
    tax
    lda se_ft_written
    sta se_ft_parents,x
    lda se_ft_written+1
    sta se_ft_parents+1,x
    lda se_ft_record+SF_FLAGS
    and #SF_COLLAPSED
    sta se_ft_record+SF_FLAGS
    lda #0
    ldx #9
@clear:
    ; caret14..16, motion21..24 and reserved25..31: no restoration hint.
    sta se_ft_record+21,x
    dex
    bpl @clear
    sta se_ft_record+31
    sta se_ft_record+SF_CARET
    sta se_ft_record+SF_CARET+1
    sta se_ft_record+SF_CARET+2
    SF_COPY se_ft_output,se_object_id,5
    SF_COPY se_ft_written,se_object_offset,2
    jsr ft_offset
    lda #0
    jsr se_object_copy
    jcs ft_fail
    inc se_ft_written
    bne ft_next
    inc se_ft_written+1
    jmp ft_next
ft_drop:
    lda se_ft_record+SF_DEPTH
    asl
    tax
    lda #$FF
    sta se_ft_parents,x
    sta se_ft_parents+1,x
    inc se_ft_dropped
    bne :+
    inc se_ft_dropped+1
:   lda #FT_INVALID
    sta se_ft_disposition
ft_next:
    inc se_ft_index
    bne :+
    inc se_ft_index+1
:   lda #FT_READ
    sta se_ft_phase
ft_pending:
    lda #1
    clc
    rts
se_ft_cancel:
    lda #0
    sta se_ft_busy
    sta se_ft_valid
    lda #SF_CANCEL
    sta se_ft_error
    lda #0
    clc
    rts
ft_busy:
    lda #SF_BUSY
    sec
    rts
ft_stale:
    lda #SF_STALE
    jmp ft_fail
ft_bad:
    lda #SF_BAD
ft_fail:
    sta se_ft_error
    lda #0
    sta se_ft_busy
    sta se_ft_valid
    lda se_ft_error
    sec
    rts

; Subtract deleted length then add inserted length to one known unaffected
; anchor. Under/overflow drops the hint; canonical length already admitted.
ft_shift:
    sec
    lda se_ft_record,y
    sbc se_ft_delete
    sta se_ft_record,y
    iny
    lda se_ft_record,y
    sbc se_ft_delete+1
    sta se_ft_record,y
    iny
    lda se_ft_record,y
    sbc se_ft_delete+2
    sta se_ft_record,y
    bcc @bad
    dey
    dey
    clc
    lda se_ft_record,y
    adc se_ft_insert
    sta se_ft_record,y
    iny
    lda se_ft_record,y
    adc se_ft_insert+1
    sta se_ft_record,y
    iny
    lda se_ft_record,y
    adc se_ft_insert+2
    sta se_ft_record,y
    rts
@bad:
    sec
    rts
ft_offset:
    lda #0
    sta se_object_offset+2
    ldx #5
@shift:
    asl se_object_offset
    rol se_object_offset+1
    rol se_object_offset+2
    dex
    bne @shift
    lda #<se_ft_record
    sta se_object_c64
    lda #>se_ft_record
    sta se_object_c64+1
    lda #32
    sta se_object_length
    lda #0
    sta se_object_length+1
    rts

; Full token/type/capacity guards. Both committed sizes must cover inputcount
; slots. Candidate is caller-staged capacity; no resize/free/allocate here.
ft_objects:
    lda se_ft_count
    sta se_ft_temp
    lda se_ft_count+1
    sta se_ft_temp+1
    lda #0
    sta se_ft_temp+2
    ldx #5
@size:
    asl se_ft_temp
    rol se_ft_temp+1
    rol se_ft_temp+2
    dex
    bne @size
    SF_COPY se_ft_input,se_object_id,5
    jsr ft_object
    bcs @return
    lda object_banks,x
    sta se_ft_in_banks
    SF_COPY se_ft_output,se_object_id,5
    jsr ft_object
    bcs @return
    lda object_banks,x
    sta se_ft_out_banks
    clc
@return:
    rts
ft_object:
    jsr se_object_validate
    bcs @return
    lda object_owner,x
    cmp #SF_OBJECT_TYPE
    bne @bad
    lda object_size_hi,x
    cmp se_ft_temp+2
    bcc @bad
    bne @ok
    lda object_size_mid,x
    cmp se_ft_temp+1
    bcc @bad
    bne @ok
    lda object_size_lo,x
    cmp se_ft_temp
    bcc @bad
@ok:
    clc
@return:
    rts
@bad:
    lda #SF_BAD
    sec
    rts

; Freeze logical AND physical extents. Same-type bank ownership alone cannot
; detect an extent/map reassignment to a different46 object between slices.
.macro FT_MAP token,banks,logical,physical
    .local loop,verify_logical,map,verify_physical,next
    lda #0
    sta se_ft_outer
loop:
    lda token
    asl
    asl
    asl
    asl
    clc
    adc se_ft_outer
    tax
    lda object_extents,x
    sta se_ft_physical
    ldy se_ft_outer
    lda se_ft_inner
    bne verify_logical
    lda se_ft_physical
    sta logical,y
    jmp map
verify_logical:
    lda se_ft_physical
    cmp logical,y
    jne ft_stale
map:
    ldx se_ft_physical
    lda se_reu_map,x
    sta se_ft_physical
    lda se_ft_inner
    bne verify_physical
    lda se_ft_physical
    sta physical,y
    jmp next
verify_physical:
    lda se_ft_physical
    cmp physical,y
    jne ft_stale
next:
    inc se_ft_outer
    lda se_ft_outer
    cmp banks
    bcc loop
.endmacro
ft_maps:
    sta se_ft_inner
    bne @compare
    lda se_ft_in_banks
    sta se_ft_map_counts
    lda se_ft_out_banks
    sta se_ft_map_counts+1
    jmp @maps
@compare:
    lda se_ft_in_banks
    cmp se_ft_map_counts
    jne ft_stale
    lda se_ft_out_banks
    cmp se_ft_map_counts+1
    jne ft_stale
@maps:
    FT_MAP se_ft_input,se_ft_in_banks,se_ft_in_logical,se_ft_in_physical
    FT_MAP se_ft_output,se_ft_out_banks,se_ft_out_logical,se_ft_out_physical
    clc
    rts

; Validate original32B record and preorder one slice at a time. Stacks contain
; ORIGINAL geometry/indices; remapped output ordinals have their own16slots.
ft_record_check:
    SF_GE se_ft_record+SF_SUMMARY,se_ft_record+SF_HIDDEN,@bad
    SF_GE se_ft_record+SF_HIDDEN,se_ft_record+SF_END,@bad
    SF_LT se_ft_length,se_ft_record+SF_END,@bad
    lda se_ft_record+SF_KIND
    cmp #SF_HEADING
    jcc @bad
    cmp #SF_REGION+1
    jcs @bad
    lda se_ft_record+SF_FLAGS
    and #$FC
    jne @bad
    lda se_ft_record+SF_FLAGS
    and #SF_SAVED
    beq @level
    lda se_ft_record+SF_FLAGS
    and #SF_COLLAPSED
    jeq @bad
    SF_LT se_ft_record+SF_CARET,se_ft_record+SF_HIDDEN,@bad
    SF_GE se_ft_record+SF_CARET,se_ft_record+SF_END,@bad
@level:
    lda se_ft_record+SF_KIND
    cmp #SF_HEADING
    bne @other
    lda se_ft_record+SF_LEVEL
    jeq @bad
    cmp #7
    jcs @bad
    bcc @reserved
@other:
    lda se_ft_record+SF_LEVEL
    jne @bad
@reserved:
    ldx #31
@zero:
    lda se_ft_record,x
    jne @bad
    dex
    cpx #24
    bne @zero
    lda se_ft_record+SF_DEPTH
    cmp #16
    jcs @bad
    lda se_ft_index
    ora se_ft_index+1
    beq @first
    SF_GE se_ft_last,se_ft_record+SF_SUMMARY,@bad
    lda se_ft_previous_depth
    clc
    adc #1
    cmp se_ft_record+SF_DEPTH
    jcc @bad
    lda se_ft_record+SF_DEPTH
    cmp se_ft_previous_depth
    bcc @sibling
    beq @sibling
    bne @parent
@first:
    lda se_ft_record+SF_DEPTH
    jne @bad
    beq @parent
@sibling:
    lda se_ft_record+SF_DEPTH
    asl
    clc
    adc se_ft_record+SF_DEPTH
    tax
    lda se_ft_ends+2,x
    cmp se_ft_record+SF_SUMMARY+2
    bcc @parent
    jne @bad
    lda se_ft_ends+1,x
    cmp se_ft_record+SF_SUMMARY+1
    bcc @parent
    jne @bad
    lda se_ft_ends,x
    cmp se_ft_record+SF_SUMMARY
    jcc @parent
    jne @bad
@parent:
    lda se_ft_record+SF_DEPTH
    beq @root
    asl
    tax
    lda se_ft_old_indices-2,x
    cmp se_ft_record+SF_PARENT
    jne @bad
    lda se_ft_old_indices-1,x
    cmp se_ft_record+SF_PARENT+1
    jne @bad
    lda se_ft_record+SF_DEPTH
    sec
    sbc #1
    sta se_ft_temp
    asl
    clc
    adc se_ft_temp
    tax
    lda se_ft_record+SF_SUMMARY+2
    cmp se_ft_hidden+2,x
    jcc @bad
    bne @end
    lda se_ft_record+SF_SUMMARY+1
    cmp se_ft_hidden+1,x
    jcc @bad
    bne @end
    lda se_ft_record+SF_SUMMARY
    cmp se_ft_hidden,x
    jcc @bad
@end:
    lda se_ft_ends+2,x
    cmp se_ft_record+SF_END+2
    jcc @bad
    bne @save
    lda se_ft_ends+1,x
    cmp se_ft_record+SF_END+1
    jcc @bad
    bne @save
    lda se_ft_ends,x
    cmp se_ft_record+SF_END
    jcc @bad
    jmp @save
@root:
    lda se_ft_record+SF_PARENT
    and se_ft_record+SF_PARENT+1
    cmp #$FF
    jne @bad
@save:
    SF_COPY se_ft_record+SF_SUMMARY,se_ft_last,3
    lda se_ft_record+SF_DEPTH
    sta se_ft_previous_depth
    asl
    tax
    lda se_ft_index
    sta se_ft_old_indices,x
    lda se_ft_index+1
    sta se_ft_old_indices+1,x
    txa
    clc
    adc se_ft_record+SF_DEPTH
    tax
    ldy #0
@stack:
    lda se_ft_record+SF_END,y
    sta se_ft_ends,x
    lda se_ft_record+SF_HIDDEN,y
    sta se_ft_hidden,x
    inx
    iny
    cpy #3
    bne @stack
    clc
    rts
@bad:
    lda #SF_BAD
    sec
    rts

; Checked24-bit canonical edit length arithmetic.
ft_edit:
    ; Validate p<=length and p+delete<=length without24-bit wrapping.
    SF_LT se_ft_work_length,se_ft_position,ft_bad
    clc
    lda se_ft_position
    adc se_ft_delete
    sta se_ft_delete_end
    lda se_ft_position+1
    adc se_ft_delete+1
    sta se_ft_delete_end+1
    lda se_ft_position+2
    adc se_ft_delete+2
    sta se_ft_delete_end+2
    jcs ft_bad
    SF_LT se_ft_work_length,se_ft_delete_end,ft_bad
    sec
    lda se_ft_work_length
    sbc se_ft_delete
    sta se_ft_new_length
    lda se_ft_work_length+1
    sbc se_ft_delete+1
    sta se_ft_new_length+1
    lda se_ft_work_length+2
    sbc se_ft_delete+2
    sta se_ft_new_length+2
    clc
    lda se_ft_new_length
    adc se_ft_insert
    sta se_ft_new_length
    lda se_ft_new_length+1
    adc se_ft_insert+1
    sta se_ft_new_length+1
    lda se_ft_new_length+2
    adc se_ft_insert+2
    sta se_ft_new_length+2
    jcs ft_bad
    clc
    rts

; No ZP: bounded host log is addressed through eight fixed pages. The caller
; guarantees log bytes immutable; pointer/count/mode are separately bound.
ft_log_admit:
    lda se_ft_log_count
    jeq ft_bad
    cmp #113
    jcs ft_bad
    lda se_ft_log_pointer+1
    cmp #$80
    jcc ft_bad
    cmp #$88
    jcs ft_bad
    lda se_ft_log_count
    sta se_ft_temp
    lda #0
    sta se_ft_temp+1
    ldx #3
@nine:
    asl se_ft_temp
    rol se_ft_temp+1
    dex
    bne @nine
    clc
    lda se_ft_temp
    adc se_ft_log_count
    sta se_ft_temp
    lda se_ft_temp+1
    adc #0
    sta se_ft_temp+1
    clc
    lda se_ft_temp
    adc se_ft_log_pointer
    sta se_ft_temp
    lda se_ft_temp+1
    adc se_ft_log_pointer+1
    cmp #$88
    bcc @admit
    jne ft_bad
    lda se_ft_temp
    jne ft_bad
@admit:
    SF_COPY se_ft_log_pointer,se_ft_log_cursor,2
    SF_COPY se_ft_length,se_ft_new_length,3
    lda #0
    sta se_ft_log_event
    lda #FT_VALIDATE_LOG
    sta se_ft_phase
    clc
    rts
ft_log_validate:
    jsr ft_log_load
    jsr ft_edit
    jcs ft_fail
    lda se_ft_delete
    ora se_ft_delete+1
    ora se_ft_delete+2
    ora se_ft_insert
    ora se_ft_insert+1
    ora se_ft_insert+2
    beq :+
    lda #1
    sta se_ft_changed
:   SF_COPY se_ft_new_length,se_ft_work_length,3
    jsr ft_log_advance
    jcc ft_pending
    SF_COPY se_ft_new_length,se_ft_final_length,3
    lda #FT_READ
    sta se_ft_phase
    jmp ft_pending
ft_log_apply:
    jsr ft_log_load
    jsr ft_edit
    jcs ft_fail
    jmp ft_transform
ft_log_advance:
    clc
    lda se_ft_log_cursor
    adc #9
    sta se_ft_log_cursor
    lda se_ft_log_cursor+1
    adc #0
    sta se_ft_log_cursor+1
    inc se_ft_log_event
    lda se_ft_log_event
    cmp se_ft_log_count
    rts
ft_log_load:
    ldx #8
@byte:
    stx se_ft_log_byte
    txa
    clc
    adc se_ft_log_cursor
    tay
    lda se_ft_log_cursor+1
    adc #0
    tax
    jsr ft_host_byte
    ldx se_ft_log_byte
    sta se_ft_position,x
    dex
    bpl @byte
    rts
ft_host_byte:
    cpx #$80
    beq @p0
    cpx #$81
    beq @p1
    cpx #$82
    beq @p2
    cpx #$83
    beq @p3
    cpx #$84
    beq @p4
    cpx #$85
    beq @p5
    cpx #$86
    beq @p6
    lda $8700,y
    rts
@p0:lda $8000,y
    rts
@p1:lda $8100,y
    rts
@p2:lda $8200,y
    rts
@p3:lda $8300,y
    rts
@p4:lda $8400,y
    rts
@p5:lda $8500,y
    rts
@p6:lda $8600,y
    rts
