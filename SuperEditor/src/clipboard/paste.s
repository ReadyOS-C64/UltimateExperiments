.setcpu "6502"
.macpack longbranch
.include "clipboard/api.inc"
.include "object/api.inc"
.include "document/api.inc"
.include "document/math24.inc"
.segment "OBJECTS"
paste_left: .res 3
paste_pos: .res 3
paste_end: .res 3
paste_chunk: .res 3
paste_generation: .res 2
paste_error: .res 1
.segment "CODE"
; Position/span is replacement range. Empty clipboard never deletes selection.
se_clip_paste_begin:
    jsr se_clip_validate
    jcs @return
    lda se_clip_busy
    jne @busy
    jsr se_doc_validate
    jcs @return
    lda se_doc_busy
    jne @busy
    ADD24 se_clip_position,se_clip_span,paste_end
    jcs @range
    CMP24 paste_end,se_doc_length
    bcc @range_ok
    jne @range
@range_ok:
    lda se_clip_active
    beq @empty
    COPY24 se_clip_position,se_doc_edit_position
    COPY24 se_clip_span,se_doc_edit_delete
    COPY24 se_clip_length,se_doc_edit_insert
    jsr se_doc_splice_begin
    jcs @return
    lda #2
    sta se_clip_busy
    COPY24 se_clip_length,paste_left
    lda #0
    sta paste_pos
    sta paste_pos+1
    sta paste_pos+2
    lda se_clip_generation
    sta paste_generation
    lda se_clip_generation+1
    sta paste_generation+1
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
se_clip_paste_step:
    lda se_clip_busy
    cmp #2
    jne @state
    jsr se_clip_validate
    jcs paste_abort
    lda se_clip_generation
    cmp paste_generation
    jne @changed
    lda se_clip_generation+1
    cmp paste_generation+1
    jne @changed
    lda paste_left
    ora paste_left+1
    ora paste_left+2
    jeq @build
    COPY24 paste_left,paste_chunk
    lda paste_left+2
    bne @full_chunk
    lda paste_left+1
    cmp #4
    bcc @chunk
@full_chunk:
    lda #0
    sta paste_chunk
    sta paste_chunk+2
    lda #4
    sta paste_chunk+1
@chunk:
    DOC_TOKEN se_clip_token
    COPY24 paste_pos,se_object_offset
    lda #0
    sta se_object_c64
    lda #$80
    sta se_object_c64+1
    ldx #1
@request:
    lda paste_chunk,x
    sta se_object_length,x
    sta se_doc_count,x
    lda se_object_c64,x
    sta se_doc_c64,x
    dex
    bpl @request
    lda #1
    jsr se_object_copy
    jcs paste_abort
    jsr se_doc_splice_feed
    jcs paste_abort
    ADD24 paste_pos,paste_chunk,paste_pos
    SUB24 paste_left,paste_chunk,paste_left
    lda #1
    clc
    rts
@build:
    jsr se_doc_splice_step
    bcs paste_abort
    cmp #1
    beq @pending
    lda #0
    sta se_clip_busy
@pending:
    clc
    rts
@changed:
    lda #$52
    jmp paste_abort
@state:
    lda #$51
    sec
    rts
se_clip_paste_cancel:
    lda se_clip_busy
    beq @idle
    cmp #2
    bne @other_operation
    jsr se_doc_splice_cancel
@idle:
    lda #0
    sta se_clip_busy
    clc
    rts
@other_operation:
    lda #$51
    sec
    rts
paste_abort:
    sta paste_error
    jsr se_clip_paste_cancel
    lda paste_error
    sec
    rts
