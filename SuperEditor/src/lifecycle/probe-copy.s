.setcpu "6502"
.macpack longbranch
.include "lifecycle/probe-copy.inc"
.import se_reu_map,se_reu_logical_owner,se_reu_physical_owner
.import se_reu_epoch,se_reu_retired
.export se_lcp_capture,se_lcp_restore,se_lcp_thunk_size

physical=LCP_WORK
crc=LCP_WORK+1
offset=LCP_WORK+3
amount=LCP_WORK+5
saved_crc=LCP_WORK+6

; Direct DMA is deliberately LOCAL and exact-extent only. The ordinary DMA
; API's $4000..$BFFF whitelist is unchanged. No $C600..$C9FF transfer exists.
.macro transfer cpu,reu,length,command
 lda #<(cpu)
 sta $DF02
 lda #>(cpu)
 sta $DF03
 lda #<(reu)
 sta $DF04
 lda #>(reu)
 sta $DF05
 lda physical
 sta $DF06
 lda #<(length)
 sta $DF07
 lda #>(length)
 sta $DF08
 lda #0
 sta $DF09
 sta $DF0A
 lda #command
 sta $DF01
.endmacro

.segment "CODE"
se_lcp_capture:
 jsr preflight
 bcc :+
 rts
:
 ; Invalidate the previous header BEFORE any new payload mutation. A reset
 ; during capture can never advertise the former CRC as this new snapshot.
 ldx #63
 lda #0
@clear:sta LCP_HEADER,x
 dex
 bpl @clear
 transfer LCP_HEADER,LCP_HEADER_REU,64,$90
 transfer $1000,$0000,$B600,$90
 transfer $CA00,$B600,$0600,$90
 transfer $0002,$BC00,$0018,$90
 jsr payload_crc
 lda crc
 sta saved_crc
 lda crc+1
 sta saved_crc+1
 jsr capability
 bcc :+
 rts
:
 ldx #63
@header:lda template,x
 sta LCP_HEADER,x
 dex
 bpl @header
 ldx #21
@identity:lda LCP_DESCRIPTOR,x
 sta LCP_HEADER+8,x
 dex
 bpl @identity
 lda saved_crc
 sta LCP_HEADER+51
 lda saved_crc+1
 sta LCP_HEADER+52
 jsr header_crc
 lda crc
 sta LCP_HEADER+62
 lda crc+1
 sta LCP_HEADER+63
 transfer LCP_HEADER,LCP_HEADER_REU,64,$90
 lda #0
 clc
 rts

se_lcp_restore:
 jsr preflight
 bcc :+
 rts
:
 transfer LCP_HEADER,LCP_HEADER_REU,64,$91
 jsr header_crc
 lda crc
 cmp LCP_HEADER+62
 jne header_error
 lda crc+1
 cmp LCP_HEADER+63
 jne header_error
 ldx #7
@fixed1:lda template,x
 cmp LCP_HEADER,x
 jne header_error
 dex
 bpl @fixed1
 ldx #21
@identity:lda LCP_DESCRIPTOR,x
 cmp LCP_HEADER+8,x
 jne header_error
 dex
 bpl @identity
 ldx #30
@fixed2:lda template,x
 cmp LCP_HEADER,x
 jne header_error
 inx
 cpx #51
 bne @fixed2
 ldx #53
@fixed3:lda template,x
 cmp LCP_HEADER,x
 jne header_error
 inx
 cpx #62
 bne @fixed3
 jsr payload_crc
 lda crc
 cmp LCP_HEADER+51
 jne payload_error
 lda crc+1
 cmp LCP_HEADER+52
 jne payload_error
 ; Refuse a snapshot whose provider tables would replace ANY live allocation,
 ; even one unrelated to FC. CRC alone cannot establish current ownership.
 transfer LCP_BOUNCE,se_reu_map-$1000,256,$91
 ldx #0
@map:lda se_reu_map,x
 cmp LCP_BOUNCE,x
 jne provider_error
 inx
 bne @map
 transfer LCP_BOUNCE,se_reu_logical_owner-$1000,256,$91
 ldx #0
@logical:lda se_reu_logical_owner,x
 cmp LCP_BOUNCE,x
 jne provider_error
 inx
 bne @logical
 transfer LCP_BOUNCE,se_reu_physical_owner-$1000,256,$91
 ldx #0
@physical:lda se_reu_physical_owner,x
 cmp LCP_BOUNCE,x
 jne provider_error
 inx
 bne @physical
 jsr capability
 bcc :+
 rts
:
 ; All validation complete. This is the ONLY path to a warm restore write.
 ldx #0
@copy:lda thunk,x
 sta LCP_THUNK,x
 inx
 cpx #se_lcp_thunk_size
 bne @copy
 lda LCP_ENTRY
 sta LCP_THUNK+(thunk_entry-thunk)+1
 lda LCP_ENTRY+1
 sta LCP_THUNK+(thunk_entry-thunk)+2
 jmp LCP_THUNK

header_error:lda #LCP_E_HEADER
 sec
 rts
payload_error:lda #LCP_E_CRC
 sec
 rts
