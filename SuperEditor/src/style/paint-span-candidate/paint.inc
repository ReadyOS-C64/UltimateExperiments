; Private candidate: seek each span's intersection with each visible row.
; st_kind is transient row*3 during painting (the block kind is no longer live).
; No source callback occurs while the plan pointer is live. Each STEP still
; writes at most32 cells; at most22 row intersections can be skipped in a seek.
start_paint:
    lda #0
    sta st_paint
    sta st_paint+1
    sta st_row
    sta st_col
    lda #2
    sta st_phase
    jsr paint_seek
    jmp pending

paint_step:
    CMP24 st_cell,st_to
    bcs @next
    ldx st_kind
    lda st_cell+2
    cmp se_st_rows+5,x
    bne :+
    lda st_cell+1
    cmp se_st_rows+4,x
    bne :+
    lda st_cell
    cmp se_st_rows+3,x
:   bcs @next
    lda st_style
    ldx st_inline
    beq :+
    jsr merge_inline
:   jsr put_plan
    jsr inc_paint
    SM_INC24 st_cell
    inc st_col
    lda st_col
.ifdef SE_STYLE_GRID
    cmp st_columns
.else
    cmp #40
.endif
    bcc @budget
@next:
    jsr paint_next_row
    lda st_phase
    cmp #2
    jne pending
@budget:
    dec st_budget
    jne paint_step
    jmp pending

; Advance the plan index by the unvisited remainder of this row. This avoids
; another row-address table in the nearly full C14 image. st_col is always
; bounded by the selected width, including when an entire row is skipped.
paint_next_row:
.ifdef SE_STYLE_GRID
    lda st_columns
.else
    lda #40
.endif
    sec
    sbc st_col
    clc
    adc st_paint
    sta st_paint
    bcc :+
    inc st_paint+1
:   lda #0
    sta st_col
    inc st_row
paint_seek:
    lda st_row
    cmp #STYLE_ROWS
    bcc :+
    lda st_resume
    sta st_phase
    rts
:   asl
    clc
    adc st_row
    tax
    stx st_kind
    lda se_st_rows,x
    sta st_cell
    lda se_st_rows+1,x
    sta st_cell+1
    lda se_st_rows+2,x
    sta st_cell+2
    lda se_st_key+ST_KEY_MODE
.ifdef SE_STYLE_GRID
    and #1
.endif
    beq :+
    ADD24 st_cell,se_st_key+ST_KEY_PAN,st_cell
    jcs paint_next_row
:   CMP24 st_cell,st_to
    jcs paint_next_row
    CMP24 st_from,st_cell
    bcc @ready
    sec
    lda st_from
    sbc st_cell
    sta st_col
    lda st_from+1
    sbc st_cell+1
    bne @skip
    lda st_from+2
    sbc st_cell+2
    bne @skip
    lda st_col
.ifdef SE_STYLE_GRID
    cmp st_columns
.else
    cmp #40
.endif
    bcs @skip
    clc
    adc st_paint
    sta st_paint
    bcc :+
    inc st_paint+1
:   COPY24 st_from,st_cell
@ready:
    rts
@skip:
    ; A rejected difference need not fit a column. Restore the bounded value
    ; before advancing by the complete row width.
    lda #0
    sta st_col
    jmp paint_next_row
