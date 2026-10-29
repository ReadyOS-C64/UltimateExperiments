; Exact two-role body ink election. No inverse XOR: GG_INK already
; contains source reverse, whereas selection/caret are excluded by FE snapshot.
.setcpu "6502"
.macpack longbranch
.include "render/geos/editor.inc"
.include "two-color.inc"
.import se_f_owner,se_gp_cache_slot,se_gp_cache_read,se_petscii_screen,se_v_cache_count
.importzp text_ptr,screen_ptr
.export se_tcb_two_check
F=TCB_FRAME
LOW=F+7
HIGH=F+8
ROW=F+9
END=F+10
ROLE=F+11
SCAN=F+12
COL=F+13
BAND=F+14
WORK=F+15
PREVIOUS=F+16
INDEX=F+17
XL=F+18
XH=F+19
ADV=F+20
ROLEMAP=F+24 ;16 physicalpixelrow owners:0white,2heading,FEtarget,FFempty
WHITE=TCB_VOTES
YELLOW=$85D0 ;80bytes, disjoint TCBBASENINE360
CHARS=$8200
STYLES=$8300
XMAP=$8640 ;324bytes ends8784, before protecteddiag8800
.segment "CODE"
se_tcb_two_check:
 lda se_f_owner
 cmp #4
 beq :+
 lda #$B2
 sec
 rts
: lda TCB_HEADER+GPH_VALID
 cmp #1
 jne miss
 lda F+TCB_ATTR
 cmp #$16
 jne miss
 lda F+TCB_TOP
 cmp #16
 jcc miss
 cmp #184
 jcs miss
 and #$F8
 sta LOW
 clc
 adc #16
 sta HIGH
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
 lda TCB_HEADER+GPH_MAGIC
 cmp #$47
 jne miss
 lda TCB_HEADER+GPH_VERSION
 cmp #3
 jne miss
 lda TCB_HEADER+GPH_CARET_ROW
 cmp F+TCB_ROW
 jne miss ;caret-free snapshot currentlybelongs to targetrecord
 lda TCB_HEADER+GPH_FOLD_VALID
 jne miss
 lda TCB_HEADER+GPH_PAN
 ora TCB_HEADER+GPH_PAN+1
 ora TCB_HEADER+GPH_PAN+2
 jne miss
 lda #0
 sta ROW
 ldx #79
@clear:
 sta WHITE,x
 sta YELLOW,x
 dex
 bpl @clear
 lda #16
 sta PREVIOUS
 lda #$FF
 ldx #15
@owners:
 sta ROLEMAP,x
 dex
 bpl @owners
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
 jcc miss
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
 jne miss
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
 lda GP_RECORD+GPR_KIND
 jne miss ;nativecode cannotshare target's partialphysicalbands
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
 lda GP_RECORD+GPR_BACKGROUND
 cmp #6
 jne miss
 lda GP_RECORD+GPR_RASTER_X
 ora GP_RECORD+GPR_RASTER_X+1
 jne miss
 lda GP_RECORD+GPR_TAIL_VALID
 cmp #1
 jne miss
 lda GP_RECORD+GPR_REASON
 cmp #1
 beq :+
 cmp #2
 jne miss
:
 ldx #2
@first:
 lda GP_RECORD+GPR_FIRST,x
 cmp GP_RECORD+GPR_START,x
 jne miss
 dex
 bpl @first
 ; Canonicalspan mustbecomplete and onebyteperliteralvisibleglyph.
 sec
 lda GP_RECORD+GPR_END
 sbc GP_RECORD+GPR_START
 sta WORK
 lda GP_RECORD+GPR_END+1
 sbc GP_RECORD+GPR_START+1
 sta XL
 lda GP_RECORD+GPR_END+2
 sbc GP_RECORD+GPR_START+2
 ora XL
 jne miss
 lda WORK
 cmp GP_RECORD+GPR_COUNT
 jne miss
 lda #<GPR_ROLES
 ldx #>GPR_ROLES
 jsr field
 lda #<TCB_ROLEBUF
 ldx #>TCB_ROLEBUF
 ldy GP_RECORD+GPR_COUNT
 jsr read
 jcs error
 lda TCB_ROLEBUF
 cmp #0
 beq :+
 cmp #2
 jne miss
