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
valid:
    jsr se_doc_validate
    jcs return
    lda se_hot_ready
    ora se_hot_phase
    jeq state
    ldx #4
@tokens:
    lda se_hot_original,x
    cmp se_doc_original,x
    jne context
    lda se_hot_append,x
    cmp se_doc_append,x
    jne context
    dex
    bpl @tokens
    lda se_hot_command
    cmp #W_COMMIT
    bne @generation_start
    lda se_h_phase
    jne busy
    jmp se_h_validate
@generation_start:
    ldx #1
@generation:
    lda se_hot_generation,x
    cmp se_doc_generation,x
    jne context
    dex
    bpl @generation
    clc
    rts
load:
    lda se_hot_phase
    ora se_hot_pending
    jne busy
    jsr se_doc_validate
    jcs return
    CMP24 se_hot_position,se_doc_length
    bcc @range
    jne boundary
@range:
    lda #0
    sta se_hot_ready
    sta se_hot_fault
    COPY24 se_hot_position,se_hot_caret
    COPY24 se_hot_position,se_hot_base
    ; Start up to512 bytes before caret. Fill at most1024 baseline bytes.
    lda se_hot_base+2
    bne @subtract
    lda se_hot_base+1
    cmp #2
    bcs @subtract
    lda #0
    sta se_hot_base
    sta se_hot_base+1
    sta se_hot_left+1
    lda se_hot_position
    sta se_hot_left
    lda se_hot_position+1
    sta se_hot_left+1
    jmp @size
@subtract:
    sec
    lda se_hot_base+1
    sbc #2
    sta se_hot_base+1
    lda se_hot_base+2
    sbc #0
    sta se_hot_base+2
    lda #0
    sta se_hot_left
    lda #2
    sta se_hot_left+1
@size:
    SUB24 se_doc_length,se_hot_base,se_hot_tmp
    lda se_hot_tmp+2
    bne @cap
    lda se_hot_tmp+1
    cmp #4
    bcc @amount
@cap:
    lda #0
    sta se_hot_tmp
    lda #4
    sta se_hot_tmp+1
@amount:
    lda se_hot_tmp
    sta se_hot_length
    sta se_hot_old_length
    lda se_hot_tmp+1
    sta se_hot_length+1
    sta se_hot_old_length+1
    ; Gap right=2048-(length-left).
    sec
    lda se_hot_left
    sbc se_hot_length
    sta se_hot_right
    lda se_hot_left+1
    sbc se_hot_length+1
    clc
    adc #8
    sta se_hot_right+1
    ldx #4
@identity:
    lda se_doc_original,x
    sta se_hot_original,x
    lda se_doc_append,x
    sta se_hot_append,x
    dex
    bpl @identity
    lda se_doc_generation
    sta se_hot_generation
    lda se_doc_generation+1
    sta se_hot_generation+1
    jsr se_doc_read_acquire
    jcs return
    lda #1
    sta se_hot_owned
    sta se_hot_phase
    lda #0
    sta se_hot_loaded
    sta se_hot_loaded+1
    jmp pending
load_step:
    lda se_hot_phase
    cmp #1
    jne state
    ; Read at most128 bytes/eight spans, then copy directly to both gap sides.
    sec
    lda se_hot_length
    sbc se_hot_loaded
    sta se_hot_count
    lda se_hot_length+1
    sbc se_hot_loaded+1
    sta se_hot_count+1
    ora se_hot_count
    jeq loaded
    lda se_hot_count+1
    bne @cap
    lda se_hot_count
    cmp #129
    bcc @count
@cap:
    lda #128
    sta se_hot_count
@count:
    lda #0
    sta se_hot_count+1
    sta se_hot_tmp+2
    lda se_hot_loaded
    sta se_hot_tmp
    lda se_hot_loaded+1
    sta se_hot_tmp+1
    ADD24 se_hot_base,se_hot_tmp,se_doc_offset
    lda se_hot_count
    sta se_doc_count
    lda #0
    sta se_doc_count+1
    sta se_doc_c64
    lda #$80
    sta se_doc_c64+1
    jsr se_doc_read_some
    jcs return
    lda se_doc_read_done
    sta se_hot_count
    lda #0
    sta se_hot_packet
    lda #$80
    sta se_hot_packet+1
