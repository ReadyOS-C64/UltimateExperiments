; R27: retain a page without its caret, then restore it and XOR the new caret.
; Source/selection changes use the established full renderer. No same-slot calls.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/geos/editor.inc"
.include "render/geos/caret-cache.inc"
.include "render/geos/edit-certificate.inc"
.include "document/math24.inc"
.import se_mode,se_e_ui,se_e_draw_sequence,se_r_presentation,se_l_manual,se_l_pan
.import se_f_owner,se_hot_caret,se_sel_mark,se_sel_anchor
.import se_gc_handle,se_gc_epoch,se_reu_map,se_reu_c64,se_reu_offset
.import se_reu_logical,se_reu_length,se_reu_copy
.import se_gcc_status,se_gcc_cell,se_gcc_row
.import se_v_bottom,se_v_seen,se_v_caret_row,se_l_valid,se_l_need_wrap
.importzp screen_ptr
.export entry
.segment "CODE"
 OVL_BINDING
entry:
 lda se_overlay_frame
 cmp #4
 jeq chrome_row
 cmp #3
 beq root_try
 lda se_f_owner
 cmp #4
 jeq owned
 cmp #2
 jcs busy
 lda se_overlay_frame
 cmp #1
 jeq cell
 jmp busy
root_try:
 lda se_f_owner
 beq :+
 lda #2
 clc
 rts ;root caller may test while any foreign phase owns the workspace
:
 ; A missing cache can refuse without claiming or interpreting the phase.
 lda GCC_VALID
 cmp #1
 jne miss
 jsr allowed
 cmp #2
 jeq miss
 lda GCC_COUNT
 jeq miss
 cmp #23
 jcs miss
 lda #4
 sta se_f_owner
 jsr attempt
 bcs root_failed
 cmp #1
 bne root_result
root_step:
 ; Each pending STEP advances INDEX, with COUNT certified in1..22. Thus
 ; this foreground root call visits at most22 prefix units, no unbounded job.
 jsr step
 bcs root_failed
 cmp #1
 beq root_step
root_result:
 cmp #0
 bne root_miss
 ldx #2
@bottom:
 lda GP_HEADER+GPH_BOTTOM,x
 sta se_v_bottom,x
 dex
 bpl @bottom
 lda GP_HEADER+GPH_SEEN
 sta se_v_seen
 lda GP_HEADER+GPH_CARET_ROW
 sta se_v_caret_row
 lda #1
 sta se_l_valid
 lda #0
 sta se_l_need_wrap
 jsr se_gcc_status
 bcs root_failed
 lda #0
 clc
root_release:
 php
 pha
 lda #0
 sta se_f_owner
 pla
 plp
 rts
root_miss:
 lda #2
 clc
root_failed:
 pha
 lda #0
 sta GCC_VALID
 sta GCC_PHASE
 pla
 jmp root_release
chrome_row:
 jmp se_gcc_row
cell:
 jmp se_gcc_cell
owned:
 lda se_overlay_frame
 beq attempt
 cmp #1
 jeq step
 cmp #2
 jeq capture
 lda #$90
 sec
 rts
busy:
 lda #$B2
 sec
 rts
miss:
 lda #0
 sta GCC_VALID
 sta GCC_PHASE
 lda #2
 clc
 rts
allowed:
 lda se_mode
 cmp #3
 jne miss
 lda se_r_presentation
 ora se_e_ui
 jne miss
 lda se_l_pan
 ora se_l_pan+1
 ora se_l_pan+2
 jne miss ;clipped caret affinity remains the full renderer's responsibility
 lda se_sel_mark
 beq @yes
 CMP24 se_sel_anchor,se_hot_caret
 jne miss
@yes:
 lda #0
 clc
 rts
attempt:
 lda GCC_VALID
 cmp #1
 jne miss
 jsr allowed
 cmp #2
 jeq miss
 jsr se_gp_cache_guard
 jcs miss
 lda GP_HEADER+GPH_VALID
 cmp #1
 jne miss
 ldx #1
@sequence:
 lda se_e_draw_sequence,x
 cmp GCC_SEQUENCE,x
 jne miss
 lda se_gc_epoch,x
 cmp GCC_EPOCH,x
 jne miss
 dex
 bpl @sequence
 lda se_gc_handle
 cmp GCC_HANDLE
 jne miss
 tax
 lda se_reu_map,x
 cmp GCC_PHYSICAL
 jne miss
 ldx #36
