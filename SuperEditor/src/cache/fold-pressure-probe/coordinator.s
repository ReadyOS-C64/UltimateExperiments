.setcpu "6502"
.macpack longbranch
EF_CONTROLLER_IMPLEMENTATION=1
.include "editor_fold/controller.inc"
.include "render/presentation.inc"
.include "editor_fold/journal.inc"
.include "fold/editor-leaves/api.inc"
.include "fold/locate.inc"
.import se_ef_emergency,se_doc_read_locks,se_hot_caret,se_e_target
.import se_l_valid,se_r_valid,se_st_valid,se_st_request,se_st_cp_valid,se_l_need_wrap
.import se_i_ready,se_i_count,se_n_cache_count
.import se_ef_journal_call
.import ec_retention_prepare,ec_transform_step,ec_retire_hint,ec_retire_old
.export ec_size_object,ec_publish
EC_TRANSFORM=4
.export se_ef_begin,se_ef_step,se_ef_cancel
.import ec_create_fold
.segment "CODE"
se_ef_begin:
    lda se_f_owner
    jne ec_busy
    lda se_render_caps
    jeq ec_bad ;Plain has no automatic or explicit semantic fold projection
    lda se_ef_active
    jne ec_busy
    lda se_overlay_frame+1
    cmp #7
    jcs ec_bad
    pha
    lda #3
    sta se_f_owner
    ; Fresh exclusively owned union; never END a previousunownedphaseclient.
    lda #0
    sta se_i_ready
    sta se_i_count
    sta se_n_cache_count
    tax
@pages:
    sta $8D00,x
    sta $8E00,x
    sta $8F00,x
    sta $9000,x
    inx
    bne @pages
    ldx #$7F
@tail:
    sta $9100,x
    dex
    bpl @tail
    pla
    sta se_ec_action
    lda #EF_CONTROL_ID
    sta se_ef_active
    SF_COPY se_hot_caret,se_e_target,3
    lda se_ef_valid
    beq ec_build
    jsr se_ef_key_match
    jcc ec_reuse
    cmp #EF_CHANGED
    jne ec_abort

ec_build:
    lda se_ef_capacity_banks
    bne :+
    lda #1
:
    cmp #17
    jcs ec_bad_abort
    sta se_ec_banks
    jsr ec_retention_prepare
    jcs ec_abort
    cmp #2
    jeq ec_reuse
    cmp #1
    jeq ec_pending
    jsr se_ef_key_capture
    jcs ec_abort
    lda #0
    sta se_fb_old_valid
ec_candidate:
    ldx se_ec_banks
    lda #SF_OBJECT_TYPE
    jsr ec_create_fold
    jcs ec_abort
    SF_COPY se_object_id,se_ec_candidate,5
    lda #1
    sta se_ec_allocated
    jsr ec_size_object
    jcs ec_abort
    SF_COPY se_ec_candidate,se_fold_token,5
    SF_COPY se_ef_key+EF_KEY_ORIGINAL,se_fb_source,5
    ; Last1024B is the journal tail, never a parser record slot.
    lda #$E0
    sta se_fb_capacity
    lda se_ec_banks
    asl
    asl
    asl
    sec
    sbc #1
    sta se_fb_capacity+1
    lda #EC_BUILD
    sta se_ec_phase
    lda #FE_PARSE_ID
    sta se_ef_active
    lda #FE_BEGIN
    sta se_ef_operation
    jmp ec_pending

ec_reuse:
    SF_COPY se_ef_token,se_fold_token,5
    SF_COPY se_ef_count,se_fold_count,2
    SF_COPY se_ef_key+EF_KEY_LENGTH,se_fold_length,3
    SF_COPY se_ef_key+EF_KEY_REVISION,se_fold_epoch,4
    SF_COPY se_fold_token,se_fold_bound_token,5
    SF_COPY se_fold_count,se_fold_bound_count,2
    SF_COPY se_fold_length,se_fold_bound_length,3
    SF_COPY se_fold_epoch,se_fold_stamp,4
    lda #1
    sta se_fold_valid
    lda #FC_GUARD
    jsr ec_core
    jcs ec_abort
    jmp ec_start_action

se_ef_step:
    lda se_f_owner
    cmp #FE_OWNER
    jne ec_busy
    lda se_ec_carry
    beq :+
    lda se_ec_result
    jmp ec_abort
:
    jsr se_ef_key_match
    jcs ec_abort
    lda se_ec_phase
    cmp #EC_TRANSFORM
    beq ec_transform
    cmp #EC_BUILD
    beq ec_build_step
    cmp #EC_LOCATE
    jeq ec_locate_step
    cmp #EC_ACTION
    jeq ec_action_step
    jmp ec_bad_abort

ec_transform:
    jsr ec_transform_step
    jcs ec_abort
    cmp #0
    jne ec_pending
    jmp ec_candidate

