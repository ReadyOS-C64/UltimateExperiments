; No leaf admission or pixel write precedes the complete map/caret preflight.
grid_width:
    lda se_mode
    cmp #3
    bne :+
    lda #80 ;GEOS keeps R27 active for shared native8 chrome/popup tiles
    sta g_width
    lda #27
    sta g_backend
    clc
    rts
:
    lda se_v_columns
    cmp #60
    beq @sixty
    cmp #80
    bne grid_bad
    lda #GRID80_ID
    bne @save
@sixty:
    lda #GRID60_ID
@save:
    sta g_backend
    lda se_v_columns
    sta g_width
    clc
    rts
grid_bad:
    lda #$7B
    sec
    rts
grid_stale:
    lda #1
    sta se_l_need_wrap
    lda #0
    clc
    rts
grid_preflight:
    jsr grid_width
    jcs @return
    jsr se_view_init
    jcs @return
    lda se_l_valid
    jeq grid_stale
    lda se_v_nav_busy
    jne grid_stale
    lda se_n_view_columns
    cmp g_width
    jne grid_stale
    ldx #9
@tokens:
    lda se_doc_original,x
    cmp se_l_original,x
    jne grid_stale
    dex
    bpl @tokens
    ldx #1
@generation:
    lda se_doc_generation,x
    cmp se_l_generation,x
    jne grid_stale
    dex
    bpl @generation
    ldx #3
@revision:
    lda se_r_revision,x
    cmp se_l_revision,x
    jne grid_stale
    dex
    bpl @revision
    CMP24 se_v_top,se_l_top
    jne grid_stale
    CMP24 se_v_top,se_v_rows
    jne grid_stale
    lda #$FF
    sta g_found
    lda #0
    sta g_row
@row:
    jsr grid_bounds
    jcs @return
    CMP24 g_next,g_start
    jcc grid_stale
    bne @span
    CMP24 g_next,se_v_length
    jne grid_stale
@span:
    lda se_l_mode
    bne @length
    SUB24 g_next,g_start,g_delta
    lda g_delta+2
    ora g_delta+1
    jne grid_stale
    lda g_delta
    cmp g_width
    bcc @length
    jne grid_stale
@length:
    CMP24 g_next,se_v_length
    bcc @end
    jne grid_stale
@end:
    COPY24 g_next,g_end
    CMP24 g_end,g_start
    beq @store
    COPY24 g_end,se_v_pos
    jsr se_view_retreat
    jsr se_view_peek
    jcs @return
    cmp #13
    bne @store
    COPY24 se_v_pos,g_end
@store:
    ldy g_index
    ldx #0
@ends:
    lda g_end,x
    sta g_ends,y
    iny
    inx
    cpx #3
    bcc @ends
    lda g_found
    cmp #$FF
    jne @next
    CMP24 se_hot_caret,g_start
    bcc @next
    CMP24 se_hot_caret,g_end
    bcc @found
    bne @next
    ; At a soft boundary, the caret belongs to the following row. A real
    ; CR/EOF blank belongs here if there is room in this row.
    lda se_l_mode
    bne @found
    SUB24 g_end,g_start,g_delta
    lda g_delta+2
    ora g_delta+1
    bne @next
    lda g_delta
    cmp g_width
    bcs @next
@found:
    lda g_row
    sta g_found
    SUB24 se_hot_caret,g_start,g_column
@next:
    inc g_row
    lda g_row
    cmp #22
    jcc @row
    lda g_found
    cmp #$FF
    jeq grid_stale
    lda se_l_mode
    jeq @ready
    lda se_l_manual
    jne @ready
    CMP24 g_column,se_l_pan
    bcc @left
    SUB24 g_column,se_l_pan,g_delta
    lda g_delta+2
    ora g_delta+1
    bne @right
    lda g_delta
    cmp g_width
    bcc @ready
@right:
    sec
    lda g_column
    sbc g_width
    sta se_l_pan
    lda g_column+1
    sbc #0
    sta se_l_pan+1
    lda g_column+2
    sbc #0
    sta se_l_pan+2
    inc se_l_pan
    bne @ready
    inc se_l_pan+1
    bne @ready
    inc se_l_pan+2
    jmp @ready
@left:
    COPY24 g_column,se_l_pan
@ready:
    lda #0
    sta se_l_need_wrap
    clc
@return:
    rts
; Read canonical row start/next without writing the shared row map.
grid_bounds:
    lda g_row
    asl
    clc
    adc g_row
    sta g_index
    tax
    ldy #0
@copy:
    lda se_v_rows,x
    sta g_start,y
    lda se_ef_valid
    beq @unfolded
    lda se_ef_paint_ends,x
    jmp @next
@unfolded:
    lda se_v_rows+3,x
@next:
    sta g_next,y
    inx
    iny
    cpy #3
    bcc @copy
    lda g_row
    cmp #21
    bne @ready
    lda se_ef_valid
    bne @ready
    COPY24 se_v_bottom,g_next
@ready:
    clc
    rts
