.setcpu "6502"
.macpack longbranch
.ifdef EDITOR_BINDINGS
    .import se_gtt_certify
    .include "editor-api.inc"
    .include "style/api.inc"
.else
    .include "hot-api.inc"
.endif
.include "hot/api.inc"
.include "document/api.inc"
.include "object/api.inc"
.include "document/math24.inc"
.include "history/api.inc"
.ifdef EDITOR_BINDINGS
.include "render/api.inc"
.endif
.segment "CODE"
    OVL_BINDING
entry:
    lda se_overlay_frame
    sta se_hot_command
    cmp #W_LOAD
    jeq load
    jsr valid
    jcs return
    lda se_hot_command
    cmp #W_STEP
    jeq load_step
    lda se_hot_phase
    cmp #2
    bne :+
    lda se_hot_command
    cmp #W_PACKET
    jeq packet
    cmp #W_COMMIT
    jeq commit
    jmp busy
:
    lda se_hot_phase
    jne busy
    lda se_hot_ready
    jeq state
    lda se_hot_command
    cmp #W_INSERT
    jeq insert
    cmp #W_BACK
    jeq backspace
    cmp #W_DELETE
    jeq delete
    cmp #W_LEFT
    jeq left
    cmp #W_RIGHT
    jeq right
    cmp #W_PREPARE
    jeq prepare
    cmp #W_CLOSE
    jne state
    lda se_hot_pending
    jne busy
    sta se_hot_ready
okay:
    lda #0
    clc
return:
    rts
pending:
    lda #1
    clc
    rts
state:
    lda #$70
    sec
    rts
busy:
    lda #$71
    sec
    rts
boundary:
    lda #$72
    sec
    rts
full:
    lda #$73
    sec
    rts
context:
    lda #$74
    sec
    rts
; Validate every continuation against full source identity and generation.
.include "hot/validate.s"
.ifndef EDITOR_BINDINGS
.include "hot/cold/load.s"
.else
load:
load_step:
prepare:
packet:
    lda #32 ;R32: one cold job, never an ordinary per-key observer swap
    ldx #0
    jmp se_overlay_call
.endif
caret:
    lda se_hot_left
    sta se_hot_tmp
    lda se_hot_left+1
    sta se_hot_tmp+1
    lda #0
    sta se_hot_tmp+2
    ADD24 se_hot_base,se_hot_tmp,se_hot_caret
.ifdef EDITOR_BINDINGS
.endif
    jmp okay
remember:
    lda se_hot_pending
    bne @done
    COPY24 se_hot_caret,se_hot_before
@done:
    rts
; Bound unchanged prefix/suffix before a one-byte mutation (A=deleted count).
mark:
    sta se_hot_delete
.ifdef EDITOR_BINDINGS
.endif
.ifdef EDITOR_BINDINGS
    jsr se_gec_capture
    jsr se_gtt_certify
    jsr render_damage
.endif
    sec
    lda se_hot_length
    sbc se_hot_left
    sta se_hot_tmp
    lda se_hot_length+1
    sbc se_hot_left+1
    sta se_hot_tmp+1
    sec
    lda se_hot_tmp
    sbc se_hot_delete
    sta se_hot_tmp
    lda se_hot_tmp+1
    sbc #0
    sta se_hot_tmp+1
    lda se_hot_pending
    bne @prefix
    lda se_hot_left
    sta se_hot_prefix
    lda se_hot_left+1
    sta se_hot_prefix+1
    lda se_hot_tmp
    sta se_hot_suffix
    lda se_hot_tmp+1
    sta se_hot_suffix+1
    jmp @done
@prefix:
    lda se_hot_left+1
    cmp se_hot_prefix+1
    bcc @set_prefix
    bne @suffix
    lda se_hot_left
    cmp se_hot_prefix
    bcs @suffix
@set_prefix:
    lda se_hot_left
    sta se_hot_prefix
    lda se_hot_left+1
    sta se_hot_prefix+1
@suffix:
    lda se_hot_tmp+1
    cmp se_hot_suffix+1
    bcc @set_suffix
    bne @done
    lda se_hot_tmp
    cmp se_hot_suffix
    bcs @done
@set_suffix:
    lda se_hot_tmp
    sta se_hot_suffix
    lda se_hot_tmp+1
    sta se_hot_suffix+1
@done:
    lda #1
    sta se_hot_pending
    rts
