; One loaded C worker classifies successive CR lines and scans each inline
; BODY exactly once. Output is transactional/backpressured, not a cache hit.
.setcpu "6502"
.macpack longbranch
.include "cache/semantic/api.inc"
.include "supermark/api.inc"
.include "fold/source.inc"
.import se_overlay_call,se_overlay_frame,se_f_owner
.import se_sm_init,se_sm_feed,se_sm_finish,se_sm_at_line
.import se_sm_pos,se_sm_ready,se_sm_kind,se_sm_start,se_sm_end,se_sm_body
.import se_sm_level,se_sm_language,se_sm_fence,se_sm_regions,se_sm_marker
.import sm_region_overflow
.import se_si_init,se_si_feed,se_si_finish,se_si_at_body
.import se_si_pos,se_si_ready,se_si_kind,se_si_style,se_si_width,se_si_open,se_si_close
.import se_crc_init,se_crc_byte,se_crc_value
.export se_bsc_begin,se_bsc_step,se_bsc_ack
.ifdef BSC_AUTO_OWNS_CANCEL
.ifndef BSC_SELECTOR_OWNS_OWNER
.error "automatic pump must own the selector owner guard"
.endif
.export se_bsc_owned_release
se_bsc_owned_release=release
.else
.export se_bsc_cancel
.endif
.macro CP source,target,count
 ldx #count-1
:
 lda source,x
 sta target,x
 dex
 bpl :-
.endmacro
.macro EQ source,target,count
 ldx #count-1
:
 lda source,x
 cmp target,x
 bne changed
 dex
 bpl :-
.endmacro
.macro INC24 value
 inc value
 bne :+
 inc value+1
 bne :+
 inc value+2
:
.endmacro
; Exact unsigned C/Z/N; A/X are dead at every use. Saves repeated long
; absolute comparisons without changing the full24bit source contract.
.macro C24 source,target
 ldx #2
 lda a:source,x
 cmp a:target,x
 bne *+7
 dex
 bpl *-9
 lda #0
.endmacro
.macro BSC_OWNER
.ifndef BSC_SELECTOR_OWNS_OWNER
 jsr owner
 jcs return
.endif
.endmacro
.segment "BSC_CODE"
.ifndef BSC_SELECTOR_OWNS_OWNER
owner:
 lda se_f_owner
 cmp #4
 bne busy
 clc
 rts
.endif
busy:lda #BSC_BUSY
 sec
 rts
bad:lda #BSC_BAD
 sec
 rts
changed:lda #BSC_CHANGED
 sec
 rts
authority:
 EQ BSC_AUTH,BSC_F+BCF_ARENA,13
 .assert se_bc_ticket=se_bc_arena+5,lderror,"live cache descriptor token/ticket layout"
 .assert se_bc_incarnation=se_bc_arena+9,lderror,"live cache descriptor incarnation layout"
 ldx #12
@key:
 lda se_bc_arena,x
 ldy authority_offsets,x
 cmp BSC_AUTH,y
 bne changed
 dex
 bpl @key
 lda se_bc_flags
 and #BC_MUTATING
 bne changed
 lda se_bc_flags
 and #BC_LOST
 beq @allowed
 bit BSC_F+BCF_BUDGET
 bpl changed
 lda se_bc_flags
 and #BC_ARMED
 bne changed ;only explicit unarmed fresh rebuild may continue through LOST
@allowed:
 CP BSC_AUTH,se_object_id,5
 jsr se_object_validate
 bcs return
 lda object_owner,x
 cmp #BC_OBJECT_TYPE
 bne changed
 clc
return:rts
full_guard:
 jsr authority
 bcs return
 lda #1
 jmp reader
se_bsc_begin:
 BSC_OWNER
 lda BSC_F+BCF_ABI
 cmp #BSC_ABI
 bne bad
 lda BSC_F+BCF_STATE
 ora BSC_F+BCF_FLAGS
 bne busy
 lda BSC_F+BCF_CAPS
 beq miss
 cmp #1
 beq :+
 cmp #3
 jne bad
:
 lda #0
 ldx #93-21
@clear:
 sta BSC_F+21,x
 dex
 bpl @clear
 sta BSC_F+BCF_READY
 sta BSC_F+BCF_ERROR
 CP BSC_F+BCF_ARENA,BSC_AUTH,13
 jsr authority
 bcs return
 lda #0
 ldx #85
