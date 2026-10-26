; Complete raw CR transaction. No parser/carry authority is asserted.
; Stages all candidate packets before paint; copies the authenticated font once.
; The raw blitter remains in this leaf; no nested R-slot load or yield occurs.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "document/math24.inc"
.include "render/grid/caret/api.inc"
.include "render/grid/paragraph/long.inc"
.import se_cr_validate,rg_context,rg_header_crc,rg_header_same,se_cr_font,se_cr_raw_row
.import rg_packet_read,rg_packet_crc,rg_packet_request,rg_getbit
.import se_rg_check_source,se_view_peek,se_v_pos,se_v_length,se_hot_caret
.import se_reu_copy,se_reu_offset,se_crc_value,se_gc_valid
.import se_v_rows,se_v_bottom,se_doc_invalidate
.import se_i_ready,se_i_count,se_n_cache_count
.export cr_begin,cr_next
E=$8D00
FIRST=E+1
START=E+14
ROW=E+22
PHASE=E+23
NCR=E+24
COL=E+25
RR=$8DDC
SEEN=E+27
GC=E+28
ANCHORS=E+32
CRBITS=E+101
NEWROW=E+106
NEWCOL=E+107
PALETTE=E+112
DIRTY=E+3
OLD=$9000 ;retired LINEINDEX; no active FS/GL or source-grid job owns it
H=NC_HEADER
P=NC_PACKET
B=NC_SECOND
C=NC_C
W=C+1
.macro ADVANCE target
 inc target
 bne :+
 inc target+1
 bne :+
 inc target+2
:
.endmacro
.segment "CODE"
bad:lda #$90
 sec
 rts
ret:rts
cr_begin:
 jsr rg_context
 jcs ret
 lda #0
 sta se_i_ready
 sta se_i_count
 sta se_n_cache_count
 jsr se_cr_validate
 jcs ret
 lda #0
 sta PHASE
 sta SEEN
 sta DIRTY
 sta DIRTY+1
 sta DIRTY+2
 ldx #2
@init:
 lda START,x
 sta se_v_pos,x
 lda se_gc_valid,x
 sta GC,x
 lda H+N_CR,x
 sta CRBITS,x
 dex
 bpl @init
 lda FIRST
 sta ROW
@generate:
 lda ROW
 sta RR
 jsr rg_packet_read
 jcs ret
 jsr rg_packet_crc
 lda ROW
 asl
 tax
 lda se_crc_value
 cmp H+N_ROWCRC,x
 jne bad
 lda se_crc_value+1
 cmp H+N_ROWCRC+1,x
 jne bad
 ldx W
 dex
@policy:
 lda P+80,x
 jne bad
 lda P+160,x
 and #$FB
 jne bad
 dex
 bpl @policy
 ldy #0
@old:
 lda P,y
 sta OLD,y
 iny
 cpy #240
 bcc @old
 ; Unused width60 padding remains the real destination packet's bytes.
 ldx W
 dex
@blank:
 lda #32
 sta P,x
 lda #0
 sta P+80,x
 sta P+160,x
 dex
 bpl @blank
 lda ROW
 jsr anchor
 ldy #0
@start:
 lda se_v_pos,y
 sta ANCHORS,x
 inx
 iny
 cpy #3
 bcc @start
 lda #0
 sta COL
 sta NCR
@byte:
 lda SEEN
 bne @source
 CMP24 se_v_pos,se_hot_caret
 bne @source
 lda ROW
 sta NEWROW
 ldx COL
 stx NEWCOL
 lda #4
 sta P+160,x
 inc SEEN
@source:
 CMP24 se_v_pos,se_v_length
 beq @row_done
 jsr se_view_peek
 jcs ret
 cmp #13
 beq @cr
 ldx COL
 sta P,x
 ADVANCE se_v_pos
 inc COL
 lda COL
 cmp W
 bcc @byte
 bcs @row_done
@cr:
 inc NCR
 ADVANCE se_v_pos
@row_done:
 lda ROW
 and #7
 tay
 lda bits,y
 sta E+26
 lda ROW
 lsr
 lsr
 lsr
 tax
 lda E+26
 eor #$FF
 and CRBITS,x
 ldy NCR
 beq :+
 ora E+26
