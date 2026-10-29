.setcpu "6502"
.macpack longbranch
.import se_reu_map, se_reu_logical_owner, se_reu_physical_owner
.ifdef EDITOR_MANAGED_CODE
.import se_overlay_unverify
.endif
.export se_reu_copy, se_reu_c64, se_reu_offset, se_reu_length, se_reu_logical
.export se_reu_dma_calls, se_reu_dma_bytes

.segment "BSS"
; Resident nonreentrant request frame. All lengths are exact, never zero=64KiB.
se_reu_c64: .res 2
se_reu_offset: .res 2
se_reu_length: .res 2
se_reu_logical: .res 1
se_reu_dma_calls: .res 2
se_reu_dma_bytes: .res 3
dma_direction: .res 1
dma_end: .res 2
dma_physical: .res 1

.segment "CODE"
; A=0 stash, A=1 fetch. C clear/A=0 on success; C set/A error on failure.
; Clobbers A/X/Y/P. Validates the entire transfer before any REU register write.
; This one-bank primitive rejects crossings; object iterators split at mappings.
; C64 buffers must be wholly within $4000-$BFFF, excluding resident code/state,
; hardware stack, I/O and the ReadyOS shim. The bootstrap one-byte presence
; probe remains a separate, fixed-address routine with its own saved byte.
se_reu_copy:
    cmp #2
    jcs @direction
    sta dma_direction
    lda se_reu_length
    ora se_reu_length+1
    jeq @length
    lda se_reu_c64+1
    cmp #$40
    jcc @range
    lda se_reu_c64
    clc
    adc se_reu_length
    sta dma_end
    lda se_reu_c64+1
    adc se_reu_length+1
    jcs @range
    cmp #$C0
    bcc @host_valid
    jne @range
    lda dma_end
    jne @range
@host_valid:
    lda se_reu_offset
    clc
    adc se_reu_length
    sta dma_end
    lda se_reu_offset+1
    adc se_reu_length+1
    bcc @bank_valid
    ; Exactly $10000 is allowed as an exclusive end, never past that boundary.
    jne @range
    lda dma_end
    jne @range
@bank_valid:
    ldx se_reu_logical
    lda se_reu_logical_owner,x
.ifdef EDITOR_MANAGED_CODE
    jeq @handle
.else
    beq @handle
.endif
    cmp #$FF
.ifdef EDITOR_MANAGED_CODE
    jeq @handle
.else
    beq @handle
.endif
    ldy se_reu_map,x
    cmp se_reu_physical_owner,y
    bne @handle
    sty dma_physical
.ifdef EDITOR_MANAGED_CODE
    ldy dma_direction
    bne :+
    sty $CC4D ;all checked CPU->REU writes revoke preview body verification
    cmp #2
    bne :+
    jsr se_overlay_unverify
:
.endif
    php
    sei
    lda se_reu_c64
    sta $DF02
    lda se_reu_c64+1
    sta $DF03
    lda se_reu_offset
    sta $DF04
    lda se_reu_offset+1
    sta $DF05
    lda dma_physical
    sta $DF06
    lda se_reu_length
    sta $DF07
    lda se_reu_length+1
    sta $DF08
    lda #0
    sta $DF09
    sta $DF0A
    lda dma_direction
    ora #$90
    sta $DF01
    plp
    inc se_reu_dma_calls
    bne :+
    inc se_reu_dma_calls+1
:
    lda se_reu_dma_bytes
    clc
    adc se_reu_length
    sta se_reu_dma_bytes
    lda se_reu_dma_bytes+1
    adc se_reu_length+1
    sta se_reu_dma_bytes+1
    bcc :+
    inc se_reu_dma_bytes+2
:
    lda #0
    clc
    rts
@direction:
    lda #5
    bne @error
@length:
    lda #2
    bne @error
@range:
    lda #3
    bne @error
@handle:
    lda #4
@error:
    sec
    rts
