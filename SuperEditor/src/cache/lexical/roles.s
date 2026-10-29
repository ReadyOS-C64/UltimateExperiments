; Registered R37 lexical transport. Writes only unused typed53pages, never
; baseline roots/CR/INLINE data. Returned reference is not rootCRlexref linkage.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "cache/lexical/page.inc"
.include "fold/source.inc"
.import se_f_owner,se_overlay_frame,se_render_caps,se_crc_init,se_crc_byte,se_crc_value
.import se_snapshot_busy
.import bca_owner,bca_guard,bca_validate,bca_transfer,bca_pending,bca_done,bca_bad,bca_stale,bca_corrupt
.import se_bc_page_begin,bca_page_step,se_bc_arena_read
.export entry
.macro CP source,target,n
 ldy #n-1
:
 lda source,y
 sta target,y
 dey
 bpl :-
.endmacro
.macro EQ source,target,n
 ldy #n-1
:
 lda source,y
 cmp target,y
 jne bca_stale
 dey
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
.macro LIVE source,offset,n
 EQ source,LX_READER+27+offset,n
.endmacro
.segment "CODE"
 OVL_BINDING
entry:
 jsr bca_owner
 jcs return
 lda se_render_caps
 cmp #3
 beq :+
 lda #2
 clc
 rts
:
 lda se_overlay_frame
 jeq begin
 cmp #2
 jeq cancel
 cmp #4
 jeq read_begin
 jsr guard
 jcs return
 lda se_overlay_frame
 cmp #1
 jeq step
 cmp #3
 jeq append
 cmp #5
 jeq finish
 jmp bca_bad
return:rts
; The counted R14 context is owned by the Cworker; no R→R call or sharedIO
; exchange occurs here. Authenticate every59 actual liveidentity field +graphs.
guard:
 lda LP_STATE
 cmp #4
 bcc @source
 EQ LQ_START,LP_CURSOR,3
 EQ LQ_COUNT,LP_PHASE,1
@source:
 lda LX_LIVE
 cmp #1
 jne bca_stale
 lda LX_READER+7
 and LX_READER+8
 cmp #1
 jne bca_stale
 lda se_doc_read_locks
 jeq bca_stale
 EQ LX_AUTH,se_bc_arena,13
 lda se_bc_flags
 and #(BC_ARMED|BC_LOST|BC_MUTATING|BC_ACTIVE)
 cmp #(BC_ARMED|BC_ACTIVE)
 jne bca_stale
 lda se_bc_count
 jne bca_stale
 FS_FIELDS LIVE
 lda se_doc_busy
 ora se_h_phase
 ora se_b_phase
 ora se_clip_busy
 ora se_snapshot_busy
 jne bca_stale
 jsr se_doc_validate
 jcs return
 CP se_doc_meta,se_object_id,5
 jsr se_object_validate
 jcs return
 CP se_doc_original,se_object_id,5
 jsr se_object_validate
 jcs return
 CP se_doc_append,se_object_id,5
 jsr se_object_validate
 jcs return
 jmp bca_guard
begin:
 lda LP_STATE
 jne bca_bad
 lda LX_STATE
 cmp #1
 jne bca_bad
 lda LX_READY
 jne bca_bad
 CP LX_AUTH,BCA_BOUND,5
 CP LX_AUTH+5,BCA_TICKET,4
 CP LX_AUTH+9,BCA_INC,4
 jsr guard
 jcs return
 lda #0
 sta LP_COUNT
 sta LP_COUNT+1
 sta LP_GEN+1
 sta BCA_PHASE
 sta BCA_PROOF
 lda #1
 sta LP_GEN
 sta LP_PAGE
 sta LP_STATE
 jmp bca_pending
cancel:
 lda #0
 sta LP_STATE
 sta LP_PHASE
 sta BCA_PHASE
 sta BCA_PROOF
 jmp bca_done
; Convert page+payload offset to checked objectrelative24. Low12 from OFFSET.
page_offset:
 lda LP_PAGE
 asl
 asl
 asl
 asl
 sta BCA_OFFSET+1
 lda LP_PAGE
 lsr
 lsr
 lsr
 lsr
 sta BCA_OFFSET+2
 lda #0
 sta BCA_OFFSET
 rts
; Directoryentry8 at0100+8*page; free iff allzero (no guessed freebank).
dir_offset:
 lda LP_PAGE
 lsr
 lsr
 lsr
 lsr
 lsr
 clc
 adc #1
 sta BCA_OFFSET+1
 lda LP_PAGE
 asl
 asl
 asl
 sta BCA_OFFSET
 lda #0
 sta BCA_OFFSET+2
 rts
