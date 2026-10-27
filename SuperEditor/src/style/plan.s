; Bounded source40 semantic plan. No source mutation, VIC writes, overlay calls,
; or new ZP. All markers remain visible. Root owns rendering and input priority.
.setcpu "6502"
.macpack longbranch
.include "style/api.inc"
.include "render/presentation.inc"
.include "render/geos/edit-certificate.inc"
.include "supermark/api.inc"
.include "document/math24.inc"
.import se_sm_pos,se_sm_ready,se_sm_start
.ifndef SE_STYLE_GRID
.import se_sm_init,se_sm_feed,se_sm_finish
.endif
.import se_sm_end,se_sm_body,se_sm_kind,se_sm_state
.import se_sm_fence,se_sm_language,se_sm_regions
.import se_sm_state_size
.import se_si_init,se_si_feed,se_si_finish,se_si_at_body,se_si_pos,se_si_ready
.import se_si_kind,se_si_style,se_si_width,se_si_open,se_si_close
.import se_fs_begin,se_fs_guard,se_fs_read,se_fs_end
.ifdef SE_STYLE_GRID
.import se_sb_init,se_sb_step
.endif
.import se_fs_offset,se_fs_count,se_fs_buffer,se_fs_done,se_fs_length
.import se_st_cp_rows
.ifndef SE_STYLE_GRID
.import se_st_cp_carry
.endif
.import se_e_draw_sequence
.import st_phase,st_resume,st_budget,st_reads,st_index,st_used,st_buffer
.import st_pos,st_next,st_end,st_from,st_to,st_paint,st_style,st_row,st_col,st_cell
.import st_offset,st_finish,st_kind,st_base,st_owned,st_inline
.ifdef SE_STYLE_LEXICAL
.import st_lex_phase
.endif
.ifdef SE_STYLE_GRID
.import st_columns,st_plan_page
.import se_crc_init,se_crc_byte,se_crc_value
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
    lsr
    tax
    lda grid_columns,x
    sta st_columns
    lda grid_pages,x
    sta st_plan_page
.endif
    jsr se_fs_begin
    jcs failure
    inc st_owned
    CMP24 se_fs_length,se_st_key+ST_KEY_LENGTH
    jne bad_argument
.ifdef SE_STYLE_GRID
    jsr se_sb_init
    jcs failure
    cmp #1
    bne @cold
    lda #$80                ;fast job, EOF-finish remains bit0
    sta st_finish
    lda #1
    sta st_phase
    jmp @started
@cold:
    sta se_st_tx+ST_TX_PHASE ;A=0: a refused ticket cannot outlive cold fallback
.else
    jsr se_sm_init
.endif
    jsr checkpoint_begin
    jsr bind_descriptor
    lda #0
    sta se_st_cp_valid
    sta se_st_cp_count
    jsr carry_snapshot
    COPY24 se_sm_pos,st_pos
.ifdef SE_STYLE_GRID
    lda #1                  ;every live cell is overwritten by its base span
.else
    lda #0                  ;isolated fixed-size planner retains full fill ABI
.endif
    sta st_phase
    lda #0
    sta st_index
    sta st_used
    sta st_finish
    sta st_paint
    sta st_paint+1
@started:
    lda #1
    sta se_st_busy
    lda #ST_PENDING
    clc
    rts
bad_argument:
    lda #ST_ARGUMENT
    jmp failure

se_style_cancel:
    lda #0
    sta se_st_valid
    sta se_st_cp_valid
    sta se_st_tx+ST_TX_PHASE
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
    lda st_finish
    bpl @full_guard
    ; Fast mode keeps the old revision/length descriptor until convergence,
    ; but its viewport and presentation contract must remain unchanged.
    ldx #8
@fast_guard:
    lda se_st_descriptor+ST_KEY_TOP,x
    cmp se_st_key+ST_KEY_TOP,x
    jne stale
    dex
    bpl @fast_guard
    jmp @guarded
