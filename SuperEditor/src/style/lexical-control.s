; Bounded source-code token plan worker. Existing C14 owns source lease/line.
; Source callbacks are C->R14; only resident switches C14/C15 phases.
.setcpu "6502"
.macpack longbranch
.include "style/api.inc"
.include "supermark/api.inc"
.include "document/math24.inc"
.export se_style_lexical
.import st_lex_phase,st_phase,st_resume,st_pos,st_index,st_used,st_buffer
.import st_reads,st_budget,st_from,st_to,st_style,st_row,st_col,st_paint,st_cell,st_kind
.import st_end
.import se_sm_language,se_sm_body
.import se_sl_init,se_sl_feed,se_sl_finish,se_sl_next
.import se_sl_pos,se_sl_count,se_sl_start,se_sl_end,se_sl_style
.import se_fs_guard,se_fs_read,se_fs_offset,se_fs_count,se_fs_buffer,se_fs_done
.importzp text_ptr
.ifdef SE_STYLE_GRID
.import st_columns,st_plan_page
.endif
.segment "STYLE_CODE"
se_style_lexical:
    cmp #3
    jne lex_argument
    jsr se_fs_guard
    jcs lex_return
    lda #32
    sta st_budget
    lda #0
    sta st_reads
    lda st_lex_phase
    cmp #1
    jeq lex_init
    cmp #2
    jeq lex_scan
    cmp #3
    jeq lex_paint
lex_argument:
    lda #ST_ARGUMENT
    sec
lex_return:
    rts
lex_pending:
    lda #ST_PENDING
    clc
    rts

lex_init:
    lda se_sm_language
    jsr se_sl_init
    COPY24 se_sm_body,se_sl_pos
    COPY24 se_sm_body,st_pos
    lda #0
    sta st_index
    sta st_used
    sta st_resume ;finish not yet issued; C14 no longer needs this field
    lda #2
    sta st_lex_phase
    jmp lex_scan

lex_scan:
    lda se_sl_count
    jne lex_event ;drain both queued spans before any new source feed
    CMP24 st_pos,st_end
    bcc @feed
    lda st_resume
    bne lex_done
    jsr se_sl_finish
    jcs lex_return
    inc st_resume
    jmp lex_pending
@feed:
    jsr lex_byte
    bcc @accepted
    cmp #0 ;zero is an internal bounded-read yield, never a source error
    jeq lex_pending
    sec
    rts
@accepted:
    jsr se_sl_feed
    jcs lex_return
    dec st_budget
    bne lex_scan
    jmp lex_pending
lex_done:
    lda #0
    sta st_lex_phase
    lda #5
    sta st_phase ;resident returns to C14 next_line
    jmp lex_pending

lex_event:
    jsr se_sl_next
    jcs lex_return
    COPY24 se_sl_start,st_from
    COPY24 se_sl_end,st_to
    lda se_sl_style
    sec
    sbc #SM_KEYWORD
    cmp #7
    jcs lex_argument
    tax
    lda lex_colors,x
    sta st_style
    lda #0
    sta st_row
    lda #3
    sta st_lex_phase
    jsr lex_seek
    jmp lex_paint

; Seek the first possible visible column in each row, rather than scanning880
; cells per token. st_kind holds row*3 only during this private phase.
lex_seek:
    lda st_row
    cmp #STYLE_ROWS
    jcs lex_span_done
    asl
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
    jcs lex_next_row
:   CMP24 st_to,st_cell
    jcc lex_span_done
.ifdef SE_STYLE_GRID
    jeq lex_span_done
.else
    beq lex_span_done
.endif
    lda #0
    sta st_col
    CMP24 st_from,st_cell
    bcc @column
    sec
    lda st_from
    sbc st_cell
    sta st_col
    lda st_from+1
    sbc st_cell+1
    bne lex_next_row
    lda st_from+2
    sbc st_cell+2
    bne lex_next_row
    lda st_col
.ifdef SE_STYLE_GRID
    cmp st_columns
.else
    cmp #40
.endif
    bcs lex_next_row
@column:
    clc
    lda st_cell
    adc st_col
    sta st_cell
    bcc :+
    inc st_cell+1
    bne :+
    inc st_cell+2
    beq lex_next_row
:   ldx st_row
.ifdef SE_STYLE_GRID
    lda se_st_key+ST_KEY_MODE
    lsr
    beq :+
    cmp #1
    beq @sixty
    txa
    clc
    adc #44
    bne @row_index
@sixty:
    txa
    clc
    adc #22
@row_index:
    tax
:
.endif
    clc
    lda lex_row_low,x
    adc st_col
    sta st_paint
    lda lex_row_high,x
    adc #0
    sta st_paint+1
    rts
lex_next_row:
    inc st_row
    jmp lex_seek
lex_span_done:
    lda #2
    sta st_lex_phase
    rts

lex_paint:
    CMP24 st_cell,st_to
    bcs lex_span_done_yield
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
    ; No source callback occurs while this transient fixed-plan pointer is live.
    lda st_paint
    sta text_ptr
    lda st_paint+1
    clc
.ifdef SE_STYLE_GRID
    adc st_plan_page
.else
    adc #>STYLE_PLAN
.endif
    sta text_ptr+1
    ldy #0
    lda st_style
    sta (text_ptr),y
    SM_INC24 st_cell
    inc st_paint
    bne :+
    inc st_paint+1
:   inc st_col
    lda st_col
.ifdef SE_STYLE_GRID
    cmp st_columns
.else
    cmp #40
.endif
    bcc @budget
@next:
    jsr lex_next_row
    lda st_lex_phase
    cmp #3
    jne lex_pending
@budget:
    dec st_budget
    jne lex_paint
    jmp lex_pending
lex_span_done_yield:
    jsr lex_span_done
    jmp lex_pending

lex_byte:
    lda st_index
    cmp st_used
    bcc @cached
    lda st_reads
    bne @yield
    inc st_reads
    COPY24 st_pos,se_fs_offset
    lda #128
    sta se_fs_count
    lda #<st_buffer
    sta se_fs_buffer
    lda #>st_buffer
    sta se_fs_buffer+1
    jsr se_fs_read
    bcs @return
    lda se_fs_done
    beq @bad
    cmp #129
    bcs @bad
    sta st_used
    lda #0
    sta st_index
@cached:
    ldx st_index
    lda st_buffer,x
    inc st_index
    pha
    SM_INC24 st_pos
    pla
    clc
@return:
    rts
@yield:
    lda #0
    sec
    rts
@bad:
    lda #ST_ARGUMENT
    sec
    rts

lex_colors:
    .byte 7,8,9,10,7,12,0 ;keyword,number,string,comment,directive,label,operator roles
lex_row_low:
.ifdef SE_STYLE_GRID
.repeat 3,W
.repeat STYLE_ROWS,R
    .byte <((40+W*20)*R)
.endrepeat
.endrepeat
.else
.repeat STYLE_ROWS,R
    .byte <(40*R)
.endrepeat
.endif
lex_row_high:
.ifdef SE_STYLE_GRID
.repeat 3,W
.repeat STYLE_ROWS,R
    .byte >((40+W*20)*R)
.endrepeat
.endrepeat
.else
.repeat STYLE_ROWS,R
    .byte >(40*R)
.endrepeat
.endif
