; PRIVATE rootlessINLINE budgetcopy; releasedqueryprofiles unchanged.
.setcpu "6502"
.macpack longbranch
.include "cache/inline/api.inc"
.include "cache/arena/api.inc"
.include "object/api.inc"
.import se_crc_init,se_crc_byte,se_crc_value
.ifndef BCQ_SELECTOR_OWNS_OWNER
.import bq_owner
.endif
.import bq_authority,bq_source,bq_end,bq_pending,bq_bad,bq_changed,bq_corrupt,bq_fail,bq_done
.import bca_transfer,bca_guard,bca_page_step
.import read_record
.export se_bc_query_step,se_bc_query_ack,se_bc_query_cancel
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
 lda #1
 jsr bq_source
 jcs bq_fail
 lda BQ_STATE
 cmp #BQ_PAGE
 jeq @page
 cmp #BQ_PAGE_STEP
 jeq @page_step
 cmp #BQ_READ
 jeq read_record
 jmp bq_bad
@page:
 ; Keep a proof only inside this exclusive, source-bound job and exactpage.
 lda BQ_REF
 cmp BQ_CACHE
 bne @newpage
 EQ BQ_REF+2,BQ_CACHE+1,2
 lda BQ_CLASS
 cmp BQ_CACHE+3
 bne @newpage
@page_ready:
 lda #BQ_READ
 sta BQ_STATE
 jmp bq_pending
@newpage:
 lda BQ_REF
 sta BCA_PAGE
 lda BQ_CLASS
 sta BCA_KIND
 CP BQ_REF+2,BCA_GENERATION,2
.ifdef BCQ_PAGE_REUSE
 jsr bcq_restore_page
 bcc @page_ready
.endif
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
 ; OnlyafterpageCRC success can provisionalheader memo becomequeryauthority.
 CP BI_HEADER_NEXT,BQ_PAGE_NEXT,4
 lda BI_HEADER_SLOTS
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
.export payload_offset,times_width
.import advance

.ifdef BCQ_PAGE_REUSE
BCQ_PROOF_RESTORE=1
.include "cache/query/proof.inc"
.endif