@full_guard:
    ldx #STYLE_KEY_BYTES-1
@guard:
    lda se_st_descriptor,x
    cmp se_st_key,x
    jne stale
    dex
    bpl @guard
@guarded:
    lda #32
    sta st_budget
    lda #0
    sta st_reads
    lda st_phase
.ifndef SE_STYLE_GRID
    jeq clear_step
.endif
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
    sta se_st_cp_valid
    sta se_st_tx+ST_TX_PHASE
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

.ifndef SE_STYLE_GRID
clear_step:
    lda #0                  ;native prose role
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
.endif

block_step:
.ifdef SE_STYLE_GRID
    jsr se_sb_step
    jcs failure
    cmp #1
    jeq block_event
    cmp #2
    jeq complete
    jmp pending
.else
    CMP24 st_pos,se_fs_length
    bcc @byte
    lda st_finish
    and #1                  ;bit6 tracks captured top carry
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
    cmp #0
    jeq pending
    jmp failure
.endif

block_event:
    COPY24 se_sm_pos,st_next
    COPY24 se_sm_end,st_end
    COPY24 se_sm_start,st_from
    COPY24 se_sm_end,st_to
.ifdef SE_STYLE_GRID
    lda st_finish
    bpl @cold_event
    jsr fast_converged
    jcs se_st_fast_fallback
    jmp @classified
@cold_event:
.endif
    jsr carry_publish_event
@classified:
    lda se_sm_kind
    sta st_kind
    lda #0                  ;native prose role
    ldx st_kind
    cpx #SM_HEADING
    bne :+
    lda #2|$80              ;native strong role + inverse heading flag
:   cpx #SM_CODE_LINE
    bne :+
    lda #4                  ;native fixed-width/code role
:   cpx #SM_CODE_OPEN
    beq @structural
    cpx #SM_CODE_CLOSE
    beq @structural
    cpx #SM_REGION_OPEN
    beq @structural
    cpx #SM_REGION_CLOSE
    bne :+
@structural:
    lda #10                 ;native structural/comment role
:   sta st_style
    sta st_base
@paint:
    CMP24 st_end,se_st_rows
    jcc next_line
    jeq next_line
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
    lda st_finish
    bmi complete
    CMP24 st_next,se_st_rows+66
    jcs complete
    COPY24 st_next,st_pos
    jsr carry_snapshot
    lda #0
    sta st_index
    sta st_used
    lda #1
    sta st_phase
    jmp pending

complete:
    jsr se_fs_guard
    jcs failure
    jsr release
    lda st_finish
    bmi @fast_ready
    and #$40                ;cold builder captured the top logical checkpoint
    beq @carry_done
.ifdef SE_STYLE_GRID
    jsr se_crc_init
    ldy #0
@carry_crc:
    lda se_st_cp_rows,y
    jsr se_crc_byte
    iny
    cpy #STYLE_CARRY_TABLE_BYTES
    bcc @carry_crc
    lda se_crc_value
    sta se_st_cp_crc
    lda se_crc_value+1
    sta se_st_cp_crc+1
.endif
    lda #1
    sta se_st_cp_valid
@carry_done:
    inc se_st_generation
    bne :+
    inc se_st_generation+1
:   lda #1
    sta se_st_valid
    lda #0
    sta se_st_busy
    clc
    rts
@fast_ready:
    ; The plan is private until C33 paints and publishes the row transaction.
    ; Change the checksum first and the phase last so interruption is refusal.
    lda #ST_TX_CHECK_SEED^ST_TX_READY
    ldx #ST_TX_BYTES-1
@ticket_check:
    eor se_st_tx,x
    dex
    cpx #ST_TX_START-1
    bne @ticket_check
    sta se_st_tx+ST_TX_CHECK
    lda #ST_TX_READY
    sta se_st_tx+ST_TX_PHASE
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
.segment "RODATA"
grid_columns:.byte 40,60,80
grid_pages:.byte >STYLE_PLAN,$48,$48
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
    lda #4                  ;native fixed-width/code role
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

