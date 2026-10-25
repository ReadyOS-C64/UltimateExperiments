; Pair descriptors are declarative overlays on a literal source stream.
; Only a closed delimiter emits a style/hide event. Unmatched input is literal.
; Nested spans combine emphasis/strong bits; code is exclusive. No line buffer.
.include "supermark/api.inc"
.macpack longbranch
.if .defined(SE_SM_CODE_ONLY) .and .defined(SE_SM_STATE_ONLY)
    .error "choose one SuperMark split flag"
.endif
.ifndef SE_SM_STATE_ONLY
.export se_si_init, se_si_feed, se_si_finish, se_si_at_body
.endif
.ifdef SE_SM_CODE_ONLY
.import se_si_pos,se_si_ready,se_si_kind,se_si_style,se_si_width
.import se_si_open,se_si_close,se_si_depth,se_si_state,se_si_state_size
.import si_begin,si_end,si_stack,si_run,si_run_len,si_run_pos,si_code,si_code_pos
.import si_pound,si_pound_context,si_escape,si_escape_count,si_pound_pos
.import si_leading,si_indent,si_column,si_byte
.else
.export se_si_pos, se_si_ready, se_si_kind, se_si_style, se_si_width
.export se_si_open, se_si_close, se_si_depth
.export se_si_state, se_si_state_size
se_si_state = si_begin
se_si_state_size = si_end-si_begin
.segment "SM_STATE"
si_begin:
se_si_pos: .res 3
se_si_ready: .res 1
se_si_kind: .res 1
se_si_style: .res 1
se_si_width: .res 1
se_si_open: .res 3
se_si_close: .res 3
se_si_depth: .res 1
si_stack: .res 32
si_run: .res 1
si_run_len: .res 1
si_run_pos: .res 3
si_code: .res 1
si_code_pos: .res 3
si_pound: .res 1
si_pound_context: .res 1
si_escape: .res 1
si_escape_count: .res 1
si_pound_pos: .res 3
si_leading: .res 1
si_indent: .res 1
si_column: .res 3
si_byte: .res 1
si_end:
.assert si_end-si_begin <= 128, error, "init loop exceeds signed X budget"
.ifdef SE_SM_STATE_ONLY
.export si_begin,si_end,si_stack,si_run,si_run_len,si_run_pos,si_code,si_code_pos
.export si_pound,si_pound_context,si_escape,si_escape_count,si_pound_pos
.export si_leading,si_indent,si_column,si_byte
.endif
.endif ;state allocation
.ifndef SE_SM_STATE_ONLY
.segment "SM_INLINE"
se_si_init:
    lda #0
.ifdef SE_SM_CODE_ONLY
    .assert se_si_state_size>0 .and se_si_state_size<=128,lderror,"inline state ABI range"
    ldx #<(se_si_state_size-1)
.else
    ldx #si_end-si_begin-1
.endif
:   sta si_begin,x
    dex
    bpl :-
    rts
se_si_at_body:
    ; After init, pos is body origin; A/X/Y is skipped source-prefix length24.
    sta si_column
    stx si_column+1
    sty si_column+2
    lda #2
    sta si_leading
    rts
se_si_feed:
    sta si_byte
    lda #0
    sta se_si_ready
    lda si_byte
    cmp #13
    jeq @newline
    lda si_escape
    jeq @no_escape_lookahead
    jsr si_escape_lookahead
    bcc @no_escape_lookahead
    jmp @advance
@no_escape_lookahead:
    lda si_run
    beq @not_run
    cmp si_byte
    bne @flush
    lda si_run_len
    cmp #4
    jcs @advance
    inc si_run_len
    jmp @advance
@flush:
    jsr si_flush
@not_run:
    lda si_pound
    jeq @plain
    lda #0
    sta si_pound
    lda si_byte
    cmp #'*'
    beq @escape
    cmp #'@'
    beq @escape
    cmp #$5C
    beq @escape
    cmp #'#'
    beq @column_zero
    cmp #':'
    beq @column_zero
    cmp #'-'
    beq @minus
    cmp #'.'
    bne @failed_pound
    lda si_pound_context
    and #4
    bne @defer_escape
    beq @failed_pound
@column_zero:
    lda si_pound_context
    and #1
    bne @defer_escape
    beq @failed_pound
@minus:
    lda si_pound_context
    and #2
    bne @defer_escape
    beq @failed_pound
@defer_escape:
    lda si_byte
    sta si_escape
    lda #1
    sta si_escape_count
    lda #2
    sta si_leading
    jmp @advance
@failed_pound:
    lda #2
    sta si_leading
    jmp @plain
@escape:
    lda #1
    sta se_si_ready
    sta se_si_width
    lda #SM_ESCAPE
    sta se_si_kind
    lda #0
    sta se_si_style
    SM_COPY24 si_pound_pos, se_si_open
    SM_COPY24 se_si_pos, se_si_close
    lda #2
    sta si_leading
    jmp @advance
