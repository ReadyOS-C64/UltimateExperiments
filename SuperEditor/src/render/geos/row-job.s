.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/geos/api.inc"
.include "render/geos/row.inc"
.include "render/geos/row-job.inc"
.import se_input_head,se_input_tail,se_input_nmi_pending
.import se_overlay_frame
.import se_f_owner,se_geos_glyph,se_geos_packed,se_geos_widths
.importzp se_gg_context,se_gg_pointer
.export se_logical_row_job,entry
entry=se_logical_row_job
F=GEOS_ROW_FRAME
G=F+GR_GLYPH
P=RJ+RJ_PRIVATE
idx=P
gy=P+1
ay=P+2
band=P+3
sy=P+4
tile=P+5
role=P+6
flags=P+7
xpos=P+8
pixel=P+10
inkhi=P+12
inklo=P+13
inktail=P+14
covhi=P+15
covlo=P+16
covtail=P+17
phase=P+18
fragment=P+19
base=P+20
weight=P+21
rank=P+22
best=P+23
work=P+24
band0=P+25
rowlo=P+26
rowhi=P+28
fast=P+30
gx=P+31
savevalid=P+32
row_budget=P+33
.segment "CODE"
 OVL_BINDING
se_logical_row_job:
 lda se_f_owner
 cmp #4
 jne busy
 lda se_overlay_frame
 beq @dispatch
 cmp #3
 jeq resume_job
 cmp #2
 jeq clear_job
 cmp #1
 jne argument_opaque
 lda #0
 clc
 rts
@dispatch:
 ldx se_overlay_frame+1
 ldy se_overlay_frame+2
 lda se_f_owner
 cmp #4
 jne busy
 cpx #<RJ
 jne argument_opaque
 cpy #>RJ
 jne argument_opaque
 lda RJ+RJ_VALID
 sta savevalid
 lda #0
 sta RJ+RJ_VALID
 lda RJ+RJ_COUNT
 cmp #162
 jcs argument
 lda RJ+RJ_TOP
 cmp #16
 jcc argument
 cmp #192
 jcs argument
 lsr
 lsr
 lsr
 sta band0
 lda RJ+RJ_MODE
 cmp #3
 jcs argument
 lda RJ+RJ_MODE
 beq @context_ok
 lda savevalid
 cmp #1
 jne argument
 lda RJ+RJ_LAST_BAND
 ldx RJ+RJ_MODE
 cpx #2
 bne :+
 clc
 adc #1
: cmp band0
 jne argument
@context_ok:
 jsr validate_inputs
 jcs return
@font:
 lda #<se_geos_packed
 sta G+GG_FONT
 lda #>se_geos_packed
 sta G+GG_FONT+1
 lda #<se_geos_widths
 sta G+GG_WIDTHS
 lda #>se_geos_widths
 sta G+GG_WIDTHS+1
 lda #0
 sta G+GG_NATIVE
 sta F+GR_TOP
 sta F+GR_PRIVATE+3 ;actual glyph decoder's striporigin0
 sta F+GR_PRIVATE+38
 sta G+GG_STYLE
 sta G+GG_FLAGS
 lda #$48
 sta G+GG_NATIVE+1
 lda #9
 sta F+GR_BOTTOM
 lda #32
 sta G+GG_VALUE
 jsr glyph
 jcs return
 jsr setup_addresses
 lda RJ+RJ_MODE
 cmp #2
 bne @clear
 ; Actual bounded560B rolling carry, included in job cost.
 ldx #0
@carry:
 lda RJ_H1,x
 sta RJ_H0,x
 lda RJ_H1+256,x
 sta RJ_H0+256,x
 inx
 bne @carry
 ldx #47
@carry_tail:
 lda RJ_H1+512,x
 sta RJ_H0+512,x
 dex
 bpl @carry_tail
@clear:
 lda #0
 sta band
@clear_band:
 lda RJ+RJ_MODE
 beq @reset_band
 cmp #1
 jeq @clear_next
 lda band
 jeq @clear_next
@reset_band:
 jsr clear_histogram
 lda band0
 clc
 adc band
 asl
 asl
 asl
 sta ay
 cmp RJ+RJ_CLIP_TOP
 bcc @partial_clear
 clc
 adc #8
 cmp RJ+RJ_CLIP_BOTTOM
 beq @full_clear
 bcs @partial_clear
