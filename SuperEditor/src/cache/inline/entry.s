; PRIVATE component. Requires inactiveR21stage8880..89FF and a saved/dead
; C20 GLframe8D00..903F; the query itself overwrites its first576 bytes.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "cache/inline/api.inc"
.include "render/geos/semantic.inc"
.include "render/geos/inline.inc"
.import se_f_owner,se_overlay_frame,se_render_caps
F=GSEM_FRAME
S=$8880                    ;161 styles, private code-exclusive bit7
R=S+161                    ;161 roles
H=R+161                    ;21 hidden bits
P=H+21                     ;19 frozenGSEMinput bytes then11 scratch
REL=P+19                   ;relativeQUERY-CR_START24
INDEX=P+22
BUDGET=P+23
PHASE=P+24                 ;0query,1painting heldINLINE10
STYLE=P+25
.assert P+26<=$8A00,error,"inline staging exceeds backed GL lifetime"
.segment "CODE"
 OVL_BINDING
.export entry
entry:
 lda se_f_owner
 cmp #4
 jne busy
 lda se_overlay_frame
 beq begin
 cmp #1
 jeq step
 cmp #2
 jne bad
 jsr se_bc_query_cancel
 jmp result
busy:lda #$B2
 sec
 rts
bad:lda #$C0
 sec
 rts
begin:
 lda F+GSEM_ACTIVE
 jne busy
 lda se_bc_flags
 and #BC_ACTIVE             ;dedicated persistent resource claim
 jne busy
 lda F+GSEM_COUNT
 cmp #162
 jcs bad
 lda F+GSEM_ROLE
 cmp #14
 jcs bad
 ; Save the10 roles aliased bysharedIO beforeclearingquery state. Countless
 ; roles are restored afterEND; visible roles are initialized below.
 ldx #9
@oldroles:lda GI_OUTPUT_ROLES,x
 sta R,x
 dex
 bpl @oldroles
 lda #0
 ldx #0
@frame:sta BC_FRAME,x
 sta BC_FRAME+256,x
 dex
 bne @frame
 ldx #63
@tail:sta BC_FRAME+512,x
 dex
 bpl @tail
 sta PHASE
 ldx #20
@hidden:sta H,x
 dex
 bpl @hidden
 ldx #160
@style:sta S,x
 dex
 cpx #$FF
 bne @style
 ldx F+GSEM_COUNT
 beq @inputs_start
 dex
 lda F+GSEM_ROLE
@roles:sta R,x
 dex
 cpx #$FF
 bne @roles
@inputs_start:
 ldx #18
@inputs:lda F,x
 sta P,x
 dex
 bpl @inputs
 ldx #2
@query:lda F+GSEM_QUERY,x
 sta BQ_POSITION,x
 dex
 bpl @query
 lda #2
 sta F+GSEM_ERROR
 jsr se_bc_query_begin
 jcs result
 cmp #1
 beq @admitted
 clc
 jmp result
@admitted:sta F+GSEM_ACTIVE
 sta $9136
 clc
 rts
step:
 ldx #18
@frozen:lda P,x
 cmp F,x
 jne changed
 dex
 bpl @frozen
 jsr se_bc_query_step
 jcs result
 lda PHASE
 jne paint
 lda BQ_READY
 cmp #1
 jeq context
 cmp #2
 jne pending
 ; The actual query validator has authenticated this event. Temps10..18
 ; borrow the unused heldIO bytes; actualR14exchange resumes onlyafterACK.
 clc
 lda BC_IO+3
 adc BC_IO+2
 sta BC_IO+10
 lda BC_IO+4
 adc #0
 sta BC_IO+11
 lda BC_IO+5
 adc #0
 sta BC_IO+12
 clc
 lda BC_IO+6
 adc BC_IO+2
 sta BC_IO+13
 lda BC_IO+7
 adc #0
 sta BC_IO+14
 lda BC_IO+8
 adc #0
 sta BC_IO+15
 ldx #2
@pos:lda REL,x
 sta BC_IO+16,x
 dex
 bpl @pos
 lda #0
 sta INDEX
 lda BC_IO+1
 cmp #4
 bne @ordinary
 lda #$80
 bne @style
@ordinary:lsr
 and #1
 sta STYLE
 lda BC_IO+1
 and #1
 asl
 ora STYLE
