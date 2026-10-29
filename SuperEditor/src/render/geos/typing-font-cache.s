; C30 checked normal BSW/native glyph cache; no source mutation.
.setcpu "6502"
.macpack longbranch
GP_CACHE_IMPLEMENTATION=1
.include "editor-api.inc"
.include "render/geos/editor.inc"
.include "render/geos/api.inc"
.include "render/geos/typing-font-cache.inc"
.include "render/geos/typing-font-witness.inc"
.import se_f_owner,se_mode,se_r_presentation
.import se_gp_cache_guard,se_gp_cache_read,se_gp_cache_write
.import se_geos_packed,se_geos_widths
.import se_crc_init,se_crc_byte,se_crc_value
.importzp text_ptr,screen_ptr
.export entry
F=GTF_FRAME
.segment "CODE"
 OVL_BINDING
; ROOT_BEGIN3/STEP1 retain this image until READY; return to C21 op4.
; Private/public BEGIN0, STEP1, CANCEL2 retain their bounded API.
entry:
 lda se_f_owner
 cmp #4
 jne busy
 lda se_overlay_frame
 cmp #3
 bne @ordinary
 lda #1
 sta GTF_CONTROL+5
 lda #0
 sta se_overlay_frame
 beq @call
@ordinary:
 cmp #1
 beq @call
 lda #0
 sta GTF_CONTROL+5
@call:
 jsr core_entry
 bcs @return
 tax
 lda GTF_CONTROL+5
 beq @restore
 lda #30
 ldy #1
 cpx #0
 bne @publish
 lda #0
 sta GTF_CONTROL+5
 lda #21
 ldy #4
@publish:
 sta GP_CONTROL+1
 sty GP_CONTROL+2
 lda #1
 clc
 rts
@restore:
 txa
@return:
 rts
core_entry:
 lda se_f_owner
 cmp #4
 jne busy
 lda se_overlay_frame
 beq begin
 cmp #1
 jeq step
 cmp #2
 jeq cancel
 lda #$90
 sec
 rts
busy:
 lda #$B2
 sec
 rts
failed:
 pha
 lda #0
 sta GTF_PHASE
 pla
 sec
 rts
pending:
 lda #1
 clc
 rts
ready:
 lda #0
 clc
 rts
begin:
 lda #0
 sta GTF_PHASE
 jsr guard
 jcs failed
 jsr meta_request
 jsr se_gp_cache_read
 jcs failed
 ldx #31
@tag:
 lda GTF_BUFFER,x
 cmp font_header,x
 bne begin_new
 dex
 bpl @tag
 ; A READY tag is a format witness, not proof its derived payload stayed intact.
 ; Verify five bounded blocks; a bad reused cache is rebuilt before returning.
 lda #3
 sta GTF_PHASE
 jmp verify_begin
begin_new:
 lda #0
 ldx #31
@clear:
 sta GTF_BUFFER,x
 dex
 bpl @clear
 jsr meta_request
 jsr se_gp_cache_write
 jcs failed
 ldx #GG_SIZE-1
 lda #0
@frame:
 sta F,x
 dex
 bpl @frame
 lda #1
 sta F+GG_ENCODING
 sta GTF_PHASE
 lda #16
 sta F+GG_CLIP_RIGHT
 lda #9
 sta F+GG_CLIP_BOTTOM
 lda #<se_geos_packed
 sta F+GG_FONT
 lda #>se_geos_packed
 sta F+GG_FONT+1
 lda #<se_geos_widths
 sta F+GG_WIDTHS
 lda #>se_geos_widths
 sta F+GG_WIDTHS+1
 lda #0
 sta F+GG_NATIVE
 sta GTF_INDEX
 lda #$48
 sta F+GG_NATIVE+1
 jmp pending
step:
 lda GTF_PHASE
 jeq ready
 jsr guard
 jcs failed
 lda GTF_PHASE
 cmp #1
 beq @glyph
 cmp #2
 jeq verify
 cmp #3
 jeq verify
 jmp malformed
@glyph:
 lda GTF_INDEX
 cmp #128
 jcs malformed
 lda GTF_INDEX
 sta F+GG_VALUE
 ldx #<F
 ldy #>F
 jsr se_geos_glyph
 jcs failed
 ldx #0
 ldy #0
