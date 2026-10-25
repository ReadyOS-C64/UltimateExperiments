; C27 formatted, read-only GEOS presentation. Canonical source is never changed.
; Every external worker is requested through the resident pump, never C->C.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/presentation.inc"
.include "render/geos/preview.inc"
.include "render/geos/preview-cache.inc"
.include "render/geos/semantic.inc"
.include "render/geos/semantic-lex.inc"
.include "render/geos/inline.inc"
.include "render/geos/catalog-glyph.inc"
.include "render/geos/settings.inc"
.include "render/geos/fold-query.inc"
.include "render/geos/caret-cache.inc"
.include "document/math24.inc"
.include "supermark/api.inc"
REQUEST=$9135
OP=$9136
F=PP_GLYPH
.segment "GEOS_PAGE"
 OVL_BINDING
.export entry
entry:
 lda se_overlay_frame
 beq begin
 lda se_f_owner
 cmp #4
 jne busy
 lda PP_PHASE
 cmp #8
 bcc :+
 jsr pc_step
 jcs failed
 cmp #1
 jeq pending
 cmp #2
 jeq complete
 jmp preview_uncached
:
 lda PP_PHASE
 cmp #6
 jeq fold_top_step
 cmp #7
 jeq fold_line_step
 cmp #1
 jeq classified
 cmp #2
 jeq read_window
 cmp #3
 jeq inlined
 cmp #4
 jeq lexed
 cmp #5
 jeq draw
 jmp argument
begin:
 lda se_f_owner
 jne busy
 lda #4
 sta se_f_owner
 lda #0
 sta GSEM_FRAME+GSEM_CP_VALID
 sta $912C
 sta $912D
 sta $CBD5 ;font window valid (GF21); stage/chrome may have overwritten it
 sta se_v_seen
 sta PP_LINE
 sta PP_INVERSE
 sta GFQ_ACTIVE
 sta GCC_VALID
 sta PP_X
 sta PP_X+1
 jsr se_view_init
 jcs failed
 lda #16
 sta PP_Y
 COPY24 se_v_top,PP_ANCHOR
 COPY24 se_v_top,PP_POSITION
 jsr pc_begin
 jcs failed
 cmp #1
 jeq pending
preview_uncached:
 ; All176 content scanlines; top/menu and row24 stay shared chrome-owned.
 lda #<$6280
 sta screen_ptr
 lda #>$6280
 sta screen_ptr+1
 lda #0
 ldy #0
 ldx #27
@page:
 sta (screen_ptr),y
 iny
 bne @page
 inc screen_ptr+1
 dex
 bne @page
 ldx #128
@tail:
 sta (screen_ptr),y
 iny
 dex
 bne @tail
 lda #<$4050
 sta screen_ptr
 lda #>$4050
 sta screen_ptr+1
 ldx #3
 lda #$16
 ldy #0
@attrs:
 sta (screen_ptr),y
 iny
 bne @attrs
 inc screen_ptr+1
 dex
 bne @attrs
 ldx #112
@attr_tail:
 sta (screen_ptr),y
 iny
 dex
 bne @attr_tail
 lda se_ef_valid
 cmp PP_FOLD_VALID
 bne @reset_history
 lda se_ef_generation
 cmp PP_FOLD_GENERATION
 bne @reset_history
 lda se_ef_generation+1
 cmp PP_FOLD_GENERATION+1
 beq @fold_bound
@reset_history:
 lda #0
 sta PP_HISTORY_COUNT
@fold_bound:
 lda se_ef_valid
 sta PP_FOLD_VALID
 ldx #1
@fold_generation:
 lda se_ef_generation,x
 sta PP_FOLD_GENERATION,x
 dex
 bpl @fold_generation
 lda se_ef_valid
 jeq classify
 COPY24 PP_POSITION,GFQ_QUERY
 lda #0
 sta GFQ_MODE
 jsr fold_call
 jcs failed
 cmp #0
 beq fold_top_done
 lda #6
 sta PP_PHASE
 jmp pending
fold_top_step:
 lda #1
 jsr fold_call
 jcs failed
 cmp #0
 jne pending
fold_top_done:
 COPY24 GFQ_RESULT,PP_POSITION
 COPY24 GFQ_RESULT,PP_ANCHOR
 COPY24 GFQ_RESULT,se_v_top
 lda PPC_ARMED
 beq :+
 COPY24 se_v_top,PPC_META+PPC_TOP
:
classify:
 COPY24 PP_POSITION,GSEM_FRAME+GSEM_QUERY
 lda #1
 sta PP_PHASE
 lda #24
 ldx #0
 jmp request
