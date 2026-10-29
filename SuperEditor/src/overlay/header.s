.setcpu "6502"
.macpack longbranch
.include "overlay/format.inc"
.import se_overlay_call, se_overlay_frame, se_overlay_binding_digest
.import se_crc_init, se_crc_byte, se_crc_value
.export se_overlay_header, se_overlay_validate, se_overlay_header_fixed_entry
se_overlay_header_fixed_entry = EDITOR_FIXED_ENTRY
.segment "BSS"
se_overlay_header: .res OVL_HEADER
.segment "CODE"
; Header only; payload CRC is checked by import. No mutation on failure.
; C clear success; C set A=$10 malformed, $11 ABI, $12 slot/ID,
; $13 size/entry. Header CRC also covers slot/ID/length/entry/binding.
se_overlay_validate:
    ldx #3
@magic:
    lda se_overlay_header,x
    cmp magic,x
    jne @format
    dex
    bpl @magic
    lda se_overlay_header+7
    jne @format
    lda se_overlay_header+4
    cmp #2
    jne @abi
    ldx #3
@binding:
    lda se_overlay_header+16,x
    cmp binding,x
.if EDITOR_FIXED_ENTRY
    bne @abi
.else
    jne @abi
.endif
    dex
    bpl @binding
    ldx #OVL_BINDING_BYTES-1
@digest:
    lda se_overlay_header+20,x
    cmp se_overlay_binding_digest,x
    bne @abi
    dex
    bpl @digest
    lda se_overlay_header+5
    cmp #2
    bcs @identity
    lda se_overlay_header+6
    beq @identity
    lda se_overlay_header+8
    ora se_overlay_header+9
    beq @size
    lda se_overlay_header+9
    cmp #$10
    bcc @entry
    bne @size
    lda se_overlay_header+8
    bne @size
@entry:
.if EDITOR_FIXED_ENTRY
    ; Compact editor catalogs do not retain arbitrary entry pointers.
    lda se_overlay_header+11
    bne @size
    lda se_overlay_header+10
    cmp #OVL_BINDING_BYTES
    bne @size
    lda se_overlay_header+9
    bne @ok
    lda se_overlay_header+8
    cmp #OVL_BINDING_BYTES+1
    bcc @size
.else
    lda se_overlay_header+11
    bne @entry_high
    lda se_overlay_header+10
    cmp #OVL_BINDING_BYTES
    bcc @size
@entry_high:
    lda se_overlay_header+11
    cmp se_overlay_header+9
    bcc @ok
    bne @size
    lda se_overlay_header+10
    cmp se_overlay_header+8
    bcs @size
.endif
@ok:
    jsr se_crc_init
    ldy #0
@header_crc:
    lda se_overlay_header,y
    jsr se_crc_byte
    iny
    cpy #14
    bne :+
    ldy #16 ; skip the header checksum itself
:
    cpy #OVL_HEADER
    bcc @header_crc
    lda se_crc_value
    cmp se_overlay_header+14
    bne @format
    lda se_crc_value+1
    cmp se_overlay_header+15
    bne @format
    lda #0
    clc
    rts
@format:
    lda #$10
    bne @error
@abi:
    lda #$11
    bne @error
@identity:
    lda #$12
    bne @error
@size:
    lda #$13
@error:
    sec
    rts
.segment "RODATA"
magic: .byte $53,$45,$4F,$32
binding: .word se_overlay_call, se_overlay_frame
