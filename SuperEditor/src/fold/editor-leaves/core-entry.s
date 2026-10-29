.setcpu "6502"
.include "editor-api.inc"
.include "fold/editor-leaves/api.inc"
.include "fold/locate.inc"
.export entry
.segment "FOLD_EDITOR"
    OVL_BINDING
entry:
    lda se_f_owner
    cmp #FE_OWNER
    jne busy
    lda se_overlay_frame
    cmp #FC_FAIL
    bne :+
    lda se_overlay_frame+1
    jmp se_fold_fail
:
.macro ROUTE opcode,target
    cmp #opcode
    bne :+
    jmp target
:
.endmacro
    ROUTE FC_GUARD,se_fold_guard
    ROUTE FC_READ,se_fold_read
    ROUTE FC_WRITE,se_fold_write
    ROUTE FC_DONE,se_fold_done
    ROUTE FC_TICK,se_fold_tick
    ROUTE FC_VALIDATE_BEGIN,se_fold_validate_begin
    ROUTE FC_VALIDATE_STEP,se_fold_validate_step
    ROUTE FC_QUERY_BEGIN,se_fold_query_begin
    ROUTE FC_QUERY_STEP,se_fold_query_step
    ROUTE FC_ACTION_BEGIN,se_fold_action_begin
    ROUTE FC_ACTION_STEP,se_fold_action_step
    ROUTE FC_CANCEL,se_fold_cancel
    ROUTE FC_INVALIDATE,se_fold_invalidate
    ROUTE FC_LOCATE_BEGIN,se_fold_locate_begin
    ROUTE FC_LOCATE_STEP,se_fold_locate_step
    ROUTE FC_LOCATE_CANCEL,se_fold_locate_cancel
    lda #SF_BAD
    sec
    rts
busy:
    lda #SF_BUSY
    sec
    rts