@full_clear:
 ldx band
 lda rowlo,x
 sta se_gg_pointer
 lda rowhi,x
 sta se_gg_pointer+1
 lda #0
 tay
@clear_page:
 sta (se_gg_pointer),y
 iny
 bne @clear_page
 inc se_gg_pointer+1
 ldy #63
@clear_tail:
 sta (se_gg_pointer),y
 dey
 bpl @clear_tail
 jmp @clear_next
@partial_clear:
 jsr y_begin
@clear_y:
 lda ay
 cmp RJ+RJ_CLIP_BOTTOM
 bcs @clear_next
 ldx band
 lda ay
 lsr
 lsr
 lsr
 sec
 sbc band0
 cmp band
 bne @clear_next
 lda ay
 and #7
 sta sy
 lda #0
 sta tile
 sta pixel
 sta pixel+1
@clear_tile:
 jsr pixel_address
 lda #0
 ldy #0
 sta (se_gg_pointer),y
 clc
 lda pixel
 adc #8
 sta pixel
 bcc :+
 inc pixel+1
: inc tile
 lda tile
 cmp #40
 bcc @clear_tile
 inc ay
 jmp @clear_y
@clear_next:
 inc band
 lda band
 cmp #2
 jcc @clear_band
 lda #0
 sta idx
 sta RJ+RJ_DONE
 lda RJ+RJ_X
 sta xpos
 lda RJ+RJ_X+1
 sta xpos+1
 jsr map
 lda RJ+RJ_COUNT
 jeq resolve
 jmp pause_job
raster_continue:
 ldx idx
 cpx RJ+RJ_COUNT
 jcs resolve
 lda row_budget
 jeq pause_job
 dec row_budget
 lda xpos
 sta pixel
 lda xpos+1
 sta pixel+1
 jsr clipped_right
 jcs resolve
 ldx idx
 lda RJ_CHARS,x
 sta G+GG_VALUE
 lda RJ_STYLES,x
 sta G+GG_STYLE
 lda RJ_ROLES,x
 sta role
 lda RJ_FLAGS,x
 sta flags
 and #1
 sta G+GG_FLAGS
 jsr glyph
 jcs return
 lda #0
 sta fast
 sta covtail
 lda G+GG_CELL_HI
 sta covhi
 lda G+GG_CELL_LO
 sta covlo
 lda xpos
 and #7
 sta phase
 tax
 beq @coverage_done
@coverage:
 lsr covhi
 ror covlo
 ror covtail
 dex
 bne @coverage
@coverage_done:
 lda xpos+1
 beq @fast
 cmp #1
 bne @slow
 lda xpos
 clc
 adc G+GG_ADVANCE
 bcs @slow
 cmp #65
 bcs @slow
@fast:
 inc fast
@slow:
 lda RJ+RJ_TOP
 sta ay
 and #7
 sta sy
 lda #0
 sta band
 sta gy
@glyph_y:
 lda ay
 cmp RJ+RJ_CLIP_TOP
 jcc @next_y
 cmp RJ+RJ_CLIP_BOTTOM
 jcs @next_y
 lda gy
 asl
 tay
 lda G+GG_INK,y
 sta inkhi
 lda G+GG_INK+1,y
 sta inklo
 lda #0
 sta inktail
 lda xpos
 sta pixel
 lda xpos+1
 sta pixel+1
 lda inkhi
 ora inklo
 ora flags
 jeq @next_y
 lda fast
 beq @slow_row
 jsr pixel_address
 jsr histogram_address
 jsr byte_row
 jmp @next_y
@slow_row:
 lda #0
 sta gx
@pixel:
 asl inklo
 rol inkhi
 lda #0
 rol
 sta base
 jsr clipped_left
 bcc @next_pixel
 jsr clipped_right
 bcs @next_pixel
 jsr pixel_address
 jsr histogram_address
 lda base
 beq @selection
 ldy #0
 lda (se_gg_context),y
 cmp #255
 beq @selection
 clc
 adc #1
 sta (se_gg_context),y
@selection:
 lda flags
 and #6
 beq @normal
 lda base
 eor #1
 bne @paint_pixel
 beq @next_pixel
@normal:
 lda base
 beq @next_pixel
