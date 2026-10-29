; Streaming CR-delimited block classifier. Event ranges exclude CR.
; Feed accepts one byte. ready=1 only on completed line; consume before next call.
; finish emits the final nonempty unterminated line, never invents a newline.
; Fixed prefix scratch32, arbitrary 24-bit line lengths. No source rewriting.
.include "supermark/api.inc"
.macpack longbranch
.if .defined(SE_SM_CODE_ONLY) .and .defined(SE_SM_STATE_ONLY)
    .error "choose one SuperMark split flag"
.endif
.ifndef SE_SM_STATE_ONLY
.export se_sm_init, se_sm_feed, se_sm_finish, se_sm_at_line
.endif
.ifdef SE_SM_CODE_ONLY
; State-only resident object supplies these symbols. No local state allocation.
.import se_sm_pos,se_sm_ready,se_sm_kind,se_sm_start,se_sm_end
.import se_sm_body,se_sm_level,se_sm_language,se_sm_fence,se_sm_regions
.import se_sm_marker,se_sm_end_state,se_sm_state,se_sm_state_size
.import sm_begin,sm_end,sm_line,sm_length,sm_used,sm_prefix,sm_colons,sm_index
.import sm_word,sm_word_len,sm_byte,sm_list_state,sm_indent,sm_list_body
.import sm_region_overflow
.else
.export se_sm_pos, se_sm_ready, se_sm_kind, se_sm_start, se_sm_end
.export se_sm_body, se_sm_level, se_sm_language, se_sm_fence, se_sm_regions
.export se_sm_marker, se_sm_end_state
.export se_sm_state, se_sm_state_size
se_sm_state = sm_begin
se_sm_state_size = sm_end-sm_begin
.segment "SM_STATE"
sm_begin:
se_sm_pos: .res 3
se_sm_ready: .res 1
se_sm_kind: .res 1
se_sm_start: .res 3
se_sm_end: .res 3
se_sm_body: .res 3
se_sm_level: .res 1
se_sm_language: .res 1
se_sm_fence: .res 1
se_sm_regions: .res 1
se_sm_marker: .res 1
se_sm_end_state: .res 1
sm_line: .res 3
sm_length: .res 3
sm_used: .res 1
sm_prefix: .res 32
sm_colons: .res 1
sm_index: .res 1
sm_word: .res 8
sm_word_len: .res 1
sm_byte: .res 1
sm_list_state: .res 1
sm_indent: .res 1
sm_list_body: .res 3
sm_region_overflow: .res 3
sm_end:
.assert sm_end-sm_begin <= 128, error, "block init loop exceeds signed X budget"
.ifdef SE_SM_STATE_ONLY
; Linkage for the matching code-only object; not a separate callable API.
.export sm_begin,sm_end,sm_line,sm_length,sm_used,sm_prefix,sm_colons,sm_index
.export sm_word,sm_word_len,sm_byte,sm_list_state,sm_indent,sm_list_body
.export sm_region_overflow
.endif
.endif ;state allocation
.ifndef SE_SM_STATE_ONLY
.segment "SM_BLOCK"
se_sm_init:
    lda #0
.ifdef SE_SM_CODE_ONLY
    .assert se_sm_state_size>0 .and se_sm_state_size<=128,lderror,"block state ABI range"
    ldx #<(se_sm_state_size-1)
.else
    ldx #sm_end-sm_begin-1
.endif
:   sta sm_begin,x
    dex
    bpl :-
    inc sm_list_state
    rts
se_sm_at_line:
    ; After init, seed pos then call this to start at a nonzero line boundary.
    SM_COPY24 se_sm_pos, sm_line
    rts
se_sm_feed:
    sta sm_byte
    lda #0
    sta se_sm_ready
    lda sm_byte
    cmp #13
    beq @newline
    ldx sm_used
    cpx #32
    bcs :+
    sta sm_prefix,x
    inc sm_used
:   jsr sm_list_byte
    SM_INC24 sm_length
    SM_INC24 se_sm_pos
    clc
    rts
