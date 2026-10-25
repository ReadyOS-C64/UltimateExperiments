.import se_sc_begin,se_sc_event,se_sc_finish
; Bounded source40 semantic plan. No source mutation, VIC writes, overlay calls,
; or new ZP. All markers remain visible. Root owns rendering and input priority.
.setcpu "6502"
.macpack longbranch
.include "style/api.inc"
.include "render/presentation.inc"
.include "supermark/api.inc"
.include "document/math24.inc"
.include "tui/theme.inc"
.import se_sm_init,se_sm_feed,se_sm_finish,se_sm_pos,se_sm_ready,se_sm_start
.import se_sm_end,se_sm_body,se_sm_kind,se_sm_state
.import se_sm_state_size
.import se_si_init,se_si_feed,se_si_finish,se_si_at_body,se_si_pos,se_si_ready
.import se_si_kind,se_si_style,se_si_width,se_si_open,se_si_close
.import se_fs_begin,se_fs_guard,se_fs_read,se_fs_end
.import se_fs_offset,se_fs_count,se_fs_buffer,se_fs_done,se_fs_length
.import se_st_cp_state,se_st_cp_key
.import st_phase,st_resume,st_budget,st_reads,st_index,st_used,st_buffer
.import st_pos,st_next,st_end,st_from,st_to,st_paint,st_style,st_row,st_col,st_cell
.import st_offset,st_finish,st_kind,st_base,st_owned,st_inline
.ifdef SE_STYLE_LEXICAL
.import st_lex_phase
.endif
.ifdef SE_STYLE_GRID
.import st_columns,st_plan_page,st_cells
.importzp text_ptr
.endif
.segment "STYLE_CODE"
.assert se_sm_state_size=79,lderror,"style checkpoint block ABI changed"
se_style_begin:
    lda se_st_busy
    beq :+
    lda #ST_BUSY
    sec
    rts
:   lda #0
    sta se_st_valid
    sta st_owned
    sta se_st_error
.ifdef SE_STYLE_GRID
    lda se_st_key+ST_KEY_MODE
    cmp #6
    jcs bad_argument
    jsr grid_plan_init
.endif
    jsr se_fs_begin
    jcs failure
    inc st_owned
    CMP24 se_fs_length,se_st_key+ST_KEY_LENGTH
    jne bad_argument
    ldx #STYLE_KEY_BYTES-1
@bind:
    lda se_st_key,x
    sta se_st_descriptor,x
    dex
    bpl @bind
    jsr se_sm_init
    jsr checkpoint_begin
    jsr se_sc_begin
    COPY24 se_sm_pos,st_pos
    lda #1
    sta se_st_busy
    lda #0
    sta st_phase ;clear plan in32-cell slices first
    sta st_index
    sta st_used
    sta st_finish
    sta st_paint
    sta st_paint+1
    lda #ST_PENDING
    clc
    rts
bad_argument:
    lda #ST_ARGUMENT
    jmp failure

se_style_cancel:
    lda #0
    sta se_st_valid
    sta se_st_busy
    sta se_st_error
    jmp release

se_style_step:
    lda se_st_busy
    bne :+
    lda #ST_ARGUMENT
    sec
    rts
:   jsr se_fs_guard
    jcs failure
    ldx #STYLE_KEY_BYTES-1
@guard:
    lda se_st_descriptor,x
    cmp se_st_key,x
    jne stale
    dex
    bpl @guard
    lda #32
    sta st_budget
    lda #0
    sta st_reads
    lda st_phase
    jeq clear_step
    cmp #1
    jeq block_step
    cmp #2
    jeq paint_step
    cmp #3
    jeq inline_begin
    cmp #4
    jeq inline_step
.ifdef SE_STYLE_LEXICAL
    cmp #6
    jeq lexical_begin
.endif
    jmp next_line
stale:
    lda #ST_STALE
failure:
    sta se_st_error
    lda #0
    sta se_st_valid
    sta se_st_busy
    jsr release
    lda se_st_error
    sec
    rts
release:
    lda st_owned
    beq :+
    lda #0
    sta st_owned
    jsr se_fs_end
:
    lda #0
    clc
    rts
pending:
    lda #ST_PENDING
    clc
    rts

clear_step:
    lda #TUI_FG
    jsr put_plan
    jsr inc_paint
    lda st_paint+1
.ifdef SE_STYLE_GRID
    cmp st_cells+1
.else
    cmp #>STYLE_CELLS
.endif
    bne :+
    lda st_paint
.ifdef SE_STYLE_GRID
    cmp st_cells
