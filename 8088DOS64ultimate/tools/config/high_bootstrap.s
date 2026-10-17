.setcpu "6502"
; CONFIG-exclusive cold bootstrap. No C/BSS references before source validation.
; Actual linked HIGH count excludes FFFA..FFFF and is serialized at9000.
.import __CONFIG_HIGH_LOAD__,__CONFIG_HIGH_RUN__,__CONFIG_HIGH_SIZE__,__CONFIG_HRO_SIZE__,__CONFIG_HRO_LOAD__,__CONFIG_HRO_RUN__
.export __CONFIG_HIGH_TOTAL__
__CONFIG_HIGH_TOTAL__=__CONFIG_HIGH_SIZE__+__CONFIG_HRO_SIZE__
.assert __CONFIG_HRO_LOAD__=__CONFIG_HIGH_LOAD__+__CONFIG_HIGH_SIZE__,lderror,"HIGH serialized contiguous"
.assert __CONFIG_HRO_RUN__=__CONFIG_HIGH_RUN__+__CONFIG_HIGH_SIZE__,lderror,"HIGH run contiguous"
.export cp_bootstrap,_cp_high_ready,_cp_high_expected,cp_copy_begin,cp_copy_done,cp_verified
.segment "ZEROPAGE"
src:.res 2
dst:.res 2
left:.res 2
crc:.res 4
bits:.res 1
.segment "DATA"
; Host source-only builder replaces this sentinel from actual HIGH bytes.
_cp_high_expected:.byte $12,$34,$56,$78
.segment "BSS"
_cp_high_ready:.res 1
.segment "CODE"
.assert __CONFIG_HIGH_LOAD__=$9000,lderror,"HIGH source fixed staging"
.assert __CONFIG_HIGH_RUN__=$e000,lderror,"HIGH run address"
.assert __CONFIG_HIGH_TOTAL__>0,lderror,"HIGH cannot be empty"
.assert __CONFIG_HIGH_TOTAL__<=$1ffa,lderror,"HIGH excludes vectors"
.assert __CONFIG_HIGH_LOAD__+__CONFIG_HIGH_TOTAL__<=$b000,lderror,"HIGH staging stays below STATE"
cp_bootstrap:
 lda #<__CONFIG_HIGH_LOAD__
 ldx #>__CONFIG_HIGH_LOAD__
 jsr checksum
 bcs failure
 lda #<__CONFIG_HIGH_LOAD__
 sta src
 lda #>__CONFIG_HIGH_LOAD__
 sta src+1
 lda #<__CONFIG_HIGH_RUN__
 sta dst
 lda #>__CONFIG_HIGH_RUN__
 sta dst+1
 jsr count
 ldy #0
cp_copy_begin:
 lda (src),y
 sta (dst),y
 jsr step
 bne cp_copy_begin
cp_copy_done:
 lda #<__CONFIG_HIGH_RUN__
 ldx #>__CONFIG_HIGH_RUN__
 jsr checksum
 bcs failure
 ; Independent exact full-byte equality, in addition to both CRC checks.
 lda #<__CONFIG_HIGH_LOAD__
 sta src
 lda #>__CONFIG_HIGH_LOAD__
 sta src+1
 lda #<__CONFIG_HIGH_RUN__
 sta dst
 lda #>__CONFIG_HIGH_RUN__
 sta dst+1
 jsr count
 ldy #0
@compare:
 lda (src),y
 cmp (dst),y
 bne failure
 jsr step
 bne @compare
cp_verified:
 clc
 rts
failure:
 sec
 rts
count:
 lda #<__CONFIG_HIGH_TOTAL__
 sta left
 lda #>__CONFIG_HIGH_TOTAL__
 sta left+1
 rts
step:
 inc src
 bne :+
 inc src+1
: inc dst
 bne :+
 inc dst+1
: lda left
 bne :+
 dec left+1
: dec left
 lda left
 ora left+1
 rts
checksum:
 sta src
 stx src+1
 jsr count
 lda #$ff
 ldx #3
: sta crc,x
 dex
 bpl :-
 ldy #0
@byte:
 lda (src),y
 eor crc
 sta crc
 lda #8
 sta bits
@bit:
 lsr crc+3
 ror crc+2
 ror crc+1
 ror crc
 bcc @next
 lda crc
 eor #$20
 sta crc
 lda crc+1
 eor #$83
 sta crc+1
 lda crc+2
 eor #$b8
 sta crc+2
 lda crc+3
 eor #$ed
 sta crc+3
@next:
 dec bits
 bne @bit
 ; Destination is deliberately irrelevant during CRC pass.
 jsr step
 bne @byte
 ldx #3
@check:
 lda crc,x
 eor #$ff
 cmp _cp_high_expected,x
 bne failure
 dex
 bpl @check
 clc
 rts
