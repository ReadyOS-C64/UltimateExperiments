; Every result-producing overlay exposes the same entry address.  The ABI
; dispatcher can therefore choose the cache slot, load it, and tail-call one
; fixed address without retaining a cross-overlay function pointer.  Keep the
; wide result iterator first in OVERLAY8 as well; the schema helper is called
; by its linked address and must not displace the $7C00 dispatch entry.

        .import _rsql_query_aggregate_result_next_phase
        .import _rsql_query_join_result_next_phase
        .import _rsql_query_join_aggregate_result_next_phase
        .import _rsql_query_result_next_phase
        .import _rsql_query_wide_result_next_phase
        .import _rsql_query_prepare_result_table_phase_c
        .import _g_rsql_execution, _g_rsql_cursor
        .importzp ptr1

        .export _rsql_query_prepare_result_table_phase
        .export _rsql_query_parse_phase_id
        .export _rsql_result_source_column

        .segment "OVERLAY8"
        jmp _rsql_query_wide_result_next_phase

; cc65 2.18 places two unused words at the C implementation's exported label.
; Keep the public parser-phase entry on executable code, as with the larger
; join continuations, and skip those four data bytes explicitly.
        .segment "OVERLAY8"
_rsql_query_prepare_result_table_phase:
        jmp _rsql_query_prepare_result_table_phase_c + 4

; Fastcall source descriptor in A. RsqlColumnInfo is 25 bytes and the SQL
; source mask leaves only the low three bits as the column ordinal.
_rsql_result_source_column:
        tay
        and #$07
        tax
        lda result_column_offsets,x
        sta ptr1
        tya
        and #$40
        bne @subquery
        tya
        bmi @inner
        lda #<(_g_rsql_cursor+737)
        ldx #>(_g_rsql_cursor+737)
        bne @add
@inner:
        lda #<(_g_rsql_cursor+937)
        ldx #>(_g_rsql_cursor+937)
        bne @add
@subquery:
        lda #<(_g_rsql_execution+5)
        ldx #>(_g_rsql_execution+5)
@add:
        clc
        adc ptr1
        bcc @done
        inx
@done:
        rts

result_column_offsets:
        .byte 0, 25, 50, 75, 100, 125, 150, 175

        .segment "OVERLAY2"
_rsql_query_parse_phase_id:
        lda #$52
        ldx #$00
        rts

        .segment "OVERLAY1"
        jmp _rsql_query_aggregate_result_next_phase

        .segment "OVERLAY4"
        jmp _rsql_query_join_result_next_phase

        .segment "OVERLAY5"
        jmp _rsql_query_result_next_phase

        .segment "OVERLAY6"
        jmp _rsql_query_join_aggregate_result_next_phase
