.setcpu "6502"
.macpack longbranch
.include "overlay/format.inc"
.import se_overlay_header, se_overlay_validate
.export se_overlay_read, se_file_device, se_file_status
.segment "ZEROPAGE"
file_ptr: .res 2
.segment "BSS"
se_file_device: .res 1 ; zero defaults to8, otherwise8/9 only
se_file_status: .res 1 ; original KERNAL status byte on I/O failure
file_count: .res 2
file_index: .res 1
file_value: .res 1
file_error: .res 1
.segment "CODE"
; A filename length1..16, X/Y pointer. Name is native PETSCII, read PRG/SEQ
; bytes as an ordinary stream. No KERNAL LOAD and no destination from a file.
; Fixed owned LFN2/SA2; closes it on EVERY attempted-open path, CLRCHN restores
; default channels. Caller must own foreground IEC and not have LFN2 open.
; Payload at5000, header in resident state. C/A=0 success, errors20 I/O,
;21 truncated,22 trailing bytes,23 bad device/name; header errors10..13.
; Clobbers A/X/Y/P, file_ptr. IRQ remains available during IEC handshakes.
se_overlay_read:
    cmp #1
    jcc @argument
    cmp #17
    jcs @argument
    jsr $FFBD ; SETNAM
    lda se_file_device
    beq @default
    cmp #8
    beq @device
    cmp #9
    jne @argument
    beq @device
@default:
    lda #8
@device:
    tax
    lda #2
    ldy #2
    jsr $FFBA ; SETLFS
    lda #0
    sta se_file_status
    sta file_error
    sta file_index
    jsr $FFC0 ; OPEN
    jcs @io
    jsr $FFB7 ; READST
    jne @io_status
    ldx #2
    jsr $FFC6 ; CHKIN
    jcs @io
@header:
    jsr read_byte
    bcs @finish
    ldx file_index
    sta se_overlay_header,x
    inc file_index
    lda se_file_status
    bne @short ; nonempty payload must follow header
    lda file_index
    cmp #OVL_HEADER
    bcc @header
    jsr se_overlay_validate
    bcs @save_error
.ifdef EDITOR_MANAGED_CODE
    lda #0
    sta $CBD5 ;invalidate before first payload write, including partial reads
.endif
    lda #<OVL_STAGE
    sta file_ptr
    lda #>OVL_STAGE
    sta file_ptr+1
    lda se_overlay_header+8
    sta file_count
    lda se_overlay_header+9
    sta file_count+1
@body:
    jsr read_byte
    bcs @finish
    ldy #0
    sta (file_ptr),y
    inc file_ptr
    bne :+
    inc file_ptr+1
:
    lda file_count
    bne :+
    dec file_count+1
:
    dec file_count
    lda file_count
    ora file_count+1
    beq @last
    lda se_file_status
    beq @body
@short:
    lda #$21
    bne @save_error
@last:
    lda se_file_status
    cmp #$40 ; EOI belongs to the final valid byte
    beq @finish
    lda #$22
    bne @save_error
@io:
    jsr $FFB7
@io_status:
    sta se_file_status
    lda #$20
@save_error:
    sta file_error
@finish:
    jsr $FFCC ; CLRCHN, including failed CHKIN
    lda #2
    jsr $FFC3 ; CLOSE, including a failed OPEN
    lda file_error
    beq @ok
    sec
    rts
@ok:
    clc
    rts
@argument:
    lda #$23
    sec
    rts

read_byte:
    jsr $FFCF ; CHRIN
    sta file_value
    jsr $FFB7 ; READST
    sta se_file_status
    and #$BF ; bit6 EOI is success with one final byte
    bne @io_error
    lda file_value
    clc
    rts
@io_error:
    lda #$20
    sta file_error
    sec
    rts
