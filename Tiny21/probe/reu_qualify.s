.setcpu "6502"
.macpack longbranch
.import reu_transfer, REU_TILE
.importzp reu_addr, reu_ram, reu_size, reu_banks, reu_direction
.export qualify_reu, REU_QUALIFICATION_RESULT

RESULT = $ce20
REU_QUALIFICATION_RESULT = RESULT
RANGE_SIZE = 16
LAST_LOWER_TAIL = 30
WRAP_GUARD = 32
UPPER_HEAD = 33
RANGES = 34
saved_ptr = $f6

.segment "PROBEBSS"
original: .res RANGES * RANGE_SIZE
range:    .res 1
stage:    .res 1

.segment "PROBE"
; Cold diagnostic. Save all ranges before writing any, so aliased banks
; can be restored as well. Publish the first test failure independently
; from any restoration failure. The model is admitted only after success.
.proc qualify_reu
    lda #0
    ldx #9
clear:
    sta RESULT,x
    dex
    bpl clear
    .repeat 4, I
        lda signature+I
        sta RESULT+I
    .endrepeat
    lda #32
    sta reu_banks
    lda #1
    sta stage
    jsr save_ranges
    bcc saved
    jsr record_failure
    sec
    rts
saved:
    jsr test_ranges
    bcc restore
    jsr record_failure
restore:
    jsr restore_ranges
    lda RESULT+4
    ora RESULT+7
    beq success
    sec
    rts
success:
    clc
    rts
.endproc

; RESULT layout after signature: failed stage, range, backups, restoration
; errors, verified originals, and the mask of deliberately invalid spans.
.proc record_failure
    lda stage
    sta RESULT+4
    lda range
    sta RESULT+5
    rts
.endproc

.proc save_ranges
    lda #0
    sta range
next:
    jsr span
    jsr read
    bcs done
    jsr saved_address
    ldy #RANGE_SIZE-1
copy:
    lda REU_TILE,y
    sta (saved_ptr),y
    eor #$ff
    sta REU_TILE,y
    dey
    bpl copy
    ; Require a repeatable read that actually overwrites the poisoned tile
    ; before any REU write is allowed.
    jsr span
    jsr read
    bcs done
    jsr verify_saved
    bcs done
    inc RESULT+6
    inc range
    lda range
    cmp #RANGES
    bcc next
    clc
done:
    rts
.endproc

.proc test_ranges
    inc stage
    lda #0
    sta range
paint:
    ldy #RANGE_SIZE-1
bytes:
    lda signature_bytes,y
    eor range
    sta REU_TILE,y
    dey
    bpl bytes
    jsr span
    jsr write
    jcs done
    inc range
    lda range
    cmp #RANGES
    bcc paint

    ; A 32-byte write crosses $F7FFFF->$F80000. Both halves are different
    ; from the initial tags. $F00000 remains a separate wrap guard.
    inc stage
    lda #LAST_LOWER_TAIL
    sta range
    ldy #RANGE_SIZE-1
pair:
    lda signature_bytes,y
    eor #(LAST_LOWER_TAIL ^ $80)
    sta REU_TILE,y
    lda signature_bytes,y
    eor #(UPPER_HEAD ^ $80)
    sta REU_TILE+RANGE_SIZE,y
    dey
    bpl pair
    jsr crossing
    jsr write
    jcs done

    inc stage
    lda #0
    sta range
verify:
    jsr span
    jsr read
    bcs done
    lda range
    cmp #LAST_LOWER_TAIL
    beq changed
    cmp #UPPER_HEAD
    bne tag
changed:
    eor #$80
tag:
    tax
    ldy #RANGE_SIZE-1
verify_byte:
    txa
    eor signature_bytes,y
    cmp REU_TILE,y
    bne mismatch
    dey
    bpl verify_byte
    inc range
    lda range
    cmp #RANGES
    bcc verify

    inc stage
    lda #LAST_LOWER_TAIL
    sta range
    jsr crossing
    jsr read
    bcs done
    ldy #RANGE_SIZE-1
verify_pair:
    lda signature_bytes,y
    eor #(LAST_LOWER_TAIL ^ $80)
    cmp REU_TILE,y
    bne mismatch
    lda signature_bytes,y
    eor #(UPPER_HEAD ^ $80)
    cmp REU_TILE+RANGE_SIZE,y
    bne mismatch
    dey
    bpl verify_pair

    inc stage
    lda #31
    sta reu_banks
    lda #UPPER_HEAD
    sta range
    jsr span
    jsr read
    php
    inc reu_banks
    plp
    bcc mismatch
    inc RESULT+9
    lda #31
    sta range
    jsr span
    inc reu_size
    jsr read
    bcc mismatch
    inc RESULT+9
    clc
    rts
mismatch:
    sec
done:
    rts
.endproc

.proc restore_ranges
    lda #0
    sta range
restore:
    jsr saved_address
    ldy #RANGE_SIZE-1
copy:
    lda (saved_ptr),y
    sta REU_TILE,y
    dey
    bpl copy
    jsr span
    jsr write
    bcc next
    inc RESULT+7
next:
    inc range
    lda range
    cmp #RANGES
    bcc restore

    lda #0
    sta range
verify:
    jsr span
    jsr read
    bcs failed
    jsr saved_address
    jsr verify_saved
    bcs failed
    inc RESULT+8
    jmp advance
failed:
    inc RESULT+7
advance:
    inc range
    lda range
    cmp #RANGES
    bcc verify
    rts
.endproc

.proc verify_saved
    ldy #RANGE_SIZE-1
check:
    lda (saved_ptr),y
    cmp REU_TILE,y
    bne mismatch
    dey
    bpl check
    clc
    rts
mismatch:
    sec
    rts
.endproc

.proc saved_address
    lda range
    lsr
    lsr
    lsr
    lsr
    sta saved_ptr+1
    lda range
    asl
    asl
    asl
    asl
    clc
    adc #<original
    sta saved_ptr
    lda saved_ptr+1
    adc #>original
    sta saved_ptr+1
    rts
.endproc

crossing:
    jsr span
    lda #2*RANGE_SIZE
    sta reu_size
    rts

.proc span
    lda range
    cmp #WRAP_GUARD
    bcs head
    asl
    asl
    asl
    ora #7
    sta reu_addr+2
    lda #$ff
    sta reu_addr+1
    lda #$f0
    bne low
head:
    lda #$f0
    ldx range
    cpx #UPPER_HEAD
    bne :+
    lda #$f8
:
    sta reu_addr+2
    lda #0
    sta reu_addr+1
low:
    sta reu_addr
    lda #<REU_TILE
    sta reu_ram
    lda #>REU_TILE
    sta reu_ram+1
    lda #RANGE_SIZE
    sta reu_size
    lda #0
    sta reu_size+1
    rts
.endproc

read:
    lda #1
    bne transfer
write:
    lda #0
transfer:
    sta reu_direction
    jmp reu_transfer

signature: .byte "T64R"
signature_bytes:
    .byte $11,$e3,$4d,$90,$2a,$83,$fb,$62,$d8,$56,$1c,$47,$a9,$f4,$09,$b2
