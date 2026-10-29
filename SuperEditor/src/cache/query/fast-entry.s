; Private retained forward classifier: exact managedCRproof, no rootOPEN.
; Any unavailable/inapplicable seed hands off to actual C35 before publication.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "cache/query/api.inc"
.include "render/geos/semantic.inc"
.ifndef BCQ_CLASSIFY
.error "classification entry requires BCQ_CLASSIFY"
.endif
.ifndef BCQ_SELECTOR_OWNS_OWNER
.error "classification selector must own the phase admission guard"
.endif
.ifndef BCQ_EDITOR_ACTIVE
.error "classification requires editor saved-reader/ACTIVE contract"
.endif
.include "cache/arena/api.inc"
.include "cache/query/proof-api.inc"
.import se_f_owner,se_overlay_frame,se_render_caps,se_crc_init,se_crc_byte,se_crc_value
.import bq_source,bq_end,bq_pending,bq_fail,bq_baseline_miss,bca_guard,bcq_restore_page
.ifdef BCQ_COMMITTED_IDENTITY
.import bq_authority
.endif
.export se_bc_query_begin,bq_forward_handoff
.ifndef BCQ_FORWARD_QUERY
.error "fast-entry requires BCQ_FORWARD_QUERY"
.endif
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
 jne bq_baseline_miss
 dey
 bpl :-
.endmacro
F=GSEM_FRAME
.segment "CODE"
 OVL_BINDING
.export entry
entry:
 lda se_f_owner
 cmp #4
 bne busy
 lda se_overlay_frame
 beq begin
 cmp #1
 jeq step
.ifdef BCQ_COMMITTED_IDENTITY
 cmp #3
 jeq committed_identity
.endif
 cmp #2
 bne argument
 jsr se_bc_query_cancel
 jmp result
busy:lda #$B2
 sec
 rts
argument:lda #$C0
 sec
 rts
begin:
 lda F+GSEM_ACTIVE
 bne busy
 lda se_bc_flags
 and #BC_ACTIVE
 bne busy
 lda #0
 ldx #0
@clear:
 sta BC_FRAME,x
 sta BC_FRAME+256,x
 dex
 bne @clear
 ldx #63
@tail:sta BC_FRAME+512,x
 dex
 bpl @tail
 sta F+GSEM_CP_VALID
 sta F+GSEM_READS
 sta F+GSEM_READS+1
 sta F+GSEM_READS+2
 lda #2
 sta F+GSEM_ERROR          ;onlyfinalpublishchanges2→0
 lda #1
 sta BQ_ABI
 lda se_render_caps
 sta BQ_CAPS
 ldx #2
@position:lda F+GSEM_QUERY,x
 sta BQ_POSITION,x
 dex
 bpl @position
 jsr se_bc_query_begin
 jcs result
 cmp #1
 beq @admitted
 clc                        ;CMP mustnotturn optionalA2MISS into carryerror
 jmp result
@admitted:
 ldx $9135
 cpx #35
 beq @handoff
 sta F+GSEM_ACTIVE
 sta $9136                   ;root already requested C37; subsequent op1
@handoff:clc
 rts
.ifdef BCQ_COMMITTED_IDENTITY
; Operation3 is entered only from C35's already-open SOURCE_BEGIN continuation.
; It preserves that exact real lease; it never starts a different source reader.
committed_identity:
 lda F+GSEM_ACTIVE
 cmp #1
 jne argument
 lda BQ_STATE
 cmp #BQ_PAGE
 jne argument
 lda BQ_LIVE
 cmp #1
 jne argument
 lda BQ_READY
 jne argument
 jsr bq_authority
 bcs @failed
 lda #1
 jsr bq_source
 bcs @failed
 ; Both snapshots must be committed-only. The first29 canonical bytes include
 ; full tokens/epochs/generation/length/rootcount/visible revision.
 lda BQ_SOURCE+30
 ora BQ_READER+27+30
 bne @miss
 ldy #28
