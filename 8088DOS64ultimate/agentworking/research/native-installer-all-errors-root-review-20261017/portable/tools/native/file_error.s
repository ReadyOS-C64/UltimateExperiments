.setcpu "6502"
.ifndef DOS64_ALL_FILE_DIAGNOSTICS
DOS64_ALL_FILE_DIAGNOSTICS=0
.endif
.if DOS64_ALL_FILE_DIAGNOSTICS
.ifndef FD_SETUP
FD_SETUP=0
.endif
.importzp ptr1,ptr2,ptr3
.if FD_SETUP
.import dos64_reu_request,dos64_reu_transfer
.else
.import _rm_dma_c64,_rm_dma_reu,_rm_dma_length,_rm_dma_direction,_rm_dma
.assert _rm_dma_length=_rm_dma_c64+2,lderror,"CONFIG diagnostic DMA ABI length"
.assert _rm_dma_reu=_rm_dma_c64+4,lderror,"CONFIG diagnostic DMA ABI REU"
.assert _rm_dma_direction=_rm_dma_c64+8,lderror,"CONFIG diagnostic DMA ABI direction"
.endif
.import _c32_init,_c32_reset,_c32_update,_c32_finish,_c32_address,_c32_length,_c32_crc
.import bd_render
.import __FD_CODE_LOAD__,__FD_CODE_SIZE__
.if FD_SETUP=0
.import __FD_SAFE_LOAD__,__FD_SAFE_SIZE__,_ps_clear
.import cp_checksum_raw
.importzp cp_crc_src,cp_crc_left,cp_crc_raw
.endif
.export fd_stash,fd_show,fd_display,fd_park,_fd_expected
.export _fd_path,_fd_code,_fd_op,_fd_leaf,_fd_transport,_fd_closed,_fd_set_path,_fd_tail
.if FD_SETUP
.import _so_request
_fd_path=_so_request+7
.segment "HIGHBSS"
.else
.import _rm_request
_fd_path=_rm_request+5
.segment "BSS"
.endif
.exportzp _fd_origin
.segment "ZEROPAGE"
_fd_origin:.res 1
.if FD_SETUP
.segment "HIGHBSS"
.else
.segment "BSS"
.endif
_fd_code:.res 1
_fd_op:.res 1
_fd_leaf:.res 1
_fd_transport:.res 1
_fd_closed:.res 1
_fd_tail:.res 2

; Initial, load-only trusted strip; no BSS/C calls. Bank35/NMI already owned.
.segment "FD_STASH"
fd_stash:
 lda $df00
 ldx #8
@register:
 lda stash_request,x
 sta $df02,x
 dex
 bpl @register
 lda #$90
 sta $df01
.if FD_SETUP=0
 ldx #<(__FD_SAFE_SIZE__-1)
@safe:
 lda __FD_SAFE_LOAD__,x
 sta fd_fallback,x
 cmp fd_fallback,x
 bne @unsafe
 dex
 bpl @safe
 rts
@unsafe:
 jmp bd_render ; cold-only: B000 has not yet been retired by zerobss
.else
 rts
.endif
stash_request:
.word __FD_CODE_LOAD__
.byte 0,0,$0a
.word __FD_CODE_SIZE__
.byte 0,0
.assert *-fd_stash<=$40,error,"diagnostic stash bounded64B"

.if FD_SETUP
.segment "FILE_DIAG"
.else
.segment "RI_CODE"
.endif
; Call only from the private first-cause site; all128 padded bytes copied.
_fd_set_path:
.if FD_SETUP
 ldy _fd_code
 bne @done
 sta ptr1
 stx ptr1+1
 lda #0
 sta _fd_tail
 sta _fd_tail+1
.else
 sta ptr1
 stx ptr1+1
 jsr fd_context_gate
 bne @done ; explicit ASM NZ contract, never inferred from C epilogue
.endif
 ldy #127
@copy:
 lda (ptr1),y
 sta _fd_path,y
 dey
 bpl @copy
@done:
 rts
.if FD_SETUP=0
.segment "CONFIG_HIGH"
; Loaded/CRC-verified before any CG/RI/RM/PUB call. Y/Z explicitly signal
; current no-error admission; STY/RTS preserve the flags from LDY.
fd_context_gate:
 ldy _fd_code
 bne :+
 sty _fd_tail
 sty _fd_tail+1
: rts
.endif
.if FD_SETUP
.segment "AUX_CODE"
.else
.segment "CODE"
.endif
; Terminal-only resident entry. All overlaid leaf/C frames have returned.
; No FILES/UCI calls, reset, context switch, retries or continuation authority.
fd_show:
.if FD_SETUP
 ldx #7