provider_error:lda #LCP_E_PROVIDER
 sec
 rts

; No scratch/REU mutation until input flags, mapping, and descriptor pass.
preflight:
 php
 pla
 and #$0C
 cmp #$04
 bne bad
 lda $00
 and #7
 cmp #7
 bne bad
 lda $01
 and #7
 cmp #5
 bne bad
 lda LCP_ENTRY+1
 cmp #$10
 bcc bad
 cmp #$40
 bcs bad
 ldx #31
@reserved:lda LCP_DESCRIPTOR,x
 bne bad
 dex
 cpx #21
 bne @reserved
 ; Expected build zero is not a valid frozen image identity.
 ldx #15
 lda #0
@build:ora LCP_BUILD,x
 dex
 bpl @build
 cmp #0
 beq bad
capability:
 lda se_reu_retired
 bne cap_bad
 lda LCP_EPOCH
 ora LCP_EPOCH+1
 beq cap_bad
 lda LCP_EPOCH
 cmp se_reu_epoch
 bne cap_bad
 lda LCP_EPOCH+1
 cmp se_reu_epoch+1
 bne cap_bad
 ldx LCP_LOGICAL
 beq cap_bad
 lda se_reu_logical_owner,x
 cmp #LCP_OWNER
 bne cap_bad
 ldy LCP_PHYSICAL
 beq cap_bad
 tya
 cmp se_reu_map,x
 bne cap_bad
 lda se_reu_physical_owner,y
 cmp #LCP_OWNER
 bne cap_bad
 sty physical
 clc
 rts
bad:lda #LCP_E_BAD
 sec
 rts
cap_bad:lda #LCP_E_CAP
 sec
 rts

payload_crc:
 jsr crc_init
 lda #0
 sta offset
 sta offset+1
@chunk:
 ; Fixed payload is 188 full pages plus24 bytes. No 65536/zero DMA length.
 lda #0
 sta amount
 lda offset+1
 cmp #$BC
 bne :+
 lda #$18
 sta amount
:
 jsr dynamic_read
 ldx #0
@byte:lda LCP_BOUNCE,x
 jsr crc_byte
 inx
 cpx amount
 bne @byte
 lda offset+1
 cmp #$BC
 beq @done
 inc offset+1
 jmp @chunk
@done:rts

dynamic_read:
 lda #0
 sta $DF02
 sta $DF04
 sta $DF08
 sta $DF09
 sta $DF0A
 lda #>LCP_BOUNCE
 sta $DF03
 lda offset+1
 sta $DF05
 lda physical
 sta $DF06
 lda amount
 bne @tail
 lda #1
 sta $DF08
 lda #0
@tail:sta $DF07
 lda #$91
 sta $DF01
 rts

header_crc:
 jsr crc_init
 ldx #0
@byte:lda LCP_HEADER,x
 jsr crc_byte
 inx
 cpx #62
 bne @byte
 rts
crc_init:lda #$FF
 sta crc
 sta crc+1
 rts
crc_byte:
 eor crc+1
 tay
 lda crc
 eor crc_hi,y
 sta crc+1
 lda crc_lo,y
 sta crc
 rts

; Immutable template -> copied COLD thunk. After first DMA A000/B000 and the
; entire resident are overwritten. No instruction/call/return depends on them.
thunk:
 sei
 cld
 ldx #$FF
 txs
 transfer $1000,$0000,$B600,$91
 transfer $CA00,$B600,$0600,$91
 transfer $0002,$BC00,$0018,$91
 lda #0
 clc
thunk_entry:jmp $FFFF
se_lcp_thunk_size=*-thunk
.assert se_lcp_thunk_size<256,error,"cold thunk capacity"

.segment "RODATA"
template:
.byte "LCP1",1,$A5,3,LCP_OWNER
.res 22,0
.byte $18,$BC,0
.word $1000,$B600,$0000,$CA00,$0600,$B600,$0002,$0018,$BC00
.word 0
.res 9,0
.word 0
.assert *-template=64,error,"LCP header size"
crc_lo:
.repeat 256,I
 V .set I<<8
 .repeat 8
  .if V & $8000
   V .set ((V<<1)^$1021)&$FFFF
  .else
   V .set (V<<1)&$FFFF
  .endif
 .endrepeat
 .byte <V
.endrepeat
crc_hi:
.repeat 256,I
 V .set I<<8
 .repeat 8
  .if V & $8000
   V .set ((V<<1)^$1021)&$FFFF
  .else
   V .set (V<<1)&$FFFF
  .endif
 .endrepeat
 .byte >V
.endrepeat
.assert se_reu_map>=$1000 && se_reu_map+256<=$C600,lderror,"map outside snapshot"
.assert se_reu_logical_owner>=$1000 && se_reu_logical_owner+256<=$C600,lderror,"owners outside snapshot"
.assert se_reu_physical_owner>=$1000 && se_reu_physical_owner+256<=$C600,lderror,"owners outside snapshot"
.assert se_reu_epoch>=$1000 && se_reu_epoch+2<=$C600,lderror,"epoch outside snapshot"
