        .import _rsql_wide_scalar_compare_c
        .import _rsql_aggregate_scalar_compare_admin_c
        .import addysp, subysp
        .importzp sp

        .export _rsql_wide_scalar_compare_entry
        .export _rsql_aggregate_scalar_compare_admin_entry

        .segment "OVERLAY8"

; Preserve one fixed-row-sized scalar chunk while the target triple is loaded.
; Concatenations can span two chunks; the dispatcher reloads both triples for
; each chunk so the fixed 1KB software stack always retains ample call depth.
_rsql_wide_scalar_compare_entry:
        ldy #240
        jsr subysp
        lda sp
        ldx sp+1
        jsr _rsql_wide_scalar_compare_c
        pha
        ldy #240
        jsr addysp
        pla
        ldx #0
        rts

        .segment "OVERLAY7"

; Aggregate owners share the same 240-byte streamed comparison chunk. The
; admin dispatcher asks the resident bridge to load each representative while
; its own return addresses remain protected by an owner restore.
_rsql_aggregate_scalar_compare_admin_entry:
        ldy #240
        jsr subysp
        lda sp
        ldx sp+1
        jsr _rsql_aggregate_scalar_compare_admin_c
        pha
        ldy #240
        jsr addysp
        pla
        ldx #0
        rts