: sta ROLE
 lda GP_RECORD+GPR_FLAGS
 beq @white
 cmp #1
 jne miss
 lda ROLE
 cmp #2
 jne miss
 beq @uniform
@white:
 lda ROLE
 jne miss
@uniform:
 ldy GP_RECORD+GPR_COUNT
@roles:
 dey
 lda TCB_ROLEBUF,y
 cmp ROLE
 jne miss
 tya
 bne @roles
 lda ROW
 cmp F+TCB_ROW
 bne :+
 lda ROLE
 jne miss
 lda GP_RECORD+GPR_TOP
 cmp F+TCB_TOP
 jne miss
:
 lda #<GPR_CHARS
 ldx #>GPR_CHARS
 jsr field
 lda #<CHARS
 ldx #>CHARS
 ldy GP_RECORD+GPR_COUNT
 jsr read
 jcs error
 lda ROLE
 beq :+
 lda CHARS
 cmp #$23
 jne miss ;uniform inverseheading only, no inventedinverseproseclass
:
 lda #<GPR_STYLES
 ldx #>GPR_STYLES
 jsr field
 lda #<STYLES
 ldx #>STYLES
 ldy GP_RECORD+GPR_COUNT
 jsr read
 jcs error
 lda #<GPR_X
 ldx #>GPR_X
 jsr field
 lda #<XMAP
 sta GP_IO_POINTER
 lda #>XMAP
 sta GP_IO_POINTER+1
 lda GP_RECORD+GPR_COUNT
 clc
 adc #1
 asl
 sta GP_IO_LENGTH
 lda #0
 rol
 sta GP_IO_LENGTH+1
 jsr se_gp_cache_read
 jcs error
 lda XMAP
 ora XMAP+1
 jne miss
 lda #<XMAP
 sta text_ptr
 lda #>XMAP
 sta text_ptr+1
 lda #0
 sta XL
 sta XH
 sta INDEX
@glyph:
 ldy INDEX
 lda STYLES,y
 cmp #4
 jcs miss
 and #1
 sta ADV
 lda STYLES,y
 and #2
 clc
 adc ADV
 sta ADV
 lda CHARS,y
 jsr se_petscii_screen
 tax
 lda widths,x
 clc
 adc ADV
 adc XL
 sta XL
 bcc :+
 inc XH
: ldy #2
 lda (text_ptr),y
 cmp XL
 jne miss
 iny
 lda (text_ptr),y
 cmp XH
 jne miss
 clc
 lda text_ptr
 adc #2
 sta text_ptr
 bcc :+
 inc text_ptr+1
: inc INDEX
 lda INDEX
 cmp GP_RECORD+GPR_COUNT
 bcc @glyph
 lda XH
 cmp #2
 jcs miss
 cmp #1
 bne :+
 lda XL
 cmp #64
 jcs miss
:
 lda XL
 cmp GP_RECORD+GPR_TAIL_X
 jne miss
 lda XH
 cmp GP_RECORD+GPR_TAIL_X+1
 jne miss
 lda GP_RECORD+GPR_TOP
 sta SCAN
@map:
 lda SCAN
 cmp LOW
 bcc @skip
 cmp HIGH
 bcs next
 sec
 sbc LOW
 tax
 lda ROW
 cmp F+TCB_ROW
 bne :+
 lda #$FE
 bne @mapped
: lda ROLE
@mapped:
 sta ROLEMAP,x
@skip:
 inc SCAN
 lda SCAN
 cmp END
 bcc @map
next:
 inc ROW
 lda ROW
 cmp TCB_HEADER+GPH_COUNT
 jcc row_loop
 ; Read actualcaret-free cachepixels onlyafter classifyingallowningrows.
 lda #0
 sta se_v_cache_count
 sta se_v_cache_count+1
 lda LOW
 lsr
 lsr
 lsr
 tax
 and #3
 .repeat 6
 asl
 .endrepeat
 sta GP_IO_OFFSET
 txa
 lsr
 lsr
 clc
 adc #$B2
 stx WORK
 adc WORK
 sta GP_IO_OFFSET+1
 lda #0
 sta GP_IO_POINTER
 lda #$80
 sta GP_IO_POINTER+1
 lda #$80
 sta GP_IO_LENGTH
 lda #2
 sta GP_IO_LENGTH+1 ;640B, two complete VICtilebands
 jsr se_gp_cache_read
 jcs error
 lda #0
 sta SCAN
