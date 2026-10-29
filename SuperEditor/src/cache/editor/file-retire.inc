; File owner1 has no cache reader. Release only the checked optional type53
; object, before reserving the two staged OPEN objects. Do not touch BC_FRAME:
; that phase union currently contains the live File coordinator.
.include "cache/api.inc"
.export f_cache_retire
.segment "CODE"
f_cache_retire:
    lda se_f_owner
    cmp #1
    bne @done
    lda se_bc_flags
    and #(BC_ACTIVE|BC_MUTATING)
    bne @done
    ldy #4
@token:
    lda se_bc_arena,y
    sta se_object_id,y
    dey
    bpl @token
    jsr se_object_validate
    bcs @done
    lda object_owner,x
    cmp #BC_OBJECT_TYPE
    bne @done
    jsr se_object_release
    bcs @done
    ; All extents were validated before release. No yield occurs between the
    ; release and revocation; active/mutating jobs were refused above.
    lda #0
    ldy #4
@clear:
    sta se_bc_arena,y
    dey
    bpl @clear
    lda se_bc_flags
    and #($FF-BC_ARMED-BC_PAGE_PROOF)
    ora #BC_LOST
    sta se_bc_flags
    ; Ticket, incarnation and unread edit records survive derived retirement.
@done:
    rts