@key:
 lda GP_HEADER+4,x
 cmp GCC_KEY,x
 jne miss
 dex
 bpl @key
 ldx #2
@fold:
 lda GP_HEADER+GPH_FOLD_VALID,x
 cmp GCC_FOLD,x
 jne miss
 dex
 bpl @fold
 lda GP_HEADER+GPH_COUNT
 cmp GCC_COUNT
 jne miss
 sta GCC_TEMP
 cmp #0 ;STA retains the equality flags from CMP GCC_COUNT
 jeq miss
 lda GP_HEADER+GPH_CARET_ROW
 sta GCC_OLD_ROW
 ldx #5
@previous:
 lda GCC_X,x
 sta GCC_PREVIOUS,x
 dex
 bpl @previous
 lda #0
 sta GCC_VALID ;an interrupted restore must take the full-render recovery path
 sta GCC_INDEX
 sta GCC_RECT
 COPY24 se_hot_caret,GCC_CARET
 COPY24 se_sel_anchor,GCC_ANCHOR
 lda se_sel_mark
 sta GCC_MARK
 lda #1
 sta GCC_PHASE
pending:
 lda #1
 clc
 rts
step:
 lda GCC_PHASE
 cmp #1
 jne miss
 jsr allowed
 cmp #2
 jeq miss
 CMP24 se_hot_caret,GCC_CARET
 jne miss
 CMP24 se_sel_anchor,GCC_ANCHOR
 jne miss
 lda se_sel_mark
 cmp GCC_MARK
 jne miss
 jsr se_gp_cache_guard
 jcs return
 lda GCC_INDEX
 cmp GCC_COUNT
 jcs miss
 jsr prefix
 jcs return
 CMP24 GCC_CARET,GP_RECORD+GPR_START
 bcc @next
 CMP24 GCC_CARET,GP_RECORD+GPR_END
 bcc @found
 bne @next
 lda GP_RECORD+GPR_REASON
 cmp #3 ;CR1/EOF2 own the virtual end cell; softwrap belongs to the next row
 bcc @found
@next:
 inc GCC_INDEX
 jmp pending
@found:
 jsr rectangle
 jcs return
 cmp #2
 jeq miss
 ; Restore only the old caret's tiles from the cached unselected page.
 ; Neighboring glyph ink in those tiles is restored by the same tiny DMA.
 jsr restore_previous
 jcs return
 jsr invert
 ; Clear the old prefix's caret witnesses, then publish the new row prefix.
 lda GCC_OLD_ROW
 cmp GCC_INDEX
 beq @new
 cmp GCC_COUNT
 bcs @new
 jsr se_gp_cache_slot
 lda #0
 sta GCC_SCRATCH+4
 sta GCC_SCRATCH+5
 sta GCC_SCRATCH+6
 lda #18
 jsr old_request
 lda #3
 sta GP_IO_LENGTH
 jsr se_gp_cache_write
 jcs return
 lda GCC_OLD_ROW
 jsr se_gp_cache_slot
 lda #26
 jsr old_request
 lda #1
 sta GP_IO_LENGTH
 jsr se_gp_cache_write
 jcs return
@new:
 lda #1
 sta GP_RECORD+GPR_MEMBER
 sta GP_HEADER+GPH_SEEN
 lda GCC_RECT
 sta GP_RECORD+GPR_CARET_VALID
 sta GP_HEADER+GPH_CARET_VISIBLE
 lda GCC_X
 sta GP_RECORD+GPR_CARET_X
 sta GP_HEADER+GPH_CARET_X
 lda GCC_X+1
 sta GP_RECORD+GPR_CARET_X+1
 sta GP_HEADER+GPH_CARET_X+1
 lda GCC_INDEX
 sta GP_HEADER+GPH_CARET_ROW
 jsr se_gp_cache_slot
 jsr prefix_request
 jsr se_gp_cache_write
 jcs return
 jsr header_write
 jcs return
 jmp publish
old_request:
 clc
 adc GP_IO_OFFSET
 sta GP_IO_OFFSET
 bcc :+
 inc GP_IO_OFFSET+1
