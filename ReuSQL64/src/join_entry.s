; cc65 2.18 emits three unused two-byte temporaries immediately after the
; exported label for the large join continuation. Keep the stable public
; phase entry on executable code while the C implementation remains bounded.

.segment "OVERLAY4"

.import _rsql_query_join_next_phase_c
.export _rsql_query_join_next_phase

_rsql_query_join_next_phase:
        jmp _rsql_query_join_next_phase_c + 6
