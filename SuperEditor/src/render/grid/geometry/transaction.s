; Complete R24 row-geometry body. No saved continuation across yields.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/grid/caret/api.inc"
.include "render/grid/paragraph/long.inc"
.import se_rg_prepare,se_rg_apply,se_rg_check_owner
.import se_rg_capture_source,se_rg_check_source
.import se_doc_meta,se_doc_generation,se_r_revision,se_v_length,se_reu_epoch,se_doc_epoch,se_hot_caret,se_hot_base
.import se_render_caps,se_gc_valid,se_gc_handle,se_v_rows,se_v_bottom
.import se_e_ui,se_e_job,se_e_draw_busy,se_e_error,se_r_presentation,se_mode
.import se_crc_init,se_crc_byte,se_crc_value,se_crc_table_low,se_crc_table_high
.import se_reu_logical,se_reu_offset,se_reu_length,se_reu_c64,se_reu_copy
.importzp text_ptr
.export rg_boundary,rg_prepare,rg_apply
G=$8D80
FIRST=G+2
COUNT=G+3
READY=G+4
SRC=G+9
LENGTH=G+13
LAST=G+91
RR=G+92
TR=G+93
BLANK=G+94
HCRC=G+95
VALID=G+97
MASK=G+98
FLAG=G+99
LIMIT=G+100
GEOM=G+127
H=NC_HEADER
P=NC_PACKET
B=NC_SECOND
C=NC_C
W=C+1
ROW=C+3
SIGN=C+62
.segment "CODE"
zero:lda #0
 clc
 rts
bad:lda #$90
 sec
 rts
context:
 jsr se_rg_check_owner
 bcs ret
 lda se_mode
 cmp H+N_MODE
 bne bad
 lda C
 cmp #1
 bne bad
 lda C+63
 cmp #2
 bne bad
 lda se_e_ui
 ora se_e_job
 ora se_e_draw_busy
 ora se_e_error
 ora se_r_presentation
 bne bad
 clc
 rts
; This is only the old terminal admission. Actual source/packet validation
; continues in C33; PREPARE is called after it has completed successfully.
rg_boundary:
 jsr context
 jcs ret
 lda LS_COUNT
 ldx SIGN
 cpx #1
 bne @delete
 clc
 adc #1
 cmp W
 bne bad
 lda ROW
 cmp #21
 bcs bad
 jmp @cr
@delete:
 cpx #$FF
 bne bad
 cmp #0
 bne bad
 lda ROW
 beq bad
@cr:
 lda ROW
 jsr getbit
 beq bad
 jsr expected
 jcs ret
 jsr se_rg_capture_source
 jcs ret
 lda SIGN
 sta GEOM
 jmp zero
ret:rts
rg_prepare:
 jsr context
 jcs ret
 lda #0
 sta VALID
 lda GEOM
 cmp SIGN
 jne bad
 lda LS_LAST
 cmp #22
 jcs bad
 sta LAST
 ldx #2
@oldbottom:
 lda H+N_ROWS+63,x
 sta G+103,x
 dex
 bpl @oldbottom
 lda LAST
 clc
 adc #1
 sta FIRST
 lda #21
 sec
 sbc LAST
 sta COUNT
 lda GEOM
 sta G+1
 cmp #1
 beq @down
 cmp #$FF
 jne bad
 lda LAST
 jeq bad
 ; Unknown rows beyond the old viewport cannot be synthesized on deletion.
 ldx #2
@eof:
 lda H+N_ROWS+66,x
 cmp H+N_KEY+21,x
 jne bad
 dex
 bpl @eof
 jmp @plan
@down:
 dec COUNT
@plan:
 lda #1
 sta G
 jsr se_rg_prepare
 jcs ret
 jsr se_rg_check_source
 jcs ret
 jsr tables
 jsr header_crc
 jcs ret
 lda H+N_CRC
 sta HCRC
 lda H+N_CRC+1
 sta HCRC+1
 jsr header_same
 jcs ret
 jsr packets_valid
 jcs ret
 lda #$A5
 sta VALID
 jmp zero
