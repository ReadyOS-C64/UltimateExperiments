; Readonly full-row authority. CPU transaction only; no source writes/leases.
.setcpu "6502"
.macpack longbranch
GP_CACHE_IMPLEMENTATION=1
.include "render/geos/code-typing/worker.inc"
.include "document/math24.inc"
.import se_gct_current,se_gp_cache_read,se_gp_cache_slot
.import se_hot_caret,se_v_top,se_v_length,se_v_pos,se_view_peek
.export se_gct_admit
P=GCT_PACKET
H=GCT_HEADER
.segment "CODE"
se_gct_admit:
 jsr se_gct_current
 jcs done
 cmp #2
 jeq miss ;CMP equality sets carry; readonly miss must return C clear
 lda #0
 sta GP_IO_OFFSET
 sta GP_IO_OFFSET+1
 lda #<H
 ldx #>H
 ldy #64
 jsr read
 jcs done
 lda H+GPH_VALID
 cmp #1
 jne miss
 lda H+GPH_MAGIC
 cmp #$47
 jne miss
 lda H+GPH_VERSION
 cmp #3
 jne miss
 lda H+GPH_COUNT
 jeq miss
 cmp #23
 jcs miss
 cmp GCC_COUNT
 jne miss
 ldx #36
@key:
 lda H+GPH_KEY,x
 cmp GCC_KEY,x
 jne miss
 dex
 bpl @key
 ldx #2
@view:
 lda H+GPH_TOP,x
 cmp se_v_top,x
 jne miss
 lda H+GPH_PAN,x
 jne miss
 lda H+GPH_FOLD_VALID,x
 cmp GCC_FOLD,x
 jne miss
 dex
 bpl @view
 lda H+GPH_CARET_ROW
 cmp H+GPH_COUNT
 jcs miss
 sta GCT_ROW
 jsr se_gp_cache_slot
 jcs done
 lda GP_IO_OFFSET
 sta GCT_SLOT
 lda GP_IO_OFFSET+1
 sta GCT_SLOT+1
 lda #<P
 ldx #>P
 jsr request
 lda #<GPR_USED
 sta GP_IO_LENGTH
 lda #>GPR_USED
 sta GP_IO_LENGTH+1
 jsr se_gp_cache_read
 jcs done
 lda P+GPR_KIND
 cmp #1
 jne miss
 lda P+GPR_BACKGROUND
 cmp #6
 jne miss
 lda P+GPR_HEIGHT
 cmp #8
 jne miss
 lda P+GPR_FLAGS
 ora P+GPR_RASTER_X
 ora P+GPR_RASTER_X+1
 ora P+GPR_COUNT+1
 jne miss
 lda P+GPR_TOP
 cmp #16
 jcc miss
 cmp #185
 jcs miss
 and #7
 jne miss
 lda P+GPR_COUNT
 jeq miss
 cmp #40
 jcs miss
 lda P+GCT_LANG_OFFSET
 cmp #1
 beq :+
 cmp #2
 jne miss
: eor #$FF
 cmp P+GCT_LANG_CHECK
 jne miss
 CMP24 P+GPR_START,P+GPR_FIRST
 jne miss
 SUB24 P+GPR_END,P+GPR_START,GTT_TEMP
 lda GTT_TEMP+1
 ora GTT_TEMP+2
 jne miss
 lda GTT_TEMP
 cmp P+GPR_COUNT
 jne miss
 SUB24 GEC_POSITION,P+GPR_START,GTT_TEMP
 lda GTT_TEMP+1
 ora GTT_TEMP+2
 jne miss
 lda GTT_TEMP
 sta GCT_INDEX_OLD
 cmp P+GPR_COUNT
 bcc :+
 jne miss
 lda GEC_OP
 jne miss
:
 COPY24 P+GPR_NEXT,GCT_OLD_NEXT
 lda P+GPR_REASON
 cmp #1
 beq @CR
 cmp #2
 jne miss
 CMP24 P+GPR_END,P+GPR_NEXT
 jne miss
 CMP24 P+GPR_END,GEC_LENGTH
 jne miss
 jmp @leading
@CR:
 COPY24 P+GPR_END,GTT_TEMP
 inc GTT_TEMP
 bne :+
 inc GTT_TEMP+1
 bne :+
 inc GTT_TEMP+2
: CMP24 GTT_TEMP,P+GPR_NEXT
 jne miss
@leading:
 ; Unchanged firstnonspace alpha/digit prevents this line becoming a fence.
 ldx #0
@space:
 cpx GCT_INDEX_OLD
 jcs miss
 lda P+GPR_CHARS,x
 cmp #32
 bne @first
 inx
 bne @space
@first:
 and #$7F
 cmp #'0'
 bcc @alpha
 cmp #'9'+1
 bcc @op
@alpha:
 cmp #$41
 jcc miss
 cmp #$5B
 jcs miss
@op:
 lda GEC_OP
 sta GCT_OP
 beq @insert
 ldx GCT_INDEX_OLD
 lda P+GPR_CHARS,x
 cmp GEC_OLD
 jne miss
 jmp @preceding
@insert:
 lda P+GPR_COUNT
 cmp #39
 jcs miss
 ; No CR/control can preserve a complete native8 row. Printable graphics are
 ; literal; the actual lexer recomputes allroles and markerpresence.
 lda GEC_NEW
 cmp #32
 jcc miss
 cmp #$80
 bcc @preceding
 cmp #$A0
 jcc miss
@preceding:
 COPY24 P+GPR_START,se_v_pos
 lda se_v_pos
 ora se_v_pos+1
 ora se_v_pos+2
 beq @accepted
 lda se_v_pos
 bne @low
 lda se_v_pos+1
 bne @mid
 dec se_v_pos+2
@mid:
 dec se_v_pos+1
@low:
 dec se_v_pos
 jsr se_view_peek
 jcs done
 cmp #13
 jne miss
@accepted:
 lda #1
 clc
done:
 rts
miss:
 lda #2
 clc
 rts
read:
 jsr request
 sty GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 jmp se_gp_cache_read
request:
 sta GP_IO_POINTER
 stx GP_IO_POINTER+1
 rts
