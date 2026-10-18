        .import _g_shape_scalar_result, _g_shape_scalar_buffer
        .import _rsql_shape_compare_scalar_c
        .import addysp, subysp
        .importzp sp

        .export _rsql_shape_compare_scalar

        .segment "OVERLAY4"

; Reserve one complete CHAR(255) payload on the already-budgeted cc65 stack.
; Slot 4 caches the first target part there; the final part can remain in the
; execution row because no later target read can overwrite it.
_rsql_shape_compare_scalar:
        sta _g_shape_scalar_result
        ldy #255
        jsr subysp
        lda sp
        sta _g_shape_scalar_buffer
        lda sp+1
        sta _g_shape_scalar_buffer+1
        jsr _rsql_shape_compare_scalar_c
        pha
        ldy #255
        jsr addysp
        pla
        ldx #0
        cmp #$80
        bcc :+
        dex
:
        rts