@reader:
 sta BSC_READER,x
 dex
 bpl @reader
 jsr reader
 bcs return
 lda #BSC_READER_LIVE
 sta BSC_F+BCF_FLAGS
 CP BSC_READER+10,BSC_LENGTH,3
 jsr se_sm_init
 lda #BSC_BLOCK
 sta BSC_F+BCF_STATE
pending:
 lda #1
 clc
 rts
miss:lda #2
 clc
 rts
.ifndef BSC_AUTO_OWNS_CANCEL
se_bsc_cancel:
 BSC_OWNER
 lda BSC_F+BCF_ABI
 cmp #BSC_ABI
 jne bad
 lda BSC_F+BCF_FLAGS
 cmp #BSC_READER_LIVE+1
 jcs bad
 jsr release
 sta BSC_F+BCF_ERROR
 clc
 rts
.endif
release:
.ifndef BSC_AUTO_OWNS_CANCEL
 lda BSC_F+BCF_FLAGS
 and #BSC_READER_LIVE
 beq @clear
.endif
 CP BSC_READER,se_fs_state,86
 jsr se_fs_end ;resident, epoch/token safe even if R14 is absent
 CP se_fs_state,BSC_READER,86
@clear:
 lda #0
 sta BSC_F+BCF_FLAGS
 sta BSC_F+BCF_READY
 sta BSC_F+BCF_STATE
.ifdef BSC_AUTO_OWNS_CANCEL
 clc
.endif
 rts
failed:
 pha
 jsr release
 pla
 sta BSC_F+BCF_ERROR
 sec
 rts
se_bsc_ack:
 BSC_OWNER
 lda BSC_F+BCF_ABI
 cmp #BSC_ABI
 jne bad
 lda BSC_F+BCF_FLAGS
 cmp #BSC_READER_LIVE
 jne bad
 lda BSC_F+BCF_READY
 beq state_error
 jsr full_guard
 bcs failed
 lda #0
 sta BSC_F+BCF_READY
 jmp pending
se_bsc_step:
 BSC_OWNER
 lda BSC_F+BCF_ABI
 cmp #BSC_ABI
 jne bad
 lda BSC_F+BCF_FLAGS
 cmp #BSC_READER_LIVE
 jne bad
 lda BSC_F+BCF_STATE
 beq state_error
 jsr authority
 bcs failed
 ; The caller owns a pending IO packet until ACK. No R14/arena IO reuse.
 lda BSC_F+BCF_READY
 jne pending
 jsr full_guard
 bcs failed
 lda BSC_F+BCF_STATE
 cmp #BSC_BLOCK
 beq block
 cmp #BSC_BODY
 jeq body
 cmp #BSC_FINISH
 jeq inline_finish
 cmp #BSC_NEXT
 jeq next_line
state_error:
 lda #BSC_BAD
 jmp failed
; R14's current86B context aliases IO. Exchange only with no outstanding IO.
reader:
 pha
 CP BSC_READER,se_fs_state,86
 pla
 sta se_overlay_frame
 lda #14
 ldx #0
 jsr se_overlay_call
 php
 pha
 CP se_fs_state,BSC_READER,86
 pla
 plp
 rts
read:
 CP BSC_CURSOR,BSC_READER,3
 lda #32
 sta BSC_READER+3
 lda #<BSC_PACKET
 sta BSC_READER+4
 lda #>BSC_PACKET
 sta BSC_READER+5
 lda #2
 jsr reader
 jcs return
 INC24 BSC_READS
 lda BSC_READER+6
 sta BSC_USED
 lda #0
 sta BSC_INDEX
 clc
 rts
block:
 jsr read
 jcs failed
 lda BSC_USED
 beq @finish
@feed:
 ldx BSC_INDEX
 lda BSC_PACKET,x
 jsr se_sm_feed
 INC24 BSC_BLOCK_FEEDS
 INC24 BSC_CURSOR
 inc BSC_INDEX
 lda se_sm_ready
 jne record
 lda BSC_INDEX
 cmp BSC_USED
 bne @feed
 jmp pending
@finish:
 lda #1
 sta BSC_AT_EOF
 jsr se_sm_finish
 lda se_sm_ready
 bne record
 ; Explicit layout EOF sentinel, never an invented actual parser event.
 lda #1
 sta BSC_TERMINAL
 jsr clear_record
 CP BSC_LENGTH,BSC_CR+16,3
 lda #$FF
 sta BSC_CR+3
 INC24 BSC_LINES
 CP BSC_LINES,BSC_CR+4,3
 lda #8|2
 sta BSC_CR+2
 ldx #5
