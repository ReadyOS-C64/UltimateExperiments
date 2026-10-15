; cc65 2.18 emits three unused two-byte temporaries immediately after the
; exported label for the duplicated join continuation. Keep callers on the
; first executable instruction, matching the ordinary join entry trampoline.

.segment "OVERLAY6"

.import _rsql_query_join_aggregate_source_next_phase_c
.importzp ptr1, tmp1
.export _rsql_query_join_aggregate_source_next_phase
.export _rsql_join_aggregate_column_mask
.export _rsql_join_aggregate_i64_increment
.export _rsql_join_aggregate_i64_zero
.export _rsql_join_aggregate_i64_negate
.export _rsql_join_aggregate_integer_width

_rsql_query_join_aggregate_source_next_phase:
        jmp _rsql_query_join_aggregate_source_next_phase_c + 6

column_masks:
        .byte $01, $02, $04, $08, $10, $20, $40, $80
integer_widths:
        .byte $01, $02, $04, $08, $02

_rsql_join_aggregate_column_mask:
        and #$07
        tax
        lda column_masks,x
        ldx #$00
        rts

_rsql_join_aggregate_integer_width:
        sec
        sbc #$02
        tax
        lda integer_widths,x
        ldx #$00
        rts

_rsql_join_aggregate_i64_increment:
        sta ptr1
        stx ptr1+1
        ldy #$00
increment_loop:
        lda (ptr1),y
        clc
        adc #$01
        sta (ptr1),y
        bne increment_done
        iny
        cpy #$08
        bne increment_loop
increment_done:
        rts

_rsql_join_aggregate_i64_zero:
        sta ptr1
        stx ptr1+1
        ldy #$00
zero_loop:
        lda (ptr1),y
        bne zero_false
        iny
        cpy #$08
        bne zero_loop
        lda #$01
        ldx #$00
        rts
zero_false:
        lda #$00
        tax
        rts

_rsql_join_aggregate_i64_negate:
        sta ptr1
        stx ptr1+1
        lda #$01
        sta tmp1
        ldy #$00
negate_loop:
        lda (ptr1),y
        eor #$FF
        clc
        adc tmp1
        sta (ptr1),y
        lda #$00
        adc #$00
        sta tmp1
        iny
        cpy #$08
        bne negate_loop
        rts