classified:
 lda GSEM_FRAME+GSEM_ACTIVE
 beq @ready
 lda #24
 ldx #1
 jmp request
@ready:
 lda #0
 sta PP_COLLAPSED
 lda se_ef_valid
 beq classified_ready
 COPY24 GSEM_FRAME+GSEM_END,GFQ_QUERY
 CMP24 GFQ_QUERY,se_v_length
 bcs classified_ready
 SM_INC24 GFQ_QUERY
 lda #1
 sta GFQ_MODE
 lda #0
 jsr fold_call
 jcs failed
 cmp #0
 beq fold_line_done
 lda #7
 sta PP_PHASE
 jmp pending
fold_line_step:
 lda #1
 jsr fold_call
 jcs failed
 cmp #0
 jne pending
fold_line_done:
 lda GFQ_HIDDEN
 sta PP_COLLAPSED
 COPY24 GFQ_RESULT,PP_FOLD_END
classified_ready:
 COPY24 PP_POSITION,PP_ANCHOR
 lda GSEM_FRAME+GSEM_KIND
 cmp #SM_CODE_OPEN
 bne :+
 lda PP_COLLAPSED
 jeq skip_line
 lda #SM_CODE_OPEN
:

 cmp #SM_CODE_CLOSE
 jeq skip_line
 cmp #SM_REGION_CLOSE
 jeq skip_line
 lda #SES_BODY
 ldx #0
 stx PP_CODE
 lda GSEM_FRAME+GSEM_KIND
 cmp #SM_CODE_LINE
 bne @fence
 inc PP_CODE
 bne @code_profile
@fence:
 cmp #SM_CODE_OPEN
 bne @heading
 ; Keep the code appearance, but only code-body lines admit the C25 lexer.
 ; C26 returns literal fixed-code roles for the fence label itself.
@code_profile:
 lda #SES_CODE
 bne @profile
@heading:
 cmp #SM_HEADING
 bne @body
 lda GSEM_FRAME+GSEM_LEVEL
 cmp #1
 bcc @body
 cmp #7
 bcs @body
 tax
 lda #SES_BODY
@level:
 clc
 adc #7
 dex
 bne @level
 jmp @profile
@body:
 lda #SES_BODY
@profile:
 sta PP_PROFILE_INDEX
 tax
 ldy #0
@copy:
 lda se_editor_settings,x
 sta PP_BASE_PROFILE,y
 sta PP_PROFILE,y
 inx
 iny
 cpy #7
 bcc @copy
 lda #0
 sta PP_HEIGHT
 lda GSEM_FRAME+GSEM_KIND
 cmp #SM_CODE_OPEN
 jeq window ;collapsedfence keeps its literal label
 cmp #SM_LIST
 jeq window ;native hyphen/number prefix retains list semantics
 CMP24 PP_POSITION,GSEM_FRAME+GSEM_BODY
 bcs window
 COPY24 GSEM_FRAME+GSEM_BODY,PP_POSITION
 jmp window
skip_line:
 COPY24 GSEM_FRAME+GSEM_END,PP_POSITION
 CMP24 PP_POSITION,se_v_length
 jcs complete
 SM_INC24 PP_POSITION
 jmp classify
window:
 COPY24 PP_POSITION,PP_WINDOW
 COPY24 PP_POSITION,se_v_pos
 SUB24 GSEM_FRAME+GSEM_END,PP_POSITION,PP_TEMP24
 lda PP_TEMP24+1
 ora PP_TEMP24+2
 bne @full
 lda PP_TEMP24
 cmp #161
 bcc @count
@full:
 lda #160
@count:
 sta PP_COUNT
 lda #0
 sta PP_READ
 sta PP_INDEX
 lda #2
 sta PP_PHASE
 jmp pending
read_window:
 ldx #0
@read:
 lda PP_READ
 cmp PP_COUNT
 beq @done
 txa
 pha
 jsr se_view_peek
 jcs failed_stack
 ldy PP_READ
 sta $8200,y
 jsr se_view_advance
 inc PP_READ
 pla
 tax
 inx
 cpx #32
 bcc @read
 jmp pending
@done:
 COPY24 PP_WINDOW,GSEM_FRAME+GSEM_QUERY
 lda PP_COUNT
 sta GSEM_FRAME+GSEM_COUNT
 lda PP_CODE
 beq @inline
 lda GSEM_FRAME+GSEM_LANG
 sta GSEM_FRAME+GSEM_LANGUAGE
 lda #4
 sta PP_PHASE
 lda #25
 ldx #0
 jmp request
@inline:
 lda #3
 sta PP_PHASE
 lda #26
 ldx #0
 jmp request
