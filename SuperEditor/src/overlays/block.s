.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "editor/api.inc"
.include "block/api.inc"
.include "clipboard/api.inc"
.include "hot/api.inc"
.include "history/api.inc"
.include "document/api.inc"
.include "document/math24.inc"
.include "object/api.inc"
.include "editor_file/api.inc"
.segment "CODE"
    OVL_BINDING
entry:
    lda se_overlay_frame
    cmp #FT_INIT
    jcs se_file_transport
    cmp #B_COPY_STEP ; direct private COPY slice, no C10 nesting
    jeq se_clip_overlay_copy_step
    cmp #B_COPY_BEGIN ; public wrapper compatibility, no setup mutation
    jeq se_clip_overlay_copy_begin
    cmp #B_PACKET
    jeq packet
    cmp #B_AFTER_COPY
    jeq prepare_edit
    cmp #B_SETUP
    beq :+
    lda #$51
    sec
    rts
:
    jsr se_view_init
    jcs return
    lda se_hot_pending
    ora se_hot_phase
    jne busy
    jsr se_clip_init
    jcs return
    jsr se_clip_validate
    jcs return
    jsr se_selection_range
    COPY24 se_sel_start,se_b_start
    COPY24 se_sel_length,se_b_delete
    lda #0
    sta se_b_position
    sta se_b_position+1
    sta se_b_position+2
    sta se_b_left
    sta se_b_left+1
    sta se_b_left+2
    sta se_b_mode
    lda se_b_command
    cmp #E_COPY
    beq copy
    cmp #E_CUT
    beq copy
    cmp #E_PASTE
    beq paste
    cmp #E_INSERT
    jne prepare_edit
    lda #1
    sta se_b_mode
    sta se_b_left
    jne prepare_edit
copy:
    COPY24 se_b_start,se_clip_position
    COPY24 se_b_delete,se_clip_span
    jsr se_clip_overlay_copy_begin
    bcs return
    cmp #0
    beq return
    lda #B_COPYING
    sta se_b_phase
    lda #1
    clc
return:
    rts
busy:
    lda #$51
    sec
    rts
paste:
    lda se_clip_busy
    bne busy
    lda se_clip_active
    beq return ;empty clipboard cannot delete a selection
    ldx #4
@token:
    lda se_clip_token,x
    sta se_b_token,x
    dex
    bpl @token
    lda se_clip_generation
    sta se_b_generation
    lda se_clip_generation+1
    sta se_b_generation+1
    lda se_clip_epoch
    sta se_b_epoch
    lda se_clip_epoch+1
    sta se_b_epoch+1
    lda #1
    sta se_b_clip_owned
    lda #2
    sta se_clip_busy
    sta se_b_mode
    COPY24 se_clip_length,se_b_left
prepare_edit:
    COPY24 se_b_start,se_doc_edit_position
    COPY24 se_b_delete,se_doc_edit_delete
    COPY24 se_b_left,se_doc_edit_insert
    COPY24 se_hot_caret,se_h_before_caret
    ADD24 se_b_start,se_b_left,se_h_after_caret
    lda #0
    sta se_h_group
    lda #B_BEGIN_HISTORY
    sta se_b_phase
    lda #1
    clc
    rts
packet:
    lda se_b_left+2
    ora se_b_left+1
    bne @full
    lda se_b_left
    cmp #129
    bcc @count
@full:
    lda #128
@count:
    sta se_b_count
    sta se_doc_count
    lda #0
    sta se_doc_count+1
    sta se_doc_c64
    lda #$80
    sta se_doc_c64+1
    lda se_b_mode
    cmp #1
    beq @byte
    jsr se_clip_validate
    jcs return
    ldx #4
@context:
    lda se_clip_token,x
    cmp se_b_token,x
    jne changed
    dex
    bpl @context
    lda se_clip_generation
    cmp se_b_generation
    jne changed
    lda se_clip_generation+1
    cmp se_b_generation+1
    jne changed
    DOC_TOKEN se_b_token
    COPY24 se_b_position,se_object_offset
    lda se_b_count
    sta se_object_length
    lda #0
    sta se_object_length+1
    sta se_object_c64
    lda #$80
    sta se_object_c64+1
    lda #1
    jsr se_object_copy
    jcs return
    jmp @advance
@byte:
    lda se_b_byte
    sta $8000
@advance:
    lda se_b_count
    sta se_b_temp
    lda #0
    sta se_b_temp+1
    sta se_b_temp+2
    ADD24 se_b_position,se_b_temp,se_b_position
    SUB24 se_b_left,se_b_temp,se_b_left
    lda #0
    clc
    rts
changed:
    lda #$52
    sec
    rts
.include "clipboard/copy_overlay.s"
