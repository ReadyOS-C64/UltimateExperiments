; Bounded local plain/styled transaction in the sealed C32 window.
.setcpu "6502"
.macpack longbranch
GP_CACHE_IMPLEMENTATION=1
.include "editor-api.inc"
.include "render/geos/typing/guard.inc"
.include "render/geos/style-typing/wide.inc"
.include "render/geos/typing/font-cache.inc"
.include "document/math24.inc"
.import se_gtt_admit,se_gtt_current
.import se_typing_validate,se_typing_patch,se_gcc_status
.import se_gp_cache_read,se_gp_cache_write,se_gp_cache_slot
.import se_f_owner,se_hot_caret,se_sel_anchor,se_e_draw_sequence
.import se_v_pos,se_view_peek,se_v_cache_count,se_v_length,se_v_rows
.import se_v_bottom,se_v_seen,se_v_caret_row,se_l_valid,se_l_need_wrap,se_r_revision
.import se_petscii_screen,se_crc_init,se_crc_byte,se_crc_value
.importzp text_ptr,screen_ptr
.import se_gst_prepare
.export se_gst_transaction
.exportzp gt_base,gt_bitmap
gt_base=text_ptr
gt_bitmap=screen_ptr
F=GT_FRAME
P=GTT_PACKET
H=GTT_HEADER
COPY=GTT_CONTROL+9
CACHE=GTT_CONTROL+10         ;2 ownedFEbitmapoffset
LINE=GTT_CONTROL+12
COUNT=GTT_CONTROL+13
CARETI=GTT_CONTROL+14
R=GTT_CONTROL+15
.segment "CODE"
se_gst_transaction:
 jsr begin
 bcs root_return
@next:
 cmp #1
 beq :+
 clc
 bcc root_return
: jsr step
 bcc @next
root_return:
 rts
failure:
 pha
 lda #0
 sta GCC_VALID
 sta GEC_VALID
 sta GTT_PHASE
 pla
 sec
 rts
miss:
 lda GTT_PHASE
 beq :+
 lda #0
 sta GCC_VALID
: lda #0
 sta GTT_PHASE
 lda #2
 clc
 rts
pending:
 lda #1
 clc
 rts
begin:
 lda #0
 sta GTT_PHASE
 jsr se_gtt_admit
 bcs failure
 cmp #1
 bne miss
 ; Authenticate the prefetched glyph against a sealed trustedfont witness.
 lda #<GTF_META
 sta GP_IO_OFFSET
 lda #>GTF_META
 sta GP_IO_OFFSET+1
 lda #<GTT_META
 ldx #>GTT_META
 ldy #32
 jsr read
 bcs failure
 ldx #31
@font:
 lda GTT_META,x
 cmp font_header,x
 bne miss
 dex
 bpl @font
 lda GEC_OP
 beq @insert
 lda GEC_OLD
 bne @screen
@insert:
 lda GEC_NEW
@screen:
 jsr se_petscii_screen
 sta GTT_ERROR
 jsr se_crc_init
 ldy #0
@font_crc:
 lda $8B4A,y
 jsr se_crc_byte
 iny
 cpy #9
 bcc @font_crc
 lda $8B43
 jsr se_crc_byte
 ldx GTT_ERROR
 lda se_crc_value
 cmp gtf_crc_low,x
 bne miss
 lda se_crc_value+1
 cmp gtf_crc_high,x
 jne miss
 ldx #63
@header:
 lda GP_HEADER,x
 sta H,x
 dex
 bpl @header
 jsr packet_request
 jsr se_gp_cache_read
 jcs failure
 lda P+GPR_COUNT
 sta COUNT
 lda GEC_OP
 sta F+GT_OP
 lda #0
 sta F+GT_FLAGS
 lda P+GPR_TOP
 sta F+GT_TOP
 lda GTT_X
 sta F+GT_X
 lda GTT_X+1
 sta F+GT_X+1
 lda GTT_WIDTH
 sta F+GT_OLD_WIDTH
 lda GTT_WIDTH+1
 sta F+GT_OLD_WIDTH+1
 lda #5
 sta F+GT_CARET_WIDTH
 lda P+GPR_BACKGROUND
 cmp #16
 jcs miss
 ora #$10
 sta F+GT_ATTRIBUTE
 jsr se_gst_prepare
 jcs miss
 jsr se_typing_validate
 jcs miss
 lda GEC_OP
 bne @delete
 ; Move characters backward; styles/roles are certifiedzero, newtailzeroed.
 ldx COUNT
