; Stream a two-part TEXT concatenation without materialising either value.
;
; Each prepared part is either fixed bytes (a trimmed CHAR or literal) or a
; stable TEXT handle.  The helper consumes the public slice across both parts,
; copying fixed bytes directly and delegating one TEXT range at a time to the
; validated blob reader. Query entry points are non-reentrant, so one compact
; workspace is sufficient.

        .import _memcpy
        .import _rsql_blob_read
        .import axulong, pusheax, pushax
        .importzp ptr1, sreg

        .export _g_scalar_concat_request
        .export _g_scalar_concat_left
        .export _g_scalar_concat_right
        .export _g_scalar_concat_left_length
        .export _g_scalar_concat_right_length
        .export _g_scalar_concat_text_mask
        .export _rsql_scalar_variable_concat

REQ_OFFSET      = 2
REQ_DESTINATION = 4
REQ_CAPACITY    = 6
REQ_BYTES_READ  = 8

RSQL_OK                  = 0
RSQL_ERR_UNSUPPORTED_SQL = 17

        .segment "BSS"

_g_scalar_concat_request:        .res 2
_g_scalar_concat_left:           .res 2
_g_scalar_concat_right:          .res 2
_g_scalar_concat_left_length:    .res 2
_g_scalar_concat_right_length:   .res 2
_g_scalar_concat_text_mask:      .res 1

concat_available: .res 2
concat_offset:    .res 2
concat_piece:     .res 2
concat_copied:    .res 2
concat_data:      .res 2
concat_length:    .res 2
concat_text:      .res 1
concat_rc:        .res 1

        .segment "OVERLAY0"

.macro LOAD_REQUEST
        lda _g_scalar_concat_request
        sta ptr1
        lda _g_scalar_concat_request+1
        sta ptr1+1
.endmacro

return_ok:
        lda #RSQL_OK
        ldx #$00
        rts

return_unsupported:
        lda #RSQL_ERR_UNSUPPORTED_SQL
        ldx #$00
        rts

; Limit concat_piece to the still-requested byte count.
limit_piece:
        lda concat_piece+1
        cmp concat_available+1
        bcc @done
        bne @use_available
        lda concat_piece
        cmp concat_available
        bcc @done
        beq @done
@use_available:
        lda concat_available
        sta concat_piece
        lda concat_available+1
        sta concat_piece+1
@done:  rts

; Publish bytes copied by one part and reset the relative offset for the next.
finish_part:
        LOAD_REQUEST
        ldy #REQ_BYTES_READ
        lda (ptr1),y
        clc
        adc concat_copied
        sta (ptr1),y
        iny
        lda (ptr1),y
        adc concat_copied+1
        sta (ptr1),y

        lda concat_available
        sec
        sbc concat_copied
        sta concat_available
        lda concat_available+1
        sbc concat_copied+1
        sta concat_available+1
        lda #$00
        sta concat_offset
        sta concat_offset+1
        lda concat_rc
        ldx #$00
        rts

select_left:
        lda _g_scalar_concat_left
        sta concat_data
        lda _g_scalar_concat_left+1
        sta concat_data+1
        lda _g_scalar_concat_left_length
        sta concat_length
        lda _g_scalar_concat_left_length+1
        sta concat_length+1
        lda _g_scalar_concat_text_mask
        and #$01
        sta concat_text
        rts

select_right:
        lda _g_scalar_concat_right
        sta concat_data
        lda _g_scalar_concat_right+1
        sta concat_data+1
        lda _g_scalar_concat_right_length
        sta concat_length
        lda _g_scalar_concat_right_length+1
        sta concat_length+1
        lda _g_scalar_concat_text_mask
        and #$02
        sta concat_text
        rts

; Copy the selected part at concat_offset. If the public offset lies beyond
; this part, consume its length and leave the requested capacity unchanged.
copy_part:
        lda concat_offset+1
        cmp concat_length+1
        bcc @inside
        bne @skip
        lda concat_offset
        cmp concat_length
        bcc @inside
