.setcpu "6502"
.macpack longbranch
.include "fileio/api.inc"
.include "fileio/save.inc"
.ifdef SE_FILE_CODE_ONLY
.import se_sv_phase,se_sv_had_target,se_sv_error
.else
.ifdef SE_FILE_UNION
.segment "FILESTATE"
.else
.segment "BSS"
.endif
se_sv_phase: .res 1
se_sv_had_target: .res 1
se_sv_error: .res 1 ; caller's original diagnostic; zero denotes success
.endif
.ifndef SE_FILE_STATE_ONLY
.segment "CODE"
; Pure save policy. The resident coordinator carries out the published action,
; with exact private names/capabilities and document snapshot leases. No disk
; mutation occurs here. A=0 new target/A=1 existing; idle/done only.
se_sv_begin:
    cmp #2
    jcs invalid
    tax
    lda se_sv_phase
    beq :+
    cmp #SV_DONE
    jne invalid
:   stx se_sv_had_target
    lda #0
    sta se_sv_error
    lda #SV_CREATE
    jne publish
se_sv_step:
    cmp #6
    jcs invalid
    ldx se_sv_phase
    jeq invalid
    cpx #SV_DONE
    jeq invalid
    cpx #SV_RECOVERY
    jcs invalid
    cmp #SV_UNCERTAIN
    jeq recovery ; never guess after an acknowledgement may have been lost
    cmp #SV_CANCEL
    jeq cancel
    cpx #SV_COMPARE
    beq compare
    cmp #SV_OK
    jne failure
    cpx #SV_CREATE
    beq advance
    cpx #SV_WRITE
    beq advance
    cpx #SV_CLOSE
    beq advance
    cpx #SV_OPEN_VERIFY
    beq advance
    cpx #SV_CLOSE_VERIFY
    beq verified
    cpx #SV_BACKUP
    beq advance
    cpx #SV_PROMOTE
    beq advance
    cpx #SV_CHECK_TARGET
    beq checked
    cpx #SV_DELETE_BACKUP
    jeq done
    cpx #SV_ABORT_CLOSE
    jeq delete_temp
    cpx #SV_DELETE_TEMP
    jeq done
    cpx #SV_ROLLBACK
    jeq delete_temp
    jne invalid
advance:
    inx
    txa
    jne publish
compare:
    cmp #SV_MATCH
    beq advance
    cmp #SV_MISMATCH
    beq abort_close
    cmp #SV_FAILED
    beq abort_close
    jne invalid
verified:
    lda se_sv_had_target
    beq promote
    lda #SV_BACKUP
    jne publish
promote:
    lda #SV_PROMOTE
    jne publish
checked:
    lda se_sv_had_target
    jeq done
    lda #SV_DELETE_BACKUP
    jne publish
failure:
    cmp #SV_FAILED
    jne invalid
    cpx #SV_CREATE
    jeq done ; definite create refusal never grants temp ownership
    cpx #SV_WRITE
    beq abort_close
    cpx #SV_OPEN_VERIFY
    beq abort_close
    cpx #SV_CLOSE
    jeq delete_temp
    cpx #SV_CLOSE_VERIFY
    jeq delete_temp
    cpx #SV_BACKUP
    jeq delete_temp ; target unchanged, candidate not owned
    cpx #SV_PROMOTE
    beq promotion_failed
    bne recovery ; cleanup/rollback/final verification need explicit recovery
promotion_failed:
    lda se_sv_had_target
    jeq delete_temp
    lda #SV_ROLLBACK
    jne publish
cancel:
    cpx #SV_CREATE
    jeq done ; before action has run
    cpx #SV_BACKUP
    bcs recovery ; target rename may already have happened: keep both copies
abort_close:
    lda #SV_ABORT_CLOSE
    jne publish
delete_temp:
    lda #SV_DELETE_TEMP
    jne publish
done:
    lda #SV_DONE
    jne publish
recovery:
    lda #SV_RECOVERY
publish:
    sta se_sv_phase
    lda #0
    clc
    rts
invalid:
    lda #FIO_STATE
    sec
    rts
.endif