@back:
 cpx GTT_INDEX
 beq @newchar
 lda P+GPR_CHARS-1,x
 sta P+GPR_CHARS,x
 lda P+GPR_STYLES-1,x
 sta P+GPR_STYLES,x
 dex
 bne @back
@newchar:
 lda GEC_NEW
 sta P+GPR_CHARS,x
 lda $8A4E
 sta P+GPR_STYLES,x
 ldx COUNT
 lda #0
 sta P+GPR_ROLES,x
 inc P+GPR_COUNT
 lda COUNT
 jsr xpointer
@xback:
 ldy #0
 clc
 lda (text_ptr),y
 adc F+GT_ADVANCE
 ldy #2
 sta (text_ptr),y
 ldy #1
 lda (text_ptr),y
 adc #0
 ldy #3
 sta (text_ptr),y
 lda COUNT
 cmp GTT_INDEX
 beq @maps_done
 sec
 lda text_ptr
 sbc #2
 sta text_ptr
 bcs :+
 dec text_ptr+1
: dec COUNT
 jmp @xback
@delete:
 lda F+GT_ADVANCE
 cmp GTT_ADVANCE
 jne miss
 dec P+GPR_COUNT
 ldx GTT_INDEX
@forward:
 cpx P+GPR_COUNT
 bcs @xdelete
 lda P+GPR_CHARS+1,x
 sta P+GPR_CHARS,x
 lda P+GPR_STYLES+1,x
 sta P+GPR_STYLES,x
 inx
 bne @forward
@xdelete:
 lda GTT_INDEX
 sta COUNT
 jsr xpointer
@xforward:
 ldy #2
 sec
 lda (text_ptr),y
 sbc F+GT_ADVANCE
 ldy #0
 sta (text_ptr),y
 ldy #3
 lda (text_ptr),y
 sbc #0
 ldy #1
 sta (text_ptr),y
 lda COUNT
 cmp P+GPR_COUNT
 beq @maps_done
 inc COUNT
 jsr plus2
 jmp @xforward
@maps_done:
 lda GTT_INDEX
 clc
 adc #1
 ldx GEC_OP
 beq :+
 sec
 sbc #1
: sta CARETI
 jsr xpointer
 ldy #0
 lda (text_ptr),y
 sta P+GPR_CARET_X
 iny
 lda (text_ptr),y
 sta P+GPR_CARET_X+1
 lda #1
 sta P+GPR_CARET_VALID
 lda CARETI
 cmp P+GPR_COUNT
 beq @tailcaret
 ldy #2
 sec
 lda (text_ptr),y
 ldy #0
 sbc (text_ptr),y
 sta F+GT_CARET_WIDTH
@tailcaret:
 lda P+GPR_COUNT
 jsr xpointer
 ldy #0
 lda (text_ptr),y
 sta P+GPR_TAIL_X
 iny
 lda (text_ptr),y
 sta P+GPR_TAIL_X+1
 lda #1
 sta P+GPR_TAIL_VALID
 ; Shift both canonicalendpoints byexactlyone byte.
 lda #<(P+GPR_END)
 sta text_ptr
 lda #>(P+GPR_END)
 sta text_ptr+1
 jsr shift
 jsr plus3
 jsr shift
 ; Full canonicalrow proof afterRAMpacketupdate; no sourcelease or mutation.
 COPY24 P+GPR_START,se_v_pos
 lda #0
 sta GTT_SCAN
@source:
 ldx GTT_SCAN
 cpx P+GPR_COUNT
 beq @end
 jsr se_view_peek
 jcs failure
 ldx GTT_SCAN
 cmp P+GPR_CHARS,x
 jne miss
 inc GTT_SCAN
 inc se_v_pos
 bne @source
 inc se_v_pos+1
 bne @source
 inc se_v_pos+2
 jmp @source
@end:
 CMP24 se_v_pos,P+GPR_END
 jne miss
 lda P+GPR_REASON
 cmp #1
 bne @eof
 jsr se_view_peek
 jcs failure
 cmp #13
 jne miss
 jmp @validated
@eof:
 CMP24 se_v_pos,se_v_length
 jne miss
