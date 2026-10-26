; Classify only: no INLINE stream is consumed or certified. Legacy C26 may
; execute later for actual inline presentation when the conservative hint is1.
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
 inc F+GSEM_INLINE           ;hint only, no INLINE grammar reuse certificate
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
@done:lda #0
 sta F+GSEM_ERROR
 sta F+GSEM_ACTIVE
 clc
 rts