:
 lda #<(GCC_SCRATCH+4)
 sta GP_IO_POINTER
 lda #>(GCC_SCRATCH+4)
 sta GP_IO_POINTER+1
 lda #0
 sta GP_IO_LENGTH+1
 rts
capture:
 lda #0
 sta GEC_VALID ;a new complete base supersedes every prior edit certificate
 sta GCC_VALID
 jsr allowed
 cmp #2
 jeq miss
 jsr se_gp_cache_guard
 jcs return
 lda GP_HEADER+GPH_VALID
 cmp #1
 jne miss
 lda GP_HEADER+GPH_COUNT
 jeq miss
 sta GCC_COUNT
 lda GP_HEADER+GPH_CARET_ROW
 cmp GCC_COUNT
 jcs miss
 sta GCC_INDEX
 COPY24 se_hot_caret,GCC_CARET
 jsr prefix
 jcs return
 jsr rectangle
 jcs return
 cmp #2
 jeq miss
 lda GP_HEADER+GPH_CARET_VISIBLE
 and GP_RECORD+GPR_CARET_VALID
 bne :+
 lda #0
 sta GCC_RECT ;the accepted full paint may intentionally omit this caret
:
 jsr invert ;temporarily remove caret; attributes do not depend on caret ink
 lda #0
 jsr bitmap
 bcs @undo
 lda #0
 jsr attributes
@undo:
 php
 pha
 jsr invert
 pla
 plp
 jcs return
 ldx #36
@key:
 lda GP_HEADER+4,x
 sta GCC_KEY,x
 dex
 bpl @key
 ldx #2
@fold:
 lda GP_HEADER+GPH_FOLD_VALID,x
 sta GCC_FOLD,x
 dex
 bpl @fold
 lda se_gc_handle
 sta GCC_HANDLE
 tax
 lda se_reu_map,x
 sta GCC_PHYSICAL
 ldx #1
@epoch:
 lda se_gc_epoch,x
 sta GCC_EPOCH,x
 dex
 bpl @epoch
publish:
 clc
 lda se_e_draw_sequence
 adc #1
 sta GCC_SEQUENCE
 lda se_e_draw_sequence+1
 adc #0
 sta GCC_SEQUENCE+1
 lda #1
 sta GCC_VALID
 lda #0
 sta GCC_PHASE
 clc
return:
 rts
prefix:
 lda GCC_INDEX
 jsr se_gp_cache_slot
 jsr prefix_request
 jmp se_gp_cache_read
prefix_request:
 lda #<GP_RECORD
 sta GP_IO_POINTER
 lda #>GP_RECORD
 sta GP_IO_POINTER+1
 lda #32
 sta GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 rts
header_write:
 lda #0
 sta GP_IO_OFFSET
 sta GP_IO_OFFSET+1
 lda #<GP_HEADER
 sta GP_IO_POINTER
 lda #>GP_HEADER
 sta GP_IO_POINTER+1
 lda #64
 sta GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 jmp se_gp_cache_write
rectangle:
 lda #0
 sta GCC_RECT
 sta GCC_X
 sta GCC_X+1
 lda GP_RECORD+GPR_TOP
 cmp #16
 jcc argument
 cmp #192
 jcs argument
 sta GCC_Y
 lda GP_RECORD+GPR_HEIGHT
 cmp #8
 beq :+
 cmp #9
 jne argument
:
 sta GCC_HEIGHT
 lda GP_RECORD+GPR_COUNT+1
 jne argument
 lda GP_RECORD+GPR_COUNT
 cmp #GP_MAX_GLYPHS+1
 jcs argument
 SUB24 GCC_CARET,GP_RECORD+GPR_FIRST,GCC_TEMP
 jcc hidden
 lda GCC_TEMP+2
 ora GCC_TEMP+1
 jne hidden
 lda GCC_TEMP
 cmp GP_RECORD+GPR_COUNT
 beq tail
 jcs hidden
 asl
 sta GCC_TEMP
 lda #0
 rol
 sta GCC_TEMP+1
 lda GCC_INDEX
 jsr se_gp_cache_slot
 clc
 lda GP_IO_OFFSET
 adc #<GPR_X
 sta GP_IO_OFFSET
 lda GP_IO_OFFSET+1
 adc #>GPR_X
 sta GP_IO_OFFSET+1
 clc
 lda GP_IO_OFFSET
 adc GCC_TEMP
 sta GP_IO_OFFSET
 lda GP_IO_OFFSET+1
 adc GCC_TEMP+1
 sta GP_IO_OFFSET+1
 lda #<GCC_SCRATCH
 sta GP_IO_POINTER
 lda #>GCC_SCRATCH
 sta GP_IO_POINTER+1
 lda #4
 sta GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 jsr se_gp_cache_read
 jcs return
 lda GCC_SCRATCH
 sta GCC_X
 lda GCC_SCRATCH+1
 sta GCC_X+1
 sec
 lda GCC_SCRATCH+2
 sbc GCC_X
 sta GCC_WIDTH
 lda GCC_SCRATCH+3
 sbc GCC_X+1
 jne argument
 jmp bounds
