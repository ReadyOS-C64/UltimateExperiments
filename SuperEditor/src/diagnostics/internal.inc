.macpack longbranch
.include "diagnostics/api.inc"
.include "document/api.inc"
.include "document/math24.inc"
.include "hot/api.inc"
.importzp text_ptr
.import se_reu_epoch,se_reu_map,se_reu_logical_owner,se_reu_physical_owner
.import se_reu_banks,se_reu_retired,se_overlay_loads,se_overlay_hits,se_overlay_calls
.import se_h_dirty,se_h_phase,se_b_phase,se_clip_busy,se_r_revision
.global se_diag_pointer,se_diag_abort,se_diag_context,se_diag_shape
.macro D_CAPTURE source,offset,bytes
    ldy #offset
    ldx #0
:
    lda source,x
    sta (text_ptr),y
    iny
    inx
    cpx #bytes
    bne :-
.endmacro
.macro D_CHECK source,offset,bytes
    ldy #offset
    ldx #0
:
    lda source,x
    cmp (text_ptr),y
    jne se_diag_context_changed
    iny
    inx
    cpx #bytes
    bne :-
.endmacro
.macro D_CONTEXT action
    action se_doc_epoch,DS_EPOCH,2
    action se_doc_generation,DS_GENERATION,2
    action se_doc_original,DS_ORIGINAL,5
    action se_doc_append,DS_APPEND,5
    action se_doc_meta,DS_META,5
    action se_doc_length,DS_COMMITTED_LENGTH,3
    action se_hot_ready,DS_HOT_READY,1
    action se_hot_pending,DS_PENDING,1
    action se_hot_phase,DS_HOT_PHASE,1
    action se_hot_base,DS_HOT_BASE,3
    action se_hot_old_length,DS_HOT_OLD_LENGTH,2
    action se_hot_length,DS_HOT_LENGTH,2
    action se_hot_left,DS_HOT_LEFT,2
    action se_hot_right,DS_HOT_RIGHT,2
    action se_hot_generation,DS_HOT_GENERATION,2
    action se_hot_original,DS_HOT_ORIGINAL,5
    action se_hot_append,DS_HOT_APPEND,5
    action se_r_revision,DS_REVISION,4
.endmacro