: sta CRBITS,x
 ldy #0
@same:
 lda P,y
 cmp OLD,y
 bne @dirty
 iny
 cpy #240
 bcc @same
 ; Exact240-byte equality reuses the CRC of the just-validated old packet.
 ; This is equality of bytes, not trust in CRC equality as content proof.
 lda ROW
 asl
 tax
 lda H+N_ROWCRC,x
 sta B,x
 lda H+N_ROWCRC+1,x
 sta B+1,x
 jmp @staged
@dirty:
 jsr rg_packet_crc
 lda ROW
 asl
 tax
 lda se_crc_value
 sta B,x
 lda se_crc_value+1
 sta B+1,x
 lda ROW
 jsr dirty_bit
 ora DIRTY,x
 sta DIRTY,x
 jsr staged_request
 lda #0
 jsr se_reu_copy
 jcs ret
@staged:
 inc ROW
 lda ROW
 cmp #22
 jcc @generate
 jsr anchor
 ldy #0
@bottom:
 lda se_v_pos,y
 sta ANCHORS,x
 inx
 iny
 cpy #3
 bcc @bottom
 lda SEEN
 cmp #1
 jne bad
 jsr se_rg_check_source
 jcs ret
 jsr rg_header_crc
 jcs ret
 ; Header equality was already established by preflight, and no callback or
 ; foreground yield occurs during generation. B now holds candidate CRCs.
 jsr se_cr_font
 jcs ret
 lda #0
 ldx #2
@invalidate:
 sta se_gc_valid,x
 dex
 bpl @invalidate
 lda FIRST
 sta ROW
@paint:
 lda ROW
 jsr dirty_bit
 and DIRTY,x
 beq @next_paint
 jsr se_rg_check_source
 jcs ret
 jsr staged_request
 lda #1
 jsr se_reu_copy
 jcs ret
 jsr rg_packet_crc
 lda ROW
 asl
 tax
 lda se_crc_value
 cmp B,x
 jne bad
 lda se_crc_value+1
 cmp B+1,x
 jne bad
 lda ROW
 sta C+3
 jsr se_cr_raw_row
 jcs ret
 lda ROW
 jsr rg_packet_request
 lda #0
 jsr se_reu_copy
 jcs ret
@next_paint:
 inc ROW
 lda ROW
 cmp #22
 jcc @paint
 jsr se_rg_check_source
 jcs ret
 ; All affected rows have actually painted. Publish geometry only now; the
 ; parent still performs the real R25 source/revision/CRC VALID-last commit.
 lda FIRST
 jsr anchor
@anchors:
 lda ANCHORS,x
 sta H+N_ROWS,x
 cpx #66
 bcs :+
 sta se_v_rows,x
: inx
 cpx #69
 bcc @anchors
 ldx #2
@tail:
 lda ANCHORS+66,x
 sta se_v_bottom,x
 lda CRBITS,x
 sta H+N_CR,x
 lda GC,x
 sta LS_GC,x
 dex
 bpl @tail
 lda FIRST
 asl
 tax
@crcs:
 lda B,x
 sta H+N_ROWCRC,x
 inx
 cpx #44
 bcc @crcs
 lda NEWROW
 sta C+20
 lda NEWCOL
 sta C+21
 lda #1
 sta LS_NOEND
 lda #21
 sta LS_LAST
 lda #0
 sta PHASE
 lda #1
 clc
 rts
cr_next:
 jmp bad
staged_request:
 lda ROW
 jsr rg_packet_request
 lda se_reu_offset+1
 clc
 adc #$40
 sta se_reu_offset+1
 rts
anchor:
 sta E+26
 asl
 clc
 adc E+26
 tax
 rts
dirty_bit:
 pha
 and #7
 tax
 lda bits,x
 sta E+26
 pla
 lsr
 lsr
 lsr
 tax
 lda E+26
 rts
.segment "RODATA"
bits:.byte 1,2,4,8,16,32,64,128
palette:.byte 1,3,7,10,14,1,1,7,13,5,15,7,3,1
descriptor:
 .byte 0,0,0,0,6
 .word $6000,$4000,$A800,P,P+80,P+160,PALETTE
