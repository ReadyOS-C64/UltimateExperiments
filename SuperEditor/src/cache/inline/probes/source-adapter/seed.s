; PRIVATE source-adapter profile: publicentryownsownercheck.
.setcpu "6502"
.macpack longbranch
.include "cache/inline/api.inc"
.include "cache/arena/api.inc"
.include "cache/query/proof-api.inc"
.include "render/geos/semantic.inc"
.import se_render_caps,bca_guard,bq_source,bq_pending,bq_fail,bq_end
.export se_bc_query_begin
F=GSEM_FRAME
.macro CP source,target,count
 ldy #count-1
:lda source,y
 sta target,y
 dey
 bpl :-
.endmacro
.macro EQ source,target,count
 ldy #count-1
:lda source,y
 cmp target,y
 jne inline_seed_miss
 dey
 bpl :-
.endmacro
.segment "CODE"
se_bc_query_begin:
 lda se_render_caps
 cmp #1
 beq :+
 cmp #3
 jne inline_seed_miss
:lda se_bc_flags
 and #BC_ARMED|BC_LOST|BC_MUTATING|BC_ACTIVE|BC_PAGE_PROOF
 cmp #BC_ARMED|BC_PAGE_PROOF
 jne inline_seed_miss
 lda se_bc_count
 jne inline_seed_miss
 CP se_bc_arena,BQ_AUTH,13
 CP se_bc_arena,BCA_BOUND,5
 CP se_bc_incarnation,BCA_INC,4
 CP se_bc_ticket,BCA_TICKET,4
 jsr bca_guard
 jcs bq_fail
 CP BCQP_SOURCE,BQ_SOURCE,59
 lda BCQP_CACHE
 sta BQ_REF
 sta BCA_PAGE
 lda #1
 sta BQ_CLASS
 sta BCA_KIND
 lda #96
 sta BQ_WIDTH
 CP BCQP_CACHE+1,BQ_REF+2,2
 CP BCQP_CACHE+1,BCA_GENERATION,2
 ; CRC85+actual13tuple authenticate copied page/source. The later realR14
 ; BEGIN compares all59 bytes; copied-to-itself comparisons are not authority.
 jsr bcq_restore_page
 jcs inline_seed_miss
 lda BCA_PAGE
 jeq inline_seed_miss
 lsr
 lsr
 lsr
 lsr
 cmp BCA_BANKS
 jcs inline_seed_miss
 lda BCA_GENERATION
 and BCA_GENERATION+1
 cmp #$FF
 jeq inline_seed_miss
 lda BCQP_SLOTS
 jeq inline_seed_miss
 cmp #43
 jcs inline_seed_miss
 sta BQ_SLOTS
 ; Exact certifiedused mustcover exactlytheseCR slots, never arbitraryextent.
 tay
 lda #0
 sta BQ_TEMP
 sta BQ_TEMP+1
@used:clc
 lda BQ_TEMP
 adc #96
 sta BQ_TEMP
 bcc :+
 inc BQ_TEMP+1
:dey
 bne @used
 lda BQ_TEMP
 cmp BCA_USED
 jne inline_seed_miss
 lda BQ_TEMP+1
 cmp BCA_USED+1
 jne inline_seed_miss
 lda BCQP_SLOT
 cmp BQ_SLOTS
 jcs inline_seed_miss
 sta BQ_REF+1
 lda #BQ_SOURCE_BEGIN
 sta BQ_STATE
 lda #0
 jsr bq_source
 jcs bq_fail
 lda #1
 sta BQ_LIVE
 lda se_bc_flags
 ora #BC_ACTIVE
 sta se_bc_flags
 EQ BQ_SOURCE,BQ_READER+27,59
 CP BQ_READER+10,BQ_LENGTH,3
 CP F+GSEM_START,BQ_EXPECT,3
@ready:
 lda #BQ_READ
 sta BQ_STATE
 jmp bq_pending
; Optional miss releases only this ownedsource context; parentmayrunrealC26.
inline_seed_miss:
 jsr bq_end
 lda #2
 clc
 rts

.import se_crc_init,se_crc_byte,se_crc_value
.export bcq_restore_page
bcq_restore_page:
 jsr se_crc_init
 ldy #82
@crc:lda BCQP,y
 jsr se_crc_byte
 dey
 bpl @crc
 lda se_crc_value
 cmp BCQP_CRC
 bne @miss
 lda se_crc_value+1
 cmp BCQP_CRC+1
 bne @miss
 lda BCQP_CACHE+3
 cmp #1
 bne @miss
 ldy #12
@auth:lda BQ_AUTH,y
 cmp BCQP_AUTH,y
 bne @miss
 dey
 bpl @auth
 ldy #3
@request:lda BCA_PAGE,y
 sta BCA_TEMP+4,y
 dey
 bpl @request
 ldy #1
@used:lda BCQP_USED,y
 sta BCA_USED,y
 dey
 bpl @used
 ldy #4
@links:lda BCQP_NEXT,y
 sta BQ_PAGE_NEXT,y
 dey
 bpl @links
 ldy #3
@cache:lda BCQP_CACHE,y
 sta BQ_CACHE,y
 dey
 bpl @cache
 lda #$A5
 sta BCA_PROOF
 clc
 rts
@miss:sec
 rts