@compare:
 lda BQ_SOURCE,y
 cmp BQ_READER+27,y
 bne @miss
 dey
 bpl @compare
 ; Future bounded guards remain exact59 against the current real lease, not a
 ; fabricated reader context. Capture will inherit these current59 bytes.
 CP BQ_READER+27,BQ_SOURCE,59
 lda #35
 sta $9135
 lda #1
 sta $9136
 jmp bq_pending
@miss:
 jsr bq_baseline_miss
 jmp result
@failed:
 jsr bq_fail
 jmp result
.endif

; Exact exclusive-job guard remains in commonquerySTEP/ACK. BEGIN uses the
; previouslyauthenticated85B proof and currenttypedgraph before the firstread.
se_bc_query_begin:
 lda se_render_caps
 cmp #1
 beq :+
 cmp #3
 jne bq_forward_handoff
:lda se_bc_flags
 and #BC_ARMED|BC_LOST|BC_MUTATING|BC_ACTIVE|BC_PAGE_PROOF
 cmp #BC_ARMED|BC_PAGE_PROOF
 jne bq_forward_handoff
 lda se_bc_count
 jne bq_forward_handoff
 ; QUERY must be >=the previouslyvalidated canonicalSTART, not arbitraryslot.
 ldx #2
@direction:lda BQ_POSITION,x
 cmp F+GSEM_START,x
 jcc bq_forward_handoff
 bne @forward
 dex
 bpl @direction
@forward:
 CP se_bc_arena,BQ_AUTH,13
 CP se_bc_arena,BCA_BOUND,5
 CP se_bc_incarnation,BCA_INC,4
 CP se_bc_ticket,BCA_TICKET,4
 jsr bca_guard
 jcs bq_fail
 CP BCQP_SOURCE,BQ_SOURCE,59
 CP BCQP_CACHE,BQ_CACHE,4
 lda BCQP_CACHE
 sta BQ_REF
 sta BCA_PAGE
 lda #1
 sta BQ_CLASS
 sta BCA_KIND
 sta BQ_SEED_PENDING
 lda #96
 sta BQ_WIDTH
 CP BCQP_CACHE+1,BQ_REF+2,2
 CP BCQP_CACHE+1,BCA_GENERATION,2
 ; Restore authenticatesCRC85, complete13/59tuple, exactpage/gen/kind.
 jsr bcq_restore_page
 jcs bq_forward_handoff
 lda BCA_PAGE
 jeq bq_forward_handoff
 lsr
 lsr
 lsr
 lsr
 cmp BCA_BANKS
 jcs bq_forward_handoff
 lda BCA_GENERATION
 and BCA_GENERATION+1
 cmp #$FF
 jeq bq_forward_handoff
 lda BCQP_SLOTS
 jeq bq_forward_handoff
 cmp #43
 jcs bq_forward_handoff
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
 jne bq_forward_handoff
 lda BQ_TEMP+1
 cmp BCA_USED+1
 jne bq_forward_handoff
 lda BQ_SLOTS
 sec
 sbc #1
 sta BQ_LAST+1
 lda BCQP_SLOT
 cmp BQ_SLOTS
 jcs bq_forward_handoff
 sta BQ_REF+1
 CP BQ_REF,BQ_LAST,1
 CP BQ_REF+2,BQ_LAST+2,2
 lda BQ_SLOTS
 sec
 sbc BQ_REF+1
 sta BQ_REMAIN
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
 ; Publicinput muststillbe inside actualmergedsource.
 ldx #2
@range:lda BQ_POSITION,x
 cmp BQ_LENGTH,x
 bcc @ready
 jne bq_baseline_miss
 dex
 bpl @range
@ready:
 lda #BQ_READ
 sta BQ_STATE
 jmp bq_pending
; Release only this ownedquery context. The root invokesC35nextslice, not a
; nested Ccall. KeepQUERY and semanticoutputs for its independent admission.
bq_forward_handoff:
 jsr bq_end
 lda #0
 sta F+GSEM_ACTIVE
 sta $9136
 lda #35
 sta $9135
 lda #1
 clc
 rts
