; Reusable byte-stream lexical assistance. Input is native PETSCII, never CHROUT.
; feed accepts one byte iff count=0; drain next until carry set before feeding.
; At most2 token spans can end on one input byte. CR resets lexical state.
.include "supermark/api.inc"
.macpack longbranch
.if .defined(SE_SM_CODE_ONLY) .and .defined(SE_SM_STATE_ONLY)
    .error "choose one SuperMark split flag"
.endif
.ifndef SE_SM_STATE_ONLY
.export se_sl_init, se_sl_feed, se_sl_finish, se_sl_next
.endif
.ifdef SE_SM_CODE_ONLY
.import se_sl_pos,se_sl_language,se_sl_count,se_sl_start,se_sl_end,se_sl_style
.import se_sl_state,se_sl_state_size
.import sl_begin,sl_end,sl_queue,sl_state,sl_start,sl_endpos,sl_style,sl_byte
.import sl_normal,sl_buf,sl_length,sl_overflow,sl_prefix,sl_table_length
.import sl_table_chars,sl_number,sl_numflags,sl_quote,sl_dataquote,sl_plain
.import sl_consumed,sl_numdigits
.else
.export se_sl_pos, se_sl_language, se_sl_count
.export se_sl_start, se_sl_end, se_sl_style
.export se_sl_state, se_sl_state_size
se_sl_state = sl_begin
se_sl_state_size = sl_end-sl_begin
.segment "SM_STATE"
sl_begin:
se_sl_pos: .res 3
se_sl_language: .res 1
se_sl_count: .res 1
se_sl_start: .res 3
se_sl_end: .res 3
se_sl_style: .res 1
sl_queue: .res 14
sl_state: .res 1
sl_start: .res 3
sl_endpos: .res 3
sl_style: .res 1
sl_byte: .res 1
sl_normal: .res 1
sl_buf: .res 12
sl_length: .res 1
sl_overflow: .res 1
sl_prefix: .res 1
sl_table_length: .res 1
sl_table_chars: .res 1
sl_number: .res 1
sl_numflags: .res 1
sl_quote: .res 1
sl_dataquote: .res 1
sl_plain: .res 1
sl_consumed: .res 1
sl_numdigits: .res 1
sl_end:
.assert sl_end-sl_begin <= 128, error, "init loop exceeds signed X budget"
.ifdef SE_SM_STATE_ONLY
; Linkage for the matching code-only object; not additional callable services.
.export sl_begin,sl_end,sl_queue,sl_state,sl_start,sl_endpos,sl_style,sl_byte
.export sl_normal,sl_buf,sl_length,sl_overflow,sl_prefix,sl_table_length
.export sl_table_chars,sl_number,sl_numflags,sl_quote,sl_dataquote,sl_plain
.export sl_consumed,sl_numdigits
.endif
.endif ;state allocation
.ifndef SE_SM_STATE_ONLY
.segment "SM_LEXER"
se_sl_init:
    ; A selects plain0/BASIC1/asm2, out-of-range maps to plain.
    pha
    lda #0
.ifdef SE_SM_CODE_ONLY
    .assert se_sl_state_size>0 .and se_sl_state_size<=128,lderror,"lexer state ABI range"
    ldx #<(se_sl_state_size-1)
.else
    ldx #sl_end-sl_begin-1
.endif
:   sta sl_begin,x
    dex
    bpl :-
    pla
    cmp #3
    bcc :+
    lda #0
:   sta se_sl_language
    clc
    rts
se_sl_next:
    lda se_sl_count
    bne :+
    sec
    rts
:   ldx #0
@copy:
    lda sl_queue,x
    sta se_sl_start,x
    lda sl_queue+7,x
    sta sl_queue,x
    inx
    cpx #7
    bne @copy
    dec se_sl_count
    clc
    rts
se_sl_feed:
    sta sl_byte
    lda se_sl_count
    beq :+
    lda #1
    sec
    rts
:   lda se_sl_language
    jeq sl_advance
    lda #0
    sta sl_consumed
    lda sl_state
    cmp #1
    jeq sl_word
    cmp #2
    jeq sl_number_more
    cmp #3
    jeq sl_string
    cmp #4
    jeq sl_comment
    cmp #5
    jeq sl_data