inlined:
 lda GI_ACTIVE
 beq ready_draw
 lda #26
 ldx #1
 jmp request
lexed:
 lda GLEX_ACTIVE
 beq @ready
 lda #25
 ldx #1
 jmp request
@ready:
 lda #0
 ldx #19
@mask:
 sta GI_OUTPUT_HIDDEN,x
 dex
 bpl @mask
 ldx PP_COUNT
 beq ready_draw
 dex
@styles:
 lda GLEX_ROLES,x
 sta $8400,x
 lda #0
 sta GI_OUTPUT_STYLES,x
 dex
 cpx #$FF
 bne @styles
 jsr se_doc_invalidate ;8400 code-role packet borrowed the cached metadata leaf
ready_draw:
 lda PP_HEIGHT
 bne @metrics_ready
 jsr deferred_metrics
 bcc @metrics_ready
 cpx #0
 jeq complete
 jmp failed
@metrics_ready:
 lda #5
 sta PP_PHASE
 jmp pending
draw:
 lda PP_INDEX
 cmp PP_COUNT
 jeq end_window
 ; Matched control markers vanish. Broken/unmatched pairs remain literal.
 lsr
 lsr
 lsr
 tay
 lda GI_OUTPUT_HIDDEN,y
 sta PP_TEMP
 lda PP_INDEX
 and #7
 tax
 lda masks,x
 and PP_TEMP
 jne consumed
 ldy PP_INDEX
 lda $8200,y
 sta PP_VALUE
 lda GI_OUTPUT_STYLES,y
 sta PP_STYLE
 lda PP_CODE
 bne @code_role
 lda GI_OUTPUT_ROLES,y
 jmp @role
@code_role:
 lda $8400,y
@role:
 sta PP_ROLE
 cmp #4
 beq @code_font
 ldx PP_PROFILE_INDEX
 bne @font
@code_font:
 ldx #SES_CODE
@font:
 jsr copy_profile
 lda PP_PROFILE+SES_STYLES
 ora PP_STYLE
 sta PP_STYLE
 jsr glyph
 jcs failed
 clc
 lda PP_X
 adc F+CG_ADVANCE
 sta PP_TEMP
 lda PP_X+1
 adc #0
 sta PP_TEMP+1
 cmp #1
 bcc @fits
 bne @wrap
 lda PP_TEMP
 cmp #65
 bcc @fits
@wrap:
 lda PP_Y
 clc
 adc PP_HEIGHT
 sta PP_Y
 jsr new_row
 jcs complete
@fits:
 jsr paint
 clc
 lda PP_X
 adc F+CG_ADVANCE
 sta PP_X
 bcc consumed
 inc PP_X+1
consumed:
 inc PP_INDEX
 SM_INC24 PP_POSITION
 jmp pending
end_window:
 CMP24 PP_POSITION,GSEM_FRAME+GSEM_END
 jcc window
 lda PP_COLLAPSED
 jne fold_summary
 CMP24 PP_POSITION,se_v_length
 jcs complete
 SM_INC24 PP_POSITION
 lda PP_Y
 clc
 adc PP_HEIGHT
 sta PP_Y
 jmp classify
; Initialize a color-cell-aligned text band. Each cell's first ink chooses its
; foreground; all glyphs in the band share the block profile's background.
new_row:
 COPY24 PP_POSITION,PP_ANCHOR
new_row_anchor:
 lda PP_Y
 clc
 adc PP_HEIGHT
 cmp #193
 bcs @full
 lda #0
 sta PP_X
 sta PP_X+1
 ldx #159
@flags:
 sta PP_TILE_FLAGS,x
 dex
 cpx #$FF
 bne @flags
 lda PP_LINE
 cmp #22
 bcs @full
 asl
 clc
 adc PP_LINE
 tax
 ldy #0
@anchor:
 lda PP_ANCHOR,y
 sta se_v_rows,x
 inx
 iny
 cpy #3
 bcc @anchor
 inc PP_LINE
 ; Every full band uses one background. This is the C64 two-color tile policy.
 lda PP_Y
 lsr
 lsr
 lsr
 tax
 lda attr_lo,x
 sta screen_ptr
 lda attr_hi,x
 sta screen_ptr+1
 lda PP_HEIGHT
 lsr
 lsr
 lsr
 tax
 lda PP_BASE_PROFILE+SES_FOREGROUND
 asl
 asl
 asl
 asl
 ora PP_BASE_PROFILE+SES_BACKGROUND
 ldy #0
@paper:
 sta (screen_ptr),y
 iny
 cpy #40
 bcc @paper
 clc
 pha
 lda screen_ptr
 adc #40
 sta screen_ptr
 bcc :+
 inc screen_ptr+1