@carry:
 lda BSC_CARRY,x
 sta BSC_CR+28,x
 sta BSC_CR+34,x
 dex
 bpl @carry
 jmp record_complete
clear_record:
 lda #0
 ldx #95
@clear:
 sta BSC_CR,x
 dex
 bpl @clear
 lda #1
 sta BSC_CR+1
 sta BSC_CR+8
 sta BSC_CR+58
 sta BSC_CR+63
 sta BSC_CR+65
 sta BSC_CR+67
 ldx #3
@nil:
 lda BSC_F+BCF_TICKET,x
 sta BSC_CR+12,x
 sta BSC_CR+59,x
 lda #$FF
 sta BSC_CR+40,x
 sta BSC_CR+47,x
 sta BSC_CR+54,x
 dex
 bpl @nil
 rts
record:
 lda se_sm_kind
 cmp #9
 jcs changed_error
 C24 se_sm_pos,BSC_CURSOR
 jne changed_error
 C24 se_sm_start,BSC_NEXT_SOURCE
 jne changed_error
 C24 se_sm_pos,BSC_LENGTH
 bcc @position_ok
 jne changed_error
@position_ok:
 C24 se_sm_body,se_sm_start
 jcc changed_error
 C24 se_sm_body,se_sm_end
 bcc @body_ok
 jne changed_error
@body_ok:
 SUB24 se_sm_pos,se_sm_end,BSC_TEMP
 jcc changed_error
 lda BSC_TEMP+1
 ora BSC_TEMP+2
 jne changed_error
 lda BSC_TEMP
 cmp #2
 jcs changed_error
 jsr clear_record
 INC24 BSC_LINES
 CP BSC_LINES,BSC_CR+4,3
 lda se_sm_kind
 sta BSC_CR+3
 lda se_sm_language
 sta BSC_CR+69
 lda se_sm_level
 sta BSC_CR+70
 lda se_sm_marker
 sta BSC_CR+71
 CP se_sm_start,BSC_CR+16,3
 CP se_sm_end,BSC_END,3
 SUB24 se_sm_end,se_sm_start,BSC_CR+19
 SUB24 se_sm_body,se_sm_start,BSC_CR+22
 CP se_sm_pos,BSC_NEXT_SOURCE,3
 SUB24 se_sm_pos,se_sm_start,BSC_CR+25
 CP BSC_CARRY,BSC_CR+28,6
 lda se_sm_fence
 sta BSC_CR+34
 lda se_sm_language
 sta BSC_CR+35
 lda se_sm_regions
 sta BSC_CR+36
 CP sm_region_overflow,BSC_CR+37,3
 lda #1
 ldx BSC_AT_EOF
 beq :+
 lda #2
:
 sta BSC_CR+2
 CP se_sm_body,BSC_CURSOR,3
 ; All authoritative block state has now left the aliased parser frame.
 lda se_sm_kind
 cmp #4
 jcs record_complete ;fence/region/code rows have no inline interpretation
 INC24 BSC_BODY_SCANS
 lda #0
 sta BSC_INDEX
 sta BSC_USED
 jsr se_si_init
 CP BSC_CURSOR,se_si_pos,3
 lda BSC_CR+22
 ldx BSC_CR+23
 ldy BSC_CR+24
 jsr se_si_at_body
 lda #BSC_BODY
 sta BSC_F+BCF_STATE
 jmp pending
body:
 C24 BSC_CURSOR,BSC_END
 beq inline_finish
 bcs changed_error
 lda BSC_INDEX
 cmp BSC_USED
 bcc @feed
 jsr read
 jcs failed
 lda BSC_USED
 beq changed_error
@feed:
 ldx BSC_INDEX
 lda BSC_PACKET,x
 jsr se_si_feed
 INC24 BSC_INLINE_FEEDS
 INC24 BSC_CURSOR
 inc BSC_INDEX
 lda se_si_ready
 bne inline_event
 C24 BSC_CURSOR,BSC_END
 beq inline_finish
 lda BSC_INDEX
 cmp BSC_USED
 bne @feed
 jmp pending
