.setcpu "6502"
.import model_open_at, verify_model_image, load_model_file
.export select_model, active_model, requested_model, slot_banks, model_disk_load

.segment "PROBEBSS"
active_model:    .res 1
requested_model: .res 1
model_disk_load: .res 1

.segment "PROBE"
slot_banks:
    .byte $00, $10

; A is the requested model number. Verify identity before changing the
; engine. The old slot and its payload are never touched by this load.
.proc select_model
    cmp #2
    bcs invalid
    cmp active_model
    beq unchanged
    sta requested_model
    lda #0
    sta model_disk_load
    jsr verify_model_image
    bcc admit
    jsr load_model_file
    bcs restore_selection
    inc model_disk_load
    jsr verify_model_image
    bcs restore_selection
admit:
    jsr open_slot
    bcs restore_engine
    lda requested_model
    sta active_model
unchanged:
    clc
    rts
restore_engine:
    lda active_model
    sta requested_model
    jsr open_slot
restore_selection:
    lda active_model
    sta requested_model
invalid:
    sec
    rts
.endproc

.proc open_slot
    ldx requested_model
    lda slot_banks,x
    jmp model_open_at
.endproc