@paint_pixel:
 lda pixel
 and #7
 tax
 lda rj_bits,x
 ldy #0
 ora (se_gg_pointer),y
 sta (se_gg_pointer),y
@next_pixel:
 inc pixel
 bne :+
 inc pixel+1
: inc gx
 lda gx
 cmp G+GG_ADVANCE
 jcc @pixel
@next_y:
 inc ay
 inc sy
 lda sy
 cmp #8
 bcc :+
 lda #0
 sta sy
 inc band
: inc gy
 lda gy
 cmp #9
 jcc @glyph_y
 clc
 lda xpos
 adc G+GG_ADVANCE
 sta xpos
 bcc :+
 inc xpos+1
: inc idx
 jsr map
 jmp raster_continue
glyph:
 ldx #<G
 ldy #>G
 jmp se_geos_glyph
map:
 lda idx
 asl
 tay
 bcs @high
 lda xpos
 sta RJ_MAP,y
 lda xpos+1
 sta RJ_MAP+1,y
 rts
@high:
 lda xpos
 sta RJ_MAP+256,y
 lda xpos+1
 sta RJ_MAP+257,y
 rts
; bank-specific cleared560B, with no caller/source overlap.
clear_histogram:
 lda #<RJ_H0
 sta se_gg_pointer
 lda #>RJ_H0
 sta se_gg_pointer+1
 lda band
 beq :+
 lda #<RJ_H1
 sta se_gg_pointer
 lda #>RJ_H1
 sta se_gg_pointer+1
: ldy #0
 lda #0
 ldx #2
@page:
 sta (se_gg_pointer),y
 iny
 bne @page
 inc se_gg_pointer+1
 dex
 bne @page
 ldy #47
@tail:
 sta (se_gg_pointer),y
 dey
 bpl @tail
 rts
y_begin:
 lda band0
 clc
 adc band
 asl
 asl
 asl
 cmp RJ+RJ_CLIP_TOP
 bcs :+
 lda RJ+RJ_CLIP_TOP
: sta ay
 rts
clipped_left:
 lda pixel+1
 cmp #$ff
 beq @negative
 sec
 rts
@negative:
 clc
 rts
clipped_right:
 lda pixel+1
 cmp #$ff
 beq @negative
 cmp #>320
 bcc @inside
 bne @outside
 lda pixel
 cmp #<320
 rts
@inside:
 clc
 rts
@outside:
 sec
 rts
@negative:
 clc
 rts
pixel_address:
 ldx band
 lda pixel
 and #$f8
 clc
 adc rowlo,x
 sta se_gg_pointer
 lda pixel+1
 adc rowhi,x
 sta se_gg_pointer+1
 clc
 lda se_gg_pointer
 adc sy
 sta se_gg_pointer
 bcc :+
 inc se_gg_pointer+1
: lda pixel+1
 lsr
 lda pixel
 ror
 lsr
 lsr
 sta tile
 lda pixel
 and #7
 tax
 rts
histogram_address:
 ldy tile
 lda rj_histlo,y
 clc
 adc role
 sta se_gg_context
 lda rj_histhi,y
 adc #0
 sta se_gg_context+1
 lda band
 beq :+
 clc
 lda se_gg_context
 adc #<(RJ_H1-RJ_H0)
 sta se_gg_context
 lda se_gg_context+1
 adc #>(RJ_H1-RJ_H0)
 sta se_gg_context+1
: rts
byte_row:
 ldx phase
 beq @aligned
@shift:
 lsr inkhi
 ror inklo
 ror inktail
 dex
 bne @shift
@aligned:
 lda #0
 sta fragment
@fragment:
 ldy fragment
 lda covhi,y
 beq @done
 lda inkhi,y
 tax
 and #15
 tay
 lda rj_pop,y
 sta work
 txa
 lsr
 lsr
 lsr
 lsr
 tax
 lda rj_pop,x
 clc
 adc work
 ldy #0
 adc (se_gg_context),y
 bcc :+
 lda #255
: sta (se_gg_context),y
 ldy fragment
 lda flags
 and #6
 beq @plain
 lda inkhi,y
 eor covhi,y
 jmp @paint
@plain:
 lda inkhi,y
