.setcpu "6502"
.macpack longbranch
.include "cache/query/api.inc"
.include "cache/arena/api.inc"
.include "object/api.inc"
.import se_crc_init,se_crc_byte,se_crc_value
.ifndef BCQ_SELECTOR_OWNS_OWNER
.import bq_owner
.endif
.import bq_authority,bq_source,bq_end,bq_pending,bq_bad,bq_changed,bq_corrupt,bq_fail,bq_done
.import bca_transfer,bca_guard,bca_open_step,bca_page_step
.import read_record
.export se_bc_query_begin,se_bc_query_step,se_bc_query_ack,se_bc_query_cancel
.macro CP source,target,count
 ldy #count-1
:
 lda source,y
 sta target,y
 dey
 bpl :-
.endmacro
.macro EQ source,target,count
 ldy #count-1
:
 lda source,y
 cmp target,y
 jne bq_changed
 dey
 bpl :-
.endmacro
 ; Baseline inapplicability is optional onlybefore jobsource publication.
.macro EQ_BASELINE source,target,count
 ldy #count-1
:
 lda source,y
 cmp target,y
.ifdef BCQ_CLASSIFY
 jne bq_baseline_miss
.else
 jne bq_changed
.endif
 dey
 bpl :-
.endmacro
.ifdef BCQ_CLASSIFY
.import bq_baseline_miss
.endif
.segment "CODE"
se_bc_query_begin:
.ifndef BCQ_SELECTOR_OWNS_OWNER
 jsr bq_owner
 jcs @return
.endif
 lda BQ_STATE
 ora BQ_LIVE
 jne @busy
 lda BQ_ABI
 cmp #1
 jne bq_bad
 lda BQ_CAPS
 cmp #1
 beq :+
 cmp #3
 jne @miss
:
 lda se_bc_flags
 and #BC_ARMED|BC_LOST|BC_MUTATING|BC_ACTIVE
 cmp #BC_ARMED
 bne @miss
 lda se_bc_count
 bne @miss
 CP se_bc_arena,BQ_AUTH,13
 lda #0
 sta BQ_READY
 sta BQ_ERROR
 sta BQ_LEX_CERT
 sta BQ_CACHE
 ldy #85
@clear:sta BQ_READER,y
 dey
 bpl @clear
 jsr se_bc_arena_open
 jcs bq_fail
 cmp #2
 beq @miss
 lda #BQ_OPEN
 sta BQ_STATE
 jmp bq_pending
@busy:lda #$C3
 sec
 rts
@miss:lda #2
 clc
@return:rts
se_bc_query_step:
.ifndef BCQ_SELECTOR_OWNS_OWNER
 jsr bq_owner
 jcs @return
.endif
 lda BQ_STATE
 jeq bq_bad
 jsr bq_authority
 jcs bq_fail
 lda BQ_READY
 jne bq_pending ;preserveheldIO, authorityonly; ACK drains before sourceguard
 lda BQ_STATE
 cmp #BQ_OPEN
 jeq @open
 cmp #BQ_SOURCE_BEGIN
 jeq @source_begin
 lda #1
 jsr bq_source
 jcs bq_fail
 lda BQ_STATE
 cmp #BQ_PAGE
 jeq @page
 cmp #BQ_PAGE_STEP
 jeq @page_step
 cmp #BQ_HEADER
 jeq @header
 cmp #BQ_READ
 jeq read_record
 jmp bq_bad
@open:
 jsr bca_open_step
 jcs bq_fail
 cmp #1
 jeq bq_pending
 lda BC_IO+31
 cmp #1
 jne bq_corrupt
 EQ BC_IO+22,BQ_AUTH+5,4
 lda BC_IO+94
 cmp #1
 jne bq_corrupt
 lda BC_IO+96
 cmp #1
 jne bq_corrupt
 lda BC_IO+95
 ora BC_IO+97
 ora BC_IO+98
 ora BC_IO+99
 jne bq_corrupt
 CP BC_IO+32,BQ_SOURCE,59
 CP BC_IO+91,BQ_LENGTH,3
 CP BC_IO+104,BQ_REF,4
 CP BC_IO+108,BQ_LAST,4
 CP BC_IO+112,BQ_REMAIN,3
 lda BQ_REMAIN+2
 jne bq_corrupt
 lda BQ_REMAIN
 ora BQ_REMAIN+1
 jeq bq_corrupt
 lda BQ_REMAIN+1
 cmp #42
 jcs bq_corrupt
 lda #BQ_SOURCE_BEGIN
 sta BQ_STATE
 jmp bq_pending
@source_begin:
 lda #0
 jsr bq_source
 jcs bq_fail
 lda #1
 sta BQ_LIVE
.ifdef BCQ_EDITOR_ACTIVE
 lda se_bc_flags
 ora #BC_ACTIVE
 sta se_bc_flags
.endif
 EQ_BASELINE BQ_SOURCE,BQ_READER+27,59
 EQ_BASELINE BQ_LENGTH,BQ_READER+10,3
 ldy #2
@position:lda BQ_POSITION,y
 cmp BQ_LENGTH,y
 bne @different
 dey
 bpl @position
 jmp @position_ok
@different:jcs bq_bad
@position_ok:
 lda #0
 sta BQ_EXPECT
 sta BQ_EXPECT+1
 sta BQ_EXPECT+2
 lda #1
 sta BQ_CLASS
 lda #96
 sta BQ_WIDTH
 lda #BQ_PAGE
 sta BQ_STATE
 jmp bq_pending
