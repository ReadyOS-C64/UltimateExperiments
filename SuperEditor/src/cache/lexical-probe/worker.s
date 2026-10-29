; Consumes only a completed actual C35 classification frame. No host parser
; events, sourceflattening or repeatedBODY scans. Pure actual lexer is linked.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "cache/lexical-probe/api.inc"
.include "fold/source.inc"
.include "supermark/api.inc"
.import se_overlay_call,se_overlay_frame,se_f_owner,se_render_caps
.import se_sl_init,se_sl_feed,se_sl_next,se_sl_finish
.import se_sl_pos,se_sl_count,se_sl_start,se_sl_end,se_sl_style
.import se_sl_state,se_sl_state_size
.import se_crc_init,se_crc_byte,se_crc_value
.export entry,se_lx_begin,se_lx_step,se_lx_ack,se_lx_cancel
.assert se_sl_state=LX_PARSER,lderror,"lexer phase offset"
.assert se_sl_state_size=60,lderror,"lexer phase size"
.macro CP source,target,n
 ldx #n-1
:
 lda source,x
 sta target,x
 dex
 bpl :-
.endmacro
.macro EQ source,target,n
 ldx #n-1
:
 lda source,x
 cmp target,x
 jne changed
 dex
 bpl :-
.endmacro
.macro C24 left,right
 ldx #2
:
 lda left,x
 cmp right,x
 bne :+
 dex
 bpl :-
 lda #0
:
.endmacro
.segment "LX_CODE"
 OVL_BINDING
entry:
 lda se_f_owner
 cmp #4
 jne busy
 lda se_overlay_frame
 beq se_lx_begin
 cmp #1
 jeq se_lx_step
 cmp #2
 jeq se_lx_cancel
 cmp #3
 jeq se_lx_ack
 cmp #4
 jeq reopen
 jmp bad
busy:lda #LX_BUSY
 sec
 rts
bad:lda #LX_BAD
 sec
 rts
changed:lda #LX_CHANGED
 sec
 rts
pending:lda #1
 clc
 rts
; Completed C35 hasBQ_STATE0/LIVE0, rootFS59 at+32, AUTH13 at+94,
; genuine stagedCR96 at+259. Copy overlap backwards before initializing.
se_lx_begin:
 lda se_render_caps
 cmp #3
 beq :+
 lda #2
 clc
 rts
:
 lda LX_STATE
 ora LX_LIVE
 ora se_fs_owned
 ora se_doc_read_locks
 jne busy
 lda se_bc_flags
 and #(BC_ARMED|BC_LOST|BC_MUTATING|BC_ACTIVE)
 cmp #BC_ARMED
 jne changed
 lda se_bc_count
 jne changed
 CP LX+94,LX_PARK,13
 CP LX+32,LX_PARSER,59
 CP LX+259,LX_CR,96
 ; Authenticate actualCR schema and CRC before using language/ranges.
 lda LX_CR
 and LX_CR+1
 cmp #1
 jne bad
 lda LX_CR+3
 cmp #SM_CODE_LINE
 jne bad
 lda LX_CR+69
 beq bad
 cmp #3
 jcs bad
 jsr se_crc_init
 ldy #1
@crc:cpy #74
 bne :+
 ldy #76
:
 lda LX_CR,y
 jsr se_crc_byte
 iny
 cpy #96
 bne @crc
 EQ se_crc_value,LX_CR+74,2
 EQ LX_PARK,se_bc_arena,13
 ; CR ticket and completed semantic proof are required; no literalrole guess.
 EQ LX_CR+12,LX_PARK+5,4
 lda LX_CR+58
 cmp #1
 jne bad
 lda #0
 ldx #93
@clear:sta LX,x
 dex
 bpl @clear
 CP LX_PARK,LX_AUTH,13
 lda LX_CR+69
 sta LX_LANGUAGE
 clc
 lda LX_CR+16
 adc LX_CR+22
 sta LX_BODY
 lda LX_CR+17
 adc LX_CR+23
 sta LX_BODY+1
 lda LX_CR+18
 adc LX_CR+24
 sta LX_BODY+2
 jcs bad
 clc
 lda LX_CR+16
 adc LX_CR+19
 sta LX_END
 lda LX_CR+17
 adc LX_CR+20
 sta LX_END+1
 lda LX_CR+18
 adc LX_CR+21
 sta LX_END+2
 jcs bad
 C24 LX_BODY,LX_END
 jcc @ranges
 jne bad
@ranges:
 lda #0
 ldx #85
@fs:sta LX_READER,x
 dex
 bpl @fs
 jsr reader
 jcs failed
 lda #1
 sta LX_LIVE
 ; The actual newreader must equal the full59-byte rootidentity returned by
 ; actualC35. No navigation/content equivalence or inferred tokenrelaxation.
 ldx #58
@source_key:
 lda LX_READER+27,x
 cmp LX_PARSER,x
 jne failed_changed
 dex
 bpl @source_key
 C24 LX_END,LX_READER+10
 jcc @valid
 jne failed_changed
