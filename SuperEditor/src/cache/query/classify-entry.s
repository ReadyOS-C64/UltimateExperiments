; PRIVATE optional compact seed-empty profile; flag absent preserves exact C35.
; Classify only: no INLINE stream is consumed or certified. Legacy C26 may
; execute later for actual inline presentation when the conservative hint is1.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "cache/query/api.inc"
.include "render/geos/semantic.inc"
.ifdef BCQ_FORWARD_SEED
.include "cache/query/proof-api.inc"
.endif
.ifndef BCQ_CLASSIFY
.error "classification entry requires BCQ_CLASSIFY"
.endif
.ifndef BCQ_SELECTOR_OWNS_OWNER
.error "classification selector must own the phase admission guard"
.endif
.ifndef BCQ_EDITOR_ACTIVE
.error "classification requires editor saved-reader/ACTIVE contract"
.endif
.import se_f_owner,se_overlay_frame,se_render_caps
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
 beq step
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
 bcs result
 cmp #1
 beq @admitted
 clc                        ;CMP mustnotturn optionalA2MISS into carryerror
 jmp result
@admitted:
 sta F+GSEM_ACTIVE
 sta $9136                   ;root already requested C35; subsequent op1
 clc
 rts
step:
 lda F+GSEM_ACTIVE
 beq argument
 lda BQ_READY
 beq @read
 jsr se_bc_query_ack         ;final real source GUARD then END, no INLINE reuse
 bcs result
 jmp publish
@read:
 jsr se_bc_query_step
result:
 php
 pha
 bcs @fault
.ifdef BCQ_EMPTY_INLINE_HINT
 cmp #1
.else
 pla
 pha
 cmp #1
.endif
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
.ifdef BCQ_EMPTY_INLINE_HINT
@fault:
 sta F+GSEM_ERROR
.else
@fault:
 pla
 pha
 sta F+GSEM_ERROR
.endif
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
.ifdef BCQ_EMPTY_INLINE_HINT
 lda #0                     ;same four zero fields, no source semantic change
 ldx #3
@zero:sta F+GSEM_KIND,x
 dex
 bpl @zero
.else
 lda #0                     ;terminal syntheticEOF is ordinary empty prose
 sta F+GSEM_KIND
 sta F+GSEM_LANG
 sta F+GSEM_LEVEL
 sta F+GSEM_MARKER
.endif
.ifdef BCQ_EMPTY_INLINE_HINT
 jmp @anchors
.else
 beq @anchors
.endif
@ordinary:
 sta F+GSEM_KIND
.ifdef BCQ_EMPTY_INLINE_HINT
 ldx #2
@fields:lda BQ_CR+69,x
 sta F+GSEM_LANG,x
 dex
 bpl @fields
.else
 lda BQ_CR+69
 sta F+GSEM_LANG
 lda BQ_CR+70
 sta F+GSEM_LEVEL
 lda BQ_CR+71
 sta F+GSEM_MARKER
.endif
@anchors:
 ldx #2
@start:lda BQ_CR+16,x
 sta F+GSEM_START,x
 dex
 bpl @start
.ifdef BCQ_EMPTY_INLINE_HINT
 ; BQ_END is the actualchecked absolute END, retained across GUARD/END.
 ldx #2
@end:lda BQ_END,x
 sta F+GSEM_END,x
 dex
 bpl @end
.else
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
.endif
.ifdef BCQ_EMPTY_INLINE_HINT
 ; INX/DEY preserve carry between the three original ADC operations.
 ldx #0
 ldy #3
 clc
@body:lda BQ_CR+16,x
 adc BQ_CR+22,x
 sta F+GSEM_BODY,x
 inx
 dey
 bne @body
.else
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
.endif
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
 ; Only an authenticated completed empty stream proves no inline work.
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