step:
 lda LP_STATE
 cmp #1
 jeq find
 cmp #2
 jeq sealing
 cmp #4
 jeq read_crc
 cmp #5
 jeq read_desc
 cmp #6
 jeq span
 cmp #7
 jeq paint
 jmp bca_bad
find:
 lda LP_PAGE
 lsr
 lsr
 lsr
 lsr
 cmp BCA_BANKS
 jcs stream
 jsr dir_offset
 lda #8
 sta BCA_LENGTH
 lda #1
 jsr bca_transfer
 jcs return
 ldy #7
 lda #0
@free:ora BC_IO,y
 dey
 bpl @free
 cmp #0
 beq find_found
 inc LP_PAGE
 bne find_more
stream:lda #0
 sta LP_STATE
 lda #3
 clc
 rts
find_more:jmp bca_pending
find_found:lda #96
 sta LP_USED
 lda #0
 sta LP_USED+1
 sta LP_PHASE
 lda #2
 sta LP_STATE
 jmp bca_done
append:
 lda LP_STATE
 cmp #2
 jne bca_bad
 lda LP_PHASE
 jne bca_bad
 lda LX_READY
 cmp #1
 jne bca_bad
 ;7-byte actual lexeroutput; count562 is an explicit pressure/STREAM bound.
 lda LP_COUNT+1
 cmp #>LEX_SPAN_LIMIT
 bcc @room
 bne stream
 lda LP_COUNT
 cmp #<LEX_SPAN_LIMIT
 bcs stream
@room:
 lda BC_IO
 cmp #7
 jcc bca_bad
 cmp #14
 jcs bca_bad
 ; Actual lexer validates spans; page independently checks them too.
 C24 BC_IO+1,LX_BODY
 jcc bca_bad
 C24 BC_IO+4,LX_END
 jcc @end
 jne bca_bad
@end:C24 BC_IO+1,BC_IO+4
 jcs bca_bad
 jsr page_offset
 clc
 lda LP_USED
 adc #64
 sta BCA_OFFSET
 lda LP_USED+1
 adc BCA_OFFSET+1
 sta BCA_OFFSET+1
 lda BCA_OFFSET+2
 adc #0
 sta BCA_OFFSET+2
 lda #7
 sta BCA_LENGTH
 lda #0
 jsr bca_transfer
 jcs return
 clc
 lda LP_USED
 adc #7
 sta LP_USED
 bcc :+
 inc LP_USED+1
:
 inc LP_COUNT
 bne :+
 inc LP_COUNT+1
:
 jmp bca_done
; Descriptor96 andpageheader are genuinely derived from the held reader/key;
; no rootlexABI/CRref or completeness flag is invented.
finish:
 lda LP_STATE
 cmp #2
 jne bca_bad
 lda LP_PHASE
 jne bca_bad
 lda LX_READY
 cmp #2
 jne bca_bad
 jsr descriptor
 jsr page_offset
 lda #64
 sta BCA_OFFSET
 lda #96
 sta BCA_LENGTH
 lda #0
 jsr bca_transfer
 jcs return
 jsr page_offset
 lda #64
 sta LP_CURSOR
 lda BCA_OFFSET+1
 sta LP_CURSOR+1
 lda BCA_OFFSET+2
 sta LP_CURSOR+2
 lda #$FF
 sta LP_CRC
 sta LP_CRC+1
 lda #1
 sta LP_PHASE
 jmp bca_pending
sealing:
 lda LP_PHASE
 jeq bca_bad
 cmp #1
 jeq crc_payload
 cmp #2
 jeq header
 cmp #3
 jeq header_valid
 cmp #4
 jeq directory
 cmp #5
 jeq directory_valid
 jmp bca_bad
crc_payload:
 CP LP_CURSOR,BCA_OFFSET,3
 jsr page_offset
 ; Remaining = pagepayload64 + USED - cursor, in16bits.
 clc
 lda LP_USED
 adc #64
 sta LX_TEMP
 lda LP_USED+1
 adc BCA_OFFSET+1
 sta LX_TEMP+1
 sec
 lda LX_TEMP
 sbc LP_CURSOR
 sta LX_TEMP
 lda LX_TEMP+1
 sbc LP_CURSOR+1
 sta LX_TEMP+1
 lda LX_TEMP
 ora LX_TEMP+1
 beq @done
 lda #128
 ldx LX_TEMP+1
 bne @count
 cmp LX_TEMP
 bcc @count
 lda LX_TEMP
@count:sta BCA_LENGTH
 CP LP_CURSOR,BCA_OFFSET,3
 lda #1
 jsr bca_transfer
 jcs return
 CP LP_CRC,se_crc_value,2
 ldy #0
@byte:lda BC_IO,y
 jsr se_crc_byte
 iny
 cpy BCA_LENGTH
 bne @byte
 CP se_crc_value,LP_CRC,2
 clc
 lda LP_CURSOR
 adc BCA_LENGTH
 sta LP_CURSOR
 bcc :+
 inc LP_CURSOR+1
 bne :+
 inc LP_CURSOR+2
