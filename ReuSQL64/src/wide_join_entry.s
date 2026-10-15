; cc65 2.19 gives these three internal continuations different prefixes:
; raw-next has four unused anonymous pointer words, aggregate-next begins with
; executable code, and aggregate-current has a five-byte local initializer.
; Keep a separately verified executable entry for each function.

        .import _rsql_query_wide_join_next_phase_c
        .import _rsql_query_indexed_join_next_phase_c
        .import _rsql_query_wide_restore_phase_c
        .import _rsql_wide_aggregate_next_c
        .import _rsql_wide_raw_next_c
        .import _aggregate_current_c
        .import _g_rsql_meta_page0
        .import _g_wide_candidate
        .importzp ptr1, ptr2
        .export _rsql_query_wide_join_next_phase
        .export _rsql_query_indexed_join_next_phase
        .export _rsql_query_wide_restore_phase
        .export _rsql_wide_aggregate_next_entry
        .export _rsql_wide_raw_next_entry
        .export _aggregate_current_entry
        .export _rsql_wide_i64_divide

        .segment "OVERLAY8"

_rsql_query_wide_join_next_phase:
        jmp _rsql_query_wide_join_next_phase_c

_rsql_query_indexed_join_next_phase:
        ; Three compiler-emitted local words precede the executable prologue.
        jmp _rsql_query_indexed_join_next_phase_c+6

_rsql_query_wide_restore_phase:
        jmp _rsql_query_wide_restore_phase_c

_rsql_wide_aggregate_next_entry:
        jmp _rsql_wide_aggregate_next_c

_rsql_wide_raw_next_entry:
        jmp _rsql_wide_raw_next_c+8

; The accumulator has a five-byte compiler-emitted local initializer before
; its executable prologue.  Internal C calls must use this executable label.
_aggregate_current_entry:
        jmp _aggregate_current_c+5

; Divide the signed 64-bit numerator in A/X by its positive 64-bit count.
; The cursor's count array follows its value array by exactly 64 bytes.  The
; wide aggregate path owns the two metadata pages while finalizing, so the
; first 24 bytes of page 0 are bounded
; magnitude/remainder/quotient scratch rather than new C64 BSS.
_rsql_wide_i64_divide:
        sta ptr1
        stx ptr1+1
        clc
        adc #$40
        sta ptr2
        txa
        adc #$00
        sta ptr2+1
        ldy #$07
@copy_magnitude:
        lda (ptr1),y
        sta _g_rsql_meta_page0,y
        dey
        bpl @copy_magnitude
        ldy #$0F
        lda #$00
@clear_work:
        sta _g_rsql_meta_page0+8,y
        dey
        bpl @clear_work
        ldy #$07
        lda (ptr1),y
        bpl @divide
        sec
        ldy #$00
@negate_magnitude:
        lda _g_rsql_meta_page0,y
        eor #$FF
        adc #$00
        sta _g_rsql_meta_page0,y
        iny
        tya
        and #$08
        beq @negate_magnitude
@divide:
        ldx #$40
@bit:
        clc
        ldy #$00
@shift_magnitude:
        lda _g_rsql_meta_page0,y
        rol a
        sta _g_rsql_meta_page0,y
        iny
        tya
        and #$08
        beq @shift_magnitude
        ldy #$08
@shift_remainder:
        lda _g_rsql_meta_page0,y
        rol a
        sta _g_rsql_meta_page0,y
        iny
        tya
        and #$10
        beq @shift_remainder
        clc
        ldy #$10
@shift_quotient:
        lda _g_rsql_meta_page0,y
        rol a
        sta _g_rsql_meta_page0,y
        iny
        tya
        and #$08
        beq @shift_quotient
        ldy #$07
@compare:
        lda _g_rsql_meta_page0+8,y
        cmp (ptr2),y
        bcc @next_bit
        bne @subtract
        dey
        bpl @compare
@subtract:
        sec
        ldy #$00
@subtract_byte:
        lda _g_rsql_meta_page0+8,y
        sbc (ptr2),y
        sta _g_rsql_meta_page0+8,y
        iny
        tya
        and #$08
        beq @subtract_byte
        lda _g_rsql_meta_page0+16
        ora #$01
        sta _g_rsql_meta_page0+16
@next_bit:
        dex
        bne @bit
        ldy #$07
        lda (ptr1),y
        bpl @copy_quotient
        sec
        ldy #$00
@negate_quotient:
        lda _g_rsql_meta_page0+16,y
        eor #$FF
        adc #$00
        sta _g_rsql_meta_page0+16,y
        iny
        tya
        and #$08
        beq @negate_quotient
@copy_quotient:
        ldy #$07
@copy_result:
        lda _g_rsql_meta_page0+16,y
        sta (ptr1),y
        dey
        bpl @copy_result
        rts