@newline:
    jsr sm_classify
    SM_INC24 se_sm_pos
    SM_COPY24 se_sm_pos, sm_line
    lda #0
    sta sm_length
    sta sm_length+1
    sta sm_length+2
    sta sm_used
    sta sm_indent
    lda #1
    sta sm_list_state
    clc
    rts
se_sm_finish:
    lda #0
    sta se_sm_ready
    lda sm_length
    ora sm_length+1
    ora sm_length+2
    beq :+
    jsr sm_classify
    SM_COPY24 se_sm_pos, sm_line
    lda #0
    sta sm_length
    sta sm_length+1
    sta sm_length+2
    sta sm_used
    sta sm_indent
    lda #1
    sta sm_list_state
:   clc
    rts
sm_classify:
    lda #1
    sta se_sm_ready
    lda #0
    sta se_sm_kind
    sta se_sm_level
    sta se_sm_marker
    sta se_sm_end_state
    SM_COPY24 sm_line, se_sm_start
    SM_COPY24 se_sm_pos, se_sm_end
    SM_COPY24 sm_line, se_sm_body
    ; All code lines have precedence. A close has exactly N colons, no spaces.
    lda se_sm_fence
    jeq @outside
    lda #SM_CODE_LINE
    sta se_sm_kind
    lda sm_length+1
    ora sm_length+2
    jne @done
    lda sm_length
    cmp se_sm_fence
    jne @done
    ldx #0
@close_loop:
    lda sm_prefix,x
    cmp #':'
    jne @done
    inx
    cpx se_sm_fence
    bne @close_loop
    lda se_sm_fence
    sta se_sm_marker
    lda #SM_CODE_CLOSE
    sta se_sm_kind
    lda #0
    sta se_sm_fence
    lda #1
    sta se_sm_end_state
    jmp @body_marker
@outside:
    lda #SM_TEXT
    sta se_sm_language
    lda sm_length
    ora sm_length+1
    ora sm_length+2
    bne :+
    lda #SM_BLANK
    sta se_sm_kind
    rts
:   lda sm_prefix
    cmp #':'
    jeq @colon
    cmp #'#'
    jeq @heading
    lda sm_list_state
    cmp #4
    jne @done
    lda #SM_LIST
    sta se_sm_kind
    lda sm_indent
    lsr
    sta se_sm_level
    SM_COPY24 sm_list_body, se_sm_body
    ; Marker count is advisory; 0 means use the full body-start difference.
    sec
    lda se_sm_body
    sbc se_sm_start
    sta se_sm_marker
    lda se_sm_body+1
    sbc se_sm_start+1
    bne @long_marker
    lda se_sm_body+2
    sbc se_sm_start+2
    jeq @done
@long_marker:
    lda #0
    sta se_sm_marker
    rts
@heading:
    ldx #0
@hashes:
    inx
    cpx #7
    jcs @done
    cpx sm_used
    jcs @done
    lda sm_prefix,x
    cmp #'#'
    beq @hashes
    cmp #' '
    jne @done
    stx se_sm_level
    inx
    stx se_sm_marker
    lda #SM_HEADING
    sta se_sm_kind
    jmp @body_marker
@colon:
    ldx #0
@colons:
    inx
    cpx sm_used
    jcs @done
    lda sm_prefix,x
    cmp #':'
    bne @label
    cpx #15
    bcc @colons
    rts
@label:
    cpx #3
    jcc @done
    stx sm_colons
    stx sm_index
    ; Labels up to7 native letters. Unknown/long labels are plain-code fences.
    ldy #0
@word:
    cpx sm_used
    bcs @word_end
    lda sm_prefix,x
    cmp #' '
    beq @word_end
    cpy #7
    jcs @unknown
    jsr sm_fold
    sta sm_word,y
    iny
    inx
    bne @word
@word_end:
    sty sm_word_len
    cpy #0
    jeq @done
    lda #0
    sta se_sm_language
    cpy #3
    bne @not_end
    lda sm_word
    cmp #'E'
    bne @asm
    lda sm_word+1
    cmp #'N'
    bne @asm
    lda sm_word+2
    cmp #'D'
    bne @asm
    ; :::end is only a region close with exactly3 colons, no suffix.
    lda sm_colons
    cmp #3
    jne @done
    txa
    cmp sm_length
    jne @done
    lda sm_length+1
    ora sm_length+2
    jne @done
    lda sm_region_overflow
    ora sm_region_overflow+1
    ora sm_region_overflow+2
    beq @close_region
    ; Extra nesting and its matching end stay literal as a balanced pair.
    jsr sm_overflow_dec
    rts