.else
    cmp #<STYLE_CELLS
.endif
    bne :+
    lda #1
    sta st_phase
    jmp pending
:   dec st_budget
    bne clear_step
    jmp pending

block_step:
    CMP24 st_pos,se_fs_length
    bcc @byte
    lda st_finish
    jne complete
    inc st_finish
    jsr se_sm_finish
    lda se_sm_ready
    jeq complete
    jmp block_event
@byte:
    jsr read_byte
    bcs @read_return
    jsr se_sm_feed
    lda se_sm_ready
    bne block_event
    dec st_budget
    bne block_step
    jmp pending
@read_return:
    cmp #0 ;internal yield; callback errors must be nonzero
    jeq pending
    jmp failure

block_event:
    COPY24 se_sm_pos,st_next
    COPY24 se_sm_end,st_end
    COPY24 se_sm_start,st_from
    COPY24 se_sm_end,st_to
    lda se_sm_kind
    sta st_kind
    lda #TUI_FG
    ldx st_kind
    cpx #SM_HEADING
    bne :+
    lda #TUI_TITLE|$80
:   cpx #SM_CODE_LINE
    bne :+
    lda #TUI_BORDER
:   cpx #SM_CODE_OPEN
    beq @structural
    cpx #SM_CODE_CLOSE
    beq @structural
    cpx #SM_REGION_OPEN
    beq @structural
    cpx #SM_REGION_CLOSE
    bne :+
@structural:
    lda #TUI_STATUS
:   sta st_style
    sta st_base
    ; Only a CR-complete boundary can seed another block parser scan.
    lda st_finish
    bne @paint
    CMP24 st_next,se_st_key+ST_KEY_TOP
    bcc :+
    bne @paint
:   
    jsr checkpoint_save
@paint:
    CMP24 st_end,se_st_rows
    jcc next_line
    jeq next_line
    jsr se_sc_event
    lda #0
    sta st_inline
    lda #3
    ldx st_kind
    cpx #SM_CODE_OPEN
    bcc :+
    cpx #SM_CODE_CLOSE+1
    bcs :+
    lda #5
:   sta st_resume
.ifdef SE_STYLE_LEXICAL
    cpx #SM_CODE_LINE
    bne :+
    lda se_render_caps
    and #RENDER_CODE_COLOR
    beq :+
    lda #6
    sta st_resume
:
.endif
    jmp start_paint

.ifdef SE_STYLE_LEXICAL
; Return to resident before changing command images. C15 retains this source
; lease and returns here at next_line after its bounded lexical line pass.
lexical_begin:
    lda #1
    sta st_lex_phase
    lda #5
    sta st_phase
    jmp pending
.endif

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

inline_begin:
    jsr se_si_init
    COPY24 se_sm_body,se_si_pos
    COPY24 se_sm_body,st_pos
    SUB24 se_sm_body,se_sm_start,st_from
    lda st_from
    ora st_from+1
    ora st_from+2
    beq :+
    lda st_from
    ldx st_from+1
    ldy st_from+2
    jsr se_si_at_body
:   lda #0
    sta st_index
    sta st_used
    lda #4
    sta st_phase
    jmp pending

inline_step:
    CMP24 st_pos,st_end
    bcc @byte
    jsr se_si_finish
    lda #5
    sta st_resume
    sta st_phase
    lda se_si_ready
    bne inline_event
    jmp pending
@byte:
    jsr read_byte
    bcs @read_return
    jsr se_si_feed
    lda se_si_ready
    bne @event
    dec st_budget
    bne inline_step
    jmp pending
@event:
    lda #4
    sta st_resume
    bne inline_event
@read_return:
    cmp #0
    jeq pending
    jmp failure
inline_event:
    lda se_si_kind
    cmp #SM_PAIR
    jne pending
    lda se_si_open
    clc
    adc se_si_width
    sta st_from
    lda se_si_open+1
    adc #0
    sta st_from+1
    lda se_si_open+2
    adc #0
    sta st_from+2
    COPY24 se_si_close,st_to
    ; Nesting events arrive inner first. Merge outer emphasis/strong in cells;
    ; code overrides both. Heading reverse is retained by the painter.
    ldx se_si_style
    txa
    asl
    asl
    asl
    asl
    sta st_style
    lda #1
    sta st_inline
    jmp start_paint

next_line:
    CMP24 st_next,se_st_rows+66
    jcs complete
    COPY24 st_next,st_pos
    lda #0
    sta st_index
    sta st_used
    lda #1
    sta st_phase
    jmp pending

