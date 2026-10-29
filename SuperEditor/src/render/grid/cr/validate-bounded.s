; Genuine-CR preflight. No pixel/cache/header publication.
; Caller has actual R25 type_long_prepare, then retired the sparse index.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "document/math24.inc"
.include "render/grid/caret/api.inc"
.macro INC24 target
 inc target
 bne :+
 inc target+1
 bne :+
 inc target+2
:
.endmacro
.macro DEC24 target
 lda target
 bne :++
 lda target+1
 bne :+
 dec target+2
: dec target+1
: dec target
.endmacro
.import rg_context,rg_expected,rg_tables,rg_header_crc,rg_header_same
.import rg_packet_read,rg_packet_crc,rg_getbit
.import se_rg_capture_source,se_rg_check_source
.import se_view_peek,se_v_pos,se_v_length,se_hot_caret,se_crc_value
.export se_cr_validate
G=$8D80
RR=G+92
E=$8D00
MODE=E
FIRST=E+1
LAST=E+2
LEFT=E+3
COUNT=E+4
INDEX=E+5
CR=E+6
EDITED=E+7
OLDPOS=E+8
EDITPOS=E+11
START=E+14
NEWEND=E+17
GOT=E+20
READY=E+21
H=NC_HEADER
P=NC_PACKET
C=NC_C
W=C+1
OLDROW=C+23
OLDCOL=C+24
SIGN=C+62
.segment "CODE"
bad:lda #$90
 sec
 rts
se_cr_validate:
 jsr rg_context
 jcs ret
 jsr rg_expected
 jcs ret
 jsr se_rg_capture_source
 jcs ret
 jsr rg_tables
 jsr rg_header_crc
 jcs ret
 jsr rg_header_same
 jcs ret
 lda #0
 sta READY
 sta EDITED
 lda SIGN
 sta MODE
 lda OLDROW
 sta FIRST
 sta RR
 ldx #2
@position:
 lda H+N_CARET,x
 sta EDITPOS,x
 dex
 bpl @position
 lda MODE
 cmp #1
 beq @insert
 cmp #$FF
 jne bad
 lda OLDCOL
 jne bad
 lda RR
 jeq bad
 dec RR
 dec FIRST
 lda RR
 jsr rg_getbit
 jeq bad
 DEC24 EDITPOS
 lda #2
 bne @range
@insert:
 lda #1
@range:
 sta LEFT
 ; Cheap refusal only, from the CRC-checked old header. Do not scan an
 ; unfinished offscreen paragraph byte-by-byte before the normal fallback.
 ; A visible EOF can terminate the final logical row without a true CR.
 CMP24 H+N_ROWS+66,H+N_KEY+21
 beq @visible
 lda LEFT
 sta E+22
@closed_visible:
 lda RR
 jsr rg_getbit
 beq :+
 dec E+22
 beq @visible
: inc RR
 lda RR
 cmp #22
 bcc @closed_visible
 jmp bad
@visible:
 lda FIRST
 sta RR
 lda FIRST
 asl
 clc
 adc FIRST
 tax
 ldy #0
@start:
 lda H+N_ROWS,x
 sta START,y
 sta OLDPOS,y
 sta se_v_pos,y
 inx
 iny
 cpy #3
 bcc @start
@row:
 lda RR
 jsr rg_getbit
 beq :+
 lda #1
: sta CR
 lda RR
 asl
 clc
 adc RR
 tax
 sec
 lda H+N_ROWS+3,x
 sbc H+N_ROWS,x
 sta COUNT
 lda H+N_ROWS+4,x
 sbc H+N_ROWS+1,x
 jne bad
 lda H+N_ROWS+5,x
 sbc H+N_ROWS+2,x
 jne bad
 lda COUNT
 sec
 sbc CR
 jcc bad
 sta COUNT
 cmp W
 beq :+
 jcs bad
: jsr rg_packet_read
 jcs ret
 jsr rg_packet_crc
 lda RR
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
@roles:
 lda P+80,x
 jne bad
 lda P+160,x
 and #$FB
 jne bad
 dex
 bpl @roles
 lda #0
 sta INDEX
@byte:
 jsr inserted
 jcs ret
 lda INDEX
 cmp COUNT
 bcs @end
 tax
 lda P,x
 jsr compare
 jcs ret
 inc INDEX
 jmp @byte
@end:
 lda CR
 beq @eof
 lda MODE
 cmp #$FF
 bne @samecr
 lda EDITED
 bne @samecr
 CMP24 OLDPOS,EDITPOS
 bne @samecr
 lda #1
 sta EDITED
 INC24 OLDPOS
 jmp @closed
@samecr:
 lda #13
 jsr compare
 jcs ret
@closed:
 dec LEFT
 beq @complete
@eof:
 CMP24 OLDPOS,H+N_KEY+21
 bne @nextrow
 ; A deleted final CR can leave the old caret on the virtual EOF row. Its
 ; packet must still authenticate before any later renderer may erase it.
 lda RR
 cmp OLDROW
 bcs @complete
@nextrow:
 inc RR
 lda RR
 cmp #22
 jcs bad
 jmp @row
@complete:
 lda EDITED
 cmp #1
 jne bad
 lda RR
 sta LAST
 ldx #2
@endcopy:
 lda OLDPOS,x
 sta NEWEND,x
 dex
 bpl @endcopy
 lda MODE
 bmi @minus
 INC24 NEWEND
 jmp @match
@minus:
 DEC24 NEWEND
@match:
 CMP24 NEWEND,se_v_pos
 jne bad
 jsr se_rg_check_source
 jcs ret
 lda #$A5
 sta READY
 lda #0
 clc
ret:rts

; A real inserted CR is consumed exactly once in canonical order; the old
; byte at that position must still compare after the new CR has been skipped.
inserted:
 lda MODE
 cmp #1
 bne clear
 lda EDITED
 bne clear
 CMP24 OLDPOS,EDITPOS
 bne clear
 jsr se_view_peek
 bcs ret
 cmp #13
 jne bad
 INC24 se_v_pos
 lda #1
 sta EDITED
clear:
 clc
 rts
compare:
 pha
 jsr se_view_peek
 bcs @error
 sta GOT
 pla
 cmp GOT
 jne bad
 INC24 se_v_pos
 INC24 OLDPOS
 clc
 rts
@error:
 pla
 sec
 rts