tail:
 lda GP_RECORD+GPR_TAIL_VALID
 jeq hidden
 lda #8
 ldx GP_RECORD+GPR_KIND
 bne @width
 lda #5
 bit GP_RECORD+GPR_FLAGS
 bpl @width
 lda #6
@width:
 sta GCC_WIDTH
 lda GP_RECORD+GPR_TAIL_X
 sta GCC_X
 lda GP_RECORD+GPR_TAIL_X+1
 sta GCC_X+1
 bpl bounds
 cmp #$FF
 jne argument
 clc
 lda GCC_X
 adc GCC_WIDTH
 sta GCC_WIDTH
 jcc hidden
 lda #0
 sta GCC_X
 sta GCC_X+1
bounds:
 lda GCC_WIDTH
 jeq hidden
 cmp #33
 jcs argument
 lda GCC_X+1
 cmp #1
 bcc @width
 jne hidden
 lda GCC_X
 cmp #64
 jcs hidden
@width:
 clc
 lda GCC_X
 adc GCC_WIDTH
 sta GCC_TEMP
 lda GCC_X+1
 adc #0
 cmp #1
 bcc @yes
 bne @clip
 lda GCC_TEMP
 cmp #65
 bcc @yes
@clip:
 lda #64
 sec
 sbc GCC_X
 sta GCC_WIDTH
@yes:
 lda #1
 sta GCC_RECT
 lda #0
 clc
 rts
hidden:
 lda se_l_manual
 jeq miss
 lda #0
 clc
 rts
argument:
 lda #$90
 sec
 rts
restore_previous:
 lda GCC_PREVIOUS+5
 jeq @done
 cmp #1
 jne argument
 lda GCC_PREVIOUS+2
 cmp #16
 jcc argument
 cmp #192
 jcs argument
 lda GCC_PREVIOUS+4
 cmp #8
 beq :+
 cmp #9
 jne argument
:
 lda GCC_PREVIOUS+1
 cmp #2
 jcs argument
 cmp #1
 bne :+
 lda GCC_PREVIOUS
 cmp #64
 jcs argument
:
 lda GCC_PREVIOUS+3
 jeq argument
 cmp #33
 jcs argument
 clc
 adc GCC_PREVIOUS
 sta GCC_TEMP
 lda GCC_PREVIOUS+1
 adc #0
 cmp #1
 bcc @validated
 jne argument
 lda GCC_TEMP
 cmp #65
 jcs argument
@validated:
 lda GCC_PREVIOUS+2
 lsr
 lsr
 lsr
 sta GCC_TILE_ROW
 lda GCC_PREVIOUS+2
 clc
 adc GCC_PREVIOUS+4
 sec
 sbc #1
 lsr
 lsr
 lsr
 cmp #24
 bcc :+
 lda #23
:
 sta GCC_TILE_LAST
 lda GCC_PREVIOUS
 sta GCC_TEMP
 lda GCC_PREVIOUS+1
 sta GCC_TEMP+1
 ldx #3
@first:
 lsr GCC_TEMP+1
 ror GCC_TEMP
 dex
 bne @first
 lda GCC_TEMP
 sta GCC_TILE_COLUMN
 clc
 lda GCC_PREVIOUS
 adc GCC_PREVIOUS+3
 sta GCC_TEMP
 lda GCC_PREVIOUS+1
 adc #0
 sta GCC_TEMP+1
 sec
 lda GCC_TEMP
 sbc #1
 sta GCC_TEMP
 lda GCC_TEMP+1
 sbc #0
 sta GCC_TEMP+1
 ldx #3