@valid:
 lda LX_LANGUAGE
 jsr se_sl_init
 CP LX_BODY,se_sl_pos,3
 lda #1
 sta LX_STATE
 clc
 rts
se_lx_step:
 lda LX_STATE
 cmp #1
 jne bad
 jsr authority
 jcs failed
 lda LX_READY
 jne pending
 jsr guard
 jcs failed
 lda se_sl_count
 jne event
 lda LX_FINISHED
 jne terminal
 lda #32
 sta LX_BUDGET
@scan:
 C24 se_sl_pos,LX_END
 bcs finish
 lda LX_INDEX
 cmp LX_USED
 bcc @feed
 ; One32B read perSTEP. A consumed short packet always yields.
 jsr read
 jcs failed
 lda LX_USED
 jeq failed_changed
@feed:
 ldx LX_INDEX
 lda LX_PACKET,x
 jsr se_sl_feed
 jcs failed
 inc LX_FEEDS
 bne :+
 inc LX_FEEDS+1
 bne :+
 inc LX_FEEDS+2
:
 inc LX_INDEX
 lda se_sl_count
 jne pending
 dec LX_BUDGET
 jeq pending
 lda LX_INDEX
 cmp LX_USED
 bcc @scan
 jmp pending
finish:
 jsr se_sl_finish
 jcs failed
 lda #1
 sta LX_FINISHED
 jmp pending
terminal:
 lda #2
 sta LX_READY
 jmp pending
event:
 jsr se_sl_next
 jcs failed
 lda se_sl_style
 cmp #7
 jcc bad_fail
 cmp #14
 jcs bad_fail
 sta LX_OUTPUT
 C24 se_sl_start,LX_BODY
 jcc failed_changed
 C24 se_sl_end,LX_END
 jcc @bound
 jne failed_changed
@bound:
 C24 se_sl_start,se_sl_end
 jcs failed_changed
 CP se_sl_start,LX_OUTPUT+1,3
 CP se_sl_end,LX_OUTPUT+4,3
 inc LX_EVENTS
 bne :+
 inc LX_EVENTS+1
:
 lda #1
 sta LX_READY
 jmp pending
se_lx_ack:
 lda LX_STATE
 cmp #1
 jne bad
 lda LX_READY
 jeq bad
 pha
 jsr guard
 jcs @failed
 pla
 cmp #2
 jeq release
 lda #0
 sta LX_READY
 jmp pending
@failed:tax
 pla
 txa
 jmp failed
reopen:
 lda se_render_caps
 cmp #3
 beq :+
 lda #2
 clc
 rts
:
 lda LX_STATE
 ora LX_LIVE
 ora se_fs_owned
 ora se_doc_read_locks
 jne busy
 jsr authority
 jcs return_reopen
 lda #0
 ldx #85
@clear:sta LX_READER,x
 dex
 bpl @clear
 jsr reader
 jcs failed
 lda #1
 sta LX_LIVE
 lda #2
 sta LX_STATE
 lda #0
 clc
return_reopen:rts
se_lx_cancel:
 lda LX_LIVE
 beq @done
 jsr release
@done:lda #0
 sta LX_ERROR
 clc
 rts
bad_fail:lda #LX_BAD
 bne failed
failed_changed:lda #LX_CHANGED
failed:
 pha
 jsr release
 pla
 sta LX_ERROR
 sec
 rts
release:
 lda LX_LIVE
 beq @clear
 CP LX_READER,se_fs_state,86
 jsr se_fs_end
 CP se_fs_state,LX_READER,86
@clear:lda #0
 sta LX_STATE
 sta LX_LIVE
 sta LX_READY
 clc
 rts
authority:
 lda se_render_caps
 cmp #3
 jne changed
 EQ LX_AUTH,se_bc_arena,13
 lda se_bc_flags
 and #(BC_ARMED|BC_LOST|BC_MUTATING|BC_ACTIVE)
 cmp #BC_ARMED
 jne changed
 lda se_bc_count
 jne changed
 CP LX_AUTH,se_object_id,5
 jsr se_object_validate
 bcs @done
 lda object_owner,x
 cmp #BC_OBJECT_TYPE
 jne changed
 clc
@done:rts
guard:
 jsr authority
 bcs @done
 lda #1
 jmp reader
@done:rts
read:
 CP se_sl_pos,LX_READER,3
 lda #32
 sta LX_READER+3
 lda #<LX_PACKET
 sta LX_READER+4
 lda #>LX_PACKET
 sta LX_READER+5
 lda #2
 jsr reader
 bcs @done
 inc LX_READS
 bne :+
 inc LX_READS+1
 bne :+
 inc LX_READS+2
:
 lda LX_READER+6
 sta LX_USED
 lda #0
 sta LX_INDEX
@done:rts
reader:
 pha
 CP LX_READER,se_fs_state,86
 pla
 sta se_overlay_frame
 lda #14
 ldx #0
 jsr se_overlay_call
 php
 pha
 CP se_fs_state,LX_READER,86
 pla
 plp
 rts
