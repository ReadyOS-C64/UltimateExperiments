.setcpu "6502"
.macpack longbranch
SE_DISPLAY_MAP_IMPLEMENTATION=1
.include "supermark/display-map.inc"
.include "supermark/api.inc"
.import se_si_init,se_si_at_body,se_si_feed,se_si_finish
.import se_si_pos,se_si_ready,se_si_kind,se_si_style,se_si_width,se_si_open,se_si_close
.export se_dm_begin,se_dm_step,se_dm_from_source,se_dm_from_visible,se_dm_glyph
F=se_dm_frame
T=F+DM_TEMP
.macro COPY from,to,size
 ldx #size-1
:
 lda from,x
 sta to,x
 dex
 bpl :-
.endmacro
.macro OFFSET from
 sec
 .repeat 3,I
 lda from+I
 sbc F+DM_START+I
 sta T+I
 .endrepeat
 jcc bad_event
 lda T+1
 ora T+2
 jne bad_event
.endmacro
.segment "SM_DISPLAY_MAP"
se_dm_begin:
 lda F+DM_BUSY
 beq @new
 lda #DM_STATE
 sec
 rts
@new:
 lda #0
 sta F+DM_VALID
 sta F+DM_ERROR
 lda F+DM_LENGTH
 cmp #129
 jcs bad_range
 lda F+DM_EOF
 cmp #2
 jcs bad_range
 cmp #0
 bne @end
 ldx F+DM_LENGTH
 jeq bad_range
 dex
 lda F+DM_INPUT,x
 cmp #13
 jne bad_range
@end:
 clc
 lda F+DM_START
 adc F+DM_LENGTH
 sta F+DM_END
 lda F+DM_START+1
 adc #0
 sta F+DM_END+1
 lda F+DM_START+2
 adc #0
 sta F+DM_END+2
 jcs bad_range
 clc
 lda F+DM_COLUMN
 adc F+DM_LENGTH
 lda F+DM_COLUMN+1
 adc #0
 lda F+DM_COLUMN+2
 adc #0
 jcs bad_range
 jsr se_si_init
 COPY F+DM_START,se_si_pos,3
 lda F+DM_COLUMN
 ora F+DM_COLUMN+1
 ora F+DM_COLUMN+2
 beq @ready
 lda F+DM_COLUMN
 ldx F+DM_COLUMN+1
 ldy F+DM_COLUMN+2
 jsr se_si_at_body
@ready:
 lda #0
 sta F+DM_INDEX
 sta F+DM_COUNT
 sta F+DM_EVENTS
 lda #1
 sta F+DM_BUSY
 sta F+DM_STAGE
 jmp pending
se_dm_step:
 lda F+DM_BUSY
 jeq okay
 lda F+DM_STAGE
 cmp #1
 beq feed
 cmp #2
 jeq compose
 lda #DM_STATE
 jmp failed
feed:
 ldx F+DM_INDEX
 cpx F+DM_LENGTH
 beq finish
 lda F+DM_INPUT,x
 sta F+DM_RAW,x
 cmp #13
 bne @literal
 txa
 clc
 adc #1
 cmp F+DM_LENGTH
 jne bad_range
 lda #13
@literal:
 pha
 lda #0
 sta F+DM_HIDDEN,x
 inc F+DM_INDEX
 pla
 jsr se_si_feed
 jsr apply
 jcs return
 jmp pending
finish:
 jsr se_si_finish
 jsr apply
 jcs return
 lda #0
 sta F+DM_INDEX
 lda #2
 sta F+DM_STAGE
 jmp pending
; Descriptor identity comes only from the actual matched-pair parser. Validate
; its complete range against already consumed packet bytes before hiding any.
apply:
 lda se_si_ready
 jeq okay
 OFFSET se_si_open
 lda T
 sta F+DM_LOW
 OFFSET se_si_close
 lda T
 sta F+DM_HIGH
 lda se_si_kind
 cmp #SM_ESCAPE
 jeq escape
 cmp #SM_PAIR
 jne bad_event
 lda se_si_style
 cmp #SM_INLINE_CODE
 beq @code
 cmp #1
 jcc bad_event
 cmp #4
 jcs bad_event
 cmp se_si_width
 jne bad_event
 beq @width
@code:
 lda se_si_width
 cmp #2
 jne bad_event
@width:
 lda se_si_width
 sta F+DM_WIDTH
 clc
 adc F+DM_LOW
 cmp F+DM_HIGH
 jcc @close
 jne bad_event
@close:
 clc
 lda F+DM_HIGH
 adc F+DM_WIDTH
 jcs bad_event
 cmp F+DM_INDEX
 jcc @hide
 jne bad_event