rg_apply:
 jsr context
 jcs ret
 lda VALID
 cmp #$A5
 jne bad
 ; Rebind every metadata-control byte before the first VIC/cache mutation.
 lda LAST
 cmp LS_LAST
 jne bad
 cmp #22
 jcs bad
 lda GEOM
 cmp SIGN
 jne bad
 cmp G+1
 jne bad
 lda LAST
 clc
 adc #1
 cmp FIRST
 jne bad
 lda #21
 sec
 sbc LAST
 ldx GEOM
 bmi :+
 sec
 sbc #1
: cmp COUNT
 jne bad
 jsr se_rg_check_source
 jcs ret
 jsr tables
 jsr header_crc
 jcs ret
 lda H+N_CRC
 cmp HCRC
 jne bad
 lda H+N_CRC+1
 cmp HCRC+1
 jne bad
 jsr header_same
 jcs ret
 jsr packets_valid ;all refusal paths above precede pixel/cache publication
 jcs ret
 lda #0
 sta VALID
 ldx #2
@invalid:
 sta se_gc_valid,x
 dex
 bpl @invalid
 jsr se_rg_apply
 jcs ret
 ; Preserve direction while moving overlapping packet/header intervals.
 lda FIRST
 sta RR
 lda GEOM
 bmi @move
 clc
 adc FIRST ;GEOM=1
 adc COUNT
 sec
 sbc #2
 sta RR
@move:
 lda COUNT
 beq @blank
 lda RR
 clc
 adc GEOM
 sta TR
 jsr packet_read
 jcs ret
 lda TR
 jsr packet_request
@packet_store:
 lda #0
 jsr se_reu_copy
 jcs ret
 lda RR
 asl
 tax
 lda TR
 asl
 tay
 lda H+N_ROWCRC,x
 sta H+N_ROWCRC,y
 lda H+N_ROWCRC+1,x
 sta H+N_ROWCRC+1,y
 lda RR
 jsr getbit
 sta FLAG
 lda TR
 jsr putbit
 lda RR
 jsr anchor_index
 txa
 tay
 lda TR
 jsr anchor_index
 .repeat 3,I
 lda H+N_ROWS+I,y
 sta H+N_ROWS+I,x
 .endrepeat
 lda GEOM
 bmi @nextup
 dec RR
 jmp @next
@nextup:
 inc RR
@next:
 dec COUNT
 jmp @move
@blank:
 lda GEOM
 bmi @removed
 lda LAST
 clc
 adc #1
 sta BLANK
 sta LS_LAST
 ; The new emptyCR anchor is the old following-row anchor, preserved by
 ; bottom-to-top movement. The future commit rebases following anchors+1.
 ; New viewport bottom is old row21 start (now header row22 unmodified).
 ldx #2
@bottom:
 lda G+103,x
 sta H+N_ROWS+66,x
 dex
 bpl @bottom
 lda #0
 sta FLAG
 lda LAST
 jsr putbit
 lda #1
 sta FLAG
 lda BLANK
 jsr putbit
 jmp @clear
@removed:
 lda LAST
 sec
 sbc #1
 sta LS_LAST
 lda #1
 sta FLAG
 jsr putbit
 lda #21
 sta BLANK
 .repeat 3,I
 lda H+N_ROWS+66+I
 sta H+N_ROWS+63+I
 .endrepeat
 lda #0
 sta FLAG
 lda BLANK
 jsr putbit
@clear:
 jsr clear_row
 jcs ret
 ; Publish exact transformed packet/CRC, then current row geometry to VIEW.
 lda BLANK
 jsr packet_request
 lda #0
 jsr se_reu_copy
 jcs ret
 jsr packet_crc
 lda BLANK
 asl
 tax
 lda se_crc_value
 sta H+N_ROWCRC,x
 lda se_crc_value+1
 sta H+N_ROWCRC+1,x
 ldx #65