inline_finish:
 lda #BSC_FINISH
 sta BSC_F+BCF_STATE
 jsr se_si_finish
 lda se_si_ready
 bne inline_event
 jmp record_complete
changed_error:
 lda #BSC_CHANGED
 jmp failed
inline_event:
 ; Parser emits only confirmed pairs/escapes; retain exact order and relative
 ;24bit ranges. The complete record cannot publish until FINISH is drained.
 jsr event_bounds
 jcs failed
 INC24 BSC_EVENTS
 INC24 BSC_CR+44
 lda se_si_kind
 sta BC_IO
 lda se_si_style
 sta BC_IO+1
 lda se_si_width
 sta BC_IO+2
 SUB24 se_si_open,BSC_CR+16,BC_IO+3
 SUB24 se_si_close,BSC_CR+16,BC_IO+6
 lda #0
 sta BC_IO+9
 lda #BSC_INLINE
 sta BSC_F+BCF_READY
 jmp pending
record_complete:
 lda BSC_CR+3
 cmp #4
 bcs @no_inline
 C24 se_si_pos,BSC_END
 jne changed_error
 lda BSC_CR+2
 ora #4
 sta BSC_CR+2
@no_inline:
 jsr se_crc_init
 ldy #1 ;publication byte0 and CRC74..75 are excluded
@crc:
 cpy #74
 bne :+
 ldy #76
:
 lda BSC_CR,y
 jsr se_crc_byte
 iny
 cpy #96
 bne @crc
 CP se_crc_value,BSC_CR+74,2
 lda #1
 sta BSC_CR ;publish complete staged record last
 CP BSC_CR,BC_IO,96
 lda #BSC_RECORD
 sta BSC_F+BCF_READY
 lda #BSC_NEXT
 sta BSC_F+BCF_STATE
 jmp pending
event_bounds:
 ; No caller may turn a malformed parser/output frame into trusted spans.
 C24 se_si_pos,BSC_CURSOR
 jne changed
 ADD24 BSC_CR+16,BSC_CR+22,BSC_TEMP
 jcs changed
 C24 se_si_open,BSC_TEMP
 jcc changed
 lda se_si_kind
 cmp #SM_ESCAPE
 beq @escape
 cmp #SM_PAIR
 jne changed
 lda se_si_style
 cmp #SM_INLINE_CODE
 beq @code
 cmp se_si_width
 jne changed
 cmp #1
 jcc changed
 cmp #4
 jcs changed
 bcc @pair
@code:
 lda se_si_width
 cmp #2
 jne changed
@pair:
 lda se_si_width
 clc
 adc se_si_open
 sta BSC_TEMP
 lda se_si_open+1
 adc #0
 sta BSC_TEMP+1
 lda se_si_open+2
 adc #0
 sta BSC_TEMP+2
 jcs changed
 C24 BSC_TEMP,se_si_close
 bcc @end
 jne changed
 beq @end
@escape:
 lda se_si_style
 jne changed
 lda se_si_width
 cmp #1
 jne changed
 CP se_si_open,BSC_TEMP,3
 INC24 BSC_TEMP
 C24 BSC_TEMP,se_si_close
 jne changed
@end:
 clc
 lda se_si_close
 adc se_si_width
 sta BSC_TEMP
 lda se_si_close+1
 adc #0
 sta BSC_TEMP+1
 lda se_si_close+2
 adc #0
 sta BSC_TEMP+2
 jcs changed
 C24 BSC_TEMP,BSC_END
 bcc @ok
 jne changed
@ok:clc
 rts
next_line:
 lda BSC_AT_EOF
 ora BSC_TERMINAL
 bne done
 CP BSC_CR+34,BSC_CARRY,6
 jsr se_sm_init
 CP BSC_NEXT_SOURCE,se_sm_pos,3
 jsr se_sm_at_line
 lda BSC_CARRY
 sta se_sm_fence
 lda BSC_CARRY+1
 sta se_sm_language
 lda BSC_CARRY+2
 sta se_sm_regions
 CP BSC_CARRY+3,sm_region_overflow,3
 CP BSC_NEXT_SOURCE,BSC_CURSOR,3
 lda #BSC_BLOCK
 sta BSC_F+BCF_STATE
 jmp pending
done:
.ifdef BSC_AUTO_OWNS_CANCEL
 jmp release
.else
 jsr release
 clc
 rts
.endif
authority_offsets:
 .byte 0,1,2,3,4,9,10,11,12,5,6,7,8
