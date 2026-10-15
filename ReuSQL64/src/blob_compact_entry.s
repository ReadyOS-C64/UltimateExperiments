; Resident ABI trampoline for the blob-maintenance phase in the admin cache.
; The single pointer argument arrives in A/X under cc65's register convention.

        .import _rsql_blob_compact_phase
        .import _rsql_overlay_load_admin
        .export _rsql_blob_compact

        .segment "BSS"
compact_result_pointer: .res 2

        .segment "ABI"

_rsql_blob_compact:
        sta compact_result_pointer
        stx compact_result_pointer+1
        jsr _rsql_overlay_load_admin
        cmp #$00
        beq @loaded
        ldx #$00
        rts
@loaded:
        lda compact_result_pointer
        ldx compact_result_pointer+1
        jmp _rsql_blob_compact_phase
