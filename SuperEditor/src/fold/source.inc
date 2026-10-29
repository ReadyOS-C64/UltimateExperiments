.ifndef SE_FOLD_SOURCE_API
SE_FOLD_SOURCE_API=1
.if .not .definedmacro(jeq)
.macpack longbranch
.endif
.include "document/api.inc"
.include "document/math24.inc"
.include "hot/api.inc"
.ifndef OBJECT_LIMIT
.include "object/api.inc"
.endif
.global se_fs_begin,se_fs_guard,se_fs_read,se_fs_end,se_fs_shape,se_fs_tokens
.global se_fs_state,se_fs_state_size,se_fs_identity,se_fs_identity_size
.global se_fs_offset,se_fs_count,se_fs_buffer,se_fs_done,se_fs_active,se_fs_owned
.global se_fs_length,se_fs_revision,se_fs_hot_end,se_fs_temp,se_fs_output,se_fs_phys,se_fs_error
.global se_r_revision,se_h_phase,se_b_phase,se_clip_busy,se_reu_epoch
.importzp text_ptr
FS_BAD=$B0
FS_CHANGED=$B1
FS_BUSY=$B2
.macro FS_CAPTURE source,offset,n
    ldx #n-1
:
    lda source,x
    sta se_fs_identity+offset,x
    dex
    bpl :-
.endmacro
.macro FS_CHECK source,offset,n
    ldx #n-1
:
    lda source,x
    cmp se_fs_identity+offset,x
    jne fs_changed
    dex
    bpl :-
.endmacro
.macro FS_FIELDS action
    action se_reu_epoch,0,2
    action se_doc_epoch,2,2
    action se_doc_generation,4,2
    action se_doc_meta,6,5
    action se_doc_original,11,5
    action se_doc_append,16,5
    action se_doc_length,21,3
    action se_doc_root_count,24,1
    action se_r_revision,25,4
    action se_hot_ready,29,1
    action se_hot_pending,30,1
    action se_hot_phase,31,1
    action se_hot_owned,32,1
    action se_hot_fault,33,1
    action se_hot_epoch,34,2
    action se_hot_generation,36,2
    action se_hot_original,38,5
    action se_hot_append,43,5
    action se_hot_base,48,3
    action se_hot_old_length,51,2
    action se_hot_length,53,2
    action se_hot_left,55,2
    action se_hot_right,57,2
.endmacro
.endif