@style:sta STYLE
 lda #1
 sta PHASE
paint:
 lda #32
 sta BUDGET
@cell:
 lda INDEX
 cmp P+GSEM_COUNT
 jeq acknowledge
 ldx #3
 jsr compare
 bcc @next
 ldx #10
 jsr compare
 bcc @hide
 lda BC_IO
 cmp #2
 beq @next
 ldx #6
 jsr compare
 bcc @ink
 ldx #13
 jsr compare
 bcs @next
@hide:
 lda INDEX
 and #7
 tay
 lda INDEX
 lsr
 lsr
 lsr
 tax
 lda bits,y
 ora H,x
 sta H,x
 jmp @next
@ink:
 ldx INDEX
 lda STYLE
 bmi @code
 lda S,x
 bmi @next
 ora STYLE
 sta S,x
 jmp @next
@code:sta S,x
 lda #4
 sta R,x
@next:
 inc INDEX
 inc BC_IO+16
 bne :+
 inc BC_IO+17
 bne :+
 inc BC_IO+18
:
 dec BUDGET
 jne @cell
pending:lda #1
 clc
 rts
compare:
 lda BC_IO+18
 cmp BC_IO+2,x
 bne :+
 lda BC_IO+17
 cmp BC_IO+1,x
 bne :+
 lda BC_IO+16
 cmp BC_IO,x
:rts
context:
 lda BQ_CR+3
 cmp #4
 jcs miss
 ldx #2
@start:lda BQ_CR+16,x
 cmp P+GSEM_START,x
 jne miss
 dex
 bpl @start
 ldx #2
@end:lda BQ_END,x
 cmp P+GSEM_END,x
 jne miss
 dex
 bpl @end
 clc
 lda BQ_CR+16
 adc BQ_CR+22
 sta BC_IO+16
 lda BQ_CR+17
 adc BQ_CR+23
 sta BC_IO+17
 lda BQ_CR+18
 adc BQ_CR+24
 sta BC_IO+18
 ldx #2
@body:lda BC_IO+16,x
 cmp P+GSEM_BODY,x
 jne miss
 dex
 bpl @body
 sec
 lda P+GSEM_QUERY
 sbc BQ_CR+16
 sta REL
 lda P+GSEM_QUERY+1
 sbc BQ_CR+17
 sta REL+1
 lda P+GSEM_QUERY+2
 sbc BQ_CR+18
 sta REL+2
 jcc miss
 ; Bound full visiblepacket against actual frozen merged source length.
 clc
 lda P+GSEM_QUERY
 adc P+GSEM_COUNT
 sta BC_IO+16
 lda P+GSEM_QUERY+1
 adc #0
 sta BC_IO+17
 lda P+GSEM_QUERY+2
 adc #0
 sta BC_IO+18
 jcs miss
 ldx #2
@length:lda BQ_LENGTH,x
 cmp BC_IO+16,x
 bne @different
 dex
 bpl @length
 jmp acknowledge
@different:jcc miss
acknowledge:
 lda #0
 sta PHASE
 jsr se_bc_query_ack
 bcs result
 cmp #0
 jne pending
 ; FinalGUARD+END completed. All output publication is now one bounded
 ; fixed161-cell operation without foregroundyield orsource/DOC scratch.
 ldx #0
@publish:
 cpx P+GSEM_COUNT
 beq @mask
 lda S,x
 and #3
 sta GI_OUTPUT_STYLES,x
 lda R,x
 cpx #160
 beq @last
 sta GI_OUTPUT_ROLES,x
 jmp @next
@last:sta GI_OUTPUT_ROLE_LAST
@next:inx
 bne @publish
@mask:ldx #9
@restore_roles:lda R,x
 sta GI_OUTPUT_ROLES,x
 dex
 bpl @restore_roles
 ldx #20
@bits:lda H,x
 sta GI_OUTPUT_HIDDEN,x
 dex
 bpl @bits
 lda #0
 sta F+GSEM_ERROR
 clc
result:
 php
 pha
 lda #0
 sta F+GSEM_ACTIVE
 pla
 plp
 rts
miss:
 jsr se_bc_query_cancel
 lda #2
 clc
 jmp result
changed:
 jsr se_bc_query_cancel
 lda #$C1
 sec
 jmp result
bits:.byte $80,$40,$20,$10,$08,$04,$02,$01