:
 jmp bca_pending
@done:inc LP_PHASE
 jmp bca_pending
header:
 lda #0
 ldy #63
@clear:sta BC_IO,y
 dey
 bpl @clear
 lda #'B'
 sta BC_IO
 lda #'P'
 sta BC_IO+1
 lda #1
 sta BC_IO+2
 lda LP_PAGE
 sta BC_IO+4
 lda #BC_PAGE_LEX
 sta BC_IO+5
 CP LP_GEN,BC_IO+6,2
 CP LX_AUTH+9,BC_IO+8,4
 CP LX_AUTH,BC_IO+12,5
 CP LP_USED,BC_IO+21,2
 CP LP_COUNT,BC_IO+23,2
 lda #$FF
 ldy #7
@nil:sta BC_IO+25,y
 dey
 bpl @nil
 CP LP_CRC,BC_IO+39,2
 jsr se_crc_init
 ldy #0
@crc:cpy #3
 beq @skip
 cpy #37
 beq @skip
 cpy #38
 beq @skip
 lda BC_IO,y
 jsr se_crc_byte
@skip:iny
 cpy #64
 bne @crc
 CP se_crc_value,BC_IO+37,2
 jsr page_offset
 lda #64
 sta BCA_LENGTH
 lda #0
 jsr bca_transfer
 jcs return
 inc LP_PHASE
 jmp bca_pending
header_valid:
 jsr page_offset
 lda #3
 sta BCA_OFFSET
 lda #1
 sta BC_IO
 sta BCA_LENGTH
 lda #0
 jsr bca_transfer
 jcs return
 inc LP_PHASE
 jmp bca_pending
directory:
 lda #0
 ldy #7
@clear:sta BC_IO,y
 dey
 bpl @clear
 CP LP_GEN,BC_IO,2
 lda #BC_PAGE_LEX
 sta BC_IO+2
 lda #1
 sta BC_IO+3
 jsr se_crc_init
 ldy #0
@crc:cpy #4
 beq @skip
 cpy #5
 beq @skip
 lda BC_IO,y
 jsr se_crc_byte
@skip:iny
 cpy #8
 bne @crc
 CP se_crc_value,BC_IO+4,2
 lda #0
 sta BC_IO+3               ;CRC isforfinalVALID1; markerremains0
 jsr dir_offset
 lda #8
 sta BCA_LENGTH
 lda #0
 jsr bca_transfer
 jcs return
 inc LP_PHASE
 jmp bca_pending
directory_valid:
 jsr dir_offset
 clc
 lda BCA_OFFSET
 adc #3
 sta BCA_OFFSET
 bcc :+
 inc BCA_OFFSET+1
:
 lda #1
 sta BC_IO
 sta BCA_LENGTH
 lda #0
 jsr bca_transfer
 jcs return
 lda #3
 sta LP_STATE
 lda #0
 sta LP_PHASE
 jmp bca_done
descriptor:
 lda #0
 ldy #95
@clear:sta BC_IO,y
 dey
 bpl @clear
 lda #'L'
 sta BC_IO
 lda #'X'
 sta BC_IO+1
 lda #'C'
 sta BC_IO+2
 lda #'1'
 sta BC_IO+3
 lda #1
 sta BC_IO+4
 sta BC_IO+5
 lda LX_LANGUAGE
 sta BC_IO+6
 CP LX_BODY,BC_IO+8,3
 CP LX_END,BC_IO+11,3
 CP LX_AUTH,BC_IO+14,13
 CP LX_READER+27,BC_IO+27,59
 CP LP_COUNT,BC_IO+86,2
 rts
; Consumer operations appended below; source isreopened by actualCworker op4.
read_begin:
 jsr guard
 jcs return
 lda LP_STATE
 cmp #3
 jne bca_bad
 lda LQ_COUNT
 jeq @bad
 cmp #129
 jcs @bad
 C24 LQ_START,LX_BODY
 jcc bca_bad
 clc
 lda LQ_START
 adc LQ_COUNT
 sta LQ_END
 lda LQ_START+1
 adc #0
 sta LQ_END+1
 lda LQ_START+2
 adc #0
 sta LQ_END+2
 jcs bca_bad
 C24 LQ_END,LX_END
 jcc @valid
 jne bca_bad
@valid:
 CP LQ_START,LP_CURSOR,3
 lda LQ_COUNT
 sta LP_PHASE
 lda #0
 sta LQ_READY
 sta LQ_INDEX
 sta LQ_INDEX+1
 sta BCA_PHASE
 sta BCA_PROOF
 lda LP_PAGE
 sta BCA_PAGE
 lda #BC_PAGE_LEX
 sta BCA_KIND
 CP LP_GEN,BCA_GENERATION,2
 jsr se_bc_page_begin
 jcs return
 lda #4
 sta LP_STATE
 jmp bca_pending