insert:
    jsr insert_quota
    jcs return
    lda se_hot_left
    cmp se_hot_right
    bne @space
    lda se_hot_left+1
    cmp se_hot_right+1
    jeq full
@space:
    jsr remember
    lda #0
    jsr mark
    lda se_hot_left
    sta se_hot_ptr
    lda se_hot_left+1
    clc
    adc #>HOT_FIRST
    sta se_hot_ptr+1
    ldy #0
    lda se_hot_byte
    sta (se_hot_ptr),y
    inc se_hot_left
    bne :+
    inc se_hot_left+1
:
    inc se_hot_length
    bne :+
    inc se_hot_length+1
:
    jmp edited
backspace:
    lda se_hot_left
    ora se_hot_left+1
    jeq boundary
    lda #2
    jsr change_quota
    jcs return
    jsr remember
    jsr left
    jmp remove
 delete:
    lda se_hot_right+1
    cmp #8
    jne @exists
    lda se_hot_right
    jeq boundary
@exists:
    lda #1
    jsr change_quota
    jcs return
    jsr remember
remove:
    lda #1
    jsr mark
    inc se_hot_right
    bne :+
    inc se_hot_right+1
:
    lda se_hot_length
    bne :+
    dec se_hot_length+1
:
    dec se_hot_length
edited:
.ifdef EDITOR_BINDINGS
    jsr lrv_plain_edit
.endif
    jmp caret
left:
    lda se_hot_left
    ora se_hot_left+1
    jeq boundary
    lda se_hot_left
    bne :+
    dec se_hot_left+1
:
    dec se_hot_left
    lda se_hot_right
    bne :+
    dec se_hot_right+1
:
    dec se_hot_right
    lda se_hot_left
    sta se_hot_ptr
    lda se_hot_left+1
    clc
    adc #>HOT_FIRST
    sta se_hot_ptr+1
    lda se_hot_right
    sta se_hot_packet
    lda se_hot_right+1
    clc
    adc #>HOT_FIRST
    sta se_hot_packet+1
    ldy #0
    lda (se_hot_ptr),y
    sta (se_hot_packet),y
    jmp caret
right:
    lda se_hot_right+1
    cmp #8
    jne @exists
    lda se_hot_right
    jeq boundary
@exists:
    lda se_hot_left
    sta se_hot_packet
    lda se_hot_left+1
    clc
    adc #>HOT_FIRST
    sta se_hot_packet+1
    lda se_hot_right
    sta se_hot_ptr
    lda se_hot_right+1
    clc
    adc #>HOT_FIRST
    sta se_hot_ptr+1
    ldy #0
    lda (se_hot_ptr),y
    sta (se_hot_packet),y
    inc se_hot_left
    bne :+
    inc se_hot_left+1
:
    inc se_hot_right
    bne :+
    inc se_hot_right+1
:
    jmp caret
.ifndef EDITOR_BINDINGS
.include "hot/cold/prepare.s"
.endif
commit:
.ifdef EDITOR_BINDINGS
    jsr render_commit
.endif
    lda se_doc_generation
    sta se_hot_generation
    lda se_doc_generation+1
    sta se_hot_generation+1
    lda se_hot_length
    sta se_hot_old_length
    lda se_hot_length+1
    sta se_hot_old_length+1
    lda #0
    sta se_hot_pending
    sta se_hot_phase
    sta se_hot_fault
    jmp okay

; Admit before remember/mark, even when a full gap would otherwise flush.
; Merged length must be below the original-object declared document quota.
; No canonical/gap/render/journal state is changed before admission.
insert_quota:
    sec
    lda se_doc_length
    sbc se_hot_old_length
    sta se_hot_tmp
    lda se_doc_length+1
    sbc se_hot_old_length+1
    sta se_hot_tmp+1
    lda se_doc_length+2
    sbc #0
    sta se_hot_tmp+2
    clc
    lda se_hot_tmp
    adc se_hot_length
    sta se_hot_tmp
    lda se_hot_tmp+1
    adc se_hot_length+1
    sta se_hot_tmp+1
    lda se_hot_tmp+2
    adc #0
    sta se_hot_tmp+2
    bcs quota_full
    DOC_TOKEN se_hot_original
    jsr se_object_validate
    bcs quota_return
    lda se_hot_tmp+2
    cmp object_banks,x
    bcs quota_full
    lda #0
    jmp change_quota
quota_full:
    lda #$32
    sec