.ifdef SE_STYLE_GRID
.export se_st_fast_fallback
; Compare the changed line's exact outgoing state and end boundary before the
; existing painter is allowed to write any style-plan cell.
fast_converged:
    ldx #2
@boundary:
    lda se_sm_pos,x
    cmp se_st_tx+ST_TX_END,x
    bne @bad
    dex
    bpl @boundary
    lda st_col
    sta st_style
    asl
    asl
    clc
    adc st_style
    tax
    lda se_sm_fence
    sta st_style
    beq @text_language
    lda se_sm_language
    bne @language
@text_language:
    lda #0
@language:
    asl
    asl
    asl
    asl
    ora st_style
    eor se_st_cp_rows,x
    and #$7F                 ;logical-start is transport; bit6 must remain zero
    bne @bad
    lda se_st_cp_rows+1,x
    cmp se_sm_regions
    bne @bad
    lda se_sm_state+76
    cmp se_st_cp_rows+2,x
    bne @bad
    lda se_sm_state+77
    cmp se_st_cp_rows+3,x
    bne @bad
    lda se_sm_state+78
    cmp se_st_cp_rows+4,x
    bne @bad
    clc
    rts
@bad:
    sec
    rts

; Convergence refusal cannot rebuild against se_st_rows: those anchors still
; describe the pre-edit publication. Return a clean retry so ordinary layout
; publishes current geometry before a fresh cold job copies the new anchors.
se_st_fast_fallback:
    lda #ST_RETRY
    clc
    rts
.endif

bind_descriptor:
    ldx #STYLE_KEY_BYTES-1
@copy:
    lda se_st_key,x
    sta se_st_descriptor,x
    dex
    bpl @copy
    rts

checkpoint_begin:
    lda se_st_cp_valid
    beq @invalid
    ; The checkpoint is part of the last published descriptor.  It may seed a
    ; same-source viewport rebuild, but never cross a source/revision change.
    ldx #16
@immutable:
    lda se_st_descriptor,x
    cmp se_st_key,x
    bne @invalid
    dex
    bpl @immutable
    ldx #1
@epoch:
    lda se_st_descriptor+ST_KEY_EPOCH,x
    cmp se_st_key+ST_KEY_EPOCH,x
    bne @invalid
    dex
    bpl @epoch
    CMP24 se_st_cp_anchor,se_st_key+ST_KEY_TOP
    bcc :+
    bne @invalid
:
    ldx #6 ;revision4+length3 must be identical for ordinary checkpoint reuse
@revision:
    lda se_st_descriptor+17,x
    cmp se_st_key+17,x
    bne @invalid
    dex
    bpl @revision
@restore:
    jsr carry_restore_top
    rts
@invalid:
    lda #0
    sta se_st_cp_valid
    rts

checkpoint_save:
    COPY24 se_sm_start,se_st_cp_anchor
.ifndef SE_STYLE_GRID
    lda st_offset
    sta se_st_cp_carry
    lda st_offset+1
    sta se_st_cp_carry+1
    lda st_style
    and #$1f
    sta se_st_cp_carry+2
    lda st_base
    sta se_st_cp_carry+3
    lda st_kind
    sta se_st_cp_carry+4
    lda st_inline
    sta se_st_cp_carry+5
.endif
    rts

; Save the exact semantic carry before any byte of a logical line is fed.
; These six bytes alias fields unused until block_event consumes the snapshot.
carry_snapshot:
    lda se_sm_fence
    sta st_offset
    beq @plain_language
    lda se_sm_language
    bne @language
@plain_language:
    lda #0
