.setcpu "6502"
.macpack longbranch
SE_EDITOR_FOLD_IMPLEMENTATION=1
.include "editor_fold/api.inc"
.ifdef EDITOR_OVERLAY
.include "editor-api.inc"
.else
.import se_ef_key,se_ef_valid,se_ef_fold_rows,se_ef_motion
.import se_view_init,se_v_length,se_doc_meta,se_doc_original,se_doc_append
.import se_doc_generation,se_r_revision,se_reu_epoch,se_doc_epoch
.import se_object_id,se_object_validate,se_ej_status,se_ef_projection_invalidate
.endif
.export se_ef_key_capture,se_ef_key_match,se_ef_invalidate,se_ef_motion_tick

.macro EF_FIELDS action
    action se_doc_meta,EF_KEY_META,5
    action se_doc_original,EF_KEY_ORIGINAL,5
    action se_doc_append,EF_KEY_APPEND,5
    action se_doc_generation,EF_KEY_GENERATION,2
    action se_r_revision,EF_KEY_REVISION,4
    action se_v_length,EF_KEY_LENGTH,3
    action se_reu_epoch,EF_KEY_REU_EPOCH,2
    action se_doc_epoch,EF_KEY_DOC_EPOCH,2
.endmacro
.macro EF_CAPTURE source,offset,size
    ldx #size-1
:
    lda source,x
    sta se_ef_key+offset,x
    dex
    bpl :-
.endmacro
.macro EF_COMPARE source,offset,size
    ldx #size-1
:
    lda source,x
    cmp se_ef_key+offset,x
    jne ef_changed
    dex
    bpl :-
.endmacro
.macro EF_TOKEN source
    ldx #4
:
    lda source,x
    sta se_object_id,x
    dex
    bpl :-
    jsr se_object_validate
    bcs ef_error
.endmacro
.segment "CODE"
se_ef_key_capture:
    jsr se_ef_invalidate
    jsr ef_refresh
    jcs ef_return
    EF_FIELDS EF_CAPTURE
    lda #0
    clc
    rts
se_ef_key_match:
    jsr ef_refresh
    jcs ef_return
    EF_FIELDS EF_COMPARE
    lda #0
    clc
    rts
ef_changed:
    lda #EF_CHANGED
ef_error:
    pha
    jsr se_ef_invalidate
    pla
    sec
ef_return:
    rts

; Actual view derives merged length and refuses stale hot/doc contexts. It
; validates the document service, not the object token generations themselves;
; validate allthree tokens explicitly before trusting/capturing the identity.
ef_refresh:
    jsr se_view_init
    bcs ef_error
    EF_TOKEN se_doc_meta
    EF_TOKEN se_doc_original
    EF_TOKEN se_doc_append
    lda #0
    clc
    rts

se_ef_motion_tick:
    inc se_ef_motion
    bne ef_zero
    inc se_ef_motion+1
    bne ef_zero
    inc se_ef_motion+2
    bne ef_zero
    inc se_ef_motion+3
    bne ef_zero
    ; Repeated serial0 cannot authorize a saved inner-caret restoration.
    lda #$80
    sta se_ej_status
    jsr se_ef_projection_invalidate
se_ef_invalidate:
    lda #0
    sta se_ef_valid
    sta se_ef_fold_rows
    sta se_ef_fold_rows+1
    sta se_ef_fold_rows+2
ef_zero:
    lda #0
    clc
    rts