@ink:
 lda F+GG_INK,x
 sta GTF_BUFFER,y
 lda F+GG_INK+1,x
 jne font_bad
 inx
 inx
 iny
 cpy #9
 bcc @ink
 ; OffsetE568+index*9, never a hardcoded physicalbank.
 lda #0
 sta GP_IO_OFFSET+1
 lda GTF_INDEX
 asl
 rol GP_IO_OFFSET+1
 asl
 rol GP_IO_OFFSET+1
 asl
 rol GP_IO_OFFSET+1
 clc
 adc GTF_INDEX
 sta GP_IO_OFFSET
 lda GP_IO_OFFSET+1
 adc #0
 sta GP_IO_OFFSET+1
 clc
 lda GP_IO_OFFSET
 adc #<GTF_DATA
 sta GP_IO_OFFSET
 lda GP_IO_OFFSET+1
 adc #>GTF_DATA
 sta GP_IO_OFFSET+1
 lda #9
 jsr buffer_request
 jsr se_gp_cache_write
 jcs failed
 lda F+GG_ADVANCE
 sta GTF_BUFFER
 clc
 lda GTF_INDEX
 adc #<GTF_WIDTHS
 sta GP_IO_OFFSET
 lda #>GTF_WIDTHS
 adc #0
 sta GP_IO_OFFSET+1
 lda #1
 jsr buffer_request
 jsr se_gp_cache_write
 jcs failed
 inc GTF_INDEX
 lda GTF_INDEX
 cmp #128
 jcc pending
 lda #2
 sta GTF_PHASE
verify_begin:
 lda #0
 sta GTF_BLOCK
 jsr se_crc_init
 lda se_crc_value
 sta GTF_CRC
 lda se_crc_value+1
 sta GTF_CRC+1
 jmp pending
font_bad:
 lda GTF_PHASE
 cmp #3
 jeq begin_new
 lda #$94
 jmp failed
malformed:
 lda #$90
 jmp failed
verify:
 lda GTF_BLOCK
 cmp #5
 jcs malformed
 ; Five256-byte readbacksteps cover the actual1280B cache in its bank.
 lda #<GTF_DATA
 sta GP_IO_OFFSET
 lda GTF_BLOCK
 clc
 adc #>GTF_DATA
 sta GP_IO_OFFSET+1
 lda #0
 jsr buffer_request
 lda #1
 sta GP_IO_LENGTH+1
 jsr se_gp_cache_read
 jcs failed
 lda GTF_CRC
 sta se_crc_value
 lda GTF_CRC+1
 sta se_crc_value+1
 ldy #0
@crc:
 lda GTF_BUFFER,y
 jsr se_crc_byte
 iny
 bne @crc
 lda se_crc_value
 sta GTF_CRC
 lda se_crc_value+1
 sta GTF_CRC+1
 inc GTF_BLOCK
 lda GTF_BLOCK
 cmp #5
 jcc pending
 lda GTF_CRC
 cmp #<GTF_EXPECTED_CRC
 jne font_bad
 lda GTF_CRC+1
 cmp #>GTF_EXPECTED_CRC
 jne font_bad
 lda GTF_PHASE
 cmp #3
 bne :+
 lda #0
 sta GTF_PHASE
 jmp ready
: ldx #31
@header:
 lda font_header,x
 sta GTF_BUFFER,x
 dex
 bpl @header
 jsr meta_request
 jsr se_gp_cache_write
 jcs failed
 lda #0
 sta GTF_PHASE
 jmp ready
cancel:
 lda GTF_PHASE
 jeq ready
 lda #0
 sta GTF_PHASE
 ; BEGIN cleared READY before anydatawrites; no guessedcapability access.
 jmp ready
guard:
 lda se_mode
 cmp #3
 bne @bad
 lda se_r_presentation
 bne @bad
 jsr se_gp_cache_guard
 bcs @return
 lda GP_HEADER+GPH_VALID
 cmp #1
 bne @bad
 lda #0
 clc
@return:
 rts
@bad:
 lda #$74
 sec
 rts
meta_request:
 lda #<GTF_META
 sta GP_IO_OFFSET
 lda #>GTF_META
 sta GP_IO_OFFSET+1
 lda #32
buffer_request:
 sta GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 sta GP_IO_POINTER
 lda #>GTF_BUFFER
 sta GP_IO_POINTER+1
 rts
.segment "RODATA"
font_header:
 .byte $A5,"GTF1",1
 OVL_BINDING
 .word GTF_EXPECTED_CRC
 .word 1280
 .res 6,0
.assert *-font_header=32,error,"glyphcache headerlayout"
