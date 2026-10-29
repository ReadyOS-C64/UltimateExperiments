.setcpu "6502"
.macpack longbranch
.include "editor_file/api.inc"
.include "fileio/api.inc"
.include "history/api.inc"
.include "editor/api.inc"
.include "aux/api.inc"
.import se_overlay_call,se_overlay_frame
.export se_editor_file_call,se_editor_file_pump
.segment "CODE"
; Resident safe point only. Neither C10 nor C12 may recursively load C.
se_editor_file_call:
    sta se_overlay_frame
    lda #12
    ldx #1
    jsr se_overlay_call
    bcc return
    cmp #$20 ;admission errors; coordinator diagnostics are outside this range
    bcs return
    ldx se_f_owner
    cpx #1
    bne return ;failed initial admission has not acquired the union
    sta se_e_error
    lda #A_FILE_ABORT
    sta se_overlay_frame
    lda #AUX_ID
    ldx #1
    jsr se_overlay_call
    cmp #F_RECOVERY
    beq recovered
    ; If both command images are unavailable, close only known owned channels.
    ; Retain frame/owner/candidates/leases: no unproved canonical rollback.
    jsr $FFCC
    lda se_io_mode
    beq raw
    cmp #4
    bcs raw
    lda #FIO_DATA_LFN
    jsr $FFC3
    lda #0
    sta se_io_mode
raw:
    lda se_f_preflight_phase
    beq recovered
    cmp #4
    bcs recovered
    lda #7
    jsr $FFC3
    lda #0
    sta se_f_preflight_phase
recovered:
    lda #F_RECOVERY
    sta se_f_error
    lda #0
    clc ;root consumes any committed2 result before showing retained recovery
return:
    rts

; One action or one coordinator slice per service. Action results live in the
; phase-owned union; consume each request once before reentering C12.
se_editor_file_pump:
    lda se_f_request
    beq step
    cmp #FA_HISTORY_INIT
    beq history
    cmp #FA_HISTORY_SAVED
    beq history
    cmp #FT_INIT
    bcc invalid
    cmp #FT_EXISTS_BEGIN+1
    bcs invalid
    sta se_overlay_frame
    lda #10
    ldx #1
    jsr se_overlay_call
    jmp result
history:
    and #$0F ;E1→H_INIT1, E8→H_SAVED8
    jsr se_history_call
    jmp result
invalid:
    lda #FIO_STATE
    sec
result:
    sta se_f_result
    lda #0
    rol
    sta se_f_carry
    lda #0
    sta se_f_request
    lda #1
    clc
    rts
step:
    lda #F_STEP
    jmp se_editor_file_call