@close_region:
    lda se_sm_regions
    jeq @done
    dec se_sm_regions
    lda #SM_REGION_CLOSE
    sta se_sm_kind
    stx se_sm_marker
    jmp @body_marker
@asm:
    lda sm_word
    cmp #'A'
    bne @code
    lda sm_word+1
    cmp #'S'
    bne @code
    lda sm_word+2
    cmp #'M'
    bne @code
    lda #SM_ASM
    sta se_sm_language
    jmp @code
@not_end:
    cpy #6
    bne @basic
    lda sm_colons
    cmp #3
    bne @code
    ldy #5
@region_match:
    lda sm_word,y
    cmp sm_region,y
    bne @code
    dey
    bpl @region_match
    lda se_sm_regions
    cmp #16
    bcc @region_room
    SM_INC24 sm_region_overflow
    rts
@region_room:
    inc se_sm_regions
    lda #SM_REGION_OPEN
    sta se_sm_kind
    ; Region title may be arbitrary length; body starts after optional space.
    cpx sm_used
    bcs :+
    lda sm_prefix,x
    cmp #' '
    bne :+
    inx
:   stx se_sm_marker
    jmp @body_marker
@basic:
    cpy #5
    bne @code
    ldy #4
@basic_match:
    lda sm_word,y
    cmp sm_basic,y
    bne @code
    dey
    bpl @basic_match
    lda #SM_BASIC
    sta se_sm_language
@code:
    ; Known labels followed by text are not a known lexer selection.
    cpx sm_used
    bcs @open
    lda #SM_TEXT
    sta se_sm_language
@open:
    lda sm_colons
    sta se_sm_fence
    lda #SM_CODE_OPEN
    sta se_sm_kind
    lda sm_used
    ; Entire opener is structural, even if its label exceeds prefix scratch.
    sta se_sm_marker
    SM_COPY24 se_sm_end, se_sm_body
    rts
@unknown:
    lda #SM_TEXT
    sta se_sm_language
    jmp @open
@body_marker:
    lda se_sm_marker
    SM_ADD8 se_sm_start, se_sm_body
@done:
    rts
sm_fold:
    cmp #$C1
    bcc :+
    cmp #$DB
    bcs :+
    and #$7F
:   rts
sm_region: .byte "REGION"
sm_basic: .byte "BASIC"

; Bounded list-prefix recognizer, including arbitrarily long supplied numbers.
sm_list_byte:
    lda sm_list_state
    beq @done
    cmp #4
    beq @done
    cmp #3
    beq @space_after
    cmp #2
    beq @digit
    lda sm_byte
    cmp #' '
    bne @first
    inc sm_indent
    lda sm_indent
    cmp #7
    bcc @done
    bcs @invalid
@first:
    lda sm_indent
    and #1
    bne @invalid
    lda sm_byte
    cmp #'-'
    beq @expect_space
    cmp #'*'
    beq @expect_space
    cmp #'0'
    bcc @invalid
    cmp #'9'+1
    bcs @invalid
    lda #2
    sta sm_list_state
    rts
@digit:
    lda sm_byte
    cmp #'.'
    beq @expect_space
    cmp #'0'
    bcc @invalid
    cmp #'9'+1
    bcs @invalid
    rts
@expect_space:
    lda #3
    sta sm_list_state
    rts
@space_after:
    lda sm_byte
    cmp #' '
    bne @invalid
    lda #4
    sta sm_list_state
    lda #1
    SM_ADD8 se_sm_pos, sm_list_body
@done:
    rts
@invalid:
    lda #0
    sta sm_list_state
    rts
sm_overflow_dec:
    lda sm_region_overflow
    bne @low
    lda sm_region_overflow+1
    bne @middle
    dec sm_region_overflow+2
@middle:
    dec sm_region_overflow+1
@low:
    dec sm_region_overflow
    rts
.endif ;code allocation