@paint:
 ldy #0
 ora (se_gg_pointer),y
 sta (se_gg_pointer),y
 inc fragment
 lda fragment
 cmp #3
 beq @done
 clc
 lda se_gg_pointer
 adc #8
 sta se_gg_pointer
 bcc :+
 inc se_gg_pointer+1
: clc
 lda se_gg_context
 adc #14
 sta se_gg_context
 bcc :+
 inc se_gg_context+1
: jmp @fragment
@done:
 rts
resolve:
 lda #$80
 sta RJ+RJ_DONE
 lda #0
 sta band
 sta tile
 jmp pause_job
resolve_continue:
 lda #40
 sta row_budget
@band:
 jsr y_begin
 lda ay
 cmp RJ+RJ_CLIP_BOTTOM
 jcs @next_band
 lsr
 lsr
 lsr
 sec
 sbc band0
 cmp band
 jne @next_band
 ; Resolver starts on any valid retained tile.  Establish both band bases once;
 ; the 40-tile budget cannot yield inside a band.
 lda #0
 sta role
 ldx band
 lda rowlo,x
 sta se_gg_pointer
 lda rowhi,x
 and #$1f
 sta se_gg_pointer+1
 ldx #3
@band_address:
 lsr se_gg_pointer+1
 ror se_gg_pointer
 dex
 bne @band_address
 lda se_gg_pointer+1
 ora #$40
 sta se_gg_pointer+1
@tile:
 lda row_budget
 jeq pause_job
 dec row_budget
 lda #0
 sta weight
 sta rank
 sta best
 jsr histogram_address
 ldy #0
@role:
 lda (se_gg_context),y
 beq @skip
 cmp weight
 bcc @skip
 bne @choose
 lda rj_priorities,y
 cmp rank
 bcc @skip
 beq @skip
@choose:
 lda (se_gg_context),y
 sta weight
 lda rj_priorities,y
 sta rank
 sty best
@skip:
 iny
 cpy #14
 bcc @role
 ldy best
 lda RJ_PALETTE,y
 asl
 asl
 asl
 asl
 ora RJ+RJ_BACKGROUND
 sta work
 ; The VIC attribute base is invariant across this physical band.
 ldy tile
 lda work
 sta (se_gg_pointer),y
@next:
 inc tile
 lda tile
 cmp #40
 jcc @tile
@next_band:
 lda #0
 sta tile
 inc band
 lda band
 cmp #2
 jcc @band
 lda idx
 sta RJ+RJ_DONE
 lda xpos
 sta RJ+RJ_NEXT_X
 lda xpos+1
 sta RJ+RJ_NEXT_X+1
 lda band0
 sta RJ+RJ_LAST_BAND
 lda #1
 sta RJ+RJ_VALID
 lda #0
 clc
return:
 rts
argument:
 lda #$90
 sec
 rts
argument_opaque:
 lda #$90
 sec
 rts
busy:
 lda #$b2
 sec
 rts

; Poll every4 glyphs/40 tiles; with no queued input the same call continues.
; No glyph, vote, map or band is
; reordered/restarted. C22 rechecks actual source/cache/selection beforeSTEP.
.segment "ROW_JOB_POLL"
pause_job:
 lda se_input_nmi_pending
 bne @yield
 lda se_input_head
 cmp se_input_tail
 bne @yield
 lda RJ+RJ_DONE
 bmi @resolve
 lda #4
 sta row_budget
 jmp raster_continue
@resolve:
 jmp resolve_continue
@yield:
 lda #2
 sta RJ+RJ_VALID
 lda #1
 clc
 rts
.segment "CODE"
.segment "ROW_JOB_HELPERS"
resume_job:
 lda se_overlay_frame+1
 cmp #<RJ
 jne argument_opaque
 lda se_overlay_frame+2
 cmp #>RJ
 jne argument_opaque
 lda RJ+RJ_VALID
 cmp #2
 jne argument
 lda #0
 sta RJ+RJ_VALID
 lda RJ+RJ_COUNT
 cmp #162
 jcs argument
 lda idx
 cmp RJ+RJ_COUNT
 bcc :+
 jne argument
