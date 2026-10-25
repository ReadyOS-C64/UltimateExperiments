; Private R31 transaction. Complete bounded native8 code rows only. No sourcewrites.
.setcpu "6502"
.macpack longbranch
GP_CACHE_IMPLEMENTATION=1
.include "editor-api.inc"
.include "render/geos/code-typing/worker.inc"
.include "stage-constants.inc"
.include "document/math24.inc"
.import se_gct_admit,se_gct_current,se_gct_stage,se_gp_cache_read,se_gp_cache_write,se_gp_cache_slot,se_gcc_status
.import se_f_owner,se_i_ready,se_i_count,se_n_cache_count
.import se_hot_caret,se_sel_anchor,se_e_draw_sequence,se_r_revision
.import se_v_pos,se_view_peek,se_v_length,se_v_rows,se_v_bottom,se_v_seen,se_v_caret_row
.import se_v_cache_count,se_l_valid,se_l_need_wrap
.importzp text_ptr,screen_ptr
.export entry
P=GCT_PACKET
H=GCT_HEADER
.segment "CODE"
 OVL_BINDING
entry:
 lda se_overlay_frame
 cmp #3
 jne bad
 lda se_f_owner
 jne root_miss
 lda #4
 sta se_f_owner
 lda #0
 sta GCT_PHASE
 jsr transaction
 php
 pha
 lda #0
 sta se_f_owner
 pla
 plp
 rts
bad:
 lda #$90
 sec
 rts
root_miss:
 lda #2
 clc
 rts
failure:
 pha
 jsr retire
 pla
 sec
 rts
miss:
 jsr retire
 lda #2
 clc
 rts
retire:
 lda GCT_PHASE
 beq :+
 lda #0
 sta GCC_VALID
 sta GEC_VALID
: rts
transaction:
 jsr se_gct_admit
 jcs failure
 cmp #1
 jne miss
 jsr se_gct_stage
 jcs failure
 ; Acceptedclaim invalidates onlythe sparse derivedindex beforephaselexeruse.
 lda #0
 sta se_i_ready
 sta se_i_count
 sta se_i_count+1
 sta se_n_cache_count
 lda P+GPR_COUNT
 tax
 lda GCT_OP
 bne @delete
@back:
 cpx GCT_INDEX_OLD
 beq @insert
 lda P+GPR_CHARS-1,x
 sta P+GPR_CHARS,x
 dex
 bne @back
@insert:
 lda GEC_NEW
 sta P+GPR_CHARS,x
 inc P+GPR_COUNT
 jmp @changed
@delete:
 dec P+GPR_COUNT
 ldx GCT_INDEX_OLD
@forward:
 cpx P+GPR_COUNT
 bcs @changed
 lda P+GPR_CHARS+1,x
 sta P+GPR_CHARS,x
 inx
 bne @forward
@changed:
 lda P+GPR_COUNT
 sta GCT_COUNT
 lda P+GPR_TOP
 sta GCT_TOP
 lda P+GCT_LANG_OFFSET
 sta GCT_LANGUAGE
 lda GCT_INDEX_OLD
 ldx GCT_OP
 bne :+
 clc
 adc #1
: sta GCT_CARET
 lda #0
 sta P+GPR_INLINE
 ldx #0
@copy:
 cpx GCT_COUNT
 beq @lex
 lda P+GPR_CHARS,x
 sta GP_SOURCE,x
 cmp #42
 beq @marker
 cmp #64
 bne @style
@marker:
 lda #1
 sta P+GPR_INLINE
@style:
 lda #0
 sta P+GPR_STYLES,x
 inx
 bne @copy
@lex:
 jsr GCT_STAGE_LEX
 jcs failure
 ldx #0
@roles:
 cpx GCT_COUNT
 beq @xmap
 lda GP_ROLES,x
 sta P+GPR_ROLES,x
 inx
 bne @roles
@xmap:
 lda #0
 sta GCT_PAIR
 ldx #0
@x:
 txa
 lsr
 asl
 asl
 asl
 sta P+GPR_X,x
 lda GCT_PAIR
 sta P+GPR_X+1,x
 inx
 inx
 cpx #64
 bne :+
 inc GCT_PAIR
: txa
 lsr
 cmp GCT_COUNT
 bcc @x
 beq @x
 lda GCT_CARET
 jsr pixel
 sta P+GPR_CARET_X
 stx P+GPR_CARET_X+1
 lda GCT_COUNT
 jsr pixel
 sta P+GPR_TAIL_X
 stx P+GPR_TAIL_X+1
 lda #1
 sta P+GPR_CARET_VALID
 sta P+GPR_MEMBER
 sta P+GPR_TAIL_VALID
 lda #<(P+GPR_END)
 sta text_ptr
 lda #>(P+GPR_END)
 sta text_ptr+1
 jsr shift
 jsr plus3
 jsr shift
 COPY24 P+GPR_START,se_v_pos
 lda #0
 sta GCT_SCAN