quota_return:
    rts
quota_ok:
    clc
    rts
; A0 insert,A1 delete,A2 backspace. Only scratch changes before admission.
; Predict the exact conservative prefix/suffix interval used by PREPARE.
; Its inserted bytes must fit the append object before any local mutation.
; A disjoint deletion may need append bytes for the retained middle.
; Use existing target/count/tmp scratch; no resident state or new ZP.
change_quota:
    sta se_hot_delete
    lda se_hot_left
    sta se_hot_target
    lda se_hot_left+1
    sta se_hot_target+1
    lda se_hot_delete
    cmp #2
    bne @position
    lda se_hot_target
    bne :+
    dec se_hot_target+1
:
    dec se_hot_target
@position:
    sec
    lda se_hot_length
    sbc se_hot_target
    sta se_hot_count
    lda se_hot_length+1
    sbc se_hot_target+1
    sta se_hot_count+1
    lda se_hot_delete
    beq @edges
    lda se_hot_count
    bne :+
    dec se_hot_count+1
:
    dec se_hot_count
@edges:
    lda se_hot_pending
    beq @span
    lda se_hot_target+1
    cmp se_hot_prefix+1
    bcc @suffix
    bne @prefix
    lda se_hot_target
    cmp se_hot_prefix
    bcc @suffix
@prefix:
    lda se_hot_prefix
    sta se_hot_target
    lda se_hot_prefix+1
    sta se_hot_target+1
@suffix:
    lda se_hot_count+1
    cmp se_hot_suffix+1
    bcc @span
    bne @set_suffix
    lda se_hot_count
    cmp se_hot_suffix
    bcc @span
@set_suffix:
    lda se_hot_suffix
    sta se_hot_count
    lda se_hot_suffix+1
    sta se_hot_count+1
@span:
    sec
    lda se_hot_length
    sbc se_hot_target
    sta se_hot_tmp
    lda se_hot_length+1
    sbc se_hot_target+1
    sta se_hot_tmp+1
    sec
    lda se_hot_tmp
    sbc se_hot_count
    sta se_hot_tmp
    lda se_hot_tmp+1
    sbc se_hot_count+1
    sta se_hot_tmp+1
    lda #0
    sta se_hot_tmp+2
    lda se_hot_delete
    beq @insert
    lda se_hot_tmp
    bne :+
    dec se_hot_tmp+1
:
    dec se_hot_tmp
    jmp @append
@insert:
    inc se_hot_tmp
    bne @append
    inc se_hot_tmp+1
@append:
    DOC_TOKEN se_hot_append
    jsr se_object_validate
    jcs quota_return
    clc
    lda object_size_lo,x
    adc se_hot_tmp
    sta se_hot_tmp
    lda object_size_mid,x
    adc se_hot_tmp+1
    sta se_hot_tmp+1
    lda object_size_hi,x
    adc #0
    cmp object_banks,x
    jcc quota_ok
    jne quota_full
    lda se_hot_tmp
    ora se_hot_tmp+1
    jne quota_full
    jmp quota_ok

.ifdef EDITOR_BINDINGS
.include "overlays/render-damage.s"
.include "render/geos/edit-certificate-body.inc"

; C6 is already resident in the command slot after a local mutation, so the
; Plain LRV3 update nests only the legal renderer-slot R25 call.  A miss simply
; retires the one-edit witness and lets the existing redraw path rebuild cold.
lrv_plain_edit:
    lda #ST_TX_INVALID
    sta se_st_tx+ST_TX_PHASE
    lda GEC_VALID
    cmp #1
    bne @done
    lda se_mode
    cmp #3
    bcs @done                  ;GEOS keeps its certificate for its own consumer
    lda se_f_owner
    bne @invalidate
    jsr lrv_row_hint
    bcs @invalidate
    lda se_render_caps
    bne lrv_style_ticket
    lda #4
    sta se_f_owner
    lda #18
    sta se_overlay_frame
    lda #25
    ldx #0
    jsr se_overlay_call
    tax
    lda #0
    sta se_f_owner
    bcs @invalidate
    txa
    beq @done
@invalidate:
    lda #0
    sta GEC_VALID
@done:
    rts