@bad:jmp bca_bad
read_crc:
 lda BCA_PHASE
 beq @done
 jsr bca_page_step
 jcs return
 jmp bca_pending
@done:lda #5
 sta LP_STATE
 jmp bca_pending
read_desc:
 lda BCA_PROOF
 cmp #$A5
 jne bca_stale
 jsr page_offset
 lda #64
 sta BCA_OFFSET
 lda #96
 sta BCA_LENGTH
 lda #1
 jsr bca_transfer
 jcs return
 lda BC_IO
 cmp #'L'
 jne bca_corrupt
 lda BC_IO+1
 cmp #'X'
 jne bca_corrupt
 lda BC_IO+2
 cmp #'C'
 jne bca_corrupt
 lda BC_IO+3
 cmp #'1'
 jne bca_corrupt
 lda BC_IO+4
 and BC_IO+5
 cmp #1
 jne bca_corrupt
 EQ BC_IO+6,LX_LANGUAGE,1
 EQ BC_IO+8,LX_BODY,3
 EQ BC_IO+11,LX_END,3
 EQ BC_IO+14,LX_AUTH,13
 EQ BC_IO+27,LX_READER+27,59
 EQ BC_IO+86,LP_COUNT,2
 lda LP_COUNT+1
 cmp #>LEX_SPAN_LIMIT
 bcc @bounded_count
 jne bca_corrupt
 lda LP_COUNT
 cmp #<(LEX_SPAN_LIMIT+1)
 jcs bca_corrupt
@bounded_count:
 lda #4
 ldx LQ_COUNT
@base:dex
 sta LX_ROLES,x
 bne @base
 lda #6
 sta LP_STATE
 jmp bca_pending
span:
 lda LQ_INDEX
 cmp LP_COUNT
 bne @more
 lda LQ_INDEX+1
 cmp LP_COUNT+1
 bne @more
 lda #1
 sta LQ_READY
 lda #3
 sta LP_STATE
 jmp bca_done
@more:
 ; 7*index16 + payload64+descriptor96; maximum4032 is prevalidated.
 lda LQ_INDEX
 sta LX_TEMP
 lda LQ_INDEX+1
 sta LX_TEMP+1
 asl LX_TEMP
 rol LX_TEMP+1
 asl LX_TEMP
 rol LX_TEMP+1
 asl LX_TEMP
 rol LX_TEMP+1
 sec
 lda LX_TEMP
 sbc LQ_INDEX
 sta LX_TEMP
 lda LX_TEMP+1
 sbc LQ_INDEX+1
 sta LX_TEMP+1
 jsr page_offset
 clc
 lda LX_TEMP
 adc #160
 sta BCA_OFFSET
 lda LX_TEMP+1
 adc BCA_OFFSET+1
 sta BCA_OFFSET+1
 lda BCA_OFFSET+2
 adc #0
 sta BCA_OFFSET+2
 lda #7
 sta BCA_LENGTH
 lda #1
 jsr bca_transfer
 jcs return
 lda BC_IO
 cmp #7
 jcc bca_corrupt
 cmp #14
 jcs bca_corrupt
 sta LQ_ROLE
 CP BC_IO+1,LQ_FROM,3
 CP BC_IO+4,LQ_TO,3
 C24 LQ_FROM,LX_BODY
 jcc bca_corrupt
 C24 LQ_TO,LX_END
 jcc @bounded
 jne bca_corrupt
@bounded:C24 LQ_FROM,LQ_TO
 jcs bca_corrupt
 inc LQ_INDEX
 bne :+
 inc LQ_INDEX+1
:
 C24 LQ_FROM,LQ_START
 bcs @from_done
 CP LQ_START,LQ_FROM,3
@from_done:
 C24 LQ_TO,LQ_END
 bcc @to_done
 CP LQ_END,LQ_TO,3
@to_done:
 C24 LQ_FROM,LQ_TO
 jcs bca_pending
 sec
 lda LQ_FROM
 sbc LQ_START
 sta LQ_PAINT
 sec
 lda LQ_TO
 sbc LQ_START
 sta LQ_LAST
 lda #7
 sta LP_STATE
 jmp bca_pending
paint:
 lda #32
 sta LX_BUDGET
@byte:ldx LQ_PAINT
 cpx LQ_LAST
 beq @done
 lda LQ_ROLE
 sta LX_ROLES,x
 inc LQ_PAINT
 dec LX_BUDGET
 bne @byte
 jmp bca_pending
@done:lda #6
 sta LP_STATE
 jmp bca_pending