:
 lda RJ+RJ_TOP
 cmp #16
 jcc argument
 cmp #192
 jcs argument
 lsr
 lsr
 lsr
 cmp band0
 jne argument
 lda RJ+RJ_BACKGROUND
 cmp #16
 jcs argument
 jsr setup_addresses
 lda RJ+RJ_DONE
 cmp #$80
 beq @resolver
 cmp #0
 jne argument
 lda idx
 cmp RJ+RJ_COUNT
 jcs argument
 lda #4
 sta row_budget
 jmp raster_continue
@resolver:
 lda band
 cmp #2
 jcs argument
 lda tile
 cmp #40
 jcs argument
 jmp resolve_continue
.segment "CODE"
; Empty/native strip clear consumes no glyph/font metadata. Sealed module
; admission, owner4, exact frame and complete destination checks still apply.
clear_job:
 lda se_overlay_frame+1
 cmp #<RJ
 jne argument_opaque
 lda se_overlay_frame+2
 cmp #>RJ
 jne argument_opaque
 lda RJ+RJ_TOP
 cmp #16
 jcc argument
 cmp #192
 jcs argument
 and #7
 jne argument
 lda RJ+RJ_BACKGROUND
 cmp #16
 jcs argument
 lda RJ_PALETTE
 cmp #16
 jcs argument
 asl
 asl
 asl
 asl
 ora RJ+RJ_BACKGROUND
 sta work
 lda RJ+RJ_TOP
 lsr
 lsr
 lsr
 sta band0
 and #3
 .repeat 6
 asl
 .endrepeat
 sta rowlo
 sta se_gg_pointer
 lda band0
 lsr
 lsr
 clc
 adc band0
 adc #$60
 sta rowhi
 sta se_gg_pointer+1
 lda #0
 sta RJ+RJ_VALID
 tay
@page:
 sta (se_gg_pointer),y
 iny
 bne @page
 inc se_gg_pointer+1
 ldy #63
@tail:
 sta (se_gg_pointer),y
 dey
 bpl @tail
 lda rowlo
 sta se_gg_pointer
 lda rowhi
 and #$1f
 sta se_gg_pointer+1
 .repeat 3
 lsr se_gg_pointer+1
 ror se_gg_pointer
 .endrepeat
 lda se_gg_pointer+1
 ora #$40
 sta se_gg_pointer+1
 ldy #39
 lda work
@attributes:
 sta (se_gg_pointer),y
 dey
 bpl @attributes
 lda #0
 clc
 rts
setup_addresses:
 lda band0
 and #3
 .repeat 6
 asl
 .endrepeat
 sta rowlo
 lda band0
 lsr
 lsr
 clc
 adc band0
 adc #$60
 sta rowhi
 clc
 lda rowlo
 adc #$40
 sta rowlo+1
 lda rowhi
 adc #1
 sta rowhi+1
 rts
validate_inputs:
 lda RJ+RJ_BACKGROUND
 cmp #16
 jcs argument
 lda RJ+RJ_LEFT
 ora RJ+RJ_LEFT+1
 jne argument
 lda RJ+RJ_RIGHT
 cmp #<320
 jne argument
 lda RJ+RJ_RIGHT+1
 cmp #>320
 jne argument
 lda RJ+RJ_CLIP_TOP
 cmp #16
 jcc argument
 cmp #193
 jcs argument
 lda RJ+RJ_CLIP_BOTTOM
 cmp #193
 jcs argument
 cmp RJ+RJ_CLIP_TOP
 jcc argument
 ldx #13
@palette:
 lda RJ_PALETTE,x
 cmp #16
 jcs argument
 dex
 bpl @palette
 ldx #0
@input:
 cpx RJ+RJ_COUNT
 beq @valid_inputs
 lda RJ_STYLES,x
 cmp #4
 jcs argument
 lda RJ_ROLES,x
 cmp #14
 jcs argument
 lda RJ_FLAGS,x
 cmp #8
 jcs argument
 inx
 bne @input
@valid_inputs:
 clc
 rts
.segment "RJ_TABLES"
rj_priorities:.byte 0,6,7,8,0,0,0,5,3,4,1,5,2,0
rj_pop:.byte 0,1,1,2,1,2,2,3,1,2,2,3,2,3,3,4
rj_bits:.byte $80,$40,$20,$10,8,4,2,1
rj_histlo:
.repeat 40,I
.byte <(RJ_H0+I*14)
.endrepeat
rj_histhi:
.repeat 40,I
.byte >(RJ_H0+I*14)
.endrepeat
