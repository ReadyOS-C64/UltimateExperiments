.setcpu "6502"
.macpack longbranch
.ifdef EDITOR_BINDINGS
    .import se_gtt_certify
    .include "editor-api.inc"
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
    jmp caret
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
.endif

.ifdef EDITOR_BINDINGS
.endif

.ifdef EDITOR_BINDINGS
.endif