sl_normal_byte:
    lda se_sl_language
    cmp #SM_BASIC
    jeq sl_basic
    lda sl_byte
    cmp #13
    jeq sl_newline
    lda sl_byte
    jsr sl_ident
    jcs sl_start_word
    cmp #'.'
    jeq sl_start_word
    cmp #'@'
    jeq sl_start_word
    cmp #'$'
    jeq sl_start_hex
    cmp #'%'
    jeq sl_start_binary
    cmp #';'
    jeq sl_start_comment
    cmp #$27
    jeq sl_start_string
sl_common:
    lda sl_byte
    cmp #'"'
    jeq sl_start_string
    cmp #'0'
    bcc sl_operator
    cmp #'9'+1
    jcc sl_start_number
sl_operator:
    lda sl_byte
    ldx #sl_ops_end-sl_ops-1
@loop:
    cmp sl_ops,x
    beq @found
    dex
    bpl @loop
    jmp sl_advance
@found:
    SM_COPY24 se_sl_pos, sl_start
    jsr sl_end_inclusive
    lda #SM_OPERATOR
    sta sl_style
    jsr sl_emit
    lda #0
    sta sl_plain
    jmp sl_advance
sl_basic:
    lda sl_byte
    cmp #'.'
    bne @ident
    lda sl_length
    ora sl_plain
    bne @ident
    lda #0
    sta sl_numdigits
    sta sl_number
    lda #1
    sta sl_numflags
    jmp sl_number_begin