; The edit overlay already owns the authenticated pre-edit certificate and row
; hint. Build the persistent styled ticket here instead of loading R25 merely
; to rediscover the same facts. The prior complete frame guarantees that a
; valid, idle style plan and checkpoint describe this exact view.
lrv_style_ticket:
    lda se_st_valid
    and se_st_cp_valid
    cmp #1
    bne @identity_bad
    lda se_st_request
    bne @identity_bad
    ; The validity flags are the fast lifecycle gate; these compact comparisons
    ; independently bind the retained carry to the certified old publication.
    ldx #14
@meta:
    lda se_st_descriptor,x
    cmp se_doc_meta,x
    bne @identity_bad
    dex
    bpl @meta
    ldx #1
@generation:
    lda se_st_descriptor+15,x
    cmp se_doc_generation,x
    bne @identity_bad
    lda se_st_descriptor+ST_KEY_EPOCH,x
    cmp GEC_REU_EPOCH,x
    bne @identity_bad
    dex
    bpl @generation
    ldx #6
@old_publication:
    lda se_st_descriptor+17,x
    cmp GEC_REVISION,x
    bne @identity_bad
    dex
    bpl @old_publication
    ldx #2
@view:
    lda se_st_descriptor+ST_KEY_TOP,x
    cmp se_v_top,x
    bne @identity_bad
    lda se_st_descriptor+ST_KEY_PAN,x
    cmp se_l_pan,x
    bne @identity_bad
    dex
    bpl @view
    lda se_mode
    asl
    ora se_l_mode
    cmp se_st_descriptor+ST_KEY_MODE
    beq @identity_ok
@identity_bad:
    jmp lrv_style_invalid
@identity_ok:
    lda se_st_cp_count
    cmp #STYLE_ROWS+1
    bcs @checkpoint_bad
    ; Authenticate all 22 fixed records, including unused rows, before any
    ; marker guides admission.  A fixed scan avoids count*5 arithmetic.
    jsr se_crc_init
    ldy #0
@checkpoint_crc:
    lda se_st_cp_rows,y
    jsr se_crc_byte
    iny
    cpy #STYLE_CARRY_TABLE_BYTES
    bcc @checkpoint_crc
    lda se_crc_value
    cmp se_st_cp_crc
    bne @checkpoint_bad
    lda se_crc_value+1
    cmp se_st_cp_crc+1
    beq @checkpoint_ok
@checkpoint_bad:
    jmp lrv_style_invalid
@checkpoint_ok:
    CMP24 GEC_POSITION,se_v_rows
    bcc @checkpoint_bad
    lda se_overlay_frame+1
    cmp se_st_cp_count
    bcs @checkpoint_bad
    sta se_hot_target            ;first containing physical row
@back:
    lda se_hot_target
    asl
    asl
    clc
    adc se_hot_target
    tax
    lda se_st_cp_rows,x
    bmi @start
    lda se_hot_target
    jeq lrv_style_invalid
    dec se_hot_target
    bne @back
    beq @back
@start:
    lda se_hot_target
    clc
    adc #1
    sta se_hot_target+1          ;exclusive physical-row end
@forward:
    lda se_hot_target+1
    cmp se_st_cp_count
    jcs lrv_style_invalid       ;last line lacks an outgoing convergence carry
    asl
    asl
    clc
    adc se_hot_target+1
    tax
    lda se_st_cp_rows,x
    bmi @bounds
    inc se_hot_target+1
    bne @forward
@bounds:
    lda se_hot_target+1
    sec
    sbc se_hot_target
    jeq lrv_style_invalid
    sta se_hot_count
    lda se_hot_target
    asl
    clc
    adc se_hot_target
    tax
    ldy #0
@start_copy:
    lda se_v_rows,x
    sta se_st_tx+ST_TX_START,y
    inx
    iny
    cpy #3
    bcc @start_copy
    lda se_hot_target+1
    asl
    clc
    adc se_hot_target+1
    tax
    ldy #0
@end_copy:
    lda se_v_rows,x
    sta se_st_tx+ST_TX_END,y
    inx
    iny
    cpy #3
    bcc @end_copy
@adjust_end:
    lda GEC_OP
    bne @delete_end
    inc se_st_tx+ST_TX_END
    bne @end_ready
    inc se_st_tx+ST_TX_END+1
    bne @end_ready
    inc se_st_tx+ST_TX_END+2
    jeq lrv_style_invalid
@delete_end:
    lda se_st_tx+ST_TX_END
    bne :+
    lda se_st_tx+ST_TX_END+1
    bne @delete_mid
    lda se_st_tx+ST_TX_END+2
    jeq lrv_style_invalid
    dec se_st_tx+ST_TX_END+2