@copy:
    lda se_hot_loaded
    sta se_hot_target
    lda se_hot_loaded+1
    sta se_hot_target+1
    jsr address
    ldy #0
    lda (se_hot_packet),y
    sta (se_hot_ptr),y
    inc se_hot_packet
    inc se_hot_loaded
    bne :+
    inc se_hot_loaded+1
:
    dec se_hot_count
    bne @copy
    lda se_hot_loaded
    cmp se_hot_length
    jne pending
    lda se_hot_loaded+1
    cmp se_hot_length+1
    jne pending
loaded:
    jsr se_doc_read_release
    lda #0
    sta se_hot_owned
    sta se_hot_phase
    lda #1
    sta se_hot_ready
    jmp okay
; Logical target -> HOT address; gap split maps suffix to right side.
address:
    lda se_hot_target+1
    cmp se_hot_left+1
    bcc @prefix
    bne @suffix
    lda se_hot_target
    cmp se_hot_left
    bcc @prefix
@suffix:
    sec
    lda se_hot_target
    sbc se_hot_left
    sta se_hot_ptr
    lda se_hot_target+1
    sbc se_hot_left+1
    sta se_hot_ptr+1
    clc
    lda se_hot_ptr
    adc se_hot_right
    sta se_hot_ptr
    lda se_hot_ptr+1
    adc se_hot_right+1
    jmp @high
@prefix:
    lda se_hot_target
    sta se_hot_ptr
    lda se_hot_target+1
@high:
    clc
    adc #>HOT_FIRST
    sta se_hot_ptr+1
    rts
caret:
    lda se_hot_left
    sta se_hot_tmp
    lda se_hot_left+1
    sta se_hot_tmp+1
    lda #0
    sta se_hot_tmp+2
    ADD24 se_hot_base,se_hot_tmp,se_hot_caret
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
prepare:
    lda se_hot_pending
    jeq okay
    ; Minimal conservative delta excludes every guaranteed unchanged edge.
    lda se_hot_prefix
    sta se_hot_tmp
    lda se_hot_prefix+1
    sta se_hot_tmp+1
    lda #0
    sta se_hot_tmp+2
    ADD24 se_hot_base,se_hot_tmp,se_doc_edit_position
    sec
    lda se_hot_old_length
    sbc se_hot_prefix
    sta se_doc_edit_delete
    lda se_hot_old_length+1
    sbc se_hot_prefix+1
    sta se_doc_edit_delete+1
    sec
    lda se_doc_edit_delete
    sbc se_hot_suffix
    sta se_doc_edit_delete
    lda se_doc_edit_delete+1
    sbc se_hot_suffix+1
    sta se_doc_edit_delete+1
    sec
    lda se_hot_length
    sbc se_hot_prefix
    sta se_hot_feed_left
    lda se_hot_length+1
    sbc se_hot_prefix+1
    sta se_hot_feed_left+1
    sec
    lda se_hot_feed_left
    sbc se_hot_suffix
    sta se_hot_feed_left
    sta se_doc_edit_insert
    lda se_hot_feed_left+1
    sbc se_hot_suffix+1
    sta se_hot_feed_left+1
    sta se_doc_edit_insert+1
    lda #0
    sta se_doc_edit_insert+2
    sta se_doc_edit_delete+2
    lda se_hot_prefix
    sta se_hot_feed
    lda se_hot_prefix+1
    sta se_hot_feed+1
    COPY24 se_hot_before,se_h_before_caret
    COPY24 se_hot_caret,se_h_after_caret
    lda se_hot_group
    sta se_h_group
    lda #2
    sta se_hot_phase
    jmp pending
packet:
    lda se_hot_feed_left+1
    bne @cap
    lda se_hot_feed_left
    cmp #129
    bcc @count
@cap:
    lda #128
@count:
    sta se_hot_count
    sta se_doc_count
    lda #0
    sta se_doc_count+1
    sta se_doc_c64
    sta se_hot_packet
    lda #$80
    sta se_doc_c64+1
    sta se_hot_packet+1
@byte:
    lda se_hot_feed
    sta se_hot_target
    lda se_hot_feed+1
    sta se_hot_target+1
    jsr address
    ldy #0
    lda (se_hot_ptr),y
    sta (se_hot_packet),y
    inc se_hot_packet
    inc se_hot_feed
    bne :+
    inc se_hot_feed+1
:
    lda se_hot_feed_left
    bne :+
    dec se_hot_feed_left+1
:
    dec se_hot_feed_left
    dec se_hot_count
    bne @byte
    jmp okay
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