complete:
    jsr se_fs_guard
    jcs failure
    jsr se_sc_finish
    jsr release
    inc se_st_generation
    bne :+
    inc se_st_generation+1
:   lda #1
    sta se_st_valid
    lda #0
    sta se_st_busy
    clc
    rts

; At most one source read per STEP; parser may consume an existing packet too.
read_byte:
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

put_plan:
.ifdef SE_STYLE_GRID
    pha
    jsr plan_pointer
    pla
    sta (text_ptr),y
    rts
get_plan:
    jsr plan_pointer
    lda (text_ptr),y
    rts
plan_pointer:
    lda st_paint
    sta text_ptr
    lda st_paint+1
    clc
    adc st_plan_page
    sta text_ptr+1
    ldy #0
    rts
grid_plan_init:
    lda se_st_key+ST_KEY_MODE
    lsr
    tax
    lda grid_columns,x
    sta st_columns
    lda grid_pages,x
    sta st_plan_page
    lda grid_cells_low,x
    sta st_cells
    lda grid_cells_high,x
    sta st_cells+1
    rts
.segment "RODATA"
grid_columns:.byte 40,60,80
grid_pages:.byte >STYLE_PLAN,$48,$48
grid_cells_low:.byte <880,<1320,<1760
grid_cells_high:.byte >880,>1320,>1760
.segment "STYLE_CODE"
.else
    ldx st_paint
    ldy st_paint+1
    beq @p0
    dey
    beq @p1
    dey
    beq @p2
    sta STYLE_PLAN+$300,x
    rts
@p0:sta STYLE_PLAN,x
    rts
@p1:sta STYLE_PLAN+$100,x
    rts
@p2:sta STYLE_PLAN+$200,x
    rts
get_plan:
    ldx st_paint
    ldy st_paint+1
    beq @p0
    dey
    beq @p1
    dey
    beq @p2
    lda STYLE_PLAN+$300,x
    rts
@p0:lda STYLE_PLAN,x
    rts
@p1:lda STYLE_PLAN+$100,x
    rts
@p2:lda STYLE_PLAN+$200,x
    rts
.endif
merge_inline:
    jsr get_plan
    and #$F0
    ora st_style
    sta st_offset
    and #$40
    beq @emphasis
    lda #TUI_BORDER
    bne @color
@emphasis:
    lda st_offset
    and #$30
    lsr
    lsr
    lsr
    lsr
    tax
    lda inline_colors,x
@color:
    ora st_offset
    rts
inc_paint:
    inc st_paint
    bne :+
    inc st_paint+1
:   rts

checkpoint_begin:
    lda se_st_cp_valid
    beq @invalid
    ; Immutable source capabilities + generation + provider must match.
    ldx #16
@immutable:
    lda se_st_cp_key,x
    cmp se_st_key,x
    bne @invalid
    dex
    bpl @immutable
    ldx #1
@epoch:
    lda se_st_cp_key+ST_KEY_EPOCH,x
    cmp se_st_key+ST_KEY_EPOCH,x
    bne @invalid
    dex
    bpl @epoch
    CMP24 se_st_cp_anchor,se_st_key+ST_KEY_TOP
    bcc :+
    bne @invalid
:
    ldx #6 ;revision4+length3
@revision:
    lda se_st_cp_key+17,x
    cmp se_st_key+17,x
    bne @dirty
    dex
    bpl @revision
    jmp @restore
@dirty:
    lda se_st_cp_dirty
    beq @invalid
    CMP24 se_st_cp_damage,se_st_cp_anchor
    bcc @invalid
@restore:
    ldx #78
@copy:
    lda se_st_cp_state,x
    sta se_sm_state,x
    dex
    bpl @copy
    jsr checkpoint_key
    rts
@invalid:
    lda #0
    sta se_st_cp_valid
    sta se_st_cp_dirty
    rts
checkpoint_save:
    ldx #78
@copy:
    lda se_sm_state,x
    sta se_st_cp_state,x
    dex
    bpl @copy
    COPY24 se_sm_pos,se_st_cp_anchor
    lda #1
    sta se_st_cp_valid
checkpoint_key:
    ldx #STYLE_KEY_BYTES-1
@copy:
    lda se_st_key,x
    sta se_st_cp_key,x
    dex
    bpl @copy
    lda #0
    sta se_st_cp_dirty
    rts
inline_colors:
    .byte TUI_FG,TUI_HIGHLIGHT,TUI_TITLE,TUI_ERROR,TUI_BORDER
