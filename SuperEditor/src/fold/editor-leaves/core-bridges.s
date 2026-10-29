; C-to-R calls return before any subsequent source/core R replacement.
.setcpu "6502"
.include "fold/editor-leaves/api.inc"
.segment "FOLD_EDITOR"
.macro BRIDGE name,opcode
name:
    lda #opcode
    jmp invoke
.endmacro
    BRIDGE se_fold_guard,FC_GUARD
    BRIDGE se_fold_read,FC_READ
    BRIDGE se_fold_write,FC_WRITE
se_fold_fail:
    sta se_overlay_frame+1
    lda #FC_FAIL
    jmp invoke
    BRIDGE se_fold_done,FC_DONE
    BRIDGE se_fold_tick,FC_TICK
    BRIDGE se_fold_validate_begin,FC_VALIDATE_BEGIN
    BRIDGE se_fold_validate_step,FC_VALIDATE_STEP
invoke:
    sta se_overlay_frame
    lda #FE_CORE_ID
    ldx #0
    jmp se_overlay_call