@skip:  lda concat_offset
        sec
        sbc concat_length
        sta concat_offset
        lda concat_offset+1
        sbc concat_length+1
        sta concat_offset+1
        jmp return_ok

@inside:
        lda concat_length
        sec
        sbc concat_offset
        sta concat_piece
        lda concat_length+1
        sbc concat_offset+1
        sta concat_piece+1
        jsr limit_piece
        lda concat_text
        bne copy_text

copy_fixed:
        LOAD_REQUEST
        ldy #REQ_DESTINATION
        lda (ptr1),y
        sta sreg
        iny
        lda (ptr1),y
        sta sreg+1
        ldy #REQ_BYTES_READ
        lda (ptr1),y
        clc
        adc sreg
        pha
        iny
        lda (ptr1),y
        adc sreg+1
        tax
        pla
        jsr pushax

        lda concat_data
        clc
        adc concat_offset
        pha
        lda concat_data+1
        adc concat_offset+1
        tax
        pla
        jsr pushax
        lda concat_piece
        ldx concat_piece+1
        jsr _memcpy

        lda concat_piece
        sta concat_copied
        lda concat_piece+1
        sta concat_copied+1
        lda #RSQL_OK
        sta concat_rc
        jmp finish_part

copy_text:
        lda concat_data
        ldx concat_data+1
        jsr pushax
        lda concat_offset
        ldx concat_offset+1
        jsr axulong
        jsr pusheax

        LOAD_REQUEST
        ldy #REQ_DESTINATION
        lda (ptr1),y
        sta sreg
        iny
        lda (ptr1),y
        sta sreg+1
        ldy #REQ_BYTES_READ
        lda (ptr1),y
        clc
        adc sreg
        pha
        iny
        lda (ptr1),y
        adc sreg+1
        tax
        pla
        jsr pushax

        lda concat_piece
        ldx concat_piece+1
        jsr pushax
        lda #<concat_copied
        ldx #>concat_copied
        jsr _rsql_blob_read
        sta concat_rc
        bne @error
        jmp finish_part
@error: ldx #$00
        rts

_rsql_scalar_variable_concat:
        ; total = left length + right length; public result lengths are u16.
        lda _g_scalar_concat_left_length
        clc
        adc _g_scalar_concat_right_length
        sta concat_available
        lda _g_scalar_concat_left_length+1
        adc _g_scalar_concat_right_length+1
        sta concat_available+1
        bcc @sum_ok
        jmp return_unsupported
@sum_ok:

        LOAD_REQUEST
        ldy #REQ_OFFSET
        lda (ptr1),y
        sta concat_offset
        iny
        lda (ptr1),y
        sta concat_offset+1

        ; An offset at or beyond the logical result is a successful empty read.
        lda concat_offset+1
        cmp concat_available+1
        bcc @in_range
        beq @compare_low
        jmp return_ok
@compare_low:
        lda concat_offset
        cmp concat_available
        bcc @in_range
        jmp return_ok
@in_range:
        lda concat_available
        sec
        sbc concat_offset
        sta concat_available
        lda concat_available+1
        sbc concat_offset+1
        sta concat_available+1

        ; available = min(total - offset, request capacity).
        ldy #REQ_CAPACITY
        lda (ptr1),y
        sta concat_piece
        iny
        lda (ptr1),y
        sta concat_piece+1
        lda concat_available+1
        cmp concat_piece+1
        bcc @capacity_done
        bne @use_capacity
        lda concat_available
        cmp concat_piece
        bcc @capacity_done
        beq @capacity_done
@use_capacity:
        lda concat_piece
        sta concat_available
        lda concat_piece+1
        sta concat_available+1
@capacity_done:
        lda concat_available
        ora concat_available+1
        beq @ok

        jsr select_left
        jsr copy_part
        bne @done
        lda concat_available
        ora concat_available+1
        beq @ok
        jsr select_right
        jmp copy_part
@done:  ldx #$00
        rts
@ok:   jmp return_ok
