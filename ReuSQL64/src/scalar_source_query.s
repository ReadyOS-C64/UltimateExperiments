; Compact source mapping for streamed scalar reads in metadata slot 0.
; Direct wide joins retain their third schema and row in g_rsql_execution,
; encoded with RSQL_SOURCE_SUBQUERY ($40). Keeping this mapping in assembly
; avoids spending the metadata sidecar's last bytes on cc65 pointer arithmetic.
;
; These offsets mirror RsqlExecutionState and RsqlCursorState in rsql_query.h.
; The memory-map regression catches accidental growth, while functional wide
; scalar tests exercise all three source lanes.

        .import _g_rsql_cursor
        .import _g_rsql_execution
        .export _rsql_query_scalar_source_column
        .export _rsql_query_scalar_source_row

EXEC_COLUMNS = 5
EXEC_ROW = 205
CURSOR_COLUMNS = 737
CURSOR_JOIN_COLUMNS = 937
CURSOR_ROW = 1137
CURSOR_SCAN_ROW = 1377

        .segment "BSS"
scalar_source: .res 1
scalar_offset: .res 1

        .segment "OVERLAY0"

; fastcall: source descriptor in A, pointer returned in A/X.
_rsql_query_scalar_source_column:
        sta scalar_source
        and #$07
        tax
        lda column_offsets,x
        sta scalar_offset
        lda scalar_source
        and #$40
        bne @execution
        lda scalar_source
        bmi @inner
        lda #<(_g_rsql_cursor+CURSOR_COLUMNS)
        ldx #>(_g_rsql_cursor+CURSOR_COLUMNS)
        bne @add
@inner:
        lda #<(_g_rsql_cursor+CURSOR_JOIN_COLUMNS)
        ldx #>(_g_rsql_cursor+CURSOR_JOIN_COLUMNS)
        bne @add
@execution:
        lda #<(_g_rsql_execution+EXEC_COLUMNS)
        ldx #>(_g_rsql_execution+EXEC_COLUMNS)
@add:
        clc
        adc scalar_offset
        bcc @done
        inx
@done:
        rts

column_offsets:
        .byte 0, 25, 50, 75, 100, 125, 150, 175

; fastcall: source descriptor in A, pointer returned in A/X.
_rsql_query_scalar_source_row:
        sta scalar_source
        and #$40
        bne @execution
        lda scalar_source
        bmi @inner
        lda #<(_g_rsql_cursor+CURSOR_ROW)
        ldx #>(_g_rsql_cursor+CURSOR_ROW)
        rts
@inner:
        lda #<(_g_rsql_cursor+CURSOR_SCAN_ROW)
        ldx #>(_g_rsql_cursor+CURSOR_SCAN_ROW)
        rts
@execution:
        lda #<(_g_rsql_execution+EXEC_ROW)
        ldx #>(_g_rsql_execution+EXEC_ROW)
        rts