@source:
 ldx GCT_SCAN
 cpx GCT_COUNT
 beq @end
 jsr se_view_peek
 jcs failure
 ldx GCT_SCAN
 cmp P+GPR_CHARS,x
 jne miss
 inc GCT_SCAN
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
 jsr se_gct_current
 jcs failure
 cmp #2
 jeq miss
 lda #1
 sta GCT_PHASE
 lda #0
 sta GCC_VALID
 sta H+GPH_VALID
 jsr header_write
 jcs failure
 ; Paintcaret-freebase then saveonlythis320Bbitmap/40Bmatrix region.
 lda #1
 sta GCT_FLAGS
 jsr GCT_STAGE_PAINT
 jcs failure
 jsr base_write
 php
 pha
 lda #0
 sta GCT_FLAGS
 jsr GCT_STAGE_PAINT
 bcs @paintfail
 pla
 plp
 jcs failure
 jmp commit
@paintfail:
 tax
 pla
 plp
 txa
 jmp failure
pixel:
 ldx #0
 asl
 asl
 asl
 bcc :+
 inx
: rts
commit:
 jsr packet_request
 jsr se_gp_cache_write
 jcs failure
 lda GCT_ROW
 sta GCT_REBASE_ROW
@row:
 lda GCT_REBASE_ROW
 cmp H+GPH_COUNT
 jcs @page
 cmp GCT_ROW
 jeq @anchor_edit
 jsr se_gp_cache_slot
 lda #<GP_RECORD
 ldx #>GP_RECORD
 ldy #32
 jsr read
 jcs failure
 ; Prefixcanonicaloffsetsmustbe in the unaffected suffix and olddocument.
 ldx #0
@bounds:
 .repeat 3,I
 lda GP_RECORD+I,x
 sta GTT_TEMP+I
 .endrepeat
 CMP24 GTT_TEMP,GCT_OLD_NEXT
 jcc failure_range
 CMP24 GTT_TEMP,GEC_LENGTH
 bcc :+
 jne failure_range
: txa
 clc
 adc #3
 tax
 cpx #12
 bcc @bounds
 lda #<GP_RECORD
 sta text_ptr
 lda #>GP_RECORD
 sta text_ptr+1
 lda #4
 sta GCT_PAIR
@delta:
 jsr shift
 jsr plus3
 dec GCT_PAIR
 bne @delta
 lda GCT_REBASE_ROW
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
: lda P+GPR_START,x
 sta GP_RECORD+GPR_START,x
 dex
 bpl :-
@anchor:
 lda GCT_REBASE_ROW
 asl
 clc
 adc GCT_REBASE_ROW
 tax
 ldy #0
: lda GP_RECORD+GPR_START,y
 sta se_v_rows,x
 inx
 iny
 cpy #3
 bcc :-
 inc GCT_REBASE_ROW
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
@caretx:
 lda P+GPR_CARET_X,x
 sta H+GPH_CARET_X,x
 sta GCC_X,x
 dex
 bpl @caretx
 lda GCT_TOP
 sta GCC_Y
 lda #8
 sta GCC_WIDTH
 sta GCC_HEIGHT
 lda #1
 sta H+GPH_SEEN
 sta H+GPH_CARET_VISIBLE
 sta GCC_RECT
 sta se_v_seen
 sta se_l_valid
 lda GCT_ROW
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
 sta $9149 ;retireoldR28certificate
 sta GCT_PHASE
 clc
 rts
failure_range:
 lda #$90
 jmp failure
plus3:
 clc
 lda text_ptr
 adc #3
 sta text_ptr
 bcc :+
 inc text_ptr+1
: rts
shift:
 ldy #0
 ldx #3
 lda GCT_OP
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
 lda GCT_ROW
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
base_write:
 lda #0
 sta se_v_cache_count
 sta se_v_cache_count+1
 lda GCT_BITMAP
 sta text_ptr
 lda GCT_BITMAP+1
 sta text_ptr+1
 lda #0
 sta screen_ptr
 lda #$80
 sta screen_ptr+1
 ldy #0
@copy256:
 lda (text_ptr),y
 sta (screen_ptr),y
 iny
 bne @copy256
 inc text_ptr+1
 inc screen_ptr+1
@copy64:
 lda (text_ptr),y
 sta (screen_ptr),y
 iny
 cpy #64
 bcc @copy64
 clc
 lda GCT_BITMAP
 adc #$00
 sta GP_IO_OFFSET
 lda GCT_BITMAP+1
 adc #$52
 sta GP_IO_OFFSET+1
 lda #0
 sta GP_IO_POINTER
 lda #$80
 sta GP_IO_POINTER+1
 lda #$40
 sta GP_IO_LENGTH
 lda #1
 sta GP_IO_LENGTH+1
 jsr se_gp_cache_write
 bcs @done
 lda GCT_ATTRIBUTES
 sta text_ptr
 lda GCT_ATTRIBUTES+1
 sta text_ptr+1
 ldy #39
@attrs:
 lda (text_ptr),y
 sta $8400,y
 dey
 bpl @attrs
 clc
 lda GCT_ATTRIBUTES
 adc #$40
 sta GP_IO_OFFSET
 lda GCT_ATTRIBUTES+1
 adc #$91
 sta GP_IO_OFFSET+1
 lda #0
 ldx #$84
 ldy #40
 jsr request
 jmp se_gp_cache_write
@done:rts
