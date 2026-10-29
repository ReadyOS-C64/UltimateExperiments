; CR geometry authority and checked packet operations. No saved continuation.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/grid/caret/api.inc"
.include "render/grid/paragraph/long.inc"
.import se_rg_check_owner
.import se_i_ready,se_i_count,se_n_cache_count
.import se_rg_capture_source,se_rg_check_source
.import se_doc_meta,se_doc_generation,se_r_revision,se_v_length,se_reu_epoch,se_doc_epoch,se_hot_caret,se_hot_base
.import se_render_caps,se_gc_valid,se_gc_handle,se_v_rows,se_v_bottom
.import se_e_ui,se_e_job,se_e_draw_busy,se_e_error,se_r_presentation,se_mode
.import se_crc_init,se_crc_byte,se_crc_value,se_crc_table_low,se_crc_table_high
.import se_reu_logical,se_reu_offset,se_reu_length,se_reu_c64,se_reu_copy
.importzp text_ptr

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

ret:rts
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
tables:
 lda #0
 sta se_i_ready
 sta se_i_count
 sta se_n_cache_count
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

.export rg_context
rg_context=context

.export rg_expected
rg_expected=expected

.export rg_tables
rg_tables=tables

.export rg_header_crc
rg_header_crc=header_crc

.export rg_header_same
rg_header_same=header_same

.export rg_packet_read
rg_packet_read=packet_read

.export rg_packet_crc
rg_packet_crc=packet_crc

.export rg_packet_request
rg_packet_request=packet_request

.export rg_getbit
rg_getbit=getbit