@language:
    sta st_offset+1
    lda se_sm_regions
    sta st_style
    lda se_sm_state+76
    sta st_base
    lda se_sm_state+77
    sta st_kind
    lda se_sm_state+78
    sta st_inline
    rts

; Publish incoming carry for each physical row in this logical line.  Repeating
; five bytes makes lookup constant-time. Bit7 of the packed first byte marks a
; true logical start; wrapped continuations retain the same semantic carry.
carry_publish_event:
@row:
    lda se_st_cp_count
    cmp #STYLE_ROWS
    jcs @top
    asl
    clc
    adc se_st_cp_count
    tax
    ; Rows are ordered and each is visited once.  Stop at the first anchor
    ; outside this event; the following event resumes at that same row.
    lda se_st_rows+2,x
    cmp se_sm_pos+2
    bcc @within
    jne @top
    lda se_st_rows+1,x
    cmp se_sm_pos+1
    bcc @within
    bne @top
    lda se_st_rows,x
    cmp se_sm_pos
    bcc @within
    bcs @top
@within:
    lda se_st_cp_count
    sta st_col
    asl
    asl
    clc
    adc st_col
    tay                         ;keep X=row*3 for the logical-start test below
    lda st_offset+1
    asl
    asl
    asl
    asl
    ora st_offset
    sta se_st_cp_rows,y
    lda st_style
    and #$1f
    sta se_st_cp_rows+1,y
    lda st_base
    sta se_st_cp_rows+2,y
    lda st_kind
    sta se_st_cp_rows+3,y
    lda st_inline
    sta se_st_cp_rows+4,y
    ; Mark exactly the row whose anchor is the logical start.
    lda se_st_rows,x
    cmp se_sm_start
    bne @advance
    lda se_st_rows+1,x
    cmp se_sm_start+1
    bne @advance
    lda se_st_rows+2,x
    cmp se_sm_start+2
    bne @advance
    lda se_st_cp_rows,y
    ora #STYLE_CARRY_START
    sta se_st_cp_rows,y
@advance:
    inc se_st_cp_count
    jmp @row
@top:
    ; The logical line containing TOP is the exact restart checkpoint.
    lda st_finish
    and #$40
    bne @done
    CMP24 se_st_key+ST_KEY_TOP,se_sm_pos
    bcs @done
    jsr checkpoint_save
    lda st_finish
    ora #$40
    sta st_finish
@done:
    rts

; Restore only the semantic state that can cross a CR boundary.  All prefix,
; list and event fields remain the clean values produced by se_sm_init.
carry_restore_top:
    COPY24 se_st_cp_anchor,se_sm_pos
    COPY24 se_st_cp_anchor,se_sm_state+20
.ifdef SE_STYLE_GRID
    lda se_st_cp_rows
.else
    lda se_st_cp_carry
.endif
    and #STYLE_CARRY_FENCE_MASK
    sta se_sm_fence
.ifdef SE_STYLE_GRID
    lda se_st_cp_rows
.else
    lda se_st_cp_carry+1
.endif
 .ifdef SE_STYLE_GRID
    lsr
    lsr
    lsr
    lsr
    and #3
 .endif
    sta se_sm_language
.ifdef SE_STYLE_GRID
    lda se_st_cp_rows+1
.else
    lda se_st_cp_carry+2
.endif
    and #$1f
    sta se_sm_regions
.ifdef SE_STYLE_GRID
    lda se_st_cp_rows+2
.else
    lda se_st_cp_carry+3
.endif
    sta se_sm_state+76
.ifdef SE_STYLE_GRID
    lda se_st_cp_rows+3
.else
    lda se_st_cp_carry+4
.endif
    sta se_sm_state+77
.ifdef SE_STYLE_GRID
    lda se_st_cp_rows+4
.else
    lda se_st_cp_carry+5
.endif
    sta se_sm_state+78
    rts
inline_colors:
    .byte 0,1,2,3,4         ;prose, emphasis, strong, combined, code