@request:
 lda fetch_request,x
 sta dos64_reu_request,x
 dex
 bpl @request
 jsr dos64_reu_transfer
 bcs @fallback
 jsr _c32_init
 cmp #1
 bne @fallback
.else
 ; CONFIG's RM DMA routine lives in the retired destination and is bounded
 ; to512B. Use the one physical REU directly from permanent owned code.
 lda $df00
 ldx #8
@request:
 lda fetch_request,x
 sta $df02,x
 dex
 bpl @request
 lda #$91
 sta $df01
 inx ; request loop left X=FF; now bounded256 status observations.
@poll:
 lda $df00
 and #$60
 bne @status
 dex
 bne @poll
 beq @fallback
@status:
 cmp #$40
 bne @fallback
 ; Reuse the trusted permanent bootstrap bit-CRC body. It initializes its
 ; private raw state for this fixed span; no retired RM code/table assumptions.
 lda #0
 sta cp_crc_src
 lda #$60
 sta cp_crc_src+1
 lda #<__FD_CODE_SIZE__
 sta cp_crc_left
 lda #>__FD_CODE_SIZE__
 sta cp_crc_left+1
 jsr cp_checksum_raw
.endif
.if FD_SETUP
 jsr _c32_reset
 lda #0
 sta _c32_address
 lda #$60
 sta _c32_address+1
 lda #<__FD_CODE_SIZE__
 sta _c32_length
 lda #>__FD_CODE_SIZE__
 sta _c32_length+1
 jsr _c32_update
 cmp #1
 bne @fallback
 jsr _c32_finish
 cmp #1
 bne @fallback
 .endif
 ldx #3
@crc:
 .if FD_SETUP
 lda _c32_crc,x
 .else
 lda cp_crc_raw,x
 .endif
 cmp _fd_expected,x
 bne @fallback
 dex
 bpl @crc
 jmp fd_display
@fallback:
.if FD_SETUP
 lda _fd_origin
 jmp bd_render
.else
 jmp fd_fallback
.endif
.if FD_SETUP
.segment "AUX_RO"
.else
.segment "RODATA"
.endif
fetch_request:
.if FD_SETUP
.word $6000
.byte 0,0,$0a
.word __FD_CODE_SIZE__
.byte 1
.else
.word $6000
.byte 0,0,$0a
.word __FD_CODE_SIZE__
.byte 0,0
.endif
.if FD_SETUP=0
.segment "CONFIG_HRO"
.endif
_fd_expected:.byte $12,$34,$56,$78

.if FD_SETUP=0
.segment "FD_SAFE"
fd_fallback:
 jsr _ps_clear
 ldx #safe_text_end-safe_text-1
@copy:
 lda safe_text,x
 sta $0400,x
 dex
 bpl @copy
@park:
 jmp @park
safe_text:
 ; Native mixed-case screen codes, no C strings or retired overlay references.
.byte 3,15,14,6,9,7,46,16,18,7,32,4,9,19,16,12,1,25,32,5,18,18,15,18,32,45,32,18,5,19,20,1,18,20,32,3,54,52
safe_text_end:
.assert *-fd_fallback<=$38,error,"permanent CONFIG fallback <=56B"
.assert fd_fallback=$bfc8,lderror,"permanent CONFIG fallback address"
.endif
.segment "FD_CODE"
fd_display:
 ldx #0
@clear:
 lda #32
 sta $0400,x
 sta $0500,x
 sta $0600,x
 lda #1
 sta $d800,x
 sta $d900,x
 sta $da00,x
 inx
 bne @clear
 ldx #231
@tail:
 lda #32
 sta $0700,x
 lda #1
 sta $db00,x
 dex
 cpx #$ff
 bne @tail
.macro LINE row,text
 lda #<($0400+40*row)
 sta ptr2
 lda #>($0400+40*row)
 sta ptr2+1
 lda #<text
 ldx #>text
 jsr line
.endmacro
 LINE 0,title
 LINE 2,path_title
 lda #<($0400+40*3)
 sta ptr2
 lda #>($0400+40*3)
 sta ptr2+1
 ldx #0
@path:
 lda _fd_path,x
 beq @path_done
 cmp #32
 bcc @escape
 cmp #127
 bcs @escape
 cmp #'%'
 beq @escape
 cmp #'\'
 beq @escape
 cmp #'^'
 bcc @plain
 cmp #'a'
 bcc @escape
 cmp #'z'+1
 bcs @escape
@plain:
 jsr put
 jmp @next
@escape:
 lda #'%'
 jsr put
 lda _fd_path,x
 jsr byte