@hide:
 ldx F+DM_LOW
 ldy F+DM_WIDTH
 lda #1
@open:
 sta F+DM_HIDDEN,x
 inx
 dey
 bne @open
 ldx F+DM_HIGH
 ldy F+DM_WIDTH
@closing:
 sta F+DM_HIDDEN,x
 inx
 dey
 bne @closing
 inc F+DM_EVENTS
 jmp okay
escape:
 lda se_si_style
 jne bad_event
 lda se_si_width
 cmp #1
 jne bad_event
 clc
 lda F+DM_LOW
 adc #1
 cmp F+DM_HIGH
 jne bad_event
 cmp F+DM_INDEX
 jcs bad_event
 ldx F+DM_LOW
 lda #1
 sta F+DM_HIDDEN,x
 inc F+DM_EVENTS
 jmp okay
compose:
 ldx F+DM_INDEX
 ldy F+DM_COUNT
 tya
 sta F+DM_S2V,x
 cpx F+DM_LENGTH
 beq complete
 lda F+DM_HIDDEN,x
 bne @skip
 lda F+DM_RAW,x
 sta F+DM_GLYPHS,y
 txa
 sta F+DM_V2S,y
 inc F+DM_COUNT
@skip:
 inc F+DM_INDEX
 jmp pending
complete:
 txa
 sta F+DM_V2S,y
 lda #0
 sta F+DM_BUSY
 sta F+DM_STAGE
 lda #1
 sta F+DM_VALID
okay:
 lda #0
 clc
return:
 rts
pending:
 lda #1
 clc
 rts
bad_range:
 lda #DM_RANGE
 bne failed
bad_event:
 lda #DM_EVENT
failed:
 sta F+DM_ERROR
 pha
 lda #0
 sta F+DM_BUSY
 sta F+DM_VALID
 sta F+DM_STAGE
 pla
 sec
 rts
; Query failures deliberately do not invalidate an otherwise valid mapping.
query_valid:
 lda F+DM_VALID
 cmp #1
 bne query_state
 lda F+DM_BUSY
 bne query_state
 lda F+DM_LENGTH
 cmp #129
 bcs query_state
 lda F+DM_COUNT
 cmp F+DM_LENGTH
 bcc @valid
 bne query_state
@valid:
 clc
 rts
query_state:
 lda #DM_STATE
 sec
 rts
query_range:
 lda #DM_RANGE
 sec
 rts
se_dm_from_source:
 jsr query_valid
 jcs return
 sec
 .repeat 3,I
 lda F+DM_SOURCE+I
 sbc F+DM_START+I
 sta T+I
 .endrepeat
 bcc query_range
 lda T+1
 ora T+2
 bne query_range
 lda T
 cmp F+DM_LENGTH
 bcc @find
 bne query_range
@find:
 tax
 lda F+DM_S2V,x
 cmp F+DM_COUNT
 bcc @visible
 bne query_range
@visible:
 sta F+DM_VISIBLE
 jmp okay
se_dm_glyph:
 jsr query_valid
 jcs return
 ldx F+DM_VISIBLE
 cpx F+DM_COUNT
 bcs query_range
 lda F+DM_V2S,x
 cmp F+DM_LENGTH
 bcs query_range
 jsr absolute
 COPY T,F+DM_SOURCE,3
 jmp okay
; Add a proven packet offset to origin. No overflow after BEGIN bounds proof.
absolute:
 clc
 adc F+DM_START
 sta T
 lda F+DM_START+1
 adc #0
 sta T+1
 lda F+DM_START+2
 adc #0
 sta T+2
 rts
se_dm_from_visible:
 jsr query_valid
 jcs return
 lda F+DM_VISIBLE
 cmp F+DM_COUNT
 jcc @search
 jne query_range
@search:
 ldx #0
@first:
 lda F+DM_S2V,x
 cmp F+DM_VISIBLE
 beq @found
 cpx F+DM_LENGTH
 jeq query_range
 inx
 jmp @first
@found:
 stx F+DM_LOW
 stx F+DM_HIGH
@last:
 cpx F+DM_LENGTH
 beq @anchors
 inx
 lda F+DM_S2V,x
 cmp F+DM_VISIBLE
 bne @anchors
 stx F+DM_HIGH
 jmp @last
@anchors:
 lda F+DM_LOW
 jsr absolute
 COPY T,F+DM_LEFT,3
 lda F+DM_HIGH
 jsr absolute
 COPY T,F+DM_RIGHT,3
 jmp okay
