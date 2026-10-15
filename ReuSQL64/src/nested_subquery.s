        .import _g_rsql_statement, _g_rsql_cursor
        .import _g_nested_eval
        .import _g_nested_saved_kind, _g_nested_saved_projection
        .import _g_nested_saved_compare
        .import _subquery_truth
        .import _rsql_query_bind_subquery_phase
        .import _rsql_query_bind_join_phase
        .import _rsql_query_bind_nested_admin_phase
        .import _rsql_join_bind_indexes_admin_phase
        .import _rsql_overlay_load_admin
        .importzp ptr1

        .export _rsql_nested_subquery_truth
        .export _rsql_query_bind_complex_phase

        .segment "OVERLAY4"

; Fastcall pointer to the parsed nested predicate in A/X. The fixed offsets are
; RsqlParsedColumn.name[16], then RsqlTypeSpec tag/flags/parameter/auxiliary.
_rsql_nested_subquery_truth:
        sta ptr1
        stx ptr1+1
        lda _g_rsql_cursor+25
        sta _g_nested_saved_kind
        lda _g_rsql_cursor+26
        sta _g_nested_saved_projection
        lda _g_rsql_statement+17
        sta _g_nested_saved_compare
        lda #$01
        sta _g_nested_eval
        sta _g_rsql_cursor+16
        ldy #17
        lda (ptr1),y
        sta _g_rsql_cursor+25
        ldy #19
        lda (ptr1),y
        sta _g_rsql_cursor+26
        iny
        lda (ptr1),y
        sta _g_rsql_statement+17
        ldy #18
        lda (ptr1),y
        jsr _subquery_truth
        pha
        lda _g_nested_saved_compare
        sta _g_rsql_statement+17
        lda _g_nested_saved_projection
        sta _g_rsql_cursor+26
        lda _g_nested_saved_kind
        sta _g_rsql_cursor+25
        lda #$00
        sta _g_rsql_cursor+16
        sta _g_nested_eval
        pla
        ldx #$00
        rts

; Binding is invoked from resident query_api, so the original hardware return
; address is safe while this tail-switches to the fixed administrative cache.
_rsql_query_bind_complex_phase:
        lda _g_rsql_statement+16
        beq @join
        jsr _rsql_query_bind_subquery_phase
        cmp #$00
        bne @done
@join:  lda _g_rsql_statement+13
        beq @nested
        jsr _rsql_query_bind_join_phase
        cmp #$00
        bne @done
        lda _g_rsql_statement+12
        beq @nested
        lda #>(join_index_admin_ready-1)
        pha
        lda #<(join_index_admin_ready-1)
        pha
        jmp _rsql_overlay_load_admin
@nested:
        lda _g_rsql_statement+20
        beq @ok
        lda #>(nested_admin_ready-1)
        pha
        lda #<(nested_admin_ready-1)
        pha
        jmp _rsql_overlay_load_admin
@ok:    lda #$00
@done:  ldx #$00
        rts

        .segment "ENGINEDATA"

nested_admin_ready:
        jmp _rsql_query_bind_nested_admin_phase

join_index_admin_ready:
        jmp _rsql_join_bind_indexes_admin_phase