@page:
 ; Keep a proof only inside this exclusive, source-bound job and exactpage.
 lda BQ_REF
 cmp BQ_CACHE
 bne @newpage
 EQ BQ_REF+2,BQ_CACHE+1,2
 lda BQ_CLASS
 cmp BQ_CACHE+3
 bne @newpage
 lda #BQ_READ
 sta BQ_STATE
 jmp bq_pending
@newpage:
 lda BQ_REF
 sta BCA_PAGE
 lda BQ_CLASS
 sta BCA_KIND
 CP BQ_REF+2,BCA_GENERATION,2
 jsr se_bc_page_begin
 jcs bq_fail
 lda #BQ_PAGE_STEP
 sta BQ_STATE
 jmp bq_pending
@page_step:
 jsr bca_page_step
 jcs bq_fail
 cmp #1
 jeq bq_pending
 lda #BQ_HEADER
 sta BQ_STATE
 jmp bq_pending
@header:
 jsr page_base
 lda #64
 sta BCA_LENGTH
 jsr bca_guard
 jcs bq_fail
 lda #1
 jsr bca_transfer ;checkedtypedcopy ofheader after completePAGEproof
 jcs bq_fail
 jsr header_check
 jcs @return
 CP BC_IO+29,BQ_PAGE_NEXT,4
 lda BC_IO+23
 sta BQ_SLOTS
 lda BQ_REF
 sta BQ_CACHE
 CP BQ_REF+2,BQ_CACHE+1,2
 lda BQ_CLASS
 sta BQ_CACHE+3
 lda #BQ_READ
 sta BQ_STATE
 jmp bq_pending
@return:rts
; Checked payload address from reference; no caller-selectedhost pointer.
page_base:
 lda BQ_REF
 pha
 lsr
 lsr
 lsr
 lsr
 sta BCA_OFFSET+2
 pla
 asl
 asl
 asl
 asl
 sta BCA_OFFSET+1
 lda #0
 sta BCA_OFFSET
 rts
payload_offset:
 lda BQ_REF+1
 cmp BQ_SLOTS
 jcs bq_corrupt
 tay
 jsr times_width
 jsr page_base
 clc
 lda BQ_TEMP
 adc #64
 sta BCA_OFFSET
 lda BQ_TEMP+1
 adc BCA_OFFSET+1
 sta BCA_OFFSET+1
 lda BCA_OFFSET+2
 adc #0
 sta BCA_OFFSET+2
 lda BQ_WIDTH
 sta BCA_LENGTH
 jmp se_bc_arena_read
header_check:
 lda BC_IO+3
 cmp #1
 jne bq_corrupt
 ; Fullpageproof has checkedallfields; authenticate rereadbeforeusinglinks.
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
 lda se_crc_value
 cmp BC_IO+37
 jne bq_corrupt
 lda se_crc_value+1
 cmp BC_IO+38
 jne bq_corrupt
 EQ BC_IO+6,BQ_REF+2,2
 lda BC_IO+4
 cmp BQ_REF
 jne bq_corrupt
 lda BC_IO+5
 cmp BQ_CLASS
 jne bq_corrupt
 lda BC_IO+23
 jeq bq_corrupt
 lda BC_IO+24
 jne bq_corrupt
 ldy BC_IO+23
 jsr times_width
 lda BQ_TEMP
 cmp BC_IO+21
 jne bq_corrupt
 lda BQ_TEMP+1
 cmp BC_IO+22
 jne bq_corrupt
 clc
 rts
times_width:
 lda #0
 sta BQ_TEMP
 sta BQ_TEMP+1
 cpy #0
 beq @done
@multiply:clc
 lda BQ_TEMP
 adc BQ_WIDTH
 sta BQ_TEMP
 bcc :+
 inc BQ_TEMP+1
:
 dey
 bne @multiply
@done:rts
se_bc_query_ack:
.ifndef BCQ_SELECTOR_OWNS_OWNER
 jsr bq_owner
 jcs @return
.endif
 lda BQ_READY
 jeq bq_bad
 jsr bq_authority
 jcs bq_fail
 lda #0
 sta BQ_READY ;callerhasdrainedIO, nowR14 mayoverwriteit
 lda #1
 jsr bq_source
 jcs bq_fail
 .ifdef BCQ_CLASSIFY
 jmp bq_done
 .else
 lda BQ_CLASS
 cmp #2
 beq @event
 lda BQ_EVENTS
 ora BQ_EVENTS+1
 jeq bq_done
 lda #2
 sta BQ_CLASS
 lda #10
 sta BQ_WIDTH
 lda #BQ_PAGE
 sta BQ_STATE
 jmp bq_pending
@event:
 lda BQ_EVENTS
 bne :+
 dec BQ_EVENTS+1
:dec BQ_EVENTS
 lda BQ_EVENTS
 ora BQ_EVENTS+1
 jeq bq_done
 jsr advance
 jcs bq_fail
 lda #BQ_PAGE
 sta BQ_STATE
 jmp bq_pending
 .endif
@return:rts
se_bc_query_cancel:
.ifndef BCQ_SELECTOR_OWNS_OWNER
 jsr bq_owner
 jcs @return
.endif
 jsr bq_end
 lda #0
 clc
@return:rts
.export payload_offset
.import advance