@plain:
    lda si_byte
    cmp #'@'
    beq @start_run
    lda si_code
    jne @advance
    lda si_byte
    cmp #'*'
    beq @start_run
    cmp #$5C
    jeq @pound
    ; Track native block-prefix context for contextual pound escapes.
    lda si_leading
    cmp #2
    jeq @advance
    lda si_byte
    cmp #' '
    bne @digit
    lda si_leading
    bne @other
    inc si_indent
    jne @advance
    ; Saturate after255 spaces rather than turn a long indent into column0.
    dec si_indent
    jmp @advance
@digit:
    cmp #'0'
    bcc @other
    cmp #'9'+1
    bcs @other
    lda #1
    sta si_leading
    jmp @advance
@other:
    lda #2
    sta si_leading
    jmp @advance
@start_run:
    sta si_run
    lda #1
    sta si_run_len
    lda #2
    sta si_leading
    SM_COPY24 se_si_pos, si_run_pos
    jmp @advance
@pound:
    lda #1
    sta si_pound
    lda #0
    sta si_pound_context
    lda si_column
    ora si_column+1
    ora si_column+2
    bne :+
    inc si_pound_context
:   lda si_indent
    cmp #7
    bcs @pound_saved
    and #1
    bne @pound_saved
    lda si_leading
    cmp #1
    bne :+
    lda si_pound_context
    ora #4
    sta si_pound_context
:   lda si_leading
    bne @pound_saved
    lda si_pound_context
    ora #2
    sta si_pound_context
@pound_saved:
    SM_COPY24 se_si_pos, si_pound_pos
@advance:
    SM_INC24 se_si_pos
    SM_INC24 si_column
    clc
    rts
@newline:
    jsr si_flush
    jsr si_reset_line
    SM_INC24 se_si_pos
    clc
    rts
se_si_finish:
    lda #0
    sta se_si_ready
    jsr si_flush
    jsr si_reset_line
    clc
    rts
si_reset_line:
    lda #0
    sta si_column
    sta si_column+1
    sta si_column+2
    sta si_leading
    sta si_indent
    sta si_pound
    sta si_escape
    sta si_code
    sta se_si_depth
    rts
si_flush:
    lda si_run
    bne :+
    rts
:   cmp #'@'
    bne @stars
    lda si_run_len
    cmp #2
    jne @done
    lda si_code
    beq @open_code
    lda #0
    sta si_code
    lda #SM_INLINE_CODE
    sta se_si_style
    lda #2
    sta se_si_width
    SM_COPY24 si_code_pos, se_si_open
    jmp @event
@open_code:
    inc si_code
    SM_COPY24 si_run_pos, si_code_pos
    jmp @done
@stars:
    lda si_run_len
    cmp #4
    jcs @done
    lda se_si_depth
    beq @push
    sec
    sbc #1
    asl
    asl
    tax
    lda si_stack+3,x
    cmp si_run_len
    bne @push
    dec se_si_depth
    sta se_si_width
    ; Width1=emphasis1, width2=strong2, width3=combined3.
    sta se_si_style
    lda si_stack,x
    sta se_si_open
    lda si_stack+1,x
    sta se_si_open+1
    lda si_stack+2,x
    sta se_si_open+2
@event:
    SM_COPY24 si_run_pos, se_si_close
    lda #1
    sta se_si_ready
    lda #SM_PAIR
    sta se_si_kind
    jmp @done
@push:
    lda se_si_depth
    cmp #8
    bcs @done
    asl
    asl
    tax
    lda si_run_pos
    sta si_stack,x
    lda si_run_pos+1
    sta si_stack+1,x
    lda si_run_pos+2
    sta si_stack+2,x
    lda si_run_len
    sta si_stack+3,x
    inc se_si_depth
@done:
    lda #0
    sta si_run
    sta si_run_len
    rts

; Block-only delimiter escapes wait for enough lookahead to establish syntax.
; Carry set means current byte belongs to the pending hash/colon run.
; An emitted event and current byte may coexist; current byte still parses.
si_escape_lookahead:
    lda si_escape
    cmp #'#'
    beq @hash
    cmp #':'
    beq @colon
    ; Bullet '-' and ordered-list '.' require the following space.
    lda si_byte
    cmp #' '
    beq @confirm
    jmp @reject
@hash:
    lda si_byte
    cmp #'#'
    beq @more_hash
    cmp #' '
    beq @confirm
    jmp @reject
@more_hash:
    inc si_escape_count
    lda si_escape_count
    cmp #7
    bcc @retained
    jmp @reject
@colon:
    lda si_byte
    cmp #':'
    beq @more_colon
    cmp #' '
    beq @reject
    lda si_escape_count
    cmp #3
    bcs @confirm
    bcc @reject
@more_colon:
    inc si_escape_count
    lda si_escape_count
    cmp #16
    bcs @reject
@retained:
    sec
    rts
@confirm:
    lda #1
    sta se_si_ready
    sta se_si_width
    lda #SM_ESCAPE
    sta se_si_kind
    lda #0
    sta se_si_style
    SM_COPY24 si_pound_pos, se_si_open
    lda #1
    SM_ADD8 si_pound_pos, se_si_close
@reject:
    lda #0
    sta si_escape
    clc
    rts
.endif ;code allocation