@delete_mid:
    dec se_st_tx+ST_TX_END+1
:
    dec se_st_tx+ST_TX_END
@end_ready:
    lda se_mode
    asl
    ora se_l_mode
    asl
    asl
    asl
    asl
    asl
    ora se_hot_target
    sta se_st_tx+ST_TX_ROW_MODE
    lda se_hot_count
    ldx GEC_OP
    beq :+
    ora #ST_TX_DELETE
:
    sta se_st_tx+ST_TX_COUNT_KIND
    ldx #1
@ticket_pair:
    lda GEC_SEQUENCE,x
    sta se_st_tx+ST_TX_SEQUENCE,x
    lda se_doc_generation,x
    sta se_st_tx+ST_TX_DOC_GENERATION,x
    lda se_doc_epoch,x
    sta se_st_tx+ST_TX_DOC_EPOCH,x
    dex
    bpl @ticket_pair
    ldx #3
@ticket_revision:
    lda se_r_revision,x
    sta se_st_tx+ST_TX_REVISION,x
    dex
    bpl @ticket_revision
    ; C11 used to refresh the merged view length before C14 opened its source.
    ; This path deliberately skips C11, so advance the authenticated old view
    ; length by the same one-byte edit before publishing the ticket.
    lda GEC_OP
    bne @view_delete
    inc se_v_length
    bne @view_length_ready
    inc se_v_length+1
    bne @view_length_ready
    inc se_v_length+2
    jmp @view_length_ready
@view_delete:
    lda se_v_length
    bne :+
    lda se_v_length+1
    bne @view_delete_mid
    dec se_v_length+2
@view_delete_mid:
    dec se_v_length+1
:
    dec se_v_length
@view_length_ready:
    lda #ST_TX_CHECK_SEED^ST_TX_ADMITTED
    ldx #ST_TX_BYTES-1
@ticket_check:
    eor se_st_tx,x
    dex
    cpx #ST_TX_START-1
    bne @ticket_check
    sta se_st_tx+ST_TX_CHECK
    lda #0
    sta se_st_valid
    lda #1
    sta se_st_request
    lda #ST_TX_ADMITTED
    sta se_st_tx+ST_TX_PHASE
    clc
    rts

lrv_style_invalid:
    lda #0
    sta GEC_VALID
    rts

; Physical-row hint. Plain edits are rechecked by R25; styled admission proves
; the lower page bound before trusting this monotonic next-anchor scan.
lrv_row_hint:
    lda #0
    sta se_overlay_frame+1
    ldx #0
@row:
    cpx #63                  ;row21 uses the separately stored bottom anchor
    beq @bottom
    lda se_v_rows+3,x
    sta se_hot_tmp
    lda se_v_rows+4,x
    sta se_hot_tmp+1
    lda se_v_rows+5,x
    sta se_hot_tmp+2
    jmp @compare
@bottom:
    lda se_v_bottom
    sta se_hot_tmp
    lda se_v_bottom+1
    sta se_hot_tmp+1
    lda se_v_bottom+2
    sta se_hot_tmp+2
@compare:
    lda se_hot_tmp+2
    cmp GEC_POSITION+2
    bcc @advance
    bne @selected
    lda se_hot_tmp+1
    cmp GEC_POSITION+1
    bcc @advance
    bne @selected
    lda se_hot_tmp
    cmp GEC_POSITION
    bcc @advance
    bne @selected
    ; Equal next anchor: short CR/EOF rows own their end cell.  A wrapped row
    ; exactly one width long advances to its terminal/continuation row.
    lda se_l_mode
    bne @selected
    sec
    lda GEC_POSITION
    sbc se_v_rows,x
    sta se_hot_tmp
    lda GEC_POSITION+1
    sbc se_v_rows+1,x
    sta se_hot_tmp+1
    lda GEC_POSITION+2
    sbc se_v_rows+2,x
    ora se_hot_tmp+1
    bne @selected
    lda se_hot_tmp
    cmp se_v_columns
    bne @selected
@advance:
    inc se_overlay_frame+1
    lda se_overlay_frame+1
    cmp #22
    bcs @bad
    inx
    inx
    inx
    jmp @row
@selected:
    clc
    rts
@bad:
    sec
    rts
.endif

.ifdef EDITOR_BINDINGS
.endif

.ifdef EDITOR_BINDINGS
.endif