@anchors:
 lda H+N_ROWS,x
 sta se_v_rows,x
 dex
 bpl @anchors
 ldx #2
@bottom_view:
 lda H+N_ROWS+66,x
 sta se_v_bottom,x
 dex
 bpl @bottom_view
 jmp zero
.export rg_before_packet_store
rg_before_packet_store=@packet_store
; Bind the captured live source to the already authenticated old NC key
; plus exactly the one edit admitted by real R25. Full FS59 capture then spans
; the remaining actual byte comparison, R14 carry and geometry services.
expected:
 ldx #14
@tokens:
 lda se_doc_meta,x
 cmp H+N_KEY,x
 jne bad
 dex
 bpl @tokens
 ldx #1
@epochs:
 lda se_doc_generation,x
 cmp H+N_KEY+15,x
 jne bad
 lda se_reu_epoch,x
 cmp H+N_KEY+24,x
 jne bad
 lda se_doc_epoch,x
 cmp H+N_KEY+26,x
 jne bad
 dex
 bpl @epochs
 sec
 .repeat 4,I
 lda H+N_KEY+17+I
 adc #0
 sta G+106+I
 .endrepeat
 jcs bad
 ldx #3
@revision:
 lda se_r_revision,x
 cmp G+106,x
 jne bad
 dex
 bpl @revision
 lda #0
 ldx SIGN
 bpl :+
 lda #$FF
: sta G+110
 .macro CHECK_DELTA observed,old
 clc
 lda H+old
 adc SIGN
 sta G+106
 lda H+old+1
 adc G+110
 sta G+107
 lda H+old+2
 adc G+110
 sta G+108
 ldx #2
:
 lda observed,x
 cmp G+106,x
 jne bad
 dex
 bpl :-
 .endmacro
 CHECK_DELTA se_v_length,N_KEY+21
 CHECK_DELTA se_hot_caret,N_CARET
 ldx #2
@base:
 lda se_hot_base,x
 cmp H+N_HOTBASE,x
 jne bad
 dex
 bpl @base
 jmp zero
; Read/compare the immutable old published header, not a trusted host buffer.
header_same:
 lda #$00
 sta se_reu_offset
 lda #$15
 sta se_reu_offset+1
 lda #<B
 sta se_reu_c64
 lda #>B
 sta se_reu_c64+1
 lda #0
 sta se_reu_length
 lda #1
 sta se_reu_length+1
 lda se_gc_handle
 sta se_reu_logical
 lda #1
 jsr se_reu_copy
 jcs ret
 ldx #0
@same:
 lda B,x
 cmp H,x
 jne bad
 inx
 bne @same
 jmp zero
header_crc:
 lda H
 cmp #'N'
 jne bad
 lda H+1
 cmp #'C'
 jne bad
 lda H+2
 cmp #1
 jne bad
 lda H+3
 cmp #$A5
 jne bad
 lda H+N_CAPS
 jne bad
 lda H+N_WIDTH
 cmp W
 jne bad
 jsr se_crc_init
 ldy #0
@crc:
 lda H,y
 eor se_crc_value+1
 tax
 lda se_crc_value
 eor $8F00,x
 sta se_crc_value+1
 lda $8E00,x
 sta se_crc_value
 iny
 cpy #254
 bcc @crc
 lda se_crc_value
 cmp H+254
 jne bad
 lda se_crc_value+1
 cmp H+255
 jne bad
 jmp zero
packets_valid:
 lda FIRST
 sta RR
 clc
 adc COUNT
 sta LIMIT
@row:
 lda RR
 cmp LIMIT
 bcs @done
 jsr packet_read
 jcs ret
 jsr packet_crc
 lda RR
 asl
 tax
 lda se_crc_value
 cmp H+N_ROWCRC,x
 jne bad
 lda se_crc_value+1
 cmp H+N_ROWCRC+1,x
 jne bad
 inc RR
 bne @row
