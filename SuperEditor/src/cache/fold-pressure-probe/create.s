; Private C19 create-once, optional-derived-retirement, retry-once experiment.
; No BC_FRAME access: owner3 currently owns that entire union as fold state.
.setcpu "6502"
.include "cache/api.inc"
.include "fold/api.inc"
.include "editor_fold/controller.inc"
.import se_f_owner,se_object_create,se_object_validate,se_object_release
.import se_object_id,object_owner
.export ec_create_fold,ec_cache_retire
.segment "CODE"
ec_create_fold:
    jsr se_object_create
    bcc @done
    cmp #$35                 ; genuine object catalog exhaustion
    beq @pressure
    cmp #1                   ; actual provider logical/physical no-space result
    bne @error
@pressure:
    pha
    jsr ec_cache_retire
    bcc @retry
    pla                     ; refusal retains the original CREATE error
@error:
    sec
@done:
    rts
@retry:
    pla
    ldx se_ec_banks
    lda #SF_OBJECT_TYPE
    jmp se_object_create     ; exactly one retry, never another eviction loop

ec_cache_retire:
    lda se_f_owner
    cmp #3
    bne @refused
    lda se_bc_flags
    and #(BC_ACTIVE|BC_MUTATING)
    bne @refused
    ldy #4
@token:
    lda se_bc_arena,y
    sta se_object_id,y
    dey
    bpl @token
    jsr se_object_validate   ; complete generation/epoch/logical/physical graph
    bcs @refused
    lda object_owner,x
    cmp #BC_OBJECT_TYPE
    bne @refused
    jsr se_object_release    ; revalidates all extents before freeing anything
    bcs @refused
    lda #0
    ldy #4
@clear:
    sta se_bc_arena,y
    dey
    bpl @clear
    lda se_bc_flags
    and #($FF-BC_ARMED-BC_PAGE_PROOF)
    ora #BC_LOST
    sta se_bc_flags          ; retain TRIED, ticket, incarnation and all ring bytes
    lda #0
    clc
    rts
@refused:
    sec
    rts