step:
 lda F+GSEM_ACTIVE
 jeq argument
 lda BQ_READY
 beq @read
 jsr se_bc_query_ack         ;final real source GUARD then END, no INLINE reuse
 jcs result
 jmp publish
@read:
 jsr se_bc_query_step
result:
 php
 pha
 bcs @fault
 pla
 pha
 cmp #1
 beq @pending
@clear:
 lda #0
 sta F+GSEM_ACTIVE
 pla
 plp
 rts
@pending:
 pla
 plp
 rts
@fault:
 pla
 pha
 sta F+GSEM_ERROR
 jmp @clear
publish:
 lda BQ_CR+2
 and #$10
 sta F+GSEM_USED
 lda BQ_LEX_CERT
 beq :+
 lda #$81
 sta BQ_CACHE+3
:
 lda BQ_CR+3
 cmp #$FF
 bne @ordinary
 lda #0                     ;terminal syntheticEOF is ordinary empty prose
 sta F+GSEM_KIND
 sta F+GSEM_LANG
 sta F+GSEM_LEVEL
 sta F+GSEM_MARKER
 beq @anchors
@ordinary:
 sta F+GSEM_KIND
 lda BQ_CR+69
 sta F+GSEM_LANG
 lda BQ_CR+70
 sta F+GSEM_LEVEL
 lda BQ_CR+71
 sta F+GSEM_MARKER
@anchors:
 ldx #2
@start:lda BQ_CR+16,x
 sta F+GSEM_START,x
 dex
 bpl @start
 clc
 lda BQ_CR+16
 adc BQ_CR+19
 sta F+GSEM_END
 lda BQ_CR+17
 adc BQ_CR+20
 sta F+GSEM_END+1
 lda BQ_CR+18
 adc BQ_CR+21
 sta F+GSEM_END+2
 clc
 lda BQ_CR+16
 adc BQ_CR+22
 sta F+GSEM_BODY
 lda BQ_CR+17
 adc BQ_CR+23
 sta F+GSEM_BODY+1
 lda BQ_CR+18
 adc BQ_CR+24
 sta F+GSEM_BODY+2
 lda #0
 sta F+GSEM_ROLE
 sta F+GSEM_REVERSE
 sta F+GSEM_INLINE
 lda #9
 sta F+GSEM_HEIGHT
 lda F+GSEM_KIND
 cmp #4
 bcs @not_inline
.ifdef BCQ_EMPTY_INLINE_HINT
 ; Only a completed, canonical empty INLINE certificate proves no work.
 lda BQ_CR+2
 and #4
 beq @has_inline
 lda BQ_CR+44
 ora BQ_CR+45
 ora BQ_CR+46
 bne @has_inline
 lda BQ_CR+40
 and BQ_CR+41
 and BQ_CR+42
 and BQ_CR+43
 cmp #$FF
 beq @inline_done
@has_inline:
 inc F+GSEM_INLINE
@inline_done:
 lda F+GSEM_KIND
.else
 inc F+GSEM_INLINE           ;hint only, no INLINE grammar reuse certificate
.endif
@not_inline:
 cmp #5
 bne :+
 lda #8
 sta F+GSEM_HEIGHT
 lda #4
 bne @role
:
 cmp #2
 bne :+
 inc F+GSEM_REVERSE
 lda #2
 bne @role
:
 cmp #3
 bne :+
 lda #1
 bne @role
:
 cmp #4
 beq @code
 cmp #6
 bne @done
@code:lda #4
@role:sta F+GSEM_ROLE
@done:
.ifdef BCQ_FORWARD_SEED
 lda BQ_RECORD_REF+1
 sta BCQP_SLOT
.endif
 lda #0
 sta F+GSEM_ERROR
 sta F+GSEM_ACTIVE
 clc
 rts
