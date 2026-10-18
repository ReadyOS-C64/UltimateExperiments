; Phase-neutral result-next dispatch. Aggregate shaping is owned by slot 1,
; joined/subquery shaping by slot 4, joined aggregate shaping by slot 6, and
; ordinary/index shaping by slot 5.
; Each slot exposes its appropriate tail call at $7C00. The request pointer
; arrives in A/X under cc65 fastcall and is restored after loading the selected
; image.

        .import _g_rsql_cursor
        .import _rsql_overlay_load
        .import _rsql_query_cursor_column_phase
        .import _rsql_query_scalar_column_phase
        .import _rsql_query_variable_column_phase
        .import _rsql_api_error
        .import pusha
        .export _rsql_query_result_next_dispatch
        .export _rsql_cursor_column

CURSOR_MODE = 1
CURSOR_JOIN_TYPE = 16
CURSOR_SUBQUERY_KIND = 25

        .segment "BSS"
result_next_request: .res 2
column_request: .res 2
column_rc: .res 1

        .segment "ENGINE"

; Keep the ABI dispatcher at its hard $CFEF marker boundary. The resident
; region has room for this phase-neutral two-field predicate.
result_complex_slot:
        lda _g_rsql_cursor+CURSOR_SUBQUERY_KIND
        cmp #$04
        beq @wide
        ora _g_rsql_cursor+CURSOR_JOIN_TYPE
        beq @done
        lda _g_rsql_cursor+CURSOR_MODE
        asl
        adc #$02
@done:
        rts
@wide:
        lda #$07
        rts

; Preserve the request outside the software stack while loading overlays.
; This is also smaller than cc65's generated wrapper and remains safe for
; deeply nested, unoptimized clients whose request record lives near $7C00.
_rsql_cursor_column:
        sta column_request
        stx column_request+1
        lda #$01
        jsr _rsql_overlay_load
        sta column_rc
        bne @column_done
        lda column_request
        ldx column_request+1
        jsr _rsql_query_cursor_column_phase
        sta column_rc
        cmp #$FC
        bne @column_variable
        lda #$05
        jsr _rsql_overlay_load
        sta column_rc
        bne @column_done
        lda column_request
        ldx column_request+1
        jsr _rsql_query_scalar_column_phase
        sta column_rc
@column_variable:
        lda column_rc
        cmp #$FE
        bne @column_done
        lda #$00
        jsr _rsql_overlay_load
        sta column_rc
        bne @column_done
        lda column_request
        ldx column_request+1
        jsr _rsql_query_variable_column_phase
        sta column_rc
@column_done:
        lda column_rc
        jsr pusha
        lda #$00
        tax
        jmp _rsql_api_error

        .segment "ABI"

_rsql_query_result_next_dispatch:
        sta result_next_request
        stx result_next_request+1
        jsr result_complex_slot
        beq @not_complex
        bne @load
@not_complex:
        lda _g_rsql_cursor+CURSOR_MODE
        lsr
        lda #$01
        bcc @load
        lda #$05
@load:
        jsr _rsql_overlay_load
        beq @loaded
        rts
@loaded:
        lda result_next_request
        ldx result_next_request+1
        jmp $7C00
