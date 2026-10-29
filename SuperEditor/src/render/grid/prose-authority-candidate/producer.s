; R14 optional C14-derived visible logical-row prose authority. No BSS/ZP.
.setcpu "6502"
.macpack longbranch
.include "prose.inc"
.include "document/math24.inc"
.import se_f_owner,se_mode,se_doc_epoch,se_st_key,se_st_descriptor,se_st_rows,se_st_generation
.import se_st_busy,st_owned,st_phase,st_columns
.import se_sm_kind,se_sm_start,se_sm_ready
.import se_fs_guard,se_fs_owned
.import se_gc_handle,se_gc_epoch,se_gc_width,se_reu_epoch,se_reu_retired
.import se_reu_map,se_reu_logical_owner,se_reu_physical_owner
.import se_reu_logical,se_reu_offset,se_reu_c64,se_reu_length,se_reu_copy
.import se_crc_init,se_crc_byte,se_crc_value
.export se_sc_begin,se_sc_event,se_sc_finish
H=SC_H
ROW=SC_C
INDEX=SC_C+1
MASK=SC_C+2
.segment "FOLD_SOURCE_CODE"
se_sc_begin:
 jsr guard
 jcs miss
 lda #0
 ldx #127
@clear:
 sta H,x
 dex
 bpl @clear
 lda #'S'
 sta H
 lda #'P'
 sta H+1
 lda #1
 sta H+2
 ldx #32
@key:
 lda se_st_key,x
 sta H+SC_KEY,x
 dex
 bpl @key
 ldx #1
@epoch:
 lda se_doc_epoch,x
 sta H+SC_EPOCH,x
 dex
 bpl @epoch
 clc
 lda se_st_generation
 adc #1
 sta H+SC_GEN
 lda se_st_generation+1
 adc #0
 sta H+SC_GEN+1
 lda st_columns
 sta H+SC_WIDTH
 ldx #68
@rows:
 lda se_st_rows,x
 sta H+SC_ROWS,x
 dex
 bpl @rows
 jmp publish

se_sc_event:
 lda se_f_owner
 cmp #2
 jne miss
 lda se_sm_kind ;actual completed block event; role0 is never consulted
 jne done
 lda se_sm_ready
 cmp #1
 jne miss
 lda st_phase
 cmp #1
 jne miss
 jsr current
 jcs miss
 lda #0
 sta ROW
@row:
 lda ROW
 asl
 clc
 adc ROW
 tax
 ldy #0
@start:
 lda se_st_rows,x
 cmp se_sm_start,y
 bne @next
 inx
 iny
 cpy #3
 bcc @start
 lda ROW
 and #7
 tax
 lda bits,x
 sta MASK
 lda ROW
 lsr
 lsr
 lsr
 tax
 lda H+SC_PLAIN,x
 ora MASK
 sta H+SC_PLAIN,x
@next:
 inc ROW
 lda ROW
 cmp #22
 bcc @row
 jmp publish

se_sc_finish:
 jsr current
 jcs miss
 lda se_st_busy
 cmp #1
 jne miss
 lda #$A5
 sta H+3
 jmp publish

current:
 jsr guard
 jcs miss
 jsr request
 lda #1
 jsr se_reu_copy
 jcs miss
 jsr checksum
 ldx #1
@crc:
 lda se_crc_value,x
 cmp H+SC_CRC,x
 jne miss
 dex
 bpl @crc
 lda H
 cmp #'S'
 jne miss
 lda H+1
 cmp #'P'
 jne miss
 lda H+2
 cmp #1
 jne miss
 lda H+3
 jne miss ;only the in-progress record belongs to this producer
 ldx #32
@key:
 lda H+SC_KEY,x
 cmp se_st_key,x
 jne miss
 cmp se_st_descriptor,x
 jne miss
 dex
 bpl @key
 ldx #1
@epoch:
 lda H+SC_EPOCH,x
 cmp se_doc_epoch,x
 jne miss
 dex
 bpl @epoch
 clc
 lda se_st_generation
 adc #1
 sta INDEX
 lda se_st_generation+1
 adc #0
 cmp H+SC_GEN+1
 jne miss
 lda INDEX
 cmp H+SC_GEN
 jne miss
 lda H+SC_WIDTH
 cmp st_columns
 jne miss
 ldx #68
@rows:
 lda H+SC_ROWS,x
 cmp se_st_rows,x
 jne miss
 dex
 bpl @rows
 clc
 rts

guard:
 lda se_f_owner
 cmp #2
 jne miss
 lda se_mode
 cmp #1
 beq @sixty
 cmp #2
 jne miss
 lda #80
 bne @width
@sixty:
 lda #60
@width:
 cmp st_columns
 jne miss
 cmp se_gc_width
 jne miss
 lda se_fs_owned
 cmp #1
 jne miss
 lda st_owned
 cmp #1
 jne miss
 lda se_reu_retired
 jne miss
 ldx #1
@epoch:
 lda se_gc_epoch,x
 cmp se_reu_epoch,x
 jne miss
 dex
 bpl @epoch
 ldx se_gc_handle
 jeq miss
 lda se_reu_logical_owner,x
 cmp #$FE
 jne miss
 ldy se_reu_map,x
 jeq miss
 lda se_reu_physical_owner,y
 cmp #$FE
 jne miss
 jmp se_fs_guard

publish:
 jsr checksum
 lda se_crc_value
 sta H+SC_CRC
 lda se_crc_value+1
 sta H+SC_CRC+1
 jsr request
 lda #0
 jsr se_reu_copy
 jcs miss
done:
 lda #0
 clc
 rts
miss:
 lda #2
 sec
 rts
checksum:
 jsr se_crc_init
 ldy #0
@byte:
 lda H,y
 jsr se_crc_byte
 iny
 cpy #SC_CRC
 bcc @byte
 rts
request:
 lda se_gc_handle
 sta se_reu_logical
 lda #<SC_REU
 sta se_reu_offset
 lda #>SC_REU
 sta se_reu_offset+1
 lda #<H
 sta se_reu_c64
 lda #>H
 sta se_reu_c64+1
 lda #128
 sta se_reu_length
 lda #0
 sta se_reu_length+1
 rts
.segment "RODATA"
bits:.byte 1,2,4,8,16,32,64,128