@last:
 lsr GCC_TEMP+1
 ror GCC_TEMP
 dex
 bne @last
 sec
 lda GCC_TEMP
 sbc GCC_TILE_COLUMN
 clc
 adc #1
 sta GCC_TILE_COUNT
@row:
 ldx GCC_TILE_ROW
 lda row_lo,x
 clc
 adc GCC_PREVIOUS ;low3 bits removed below before addition
 sta se_reu_c64
 lda row_hi,x
 adc GCC_PREVIOUS+1
 sta se_reu_c64+1
 lda GCC_PREVIOUS
 and #7
 sta GCC_TEMP
 sec
 lda se_reu_c64
 sbc GCC_TEMP
 sta se_reu_c64
 lda se_reu_c64+1
 sbc #0
 sta se_reu_c64+1
 lda se_reu_c64
 sta se_reu_offset
 lda se_reu_c64+1
 clc
 adc #>(GCC_BITMAP-$6000)
 sta se_reu_offset+1
 lda GCC_TILE_COUNT
 asl
 asl
 asl
 sta se_reu_length
 lda #0
 sta se_reu_length+1
 lda se_gc_handle
 sta se_reu_logical
 lda #1
 jsr se_reu_copy
 bcs @return
 ldx GCC_TILE_ROW
 lda attr_lo,x
 clc
 adc GCC_TILE_COLUMN
 sta se_reu_c64
 lda attr_hi,x
 adc #0
 sta se_reu_c64+1
 lda se_reu_c64
 clc
 adc #<(GCC_ATTRIBUTES-$4000)
 sta se_reu_offset
 lda se_reu_c64+1
 adc #>(GCC_ATTRIBUTES-$4000)
 sta se_reu_offset+1
 lda GCC_TILE_COUNT
 sta se_reu_length
 lda #1
 jsr se_reu_copy
 bcs @return
 inc GCC_TILE_ROW
 lda GCC_TILE_LAST
 cmp GCC_TILE_ROW
 jcs @row
@done:
 lda #0
 clc
@return:
 rts
bitmap:
 pha
 lda #<$6000
 sta se_reu_c64
 lda #>$6000
 sta se_reu_c64+1
 lda #<GCC_BITMAP
 sta se_reu_offset
 lda #>GCC_BITMAP
 sta se_reu_offset+1
 lda #<8000
 sta se_reu_length
 lda #>8000
 bne transfer
attributes:
 pha
 lda #<$4000
 sta se_reu_c64
 lda #>$4000
 sta se_reu_c64+1
 lda #<GCC_ATTRIBUTES
 sta se_reu_offset
 lda #>GCC_ATTRIBUTES
 sta se_reu_offset+1
 lda #<1000
 sta se_reu_length
 lda #>1000
transfer:
 sta se_reu_length+1
 lda se_gc_handle
 sta se_reu_logical
 pla
 jmp se_reu_copy
invert:
 lda GCC_RECT
 jeq @done
 lda #0
 sta GCC_LOOP
@row:
 clc
 lda GCC_Y
 adc GCC_LOOP
 cmp #192
 bcs @done
 sta GCC_ROW
 lsr
 lsr
 lsr
 tax
 lda row_lo,x
 sta screen_ptr
 lda row_hi,x
 sta screen_ptr+1
 lda GCC_X
 and #$F8
 clc
 adc screen_ptr
 sta screen_ptr
 lda GCC_X+1
 adc screen_ptr+1
 sta screen_ptr+1
 lda GCC_ROW
 and #7
 clc
 adc screen_ptr
 sta screen_ptr
 bcc :+
 inc screen_ptr+1
:
 lda GCC_X
 and #7
 tax
 lda masks,x
 sta GCC_MASK
 lda GCC_WIDTH
 sta GCC_LEFT
 ldy #0
@pixel:
 lda (screen_ptr),y
 eor GCC_MASK
 sta (screen_ptr),y
 lsr GCC_MASK
 bne @next
 lda #$80
 sta GCC_MASK
 clc
 lda screen_ptr
 adc #8
 sta screen_ptr
 bcc @next
 inc screen_ptr+1
@next:
 dec GCC_LEFT
 bne @pixel
 inc GCC_LOOP
 lda GCC_LOOP
 cmp GCC_HEIGHT
 bcc @row
@done:
 rts
.segment "RODATA"
masks: .byte $80,$40,$20,$10,8,4,2,1
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
