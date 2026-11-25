.setcpu "6502"
.import model_open, verify_model_image, reu_transfer, REU_TILE
.importzp reu_addr, reu_ram, reu_size, reu_banks, reu_direction
.export scan_reu_model, active_model, requested_model, slot_banks

.segment "PROBEBSS"
active_model:    .res 1
requested_model: .res 1
first_byte:      .res 1
second_byte:     .res 1
test_byte:       .res 1

.segment "PROBE"
; The images share the same model address. The cache starts at $080000.
slot_banks: .byte 0, 0, 0

; Return 0 for a verified image, 1 for no REU, 2 for insufficient capacity,
; 3 for an unrecognized image, or 4 for a failed integrity check.
.proc scan_reu_model
    lda #$ff
    sta active_model
    jsr check_capacity
    bne done
    sta reu_addr
    sta reu_addr+1
    sta reu_addr+2
    ldx #1
    lda #64
    jsr transfer
    bcs absent
    ldx #3
signature:
    lda REU_TILE,x
    cmp magic,x
    bne unknown
    dex
    bpl signature
    lda REU_TILE+4
    cmp #3
    beq tiny
    cmp #4
    bne unknown
    ldx #10
programmer:
    lda REU_TILE+53,x
    cmp programmer_name,x
    bne try_japanese
    dex
    bpl programmer
    lda #1
    bne verify
try_japanese:
    ldx #10
japanese:
    lda REU_TILE+53,x
    cmp japanese_name,x
    bne unknown
    dex
    bpl japanese
    lda #2
    bne verify
tiny:
    lda #0
verify:
    sta requested_model
    jsr verify_model_image
    bcs invalid
    jsr model_open
    bcs invalid
    lda requested_model
    sta active_model
    lda #0
done:
    rts
absent:
    lda #1
    rts
unknown:
    lda #3
    rts
invalid:
    lda #4
    rts
.endproc

; Check distinct storage 512 KiB apart outside both the weights and cache.
; Confirm a clean read before writing, then restore the one modified byte.
.proc check_capacity
    lda #2
    sta reu_banks
    jsr read_first
    bcs absent
    lda REU_TILE
    sta first_byte
    eor #$ff
    sta test_byte
    sta REU_TILE
    jsr read_first
    bcs absent
    lda REU_TILE
    cmp first_byte
    bne absent
    jsr read_second
    bcs small
    lda REU_TILE
    sta second_byte
    lda test_byte
    sta REU_TILE
    jsr write_first
    bcs restore_failed
    jsr read_first
    bcs restore_failed
    lda REU_TILE
    cmp test_byte
    bne restore_failed
    jsr read_second
    bcs restore_failed
    lda REU_TILE
    cmp second_byte
    bne restore_failed
    lda #0
    beq restore
restore_failed:
    lda #2
restore:
    pha
    lda first_byte
    sta REU_TILE
    jsr write_first
    bcs restore_error
    jsr read_first
    bcs restore_error
    lda REU_TILE
    cmp first_byte
    bne restore_error
    pla
    rts
restore_error:
    pla
small:
    lda #2
    rts
absent:
    lda #1
    rts
.endproc

read_second:
    ldx #1
    lda #$0f
    bne scratch
read_first:
    ldx #1
    bne first
write_first:
    ldx #0
first:
    lda #$07
scratch:
    sta reu_addr+2
    lda #$ff
    sta reu_addr+1
    lda #$f0
    sta reu_addr
    lda #1
transfer:
    stx reu_direction
    sta reu_size
    lda #<REU_TILE
    sta reu_ram
    lda #>REU_TILE
    sta reu_ram+1
    lda #0
    sta reu_size+1
    jmp reu_transfer

magic:           .byte "T64M"
programmer_name: .byte "C64PROGINFO"
japanese_name:   .byte "E2JROMAJI", 0, 0
