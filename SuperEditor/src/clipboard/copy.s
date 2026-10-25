.setcpu "6502"
.ifndef CLIP_COPY_CODE
.macpack longbranch
.include "clipboard/api.inc"
.include "object/api.inc"
.include "document/api.inc"
.include "document/math24.inc"
.endif
.include "clipboard/frames/copy.inc"
.ifndef CLIP_COPY_CLEANUP_ONLY
.segment "CODE"
; Request position/span24 is unchanged. A1 started, A0 checked empty no-op.
se_clip_copy_begin:
    jsr se_clip_validate
    jcs @return
    lda se_clip_busy
    jne @busy
    jsr se_doc_validate
    jcs @return
    lda se_doc_busy
    jne @busy
    ADD24 se_clip_position,se_clip_span,copy_end
    jcs @range
    CMP24 copy_end,se_doc_length
    bcc @range_ok
    jne @range
@range_ok:
    lda se_clip_span
    ora se_clip_span+1
    ora se_clip_span+2
    jeq @empty
    lda #0
    sta copy_has_object
    sta copy_has_lease
    jsr se_doc_read_acquire
    jcs @return
    lda #1
    sta copy_has_lease
    lda se_doc_epoch
    sta copy_epoch
    lda se_doc_epoch+1
    sta copy_epoch+1
    lda se_doc_generation
    sta copy_generation
    lda se_doc_generation+1
    sta copy_generation+1
    ldx se_clip_span+2
    lda se_clip_span
    ora se_clip_span+1
    beq @banks
    inx
@banks:
    lda #5
    jsr se_object_create
    jcs copy_abort
    ldy #4
@token:
    lda se_object_id,y
    sta copy_token,y
    dey
    bpl @token
    lda #1
    sta copy_has_object
    sta se_clip_busy
    COPY24 se_clip_position,copy_pos
    COPY24 se_clip_span,copy_left
    COPY24 se_clip_span,copy_size
    lda #0
    sta copy_written
    sta copy_written+1
    sta copy_written+2
    lda #1
    clc
    rts
@empty:
    lda #0
    clc
@return:
    rts
@busy:
    lda #$51
    sec
    rts
@range:
    lda #$32
    sec
    rts

; At most1024 source bytes and8 source descriptors per step. Old clipboard stays readable/owned until
; candidate resize and old-object release succeed at the final safe point.
se_clip_copy_step:
    lda se_clip_busy
    cmp #1
    jne @state
    jsr se_clip_validate
    jcs copy_abort
    jsr se_doc_validate
    jcs copy_abort
    lda se_doc_generation
    cmp copy_generation
    jne @changed
    lda se_doc_generation+1
    cmp copy_generation+1
    jne @changed
    COPY24 copy_left,copy_chunk
    lda copy_left+2
    bne @full_chunk
    lda copy_left+1
    cmp #4
    bcc @chunk
@full_chunk:
    lda #0
    sta copy_chunk
    sta copy_chunk+2
    lda #4
    sta copy_chunk+1
@chunk:
    COPY24 copy_pos,se_doc_offset
    ldx #1
@request:
    lda copy_chunk,x
    sta se_doc_count,x
    dex
    bpl @request
    lda #0
    sta se_doc_c64
    lda #$80
    sta se_doc_c64+1
    jsr se_doc_read_some
    jcs copy_abort
    lda se_doc_read_done
    sta copy_chunk
    lda se_doc_read_done+1
    sta copy_chunk+1
    DOC_TOKEN copy_token
    COPY24 copy_written,se_object_offset
    ldx #1
@write_request:
    lda copy_chunk,x
    sta se_object_length,x
    lda se_doc_c64,x
    sta se_object_c64,x
    dex
    bpl @write_request
    lda #0
    jsr se_object_copy
    jcs copy_abort
    ADD24 copy_written,copy_chunk,copy_written
    ADD24 copy_pos,copy_chunk,copy_pos
    SUB24 copy_left,copy_chunk,copy_left
    lda copy_left
    ora copy_left+1
    ora copy_left+2
    beq @complete
    lda #1
    clc
    rts
@complete:
    DOC_TOKEN copy_token
    COPY24 copy_size,se_object_offset
    jsr se_object_resize
    jcs copy_abort
    lda se_clip_active
    beq @publish
    DOC_TOKEN se_clip_token
    jsr se_object_release
    jcs copy_abort
@publish:
    ldy #4
@new_token:
    lda copy_token,y
    sta se_clip_token,y
    dey
    bpl @new_token
    COPY24 copy_size,se_clip_length
    lda #1
    sta se_clip_active
    inc se_clip_generation
    bne :+
    inc se_clip_generation+1
:
    lda #0
    sta copy_has_object ; now current-owned, never cancel-free this token
    jsr copy_cleanup
    lda #0
    clc
    rts
@changed:
    lda #$52
    jmp copy_abort
@state:
    lda #$51
    sec
    rts

.endif ; BEGIN/STEP absent in resident cleanup profile

.ifndef CLIP_COPY_CODE
.segment "CODE"
.ifdef CLIP_COPY_CLEANUP_ONLY
.export se_clip_copy_abort, se_clip_copy_cleanup
.endif
se_clip_copy_cancel:
    lda se_clip_busy
    beq @idle
    cmp #1
    bne @other_operation
    jsr copy_cleanup
@idle:
    lda #0
    clc
    rts
@other_operation:
    lda #$51
    sec
    rts
.ifdef CLIP_COPY_CLEANUP_ONLY
se_clip_copy_abort:
.endif
copy_abort:
    sta copy_error
    jsr copy_cleanup
    lda copy_error
    sec
    rts
.ifdef CLIP_COPY_CLEANUP_ONLY
se_clip_copy_cleanup:
.endif
copy_cleanup:
    lda copy_has_object
    beq @lease
    DOC_TOKEN copy_token
    jsr se_object_release ; stale epoch can only refuse; never frees a new owner
    lda #0
    sta copy_has_object
@lease:
    lda copy_has_lease
    beq @done
    lda copy_epoch
    cmp se_doc_epoch
    bne @forget
    lda copy_epoch+1
    cmp se_doc_epoch+1
    bne @forget
    jsr se_doc_read_release
@forget:
    lda #0
    sta copy_has_lease
@done:
    lda #0
    sta se_clip_busy
    rts

.endif ; cleanup always resident in overlay profile
