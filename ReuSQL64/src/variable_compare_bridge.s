        .import _g_rsql_variable_compare_source
        .import _g_rsql_aggregate_scalar_bridge_mode
        .import _rsql_overlay_load
        .import _rsql_overlay_load_admin
        .import _rsql_query_variable_compare_phase
        .import _rsql_query_variable_predicates_phase
        .import _rsql_query_variable_scalar_compare_phase
        .import _rsql_wide_scalar_admin_phase
        .import _rsql_query_indexed_join_next_phase
        .import _rsql_aggregate_scalar_compare_admin_entry
        .import _rsql_query_aggregate_scalar_row_phase
        .import _rsql_query_join_aggregate_scalar_row_phase
        .import _g_cursor_next_request

        .export _rsql_query_variable_compare_owner

RSQL_OK                      = 0
RSQL_VARIABLE_COMPARE_SCALAR = 8
RSQL_VARIABLE_COMPARE_PREDICATE = 9
RSQL_VARIABLE_COMPARE_WIDE_SCALAR = 10
RSQL_VARIABLE_COMPARE_AGGREGATE_SCALAR = 11
RSQL_VARIABLE_COMPARE_INDEXED_JOIN_NEXT = 12
        .segment "ENGINE"

; An overlay may call this resident bridge while its return address still
; points into that image.  Run the requested comparison sidecar, then reload
; the owner before returning through that address.  The fastcall byte arrives
; in A and every byte return is normalized to A/X.
_rsql_query_variable_compare_owner:
        ; Keep the owner beneath the return code on the hardware stack.  It
        ; cannot alias comparison scratch: HANDLE mode needs all four bytes
        ; of both blob identities, including the high handle byte.
        pha
        jmp variable_compare_dispatch

wide_scalar_compare:
        jsr _rsql_overlay_load_admin
        bne save_compare_rc
        jsr _rsql_wide_scalar_admin_phase
        jmp save_compare_rc

scalar_compare:
        lda #3
        jsr _rsql_overlay_load
        bne save_compare_rc
        jsr _rsql_query_variable_scalar_compare_phase
        jmp save_compare_rc

variable_compare:
        lda #5
        jsr _rsql_overlay_load
        bne save_compare_rc
        jsr _rsql_query_variable_compare_phase
        ; Fall through to the common owner restore.

save_compare_rc:
        pha
        tsx
        lda $0102,x
        cmp #8
        bne restore_regular_owner
        jsr _rsql_overlay_load_admin
        jmp owner_restored
restore_regular_owner:
        jsr _rsql_overlay_load
owner_restored:
        tax
        pla
        bne discard_owner
        txa
discard_owner:
        ; Drop the still-stacked owner without disturbing the selected rc.
        tsx
        inx
        txs
        ldx #0
        rts

        .segment "ENGINEDATA"
variable_compare_dispatch:
        lda _g_rsql_aggregate_scalar_bridge_mode
        beq normal_compare_dispatch
        cmp #1
        beq aggregate_scalar_replay
        cmp #2
        beq aggregate_scalar_row
        jmp wide_scalar_compare

normal_compare_dispatch:
        lda _g_rsql_variable_compare_source
        ; Scalar shaping is the one exact descriptor-mode value.  Ordinary
        ; column descriptors (notably the $FF tuple sentinel) may also carry
        ; bit 3, so a bit test would incorrectly dispatch existing TEXT/BLOB
        ; DISTINCT comparisons to slot 3.
        cmp #RSQL_VARIABLE_COMPARE_SCALAR
        bne :+
        jmp scalar_compare
:
        cmp #RSQL_VARIABLE_COMPARE_PREDICATE
        bne :+
        jmp predicate_compare
:
        cmp #RSQL_VARIABLE_COMPARE_WIDE_SCALAR
        bne :+
        jmp wide_scalar_compare
:
        cmp #RSQL_VARIABLE_COMPARE_INDEXED_JOIN_NEXT
        bne :+
        jmp indexed_join_next
:
        jmp variable_compare

; $CFF0-$CFF6 are test controls.  The remaining RAM tail starts the predicate
; bridge, then the eleven free bytes immediately below $CFEF finish it.
        .segment "CONTROLTAIL"
predicate_compare:
        lda #6
        jsr _rsql_overlay_load
        jmp predicate_continue

        .segment "ABI"
predicate_continue:
        beq predicate_call
        jmp save_compare_rc
predicate_call:
        jsr _rsql_query_variable_predicates_phase
        jmp save_compare_rc

        .segment "ENGINE"
indexed_join_next:
        lda #7
        jsr _rsql_overlay_load
        bne indexed_join_done
        lda _g_cursor_next_request
        ldx _g_cursor_next_request+1
        jsr _rsql_query_indexed_join_next_phase
indexed_join_done:
        jmp save_compare_rc

        .segment "ENGINEDATA"
aggregate_scalar_replay:
        jsr _rsql_overlay_load_admin
        bne aggregate_scalar_done
        jsr _rsql_aggregate_scalar_compare_admin_entry
aggregate_scalar_done:
        jmp save_compare_rc

aggregate_scalar_row:
        lda _g_rsql_variable_compare_source
        jsr _rsql_overlay_load
        bne aggregate_scalar_done
        lda _g_rsql_variable_compare_source
        cmp #6
        beq aggregate_scalar_pair_row
        jsr _rsql_query_aggregate_scalar_row_phase
        jmp aggregate_scalar_done

aggregate_scalar_pair_row:
        jsr _rsql_query_join_aggregate_scalar_row_phase
        jmp aggregate_scalar_done