@ident:
    lda sl_byte
    jsr sl_ident
    bcs sl_basic_letter
    ; '$' and '(' can complete BASIC function names LEFT$/TAB(.
    lda sl_length
    beq @separator
    lda sl_byte
    cmp #'$'
    beq @symbol
    cmp #'('
    bne @separator
@symbol:
    ldx sl_length
    sta sl_buf,x
    inc sl_length
    jsr sl_basic_table1
    pha
    jsr sl_basic_table2
    sta sl_prefix
    pla
    ora sl_prefix
    sta sl_normal
    dec sl_length
    lda sl_normal
    jne sl_basic_letter
@separator:
    lda #1
    sta sl_quote ;normal BASIC only: force held keyword-prefix resolution
    jsr sl_basic_scan
    lda sl_state
    cmp #4
    jeq sl_comment
    cmp #5
    jeq sl_data
    lda sl_byte
    cmp #13
    jeq sl_newline
    cmp #'"'
    jeq sl_start_string
    cmp #'0'
    bcc @other
    cmp #'9'+1
    bcs @other
    lda sl_plain
    jne sl_advance
    jmp sl_start_number
@other:
    lda #0
    sta sl_plain
    jmp sl_common
sl_basic_letter:
    lda sl_length
    bne :+
    SM_COPY24 se_sl_pos, sl_start
:   lda sl_byte
    jsr sl_fold
    ldx sl_length
    sta sl_buf,x
    inc sl_length
    lda #0
    sta sl_quote
    jsr sl_basic_scan
    jmp sl_advance
; Greedy streaming BASIC tokens: retain viable prefixes, resolve their suffixes
; at mismatch/separator/EOF. A rejected CONT prefix may contain ON. Emit its
; exact buffered endpoints, not the current input byte, then replay the tail.
sl_basic_scan:
    lda sl_length
    beq @done
@scan:
    jsr sl_basic_table1
    cmp #2
    beq @keyword
    pha
    jsr sl_basic_table2
    cmp #2
    beq @keyword_pop
    sta sl_prefix
    pla
    ora sl_prefix
    beq @discard
    lda sl_quote
    beq @done
@discard:
    dec sl_length
    ldx #0
@shift:
    lda sl_buf+1,x
    sta sl_buf,x
    inx
    cpx #11
    bne @shift
    SM_INC24 sl_start
    lda #1
    sta sl_plain
    lda sl_length
    bne @scan
@done:
    rts
@keyword_pop:
    pla
@keyword:
    lda sl_table_length
    sta sl_overflow ;ASM-only flag is unused in BASIC normal state
    lda #0
    sta sl_plain
    lda sl_buf
    cmp #'R'
    bne @data
    lda sl_buf+1
    cmp #'E'
    bne @data
    lda sl_buf+2
    cmp #'M'
    bne @data
    lda #4
    sta sl_state
    lda #0
    sta sl_length
    rts
@data:
    lda sl_buf
    cmp #'D'
    bne @emit
    lda sl_buf+1
    cmp #'A'
    bne @emit
    lda sl_buf+2
    cmp #'T'
    bne @emit
    lda #5
    sta sl_state
    lda #0
    sta sl_dataquote
@emit:
    lda sl_overflow
    SM_ADD8 sl_start,sl_endpos
    lda #SM_KEYWORD
    sta sl_style
    jsr sl_emit
    sec
    lda sl_length
    sbc sl_overflow
    sta sl_length
    lda sl_state
    bne @clear
    ldy #0
    ldx sl_overflow
@tail:
    cpy sl_length
    beq @position
    lda sl_buf,x
    sta sl_buf,y
    inx
    iny
    bne @tail
@position:
    SM_COPY24 sl_endpos,sl_start
    jmp sl_basic_scan
@clear:
    lda #0
    sta sl_length
    rts

sl_start_word:
    lda #1
    sta sl_state
    lda #0
    sta sl_length
    sta sl_overflow
    SM_COPY24 se_sl_pos, sl_start
sl_word_add:
    lda sl_byte
    jsr sl_fold
    ldx sl_length
    cpx #12
    bcs @long
    sta sl_buf,x
    inc sl_length
    jmp sl_advance
@long:
    lda #1
    sta sl_overflow
    jmp sl_advance
sl_word:
    lda sl_byte
    jsr sl_ident
    jcs sl_word_add
    lda sl_byte
    cmp #'0'
    bcc @end
    cmp #'9'+1
    jcc sl_word_add
@end:
    jsr sl_word_end
    lda #0
    sta sl_state
    lda sl_consumed
    jne sl_advance
    jmp sl_normal_byte
sl_word_end:
    lda sl_byte
    cmp #':'
    bne @known
    lda #1
    sta sl_consumed
    jsr sl_end_inclusive
    lda #SM_LABEL
    jmp sl_emit_style
@known:
    lda sl_overflow
    bne @done
    lda sl_buf
    cmp #'.'
    beq @directive
    jsr sl_asm_table
    cmp #2
    bne @done
    lda #SM_KEYWORD
    bne @publish
@directive:
    jsr sl_directive_table
    cmp #2
    bne @done
    lda #SM_DIRECTIVE
@publish:
    sta sl_style
    SM_COPY24 se_sl_pos, sl_endpos
    jmp sl_emit
@done:
    rts
sl_start_number:
    lda #1
    sta sl_numdigits
    lda #0
    sta sl_number
    sta sl_numflags
    jmp sl_number_begin
sl_start_hex:
    lda #0
    sta sl_numdigits
    sta sl_numflags
    lda #1
    sta sl_number
    jmp sl_number_begin
sl_start_binary:
    lda #0
    sta sl_numdigits
    sta sl_numflags
    lda #2
    sta sl_number
sl_number_begin:
    lda #2
    sta sl_state
    SM_COPY24 se_sl_pos, sl_start
    jmp sl_advance
sl_number_more:
    lda sl_byte
    jsr sl_fold
    sta sl_normal
    lda sl_number
    beq @decimal
    cmp #2
    beq @binary
    lda sl_normal
    cmp #'A'
    bcc @digits
    cmp #'F'+1
    jcc @accept
    jmp @end
@binary:
    lda sl_normal
    cmp #'0'
    beq @accept
    cmp #'1'
    beq @accept
    jmp @end
@decimal:
    lda sl_byte
    cmp #'.'
    bne @exponent
    lda se_sl_language
    cmp #SM_BASIC
    bne @end
    lda sl_numflags
    and #3
    bne @end
    inc sl_numflags
    jmp sl_advance
@exponent:
    lda se_sl_language
    cmp #SM_BASIC
    bne @digits
    lda sl_normal
    cmp #'E'
    bne @sign
    lda sl_numdigits
    beq @end
    lda sl_numflags
    and #2
    bne @end
    lda sl_numflags
    ora #6
    sta sl_numflags
    jmp sl_advance
@sign:
    lda sl_byte
    cmp #'+'
    beq @maybe_sign
    cmp #'-'
    bne @digits
@maybe_sign:
    lda sl_numflags
    and #4
    beq @end
    lda sl_numflags
    and #$FB
    sta sl_numflags
    jmp sl_advance
@digits:
    lda sl_normal
    cmp #'0'
    bcc @end
    cmp #'9'+1
    bcs @end
@accept:
    lda #1
    sta sl_numdigits
    lda sl_numflags
    and #$FB
    sta sl_numflags
    jmp sl_advance
@end:
    lda sl_numdigits
    beq @not_number
    SM_COPY24 se_sl_pos, sl_endpos
    lda #SM_NUMBER
    jsr sl_emit_style
@not_number:
    lda #0
    sta sl_state
    jmp sl_normal_byte
sl_start_string:
    lda #0
    sta sl_plain
    lda sl_byte
    sta sl_quote
    lda #3
    sta sl_state
    SM_COPY24 se_sl_pos, sl_start
    jmp sl_advance
sl_string:
    lda sl_byte
    cmp #13
    beq @line
    cmp sl_quote
    jne sl_advance
    jsr sl_end_inclusive
    lda #SM_STRING
    jsr sl_emit_style
    lda #0
    sta sl_state
    jmp sl_advance
@line:
    SM_COPY24 se_sl_pos, sl_endpos
    lda #SM_STRING
    jsr sl_emit_style
    jmp sl_newline
sl_start_comment:
    SM_COPY24 se_sl_pos, sl_start
    lda #4
    sta sl_state
    jmp sl_advance
sl_comment:
    lda sl_byte
    cmp #13
    jne sl_advance
    SM_COPY24 se_sl_pos, sl_endpos
    lda #SM_COMMENT
    jsr sl_emit_style
    jmp sl_newline
sl_data:
    lda sl_byte
    cmp #13
    beq sl_newline
    cmp #'"'
    bne @colon
    lda sl_dataquote
    eor #1
    sta sl_dataquote
    jmp sl_advance
@colon:
    cmp #':'
    bne sl_advance
    lda sl_dataquote
    bne sl_advance
    lda #0
    sta sl_state
    jmp sl_normal_byte
sl_newline:
    lda #0
    sta sl_state
    sta sl_length
    sta sl_plain
    sta sl_dataquote
sl_advance:
    SM_INC24 se_sl_pos
    clc
    rts
se_sl_finish:
    lda se_sl_count
    beq :+
    lda #1
    sec
    rts
:   lda #0
    sta sl_byte
    lda se_sl_language
    cmp #SM_BASIC
    bne :+
    lda sl_state
    bne :+
    lda #1
    sta sl_quote
    jsr sl_basic_scan
:   lda sl_state
    cmp #1
    bne :+
    jsr sl_word_end
    jmp @reset
:   cmp #2
    bne :+
    lda sl_numdigits
    beq @reset
    lda #SM_NUMBER
    bne @emit
:   cmp #3
    bne :+
    lda #SM_STRING
    bne @emit
:   cmp #4
    bne @reset
    lda #SM_COMMENT
@emit:
    sta sl_style
    SM_COPY24 se_sl_pos, sl_endpos
    jsr sl_emit
@reset:
    lda #0
    sta sl_state
    sta sl_length
    sta sl_plain
    clc
    rts
sl_end_inclusive:
    lda #1
    SM_ADD8 se_sl_pos, sl_endpos
    rts
sl_emit_style:
    sta sl_style
sl_emit:
    lda se_sl_count
    beq :+
    ldx #7
    bne @copy
:   ldx #0
@copy:
    lda sl_start
    sta sl_queue,x
    lda sl_start+1
    sta sl_queue+1,x
    lda sl_start+2
    sta sl_queue+2,x
    lda sl_endpos
    sta sl_queue+3,x
    lda sl_endpos+1
    sta sl_queue+4,x
    lda sl_endpos+2
    sta sl_queue+5,x
    lda sl_style
    sta sl_queue+6,x
    inc se_sl_count
    rts
sl_fold:
    cmp #$C1
    bcc :+
    cmp #$DB
    bcs :+
    and #$7F
:   rts
sl_ident:
    jsr sl_fold
    cmp #'_'
    beq @yes
    cmp #'@'
    beq @yes
    cmp #'.'
    beq @yes
    cmp #'A'
    bcc @no
    cmp #'Z'+1
    bcs @no
@yes:
    sec
    rts
@no:
    clc
    rts
sl_ops: .byte "+-*/^=<>#:,()&|!~"
sl_ops_end:
; Search tables are individually <256 bytes, so no zero-page pointer is needed.
.macro SL_TABLE_SEARCH routine, table, index
routine:
    lda #0
    sta sl_prefix
    .ifblank index
        ldy #0
    .else
        lda sl_buf
        sec
        sbc #'A'
        cmp #26
        bcs @done
        tax
        ldy index,x
    .endif
@entry:
    lda table,y
    beq @done
    sta sl_table_length
    iny
    sty sl_table_chars
    .ifnblank index
        lda table,y
        cmp sl_buf
        bne @done
        lda sl_table_length
    .endif
    .ifblank index
        cmp sl_length
        bcc @skip
    .endif
    ldx #0
@compare:
    lda table,y
    cmp sl_buf,x
    bne @skip
    iny
    inx
    .ifnblank index
        cpx sl_table_length
        beq @exact
    .endif
    cpx sl_length
    bne @compare
    lda sl_table_length
    cmp sl_length
    beq @exact
    lda #1
    sta sl_prefix
@skip:
    clc
    lda sl_table_chars
    adc sl_table_length
    tay
    jmp @entry
@exact:
    lda #2
    rts
@done:
    lda sl_prefix
    rts
.endmacro
SL_TABLE_SEARCH sl_basic_table1, sl_basic_words1, sl_basic_index1
SL_TABLE_SEARCH sl_basic_table2, sl_basic_words2, sl_basic_index2
SL_TABLE_SEARCH sl_asm_table, sl_asm_words, sl_asm_index
SL_TABLE_SEARCH sl_directive_table, sl_directive_words

sl_basic_words1:
    .byte 3, "ABS"
    .byte 3, "AND"
    .byte 3, "ASC"
    .byte 3, "ATN"
    .byte 4, "CHR$"
    .byte 5, "CLOSE"
    .byte 3, "CLR"
    .byte 3, "CMD"
    .byte 4, "CONT"
    .byte 3, "COS"
    .byte 4, "DATA"
    .byte 3, "DEF"
    .byte 3, "DIM"
    .byte 3, "END"
    .byte 3, "EXP"
    .byte 2, "FN"
    .byte 3, "FOR"
    .byte 3, "FRE"
    .byte 3, "GET"
    .byte 5, "GOSUB"
    .byte 4, "GOTO"
    .byte 2, "IF"
    .byte 5, "INPUT"
    .byte 3, "INT"
    .byte 5, "LEFT$"
    .byte 3, "LEN"
    .byte 3, "LET"
    .byte 4, "LIST"
    .byte 4, "LOAD"
    .byte 3, "LOG"
    .byte 4, "MID$"
    .byte 3, "NEW"
    .byte 4, "NEXT"
    .byte 3, "NOT"
    .byte 2, "ON"
    .byte 4, "OPEN"
    .byte 2, "OR"
    .byte 4, "PEEK"
    .byte 4, "POKE"
    .byte 3, "POS"
    .byte 5, "PRINT"
    .byte 4, "READ"
    .byte 3, "REM"
    .byte 7, "RESTORE"
    .byte 6, "RETURN"
    .byte 6, "RIGHT$"
    .byte 3, "RND"
    .byte 3, "RUN"
    .byte 4, "SAVE"
    .byte 3, "SGN"
    .byte 3, "SIN"
    .byte 4, "SPC("
    .byte 3, "SQR"
    .byte 4, "STEP"
    .byte 4, "STOP"
    .byte 0
sl_basic_index1: .byte 0,0,16,44,57,65,76,0,91,0,0,104,132,137,150,161,0,181,220,0,0,0,0,0,0,0

sl_basic_words2:
    .byte 4, "STR$"
    .byte 3, "SYS"
    .byte 4, "TAB("
    .byte 3, "TAN"
    .byte 4, "THEN"
    .byte 2, "TO"
    .byte 3, "USR"
    .byte 3, "VAL"
    .byte 6, "VERIFY"
    .byte 4, "WAIT"
    .byte 0
sl_basic_index2: .byte 0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,9,26,30,41,0,0,0

sl_asm_words:
    .byte 3, "ADC"
    .byte 3, "AND"
    .byte 3, "ASL"
    .byte 3, "BCC"
    .byte 3, "BCS"
    .byte 3, "BEQ"
    .byte 3, "BIT"
    .byte 3, "BMI"
    .byte 3, "BNE"
    .byte 3, "BPL"
    .byte 3, "BRK"
    .byte 3, "BVC"
    .byte 3, "BVS"
    .byte 3, "CLC"
    .byte 3, "CLD"
    .byte 3, "CLI"
    .byte 3, "CLV"
    .byte 3, "CMP"
    .byte 3, "CPX"
    .byte 3, "CPY"
    .byte 3, "DEC"
    .byte 3, "DEX"
    .byte 3, "DEY"
    .byte 3, "EOR"
    .byte 3, "INC"
    .byte 3, "INX"
    .byte 3, "INY"
    .byte 3, "JMP"
    .byte 3, "JSR"
    .byte 3, "LDA"
    .byte 3, "LDX"
    .byte 3, "LDY"
    .byte 3, "LSR"
    .byte 3, "NOP"
    .byte 3, "ORA"
    .byte 3, "PHA"
    .byte 3, "PHP"
    .byte 3, "PLA"
    .byte 3, "PLP"
    .byte 3, "ROL"
    .byte 3, "ROR"
    .byte 3, "RTI"
    .byte 3, "RTS"
    .byte 3, "SBC"
    .byte 3, "SEC"
    .byte 3, "SED"
    .byte 3, "SEI"
    .byte 3, "STA"
    .byte 3, "STX"
    .byte 3, "STY"
    .byte 3, "TAX"
    .byte 3, "TAY"
    .byte 3, "TSX"
    .byte 3, "TXA"
    .byte 3, "TXS"
    .byte 3, "TYA"
    .byte 0
sl_asm_index: .byte 0,12,52,80,92,0,0,0,96,108,0,116,0,132,136,140,0,156,172,200,0,0,0,0,0,0

sl_directive_words:
    .byte 5, ".ADDR"
    .byte 7, ".ASCIIZ"
    .byte 7, ".ASSERT"
    .byte 5, ".BYTE"
    .byte 7, ".DEFINE"
    .byte 6, ".DWORD"
    .byte 5, ".ELSE"
    .byte 7, ".ELSEIF"
    .byte 6, ".ENDIF"
    .byte 9, ".ENDMACRO"
    .byte 8, ".ENDPROC"
    .byte 10, ".ENDREPEAT"
    .byte 9, ".ENDSCOPE"
    .byte 7, ".EXPORT"
    .byte 9, ".EXPORTZP"
    .byte 3, ".IF"
    .byte 6, ".IFDEF"
    .byte 7, ".IFNDEF"
    .byte 7, ".IMPORT"
    .byte 9, ".IMPORTZP"
    .byte 7, ".INCBIN"
    .byte 8, ".INCLUDE"
    .byte 6, ".MACRO"
    .byte 4, ".ORG"
    .byte 5, ".PROC"
    .byte 7, ".REPEAT"
    .byte 4, ".RES"
    .byte 6, ".SCOPE"
    .byte 8, ".SEGMENT"
    .byte 7, ".SETCPU"
    .byte 5, ".WORD"
    .byte 0
.endif ;code allocation
