.setcpu "6502"
.macpack longbranch
SE_EDITOR_FOLD_IMPLEMENTATION=1
EF_CONTROLLER_IMPLEMENTATION=1
.include "editor_fold/controller.inc"
.include "object/api.inc"
.import se_f_owner,se_fs_end
.import se_ef_token,se_ef_valid,se_ef_fold_rows,se_ef_active,se_ef_operation
.import se_ef_projection_invalidate,se_ej_status,se_fb_old_token
.export se_ef_emergency
.segment "CODE"
; Resident safe point, A primaryerror -> sameA/Cset. NoC/Rcalls. Never inspect
; unionwithoutowner3; END is actual epoch/graph-safe cleanup, preservingforeign
; leases. Candidate is disposable and never the publishedmap. A stale/foreign
; token is never released. Publishedmap remains owned for a later rebuild.
se_ef_emergency:
    pha
    lda se_f_owner
    cmp #3
    jne @return
    jsr se_fs_end
    lda se_ec_allocated
    beq @forget
    ldx #4
@published:
    lda se_ec_candidate,x
    cmp se_ef_token,x
    bne @candidate
    dex
    bpl @published
    jmp @forget
@candidate:
    ldx #4
@copy:
    lda se_ec_candidate,x
    sta se_object_id,x
    dex
    bpl @copy
    jsr se_object_validate
    bcs @forget
    lda object_owner,x
    cmp #$46
    bne @forget
    jsr se_object_release
@forget:
    lda se_ec_reuse
    and #1
    beq @clean
    ldx #4
@hint_published:
    lda se_fb_old_token,x
    cmp se_ef_token,x
    bne @hint
    dex
    bpl @hint_published
    bmi @clean
@hint:
    ldx #4
@hint_copy:
    lda se_fb_old_token,x
    sta se_object_id,x
    dex
    bpl @hint_copy
    jsr se_object_validate
    bcs @clean
    lda object_owner,x
    cmp #$46
    bne @clean
    jsr se_object_release
@clean:
    lda #$80
    sta se_ej_status
    jsr se_ef_projection_invalidate
    lda #0
    sta se_ec_allocated
    sta se_ec_reuse
    sta se_ec_phase
    sta se_ef_valid
    sta se_ef_fold_rows
    sta se_ef_fold_rows+1
    sta se_ef_fold_rows+2
    sta se_ef_active
    sta se_ef_operation
    sta se_f_owner
@return:
    pla
    sec
    rts