@validated:
 jsr se_typing_validate
 jcs miss
 ; Invalidateall derivedpublications beforea partialpixel/cachetransaction.
 lda #0
 sta GCC_VALID
 sta H+GPH_VALID
 jsr header_write
 jcs failure
 lda #1
 sta GTT_PHASE
 jmp pending
step:
 jsr se_gtt_current
 jcs failure
 cmp #2
 jeq miss
 lda GTT_PHASE
 cmp #1
 bne commit
 ; Gather the two intersectingtilebands from the actualcaret-freeFEbase.
 lda F+GT_TOP
 lsr
 lsr
 lsr
 tax
 and #3
 .repeat 6
 asl
 .endrepeat
 sta CACHE
 txa
 lsr
 lsr
 clc
 adc #>GCC_BITMAP
 stx LINE
 adc LINE
 sta CACHE+1
 lda #0
 sta COPY
 jsr block
 jcs failure
 jsr scanlines
 jsr se_typing_patch
 jcs failure
 lda #1
 sta COPY
 jsr scanlines
 jsr block
 jcs failure
 lda #2
 sta GTT_PHASE
 jmp pending
commit:
 cmp #2
 jne miss
 ; Editedpacketandall later canonicalprefixes. No ABI2affinityarrays.
 jsr packet_request
 jsr se_gp_cache_write
 jcs failure
 lda GTT_ROW
 sta R
@row:
 lda R
 cmp H+GPH_COUNT
 bcs @page
 cmp GTT_ROW
 beq @anchor_edit
 jsr se_gp_cache_slot
 lda #<GP_RECORD
 ldx #>GP_RECORD
 ldy #32
 jsr read
 jcs failure
 lda #<GP_RECORD
 sta text_ptr
 lda #>GP_RECORD
 sta text_ptr+1
 lda #4
 sta COUNT
@prefix_delta:
 jsr shift
 jsr plus3
 dec COUNT
 bne @prefix_delta
 lda R
 jsr se_gp_cache_slot
 lda #<GP_RECORD
 ldx #>GP_RECORD
 ldy #32
 jsr request
 jsr se_gp_cache_write
 jcs failure
 jmp @anchor
@anchor_edit:
 ldx #2
@edited_start:
 lda P+GPR_START,x
 sta GP_RECORD+GPR_START,x
 dex
 bpl @edited_start
@anchor:
 lda R
 asl
 clc
 adc R
 tax
 ldy #0
@view:
 lda GP_RECORD+GPR_START,y
 sta se_v_rows,x
 inx
 iny
 cpy #3
 bcc @view
 inc R
 jmp @row
@page:
 lda #<(H+GPH_BOTTOM)
 sta text_ptr
 lda #>(H+GPH_BOTTOM)
 sta text_ptr+1
 jsr shift
 ldx #3
@revision:
 lda se_r_revision,x
 sta H+GPH_KEY+17,x
 dex
 bpl @revision
 ldx #2
@length:
 lda se_v_length,x
 sta H+GPH_KEY+21,x
 lda H+GPH_BOTTOM,x
 sta se_v_bottom,x
 lda se_hot_caret,x
 sta GCC_CARET,x
 lda se_sel_anchor,x
 sta GCC_ANCHOR,x
 dex
 bpl @length
 ldx #1
@caret_x:
 lda P+GPR_CARET_X,x
 sta H+GPH_CARET_X,x
 sta GCC_X,x
 dex
 bpl @caret_x
 lda P+GPR_TOP
 sta GCC_Y
 lda F+GT_CARET_WIDTH
 sta GCC_WIDTH
 lda #9
 sta GCC_HEIGHT
 lda #1
 sta H+GPH_SEEN
 sta H+GPH_CARET_VISIBLE
 sta GCC_RECT
 sta se_v_seen
 sta se_l_valid
 lda GTT_ROW
 sta H+GPH_CARET_ROW
 sta GCC_INDEX
 sta GCC_OLD_ROW
 sta se_v_caret_row
 lda #0
 sta se_l_need_wrap
 sta GCC_MARK
 sta GCC_PHASE
 jsr se_gcc_status
 jcs failure
 lda #1
 sta H+GPH_VALID
 jsr header_write
 jcs failure
 ldx #36
@key:
 lda H+GPH_KEY,x
 sta GCC_KEY,x
 dex
 bpl @key
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
 sta GEC_VALID
 sta GTT_PHASE
 clc
 rts