ec_build_step:
    lda se_fb_error
    jne ec_abort
    lda se_fb_busy
    beq @published
    lda #FE_PARSE_ID
    ldx se_fb_phase
    cpx #FB_FILTER
    bcc :+
    lda #FE_FINISH_ID
:
    sta se_ef_active
    lda #FE_STEP
    sta se_ef_operation
    jmp ec_pending
@published:
    lda se_fold_valid
    jeq ec_bad_abort
    ldx #4
@candidate:
    lda se_ec_candidate,x
    cmp se_fold_token,x
    jne ec_bad_abort
    dex
    bpl @candidate
    jsr ec_retire_hint
    jcs ec_abort
    jsr ec_retire_old
    jcs ec_abort
    SF_COPY se_ec_candidate,se_ef_token,5
    SF_COPY se_fold_count,se_ef_count,2
    lda se_ec_banks
    sta se_ef_capacity_banks
    lda #0
    sta se_ec_allocated ;ownership transfers to persistentpublishedtoken
    jsr ec_publish

ec_start_action:
    lda se_ec_action
    cmp #6
    bne :+
    lda #5 ;internal retention rebuild reveals caret after fresh parsing
    sta se_ec_action
:
    ; Thebuilder END releasesitslease oncompletion. Reacquire theactualsource
    ; adapterlease forlocator/action too, so residentfs_end alwayscleans it.
    jsr se_fs_begin
    jcs ec_abort
    SF_COPY se_hot_caret,se_fold_caret,3
    SF_COPY se_hot_caret,se_fold_query,3
    SF_COPY se_ef_motion,se_fold_motion,4
    lda se_ec_action
    cmp #3
    jcs ec_action_begin
    ; Locator chooses innermosteligiblevisiblefold inone-recordslices.
    sta se_fold_mode ;0any,1expanded,2collapsed matchesfirstthreeactions
    lda #FC_LOCATE_BEGIN
    jsr ec_core
    jcs ec_abort
    lda #EC_LOCATE
    sta se_ec_phase
    jmp ec_pending

ec_locate_step:
    lda #FC_LOCATE_STEP
    jsr ec_core
    jcs ec_abort
    lda se_fold_busy
    jne ec_pending
    lda se_fold_target
    and se_fold_target+1
    cmp #$FF
    jeq ec_done ;no visibleeligiblefold is an idempotentno-op

ec_action_begin:
    lda se_ec_action
    sta se_fold_action
    lda #0
    sta se_ef_valid ;partialmetadatawrites are not a publishedmap
    lda #FC_ACTION_BEGIN
    jsr ec_core
    jcs ec_abort
    lda #EC_ACTION
    sta se_ec_phase
    jmp ec_pending

ec_action_step:
    lda #FC_ACTION_STEP
    jsr ec_core
    jcs ec_abort
    lda se_fold_busy
    bne ec_pending
    SF_COPY se_fold_result,se_e_target,3
    lda #1
    sta se_ec_moved
    jsr ec_publish

ec_done:
    jsr se_fs_end
    lda #0
    sta se_ec_phase
    sta se_ef_active
    sta se_ef_operation
    sta se_f_owner
    clc
    rts

ec_publish:
    inc se_ef_generation
    bne :+
    inc se_ef_generation+1
:
    lda #0
    sta se_ef_fold_rows
    sta se_ef_fold_rows+1
    sta se_ef_fold_rows+2
    sta se_l_valid
    sta se_r_valid
    sta se_st_valid
    sta se_st_request
    sta se_st_cp_valid
    lda #1
    sta se_l_need_wrap
    sta se_ef_valid
    lda #5 ;new fully published key/map is a fresh journal baseline
    jsr se_ef_journal_call
    ; Optional journal failure disarms retention, never rolls back valid folds.
    bcc @return
    pha
    lda #EJ_FAILED ;also handles R19 admission failure before its own guard runs
    sta se_ej_status
    pla
@return:
    rts

ec_size_object:
    lda #0
    sta se_object_offset
    sta se_object_offset+1
    lda se_ec_banks
    sta se_object_offset+2
    jmp se_object_resize

ec_core:
    sta se_overlay_frame
    lda #FE_CORE_ID
    ldx #0
    jmp se_overlay_call

ec_pending:
    lda #1
    clc
    rts
se_ef_cancel:
    lda se_f_owner
    cmp #FE_OWNER
    bne ec_busy
    lda #0
    jsr se_ef_emergency
    clc
    rts
ec_bad_abort:
    lda #SF_BAD
ec_abort:
    sta se_ec_error
    jmp se_ef_emergency
ec_bad:
    lda #SF_BAD
    sec
    rts
ec_busy:
    lda #SF_BUSY
    sec
    rts