:
 pla
 ldy #0
 dex
 bne @paper
 clc
 rts
@full:
 sec
 rts
deferred_metrics:
 lda #32
 sta PP_VALUE
 lda PP_BASE_PROFILE+SES_STYLES
 sta PP_STYLE
 jsr glyph
 jcs metrics_error
 lda F+CG_BASELINE
 sta PP_BASELINE
 lda F+CG_HEIGHT
 sec
 sbc PP_BASELINE
 sta PP_DESCENT
 lda GSEM_FRAME+GSEM_INLINE
 beq @height
 ; Inline code may use a taller, fixed-width face. Reserve its real height.
 ldx #SES_CODE
 jsr copy_profile
 lda PP_PROFILE+SES_STYLES
 sta PP_STYLE
 jsr glyph
 jcs metrics_error
 lda F+CG_BASELINE
 cmp PP_BASELINE
 bcc :+
 sta PP_BASELINE
:
 lda F+CG_HEIGHT
 sec
 sbc F+CG_BASELINE
 cmp PP_DESCENT
 bcc @height
 sta PP_DESCENT
@height:
 clc
 lda PP_BASELINE
 adc PP_DESCENT
 adc #7
 and #$F8
 sta PP_HEIGHT
 jsr new_row_anchor
 ldx #0
 rts
metrics_error:
 ldx #1
 rts
glyph:
 lda #0
 sta se_overlay_frame
 lda #23
 ldx #0
 jmp se_overlay_call
copy_profile:
 ldy #0
@copy:
 lda se_editor_settings,x
 sta PP_PROFILE,y
 inx
 iny
 cpy #7
 bcc @copy
 rts
; Plot <=24x27 clipped ink using actual VIC bitmap addressing.
.include "render/geos/preview-paint.inc"

complete:
 COPY24 PP_POSITION,PP_BOTTOM
 COPY24 PP_POSITION,se_v_bottom
 jsr pc_capture_begin
 jcs failed
 cmp #1
 jeq pending
 lda #1
 sta se_v_seen
 lda #0
 sta se_l_valid
 sta se_l_need_wrap
 sta se_f_owner
 lda se_e_ui
 bne :+
 lda #4
 sta se_e_ui
:
 lda #16
 ldx #4
 jmp request
pending:
 lda #27
 ldx #1
request:
 sta REQUEST
 stx OP
 lda #1
 clc
 rts
failed_stack:
 tax
 pla
 txa
failed:
 sec
 rts
busy:
 lda #$B2
 sec
 rts
argument:
 lda #$90
 sec
 rts
.segment "RODATA"
masks: .byte $80,$40,$20,$10,8,4,2,1
clip_masks: .byte $FF,$80,$C0,$E0,$F0,$F8,$FC,$FE
palette: .byte 1,3,7,10,14,1,1,7,13,5,15,7,3,1
row_lo:
.repeat 25,I
 .byte <($6000+I*320)
.endrepeat
row_hi:
.repeat 25,I
 .byte >($6000+I*320)
.endrepeat
attr_lo:
.repeat 25,I
 .byte <($4000+I*40)
.endrepeat
attr_hi:
.repeat 25,I
 .byte >($4000+I*40)
.endrepeat
; Temporary24bit arithmetic belongs to preview state, not C20 phase memory.
PP_TEMP24=PP_STATE+51

.segment "GEOS_PAGE"
fold_call:
 sta se_overlay_frame
 lda #24
 ldx #0
 jmp se_overlay_call
fold_summary:
 ldx PP_PROFILE_INDEX
 jsr copy_profile
 lda #7
 sta PP_PROFILE+SES_FOREGROUND
 lda #0
 sta PP_STYLE
 lda #2
 sta PP_ROLE
 lda #43
 sta PP_VALUE
 lda #1
 sta PP_INVERSE
 jsr glyph
 jcs failed
 clc
 lda PP_X
 adc F+CG_ADVANCE
 sta PP_TEMP
 lda PP_X+1
 adc #0
 cmp #1
 bcc @fits
 bne @wrap
 lda PP_TEMP
 cmp #65
 bcc @fits
@wrap:
 lda PP_Y
 clc
 adc PP_HEIGHT
 sta PP_Y
 jsr new_row
 bcc @fits
 lda #0
 sta PP_INVERSE
 jmp complete
@fits:
 jsr paint
 lda #0
 sta PP_INVERSE
 COPY24 PP_FOLD_END,PP_POSITION
 CMP24 PP_POSITION,se_v_length
 jcs complete
 lda PP_Y
 clc
 adc PP_HEIGHT
 sta PP_Y
 jmp classify

.include "render/geos/preview-cache.s"