@next:
 inx
 cpx #128
 bne @path
@path_done:
 lda _fd_tail
 ora _fd_tail+1
 beq @after_tail
 cpx #127
 bcs @after_tail
 lda #'/'
 jsr put
 inx
 lda _fd_tail
 sta ptr1
 lda _fd_tail+1
 sta ptr1+1
 ldy #0
@tail_name:
 lda (ptr1),y
 beq @after_tail
 jsr put
 iny
 inx
 cpx #127
 bcc @tail_name
@after_tail:
 cpx #0
 bne :+
 LINE 3,no_path
:
 LINE 14,op_title
 lda _fd_op
 bpl @normal_operation
 and #$7f
 cmp #2
 bne :+
 lda #1
 bne @normal_operation
: cmp #3
 bne :+
 lda #4
 bne @normal_operation
: cmp #4
 bne :+
 lda #9
 bne @normal_operation
: cmp #6
 bne :+
 lda #10
 bne @normal_operation
: cmp #7
 bne :+
 lda #2
 bne @normal_operation
: cmp #$21
 bne :+
 lda #3
 bne @normal_operation
: cmp #$22
 bne :+
 lda #8
 bne @normal_operation
: lda #0
@normal_operation:
 cmp #12
 bcc :+
 lda #0
: asl
 tay
 lda operations,y
 ldx operations+1,y
 jsr line
 LINE 16,cause_title
 lda #<($0400+16*40+12)
 sta ptr2
 lda _fd_code
 jsr byte
 lda #<($0400+16*40+21)
 sta ptr2
 lda _fd_leaf
 jsr byte
 lda #<($0400+16*40+28)
 sta ptr2
 lda _fd_transport
 jsr byte
 lda _fd_closed
 beq @unknown
 LINE 18,closed
 LINE 20,reload
 jmp @finish
@unknown:
 LINE 18,unknown
 LINE 20,restart
@finish:
 LINE 22,retain
fd_park:
 jmp fd_park
line:
 sta ptr1
 stx ptr1+1
 ldy #0
@loop:
 lda (ptr1),y
 beq @done
 jsr put
 iny
 cpy #40
 bne @loop
@done:rts
; Same mixed-case ROM glyphs as platform.c; ambiguous filenamebytes escape.
put:
 cmp #'a'
 bcc @punct
 cmp #'z'+1
 bcs @punct
 sec
 sbc #96
 jmp @store
@punct:
 cmp #'@'
 bne :+
 lda #0
 beq @store
: cmp #'['
 bne :+
 lda #27
 bne @store
: cmp #']'
 bne @store
 lda #29
@store:
 sty ptr3
 ldy #0
 sta (ptr2),y
 ldy ptr3
 inc ptr2
 bne :+
 inc ptr2+1
: rts
byte:
 pha
 lsr
 lsr
 lsr
 lsr
 jsr nibble
 pla
 and #15
nibble:
 cmp #10
 bcc :+
 adc #6
: adc #48
 jmp put
.if FD_SETUP
title:.asciiz "SETUP STOPPED - NO SUCCESS REPORTED"
.else
title:.asciiz "CONFIG STOPPED - KEEP OLD INSTALL"
.endif
path_title:.asciiz "FILE/PATH (%XX ESCAPES):"
no_path:.asciiz "BEFORE FILE SELECTION / STARTUP HANDLES"
op_title:.asciiz "OPERATION: "
cause_title:.asciiz "FIRST ERROR: 00 LEAF: 00 UCI: 00"
closed:.asciiz "FILES KNOWN CLOSED; NEW FILES MAY REMAIN"
unknown:.asciiz "FILE OWNERSHIP UNKNOWN"
reload:.asciiz "RELOAD PROGRAM; CHOOSE A NEW FOLDER"
restart:.asciiz "STOP. RESTART C64. DO NOT RETRY."
retain:.asciiz "KEEP ORIGINAL DISKS AND ALL NEW FILES."
operations:.word check,open,info,load,close,check,crc,build,write,read,seek,eof
check:.asciiz "CHECK"
open:.asciiz "OPEN"
info:.asciiz "INFO / EXACT SIZE"
load:.asciiz "LOAD / REU TRANSFER"
close:.asciiz "CLOSE"
crc:.asciiz "CRC / EXACT BYTES"
build:.asciiz "BUILD / INSTALL METADATA"
write:.asciiz "WRITE NEW FILE"
read:.asciiz "READ / COMPARE"
seek:.asciiz "SEEK"
eof:.asciiz "EOF"
.assert *-fd_display<=$1000,error,"terminal payload maximum4KiB"
.endif
