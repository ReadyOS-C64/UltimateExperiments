.setcpu "6502"
.macpack longbranch
.include "platform.inc"
.include "history/api.inc"
.include "document/api.inc"
.import se_doc_probe, se_doc_result, se_reu_free, se_overlay_init
.import se_overlay_read, se_overlay_import, se_print, se_hex_byte
.importzp text_ptr, screen_ptr
.export se_history_probe, se_h_probe_screen
.export se_h_probe_result, se_h_probe_cases, se_h_probe_error
.segment "BSS"
se_h_probe_result: .res 1
se_h_probe_cases: .res 1
se_h_probe_error: .res 1
.segment "COLD"
se_history_probe:
    jsr se_doc_probe
    lda se_doc_result
    cmp #1
    jne failed
    inc se_h_probe_cases
    ldx #190
    jsr se_reu_free
    jcs failed
    ldx #191
    jsr se_reu_free
    jcs failed
    jsr se_overlay_init
    jcs failed
    lda #5
    ldx #<hedit
    ldy #>hedit
    jsr import
    jcs failed
    lda #5
    ldx #<hplay
    ldy #>hplay
    jsr import
    jcs failed
    jsr se_history_cold
    jcs failed
    lda #H_INIT
    jsr se_history_call
    jcs failed
    inc se_h_probe_cases
    lda #1
    sta se_h_group
    lda #'X'
    ldx #0
    jsr byte_edit
    jcs failed
    inc se_h_probe_cases
    lda #'Y'
    ldx #1
    jsr byte_edit
    jcs failed
    lda se_h_end
    cmp #75
    jne failed
    inc se_h_probe_cases
    lda #H_SAVED
    jsr se_history_call
    jcs failed
    lda se_h_dirty
    jne failed
    inc se_h_probe_cases
    lda #'Z'
    ldx #2
    jsr byte_edit
    jcs failed
    inc se_h_probe_cases
    lda #H_UNDO
    jsr playback
    jcs failed
    lda se_h_dirty
    jne failed
    inc se_h_probe_cases
    lda #H_REDO
    jsr playback
    jcs failed
    inc se_h_probe_cases
    ; Cancel a genuine selected-range replacement after private record writes.
    lda #0
    sta se_doc_edit_position
    sta se_h_before_caret
    lda #2
    sta se_doc_edit_delete
    lda #1
    sta se_doc_edit_insert
    sta se_h_after_caret
    lda #H_BEGIN
    jsr se_history_call
    jcs failed
    lda #H_STEP
    jsr se_history_call
    jcs failed
    lda #H_CANCEL
    jsr se_history_call
    jcs failed
    lda se_h_current
    cmp #4
    jne failed
    inc se_h_probe_cases
    lda #H_UNDO
    jsr playback
    jcs failed
    inc se_h_probe_cases
    lda #'Q'
    ldx #2
    jsr byte_edit
    jcs failed
    lda se_h_current
    cmp #5
    jne failed
    inc se_h_probe_cases
    lda #H_REDO
    jsr se_history_call
    jcs failed
    cmp #0
    jne failed
    inc se_h_probe_cases
    lda #H_UNDO
    jsr playback
    jcs failed
    inc se_h_probe_cases
    lda #H_REDO
    jsr playback
    jcs failed
    inc se_h_probe_cases
    lda #0
    sta se_doc_offset
    sta se_doc_offset+1
    sta se_doc_offset+2
    sta se_doc_count+1
    sta se_doc_c64
    lda #$80
    sta se_doc_c64+1
    lda #3
    sta se_doc_count
    jsr se_doc_read
    jcs failed
    lda $8000
    cmp #'X'
    jne failed
    lda $8001
    cmp #'Y'
    jne failed
    lda $8002
    cmp #'Q'
    jne failed
    lda #0
    sta $8003
    lda se_h_dirty
    cmp #1
    jne failed
    lda se_h_saved
    cmp #3
    jne failed
    lda se_doc_generation
    cmp #11
    jne failed
    inc se_h_probe_cases
    lda #1
    sta se_h_probe_result
    rts
failed:
    sta se_h_probe_error
    lda #$EE
    sta se_h_probe_result
    rts
; A native byte,X source position. Held on hardware stack only during prep.
byte_edit:
    pha
    stx se_doc_edit_position
    stx se_h_before_caret
    inx
    stx se_h_after_caret
    lda #0
    sta se_doc_edit_position+1
    sta se_doc_edit_position+2
    sta se_h_before_caret+1
    sta se_h_before_caret+2
    sta se_h_after_caret+1
    sta se_h_after_caret+2
    sta se_doc_edit_delete
    sta se_doc_edit_delete+1
    sta se_doc_edit_delete+2
    sta se_doc_edit_insert+1
    sta se_doc_edit_insert+2
    lda #1
    sta se_doc_edit_insert
    lda #H_BEGIN
    jsr se_history_call
    bcs @early_error
@prepare:
    lda se_h_phase
    cmp #H_FEEDING
    beq @feed
    lda #H_STEP
    jsr se_history_call
    bcs @early_error
    jmp @prepare
@feed:
    pla
    sta $8000
    lda #1
    sta se_doc_count
    lda #0
    sta se_doc_count+1
    sta se_doc_c64
    lda #$80
    sta se_doc_c64+1
    lda #H_FEED
    jsr se_history_call
    bcs @return
    jmp finish
@early_error:
    tax
    pla
    txa
    sec
@return:
    rts
playback:
    jsr se_history_call
    bcs @return
    cmp #0
    bne finish
    clc
@return:
    rts
finish:
    lda #H_STEP
    jsr se_history_call
    bcs @return
    cmp #1
    beq finish
    clc
@return:
    rts
import:
    jsr se_overlay_read
    bcs @return
    jmp se_overlay_import
@return:
    rts
se_h_probe_screen:
    PRINT_AT result,17,1
    lda se_h_probe_result
    jsr se_hex_byte
    stx VIC_SCREEN+17*40+25
    sta VIC_SCREEN+17*40+26
    PRINT_AT sequence,19,1
    PRINT_AT checkpoint,21,1
    lda se_h_dirty
    jsr se_hex_byte
    stx VIC_SCREEN+21*40+32
    sta VIC_SCREEN+21*40+33
    PRINT_AT prefix,22,1
    PRINT_AT $8000,22,17
    rts
result: .asciiz "Journal model result: "
sequence: .asciiz "Group XY / undo+redo / branch XYQ"
checkpoint: .asciiz "Checkpoint3 / node5 / dirty:"
prefix: .asciiz "Source prefix:"
hedit: .byte $48,$45,$44,$49,$54
hplay: .byte $48,$50,$4C,$41,$59