@scan:
 ldx SCAN
 lda ROLEMAP,x
 cmp #$FE
 beq @target
 sta ROLE
 ; VICtile-major sourceaddress for local16pixelrows in8000..827F.
 txa
 and #7
 sta text_ptr
 lda #$80
 sta text_ptr+1
 cpx #8
 bcc @colstart
 lda text_ptr
 ora #$40
 sta text_ptr
 inc text_ptr+1
 jmp @colstart
@target:
 lda #0
 sta text_ptr
 lda #$84
 sta text_ptr+1
 sec
 lda LOW
 clc
 adc SCAN
 sec
 sbc F+TCB_TOP
 tax
 beq @colstart
@targetline:
 clc
 lda text_ptr
 adc #40
 sta text_ptr
 bcc :+
 inc text_ptr+1
: dex
 bne @targetline
@colstart:
 lda F+TCB_FIRST
 sta COL
 ; Advancepointer to first affectedcolumn, native/VIC stride8 vs base stride1.
 tax
 beq @column
@start:
 lda SCAN
 tax
 lda ROLEMAP,x
 cmp #$FE
 bne :+
 lda #1
 bne @stride
: lda #8
@stride:
 clc
 adc text_ptr
 sta text_ptr
 bcc :+
 inc text_ptr+1
: dec COL
 bne @start
 lda F+TCB_FIRST
 sta COL
@column:
 ldy #0
 lda (text_ptr),y
 sta WORK
 ldx SCAN
 lda ROLEMAP,x
 cmp #$FF
 bne @count
 lda WORK
 jne miss ;unownedgap mustreallybeempty, neverinventaroleforstaleink
 beq @advance
@count:
 lda WORK
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
 lda SCAN
 cmp #8
 lda #0
 bcc :+
 lda #40
: clc
 adc COL
 tax
 ldy SCAN
 lda ROLEMAP,y
 cmp #2
 beq @yellow
 lda WORK
 clc
 adc WHITE,x
 sta WHITE,x
 jmp @advance
@yellow:
 lda WORK
 clc
 adc YELLOW,x
 sta YELLOW,x
@advance:
 ldx SCAN
 lda ROLEMAP,x
 cmp #$FE
 bne :+
 lda #1
 bne @stride2
: lda #8
@stride2:
 clc
 adc text_ptr
 sta text_ptr
 bcc :+
 inc text_ptr+1
: inc COL
 lda F+TCB_LAST
 cmp COL
 jcs @column
 inc SCAN
 lda SCAN
 cmp #16
 jcc @scan
 ; Exacttwo-role tie: headingrole2winsnonzeroequalvotes;0/0defaultswhite.
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
 lda #0
 sta BAND
@checkband:
 lda F+TCB_FIRST
 sta COL
@check:
 lda COL
 clc
 adc BAND
 tax
 lda YELLOW,x
 beq @whiteattr
 cmp WHITE,x
 bcc @whiteattr
 lda #$76
 bne @compare
@whiteattr:
 lda #$16
@compare:
 sta WORK
 txa
 tay
 lda (screen_ptr),y
 cmp WORK
 jne miss
 inc COL
 lda F+TCB_LAST
 cmp COL
 bcs @check
 lda BAND
 bne @done
 lda #40
 sta BAND
 bne @checkband
@done:
 lda #0
 clc
 rts
miss:
 lda #2
 clc
error:
 rts
field:
 pha
 txa
 pha
 lda ROW
 jsr se_gp_cache_slot
 pla
 tax
 pla
 clc
 adc GP_IO_OFFSET
 sta GP_IO_OFFSET
 txa
 adc GP_IO_OFFSET+1
 sta GP_IO_OFFSET+1
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
widths:.incbin "assets/fonts/generated/bsw9-widths.bin"