@done:jmp zero
packet_read:
 lda RR
 jsr packet_request
 lda #1
 jmp se_reu_copy
packet_request:
 tax
 lda #0
 sta se_reu_offset
 sta se_reu_offset+1
 cpx #0
 beq @host
@add:
 clc
 lda se_reu_offset
 adc #240
 sta se_reu_offset
 bcc :+
 inc se_reu_offset+1
: dex
 bne @add
@host:
 lda #<P
 sta se_reu_c64
 lda #>P
 sta se_reu_c64+1
 lda #240
 sta se_reu_length
 lda #0
 sta se_reu_length+1
 lda se_gc_handle
 sta se_reu_logical
 rts
packet_crc:
 jsr se_crc_init
 ldy #0
@byte:
 lda P,y
 eor se_crc_value+1
 tax
 lda se_crc_value
 eor $8F00,x
 sta se_crc_value+1
 lda $8E00,x
 sta se_crc_value
 iny
 cpy #240
 bcc @byte
 rts
anchor_index:
 sta G+101
 asl
 clc
 adc G+101
 tax
 rts
getbit:
 sta G+101
 and #7
 tax
 lda bits,x
 sta MASK
 lda G+101
 lsr
 lsr
 lsr
 tax
 lda H+N_CR,x
 and MASK
 rts
putbit:
 jsr getbit
 lda MASK
 eor #$FF
 and H+N_CR,x
 ldy FLAG
 beq :+
 ora MASK
: sta H+N_CR,x
 rts
; Exactly one known-blank physical row, fully inside body2..23. Kernel move
; has already cleared GCvalid, so every later failure retains full fallback.
clear_row:
 lda BLANK
 clc
 adc #2
 sta G+102
 lda #0
 sta text_ptr
 lda #$60
 sta text_ptr+1
 ldx G+102
@base:
 clc
 lda text_ptr
 adc #$40
 sta text_ptr
 lda text_ptr+1
 adc #1
 sta text_ptr+1
 dex
 bne @base
 lda #0
 ldy #0
@page:
 sta (text_ptr),y
 iny
 bne @page
 inc text_ptr+1
 ldy #63
@tail:
 sta (text_ptr),y
 dey
 bpl @tail
 ; Attribute address4050 +logicalrow*40, not bitmap-derived raw input.
 lda #$50
 sta text_ptr
 lda #$40
 sta text_ptr+1
 ldx BLANK
 beq @attr
@add:
 clc
 lda text_ptr
 adc #40
 sta text_ptr
 bcc :+
 inc text_ptr+1
: dex
 bne @add
@attr:
 lda #$16
 ldy #39
@ink:
 sta (text_ptr),y
 dey
 bpl @ink
 ; Inactive width60 padding is retained from the actual validated packet.
 ; The producer compares all240 bytes; normalizing its unused20 columns
 ; would force every unchanged row to repaint on a later safe fallback.
 ldx W
 dex
@spaces:
 lda #32
 sta P,x
 lda #0
 sta P+80,x
 sta P+160,x
 dex
 bpl @spaces
 jmp zero
; Fresh data-only CRC expansion. C33 has retired the whole sparse index
; before LS/geometry use, and source guards prove no active FS lease. R14op7
; uses only8D40..8D68, so it cannot overwrite these newly regenerated tables.
tables:
 .assert (se_crc_table_low & $FF)=0,lderror,"half-table alignment"
 .assert se_crc_table_high=se_crc_table_low+128,lderror,"half-table layout"
 ldx #0
@byte:
 lda se_crc_table_low,x
 sta $8E00,x
 eor #$88
 sta $8E80,x
 lda se_crc_table_high,x
 sta $8F00,x
 eor #$91
 sta $8F80,x
 inx
 bpl @byte
 rts
.segment "RODATA"
bits:.byte 1,2,4,8,16,32,64,128
