.setcpu "6502"
.import _d64_cfg_input,_d64_path_source,_d64_path_output
.importzp ptr1,ptr2,ptr3,tmp1,tmp2,tmp3,tmp4
.export _d64_rebase_paths
.segment "RI_CODE"
; CONFIG-only. Caller validated full CFG, owns pointer + path scratch; no
; callbacks. Return AX=1/0, C scratch/ZP disposable, hardware stack balanced.
; ptr1=oldhome,ptr2=currentfield,ptr3=temporarypath. canonical nonroot oldhome.
_d64_rebase_paths:
 lda _d64_cfg_input
 clc
 adc #8
 sta ptr1
 lda _d64_cfg_input+1
 adc #0
 sta ptr1+1
 ldy #0
@oldlen:
 lda (ptr1),y
 beq @oldend
 iny
 bpl @oldlen
@bad:
 lda #0
 tax
 rts
@oldend:
 cpy #2
 bcc @bad
 sty tmp1
 ldy #0
@newlen:
 lda _d64_path_source,y
 beq @newend
 iny
 bpl @newlen
 bne @bad
@newend:
 sty tmp2
 lda #3
 sta tmp4
 lda ptr1
 clc
 adc #128
 sta ptr2
 lda ptr1+1
 adc #0
 sta ptr2+1
@field:
 ldy #0
@prefix:
 cpy tmp1
 beq @boundary
 lda (ptr1),y
 jsr fold
 sta tmp3
 lda (ptr2),y
 jsr fold
 cmp tmp3
 bne @next
 iny
 bne @prefix
@boundary:
 lda (ptr2),y
 cmp #'/'
 bne @next
 ; Find exact suffixlen while bounded by canonical validated128 field.
@tail:
 lda (ptr2),y
 beq @length
 iny
 bpl @tail
 bmi @bad
@length:
 tya
 sec
 sbc tmp1
 clc
 adc tmp2
 bmi @bad
 ; compose full zero padded path; copy newprefix then suffix+terminator.
 ldy #127
 lda #0
@zero:
 sta _d64_path_output,y
 dey
 bpl @zero
 ldy #0
@newprefix:
 cpy tmp2
 beq @suffix
 lda _d64_path_source,y
 sta _d64_path_output,y
 iny
 bne @newprefix
@suffix:
 ldx tmp2
 ldy tmp1
@copytail:
 lda (ptr2),y
 sta _d64_path_output,x
 beq @write
 iny
 inx
 bne @copytail
@write:
 ldy #127
@writebyte:
 lda _d64_path_output,y
 sta (ptr2),y
 dey
 bpl @writebyte
@next:
 dec tmp4
 beq @done
 lda ptr2
 clc
 adc #128
 sta ptr2
 bcc @field
 inc ptr2+1
 jmp @field
@done:
 lda #1
 ldx #0
 rts
fold:
 cmp #'A'
 bcc @ret
 cmp #'Z'+1
 bcs @ret
 ora #32
@ret:rts

.import popax
.export _cg_same_path
; cc65 fastcall two pointers: right=AX,left=software stack. Pop exactly2;
; no frames survive. Only ASCII letters fold, terminator included/bounded128.
_cg_same_path:
 sta ptr2
 stx ptr2+1
 jsr popax
 sta ptr1
 stx ptr1+1
 ldy #0
@byte:
 lda (ptr1),y
 jsr fold
 sta tmp1
 lda (ptr2),y
 jsr fold
 cmp tmp1
 bne @different
 cmp #0
 beq @same
 iny
 bpl @byte
@different:
 lda #0
 tax
 rts
@same:
 lda #1
 ldx #0
 rts
