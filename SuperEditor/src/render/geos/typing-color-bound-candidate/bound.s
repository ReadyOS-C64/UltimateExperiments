.setcpu "6502"
.macpack longbranch
.include "render/geos/editor.inc"
.include "bound.inc"
.import se_f_owner,se_gp_cache_slot,se_gp_cache_read
.importzp text_ptr,screen_ptr
.export se_tcb_check
F=TCB_FRAME
B0=F+5
B1=F+6
LOW=F+7
HIGH=F+8
ROW=F+9
END=F+10
COLORED=F+11
SCAN=F+12
COL=F+13
BAND=F+14
WORK=F+15
PREVIOUS=F+16
.segment "CODE"
se_tcb_check:
 lda se_f_owner
 cmp #4
 beq :+
 lda #$B2
 sec
 rts
: lda F+TCB_TOP
 cmp #16
 jcc miss
 cmp #184
 jcs miss
 and #$F8
 sta LOW
 clc
 adc #16
 sta HIGH
 lda F+TCB_ATTR
 cmp #$16
 jne miss
 lda F+TCB_LAST
 cmp #40
 jcs miss
 cmp F+TCB_FIRST
 jcc miss
 lda TCB_HEADER+GPH_COUNT
 jeq miss
 cmp #23
 jcs miss
 cmp F+TCB_ROW
 jcc miss
 jeq miss
 lda #0
 sta B0
 sta B1
 sta ROW
 lda #16
 sta PREVIOUS
row_loop:
 lda ROW
 jsr se_gp_cache_slot
 jcs error
 lda #<GP_RECORD
 ldx #>GP_RECORD
 ldy #32
 jsr read
 jcs error
 lda GP_RECORD+GPR_TOP
 cmp PREVIOUS
 jcc miss ;prefixes mustbeordered/nonoverlapping, notjustinsideoneband
 cmp #192
 jcs miss
 clc
 adc GP_RECORD+GPR_HEIGHT
 jcs miss
 sta END
 sta PREVIOUS
 lda GP_RECORD+GPR_HEIGHT
 cmp #8
 bne @prose
 lda GP_RECORD+GPR_KIND
 cmp #1
 jne miss
 lda GP_RECORD+GPR_TOP
 and #7
 jne miss ;nativecellwriteris8pxaligned, neverboundanunalignedprefix
 beq @geometry
@prose:
 cmp #9
 jne miss
 lda GP_RECORD+GPR_KIND
 jne miss
@geometry:
 lda GP_RECORD+GPR_TOP
 cmp HIGH
 jcs next
 lda END
 cmp LOW
 jcc next
 jeq next
 lda GP_RECORD+GPR_FLAGS
 and #$FE ;reverse1 is allowed; use base-ink bound, never displayedinverse
 jne miss
 lda GP_RECORD+GPR_BACKGROUND
 cmp #6
 jne miss
 lda GP_RECORD+GPR_COUNT+1
 jne miss
 lda GP_RECORD+GPR_COUNT
 cmp #162
 jcs miss
 cmp #0
 bne :+
 lda ROW
 cmp F+TCB_ROW
 jeq miss
 jmp next
:
 ; True target geometry must match caller's base-ink row.
 lda ROW
 cmp F+TCB_ROW
 bne :+
 lda GP_RECORD+GPR_TOP
 cmp F+TCB_TOP
 jne miss
 lda GP_RECORD+GPR_HEIGHT
 cmp #9
 jne miss
: clc
 lda GP_IO_OFFSET
 adc #<GPR_ROLES
 sta GP_IO_OFFSET
 lda GP_IO_OFFSET+1
 adc #>GPR_ROLES
 sta GP_IO_OFFSET+1
 lda #<TCB_ROLEBUF
 ldx #>TCB_ROLEBUF
 ldy GP_RECORD+GPR_COUNT
 jsr read
 jcs error
 lda #0
 sta COLORED
 ldy GP_RECORD+GPR_COUNT
@roles:
 dey
 lda TCB_ROLEBUF,y
 cmp #14
 jcs miss
 ora COLORED
 sta COLORED
 tya
 bne @roles
 lda COLORED
 beq next
 lda ROW
 cmp F+TCB_ROW
 jeq miss ;target's genuinebaseink mustwhite
 lda GP_RECORD+GPR_TOP
 sta SCAN
@coverage:
 lda SCAN
 cmp LOW
 bcc @scan_next
 cmp HIGH
 bcs next
 sec
 sbc LOW
 cmp #8
 ldx #0
 bcc :+
 inx
: lda B0,x
 clc
 adc #8 ;onecoloredpixelrow can contribute atmost8votes pertile
 cmp #65
 jcs miss ;posttargetatmost64; bound>=64cannever strictlywin
 sta B0,x
@scan_next:
 inc SCAN
 lda SCAN
 cmp END
 bcc @coverage
next:
 inc ROW
 lda ROW
 cmp TCB_HEADER+GPH_COUNT
 jcc row_loop
 ; Accumulate actualpostshiftBASEink. No bitmap/cache/attribute writes.
 ldx #79
 lda #0
@clear:
 sta TCB_VOTES,x
 dex
 bpl @clear
 lda #<TCB_BASE
 sta text_ptr
 lda #>TCB_BASE
 sta text_ptr+1
 lda #0
 sta SCAN
@scan:
 lda F+TCB_TOP
 and #7
 clc
 adc SCAN
 cmp #8
 lda #0
 bcc :+
 lda #40
: sta BAND
 lda F+TCB_FIRST
 sta COL
@pixelbyte:
 ldy COL
 lda (text_ptr),y
 pha
 and #15
 tay
 lda pops,y
 sta WORK
 pla
 lsr
 lsr
 lsr
 lsr
 tay
 lda pops,y
 clc
 adc WORK
 sta WORK
 lda COL
 clc
 adc BAND
 tax
 lda WORK
 clc
 adc TCB_VOTES,x
 sta TCB_VOTES,x
 inc COL
 lda F+TCB_LAST
 cmp COL
 bcs @pixelbyte
 clc
 lda text_ptr
 adc #40
 sta text_ptr
 bcc :+
 inc text_ptr+1
: inc SCAN
 lda SCAN
 cmp #9
 bcc @scan
 ; Attribute pointer to first physicaltileband. Atmost22boundedadds.
 lda #0
 sta screen_ptr
 lda #$40
 sta screen_ptr+1
 lda LOW
 lsr
 lsr
 lsr
 tax
@attrrow:
 clc
 lda screen_ptr
 adc #40
 sta screen_ptr
 bcc :+
 inc screen_ptr+1
: dex
 bne @attrrow
 ldx F+TCB_FIRST
@check:
 txa
 tay
 lda (screen_ptr),y
 cmp F+TCB_ATTR
 bne miss
 lda B0
 beq @second
 cmp TCB_VOTES,x
 jcs miss ;strictwhitegreater, tie conservativefallback
@second:
 txa
 clc
 adc #40
 tay
 lda (screen_ptr),y
 cmp F+TCB_ATTR
 bne miss
 lda B1
 beq @advance
 cmp TCB_VOTES+40,x
 jcs miss
@advance:
 inx
 cpx F+TCB_LAST
 bcc @check
 beq @check
 lda #0
 clc
 rts
miss:
 lda #2
 clc
error:
 rts
read:
 sta GP_IO_POINTER
 stx GP_IO_POINTER+1
 sty GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 jmp se_gp_cache_read
.segment "RODATA"
pops:.byte 0,1,1,2,1,2,2,3,1,2,2,3,2,3,3,4