; Boundedhelpers. No allocation, source mutation or overlaycalls.
xpointer:
 asl
 sta text_ptr
 lda #0
 rol
 clc
 adc #>(P+GPR_X)
 sta text_ptr+1
 clc
 lda text_ptr
 adc #<(P+GPR_X)
 sta text_ptr
 bcc :+
 inc text_ptr+1
: rts
plus2:
 clc
 lda text_ptr
 adc #2
 bcc set_low
 inc text_ptr+1
set_low:
 sta text_ptr
 rts
plus3:
 clc
 lda text_ptr
 adc #3
 bcc set_low
 inc text_ptr+1
 bne set_low
shift:
 ldy #0
 ldx #3
 lda GEC_OP
 bne @minus
 sec
@inc:
 lda (text_ptr),y
 adc #0
 sta (text_ptr),y
 iny
 dex
 bne @inc
 rts
@minus:
 clc
@dec:
 lda (text_ptr),y
 sbc #0
 sta (text_ptr),y
 iny
 dex
 bne @dec
 rts
packet_request:
 lda GTT_ROW
 jsr se_gp_cache_slot
 lda #<P
 ldx #>P
 ldy #<GPR_USED
 jsr request
 lda #>GPR_USED
 sta GP_IO_LENGTH+1
 rts
header_write:
 lda #0
 sta GP_IO_OFFSET
 sta GP_IO_OFFSET+1
 lda #<H
 ldx #>H
 ldy #64
 jsr request
 jmp se_gp_cache_write
read:
 jsr request
 jmp se_gp_cache_read
request:
 sta GP_IO_POINTER
 stx GP_IO_POINTER+1
 sty GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 rts
block:
 lda #0
 sta se_v_cache_count
 sta se_v_cache_count+1
 sta GP_IO_POINTER
 lda #$80
 sta GP_IO_POINTER+1
 sta GP_IO_LENGTH
 lda #2
 sta GP_IO_LENGTH+1
 lda CACHE
 sta GP_IO_OFFSET
 lda CACHE+1
 sta GP_IO_OFFSET+1
 lda COPY
 beq :+
 jmp se_gp_cache_write
: jmp se_gp_cache_read
scanlines:
 lda #<GT_BASE
 sta text_ptr
 lda #>GT_BASE
 sta text_ptr+1
 lda #0
 sta LINE
@line:
 lda F+GT_TOP
 and #7
 clc
 adc LINE
 tax
 and #7
 sta screen_ptr
 lda #$80
 sta screen_ptr+1
 cpx #8
 bcc :+
 lda screen_ptr
 ora #$40
 sta screen_ptr
 inc screen_ptr+1
:
 lda COPY
 jne @scatter
 ldx #10
@gather_block:
 ldy #0
 lda (screen_ptr),y
 ldy #0
 sta (text_ptr),y
 ldy #8
 lda (screen_ptr),y
 ldy #1
 sta (text_ptr),y
 ldy #16
 lda (screen_ptr),y
 ldy #2
 sta (text_ptr),y
 ldy #24
 lda (screen_ptr),y
 ldy #3
 sta (text_ptr),y
 clc
 lda text_ptr
 adc #4
 sta text_ptr
 bcc :+
 inc text_ptr+1
: clc
 lda screen_ptr
 adc #32
 sta screen_ptr
 bcc :+
 inc screen_ptr+1
:
 dex
 bne @gather_block
 jmp @next_line
@scatter:
 ldx #10
@scatter_block:
 ldy #0
 lda (text_ptr),y
 ldy #0
 sta (screen_ptr),y
 ldy #1
 lda (text_ptr),y
 ldy #8
 sta (screen_ptr),y
 ldy #2
 lda (text_ptr),y
 ldy #16
 sta (screen_ptr),y
 ldy #3
 lda (text_ptr),y
 ldy #24
 sta (screen_ptr),y
 clc
 lda text_ptr
 adc #4
 sta text_ptr
 bcc :+
 inc text_ptr+1
: clc
 lda screen_ptr
 adc #32
 sta screen_ptr
 bcc :+
 inc screen_ptr+1
:
 dex
 bne @scatter_block
@next_line:
 inc LINE
 lda LINE
 cmp #9
 jcc @line
 rts
.segment "RODATA"
GTF_INCLUDE_GLYPH_CRC=1
.include "render/geos/typing/font-witness.inc"
font_header:
 .byte $A5,"GTF1",1
 OVL_BINDING
 .word GTF_EXPECTED_CRC
 .word 1280
 .res 6,0
