; Narrow exact-extent bounded copy/restore worker. No general DMA changes.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "lifecycle/copy-entry.inc"
.import se_overlay_frame,se_reu_epoch,se_reu_retired
.import se_reu_map,se_reu_logical_owner,se_reu_physical_owner
.export entry,se_lc_copy_begin,se_lc_copy_step,se_lc_restore_begin,se_lc_copy_cancel
.segment "CODE"
binding:
 OVL_BINDING
entry:
 lda se_overlay_frame
 beq se_lc_copy_begin
 cmp #1
 jeq se_lc_copy_step
 cmp #2
 jeq se_lc_restore_begin
 cmp #3
 jeq se_lc_copy_cancel
 jmp bad
se_lc_copy_begin:
 jsr capability
 jcs done
 ; Admission precedes invalidating any previously prepared image.
 lda #0
 sta LC_PHASE
 ldx #63
@clear:sta LC_HEADER,x
 dex
 bpl @clear
 jsr header_request
 lda #$90
 jsr dma
 lda #0
 sta LC_PAGE
 lda #1
 sta LC_PHASE
 jmp pending
se_lc_copy_cancel:
 lda #0
 sta LC_PHASE
 clc
 rts
se_lc_copy_step:
 jsr capability
 jcs done
 lda LC_PHASE
 cmp #1
 jeq capture_page
 cmp #2
 jeq verify_page
 cmp #3
 jeq verify_page
 cmp #4
 jeq provider_page
 cmp #5
 jeq provider_page
 jmp bad
capture_page:
 jsr page_request
 lda #$90
 jsr dma
 inc LC_PAGE
 lda LC_PAGE
 cmp #189
 bcc pending
 lda #2
 sta LC_PHASE
 jsr verify_init
 jmp pending
verify_page:
 jsr page_request
 lda #<LC_BOUNCE
 sta LC_CPU
 lda #>LC_BOUNCE
 sta LC_CPU+1
 lda #$91
 jsr dma
 ldx #0
@byte:lda LC_BOUNCE,x
 jsr crc_byte
 inx
 cpx LC_AMOUNT
 bne @byte
 inc LC_PAGE
 lda LC_PAGE
 cmp #189
 bcc pending
 lda LC_PHASE
 cmp #2
 beq capture_verified
 lda LC_CRC
 cmp LC_HEADER+51
 jne crc_error
 lda LC_CRC+1
 cmp LC_HEADER+52
 jne crc_error
 lda #0
 sta LC_TABLE
 lda #4
 sta LC_PHASE
 jmp pending
capture_verified:
 lda LC_CRC
 sta LC_SAVECRC
 lda LC_CRC+1
 sta LC_SAVECRC+1
 lda #0
 sta LC_TABLE
 lda #5
 sta LC_PHASE
 jmp pending
pending:
 lda #1
 clc
done:rts
commit:
 ; CRC comes from saved REU bytes, never rereading already captured live RAM.
 ldx #63
@template:lda header_template,x
 sta LC_HEADER,x
 dex
 bpl @template
 ldx #15
@build:lda LC_BUILD,x
 sta LC_HEADER+8,x
 dex
 bpl @build
 lda LC_HANDLE
 sta LC_HEADER+24
 lda LC_PHYSICAL
 sta LC_HEADER+25
 lda LC_EPOCH
 sta LC_HEADER+26
 lda LC_EPOCH+1
 sta LC_HEADER+27
 lda LC_CRC
 sta LC_HEADER+51
 lda LC_CRC+1
 sta LC_HEADER+52
 jsr header_crc
 lda LC_CRC
 sta LC_HEADER+62
 lda LC_CRC+1
 sta LC_HEADER+63
 jsr header_request
 lda #$90
 jsr dma
 lda #0
 sta LC_PHASE
 clc
 rts
se_lc_restore_begin:
 jsr capability
 jcs done
 lda #0
 sta LC_PHASE
 jsr header_request
 lda #$91
 jsr dma
 jsr header_crc
 lda LC_CRC
 cmp LC_HEADER+62
 jne header_error
 lda LC_CRC+1
 cmp LC_HEADER+63
 jne header_error
 ldx #63
@fixed:
 ; Variable bytes8..27(binding/cap),51..52(payloadCRC),62..63(headerCRC).
 cpx #8
 bcc @compare
 cpx #28
 bcc @next
 cpx #51
 bcc @compare
 cpx #53
 bcc @next
 cpx #62
 bcs @next
@compare:
 lda LC_HEADER,x
 cmp header_template,x
 jne header_error
@next:dex
 bpl @fixed
 ldx #15
@build:lda LC_BUILD,x
 cmp LC_HEADER+8,x
 jne header_error
 dex
 bpl @build
 lda LC_HANDLE
 cmp LC_HEADER+24
 jne header_error
 lda LC_PHYSICAL
 cmp LC_HEADER+25
 jne header_error
 lda LC_EPOCH
 cmp LC_HEADER+26
 jne header_error
 lda LC_EPOCH+1
 cmp LC_HEADER+27
 jne header_error
 lda #3
 sta LC_PHASE
 jsr verify_init
 jmp pending
verify_init:
 lda #0
 sta LC_PAGE
 lda #$FF
 sta LC_CRC
 sta LC_CRC+1
 rts
; Exactly188 full pages:1000..C5FF +CA00..CFFF. Last24 isZP2..19.
page_request:
 lda #0
 sta LC_CPU
 sta LC_REU
 sta LC_AMOUNT
 lda LC_PAGE
 sta LC_REU+1
 cmp #$B6
 bcs @ca
 clc
 adc #$10
 sta LC_CPU+1
 jmp @full
@ca:
 cmp #$BC
 beq @zp
 clc
 adc #$14
 sta LC_CPU+1
@full:
 lda #0
 sta LC_CPU
 rts
@zp:
 lda #2
 sta LC_CPU
 lda #0
 sta LC_CPU+1
 lda #24
 sta LC_AMOUNT
 rts
header_request:
 lda #<LC_HEADER
 sta LC_CPU
 lda #>LC_HEADER
 sta LC_CPU+1
 lda #<LC_HEADER_REU
 sta LC_REU
 lda #>LC_HEADER_REU
 sta LC_REU+1
 lda #64
 sta LC_AMOUNT
 rts
dma:
 sta LC_CMD
.ifdef EDITOR_MANAGED_CODE
 lsr a ;validated commands90stash/91fetch; preserve original inLC_CMD
 bcs :+
 lda #0
 sta $CC4D ;directFCcapture also revokes memo across ownership recycling
:
.endif
 lda LC_CPU
 sta $DF02
 lda LC_CPU+1
 sta $DF03
 lda LC_REU
 sta $DF04
 lda LC_REU+1
 sta $DF05
 lda LC_PHYSICAL
 sta $DF06
 lda LC_AMOUNT
 sta $DF07
 lda #0
 sta $DF08
 sta $DF09
 sta $DF0A
 lda LC_AMOUNT
 bne :+
 inc $DF08
:
 lda LC_CMD
 sta $DF01
 rts
provider_page:
 ; Saved and LIVE tables must agree before the FIRST warm restore write.
 ldx LC_TABLE
 lda table_lo,x
 sta LC_REU
 lda table_hi,x
 sta LC_REU+1
 lda #<LC_BOUNCE
 sta LC_CPU
 lda #>LC_BOUNCE
 sta LC_CPU+1
 lda #0
 sta LC_AMOUNT
 lda #$91
 jsr dma
 lda LC_TABLE
 beq @map
 cmp #1
 beq @logical
 ldx #0
@physical:lda se_reu_physical_owner,x
 cmp LC_BOUNCE,x
 jne provider_error
 inx
 bne @physical
 beq @next
@logical:ldx #0
@l:lda se_reu_logical_owner,x
 cmp LC_BOUNCE,x
 jne provider_error
 inx
 bne @l
 beq @next
@map:ldx #0
@m:lda se_reu_map,x
 cmp LC_BOUNCE,x
 jne provider_error
 inx
 bne @m
@next:
 inc LC_TABLE
 lda LC_TABLE
 cmp #3
 jcc pending
 jsr capability
 jcs done
 lda LC_PHASE
 cmp #5
 bne @restore
 lda LC_SAVECRC
 sta LC_CRC
 lda LC_SAVECRC+1
 sta LC_CRC+1
 jmp commit
@restore:
 ; Copy a FRESH position-independent thunk. It does not return through R26.
 ldx #0
@thunk:lda thunk,x
 sta LC_THUNK,x
 inx
 cpx #thunk_end-thunk
 bne @thunk
 jmp LC_THUNK
capability:
 ; Fresh trusted worker must agree with the expected build, even when the
 ; old saved header and cold descriptor agree with each other on a stale build.
 ldx #15
@binding:
 lda LC_BUILD,x
 cmp binding,x
 jne header_error
 dex
 bpl @binding
 php
 pla
 and #$0C
 cmp #4
 jne bad
 lda $00
 and #7
 cmp #7
 jne bad
 lda $01
 and #7
 cmp #6
 jne bad
 lda se_reu_retired
 jne cap_error
 lda LC_EPOCH
 ora LC_EPOCH+1
 jeq cap_error
 lda LC_EPOCH
 cmp se_reu_epoch
 jne cap_error
 lda LC_EPOCH+1
 cmp se_reu_epoch+1
 jne cap_error
 ldx LC_HANDLE
 jeq cap_error
 lda se_reu_logical_owner,x
 cmp #LC_OWNER
 jne cap_error
 lda se_reu_map,x
 cmp LC_PHYSICAL
 jne cap_error
 tay
 jeq cap_error
 lda se_reu_physical_owner,y
 cmp #LC_OWNER
 jne cap_error
 lda #0
 clc
 rts
bad:lda #LC_E_STATE
 sec
 rts
cap_error:lda #LC_E_CAP
 sec
 rts
header_error:lda #LC_E_HEADER
 sec
 rts
crc_error:lda #LC_E_CRC
 sec
 rts
provider_error:lda #LC_E_PROVIDER
 sec
 rts
header_crc:
 lda #$FF
 sta LC_CRC
 sta LC_CRC+1
 ldx #0
@byte:lda LC_HEADER,x
 jsr crc_byte
 inx
 cpx #62
 bne @byte
 rts
crc_byte:
 eor LC_CRC+1
 tay
 lda LC_CRC
 eor crc_hi,y
 sta LC_CRC+1
 lda crc_lo,y
 sta LC_CRC
 rts
; Fixed extent DMA commands embedded in fresh low-memory code. NMI dispatch
; remains KERNAL-visible underCPU36. Caller must keep its known hooks valid.
.macro restore cpu,reu,length
 lda #<cpu
 sta $DF02
 lda #>cpu
 sta $DF03
 lda #<reu
 sta $DF04
 lda #>reu
 sta $DF05
 lda LC_PHYSICAL
 sta $DF06
 lda #<length
 sta $DF07
 lda #>length
 sta $DF08
 lda #0
 sta $DF09
 sta $DF0A
 lda #$91
 sta $DF01
.endmacro
thunk:
 sei
 cld
 ldx #$FF
 txs
 restore $1000,$0000,$B600
 restore $CA00,$B600,$0600
 restore $0002,$BC00,$0018
 jmp LC_RESUME
thunk_end:
.assert thunk_end-thunk<=256,error,"fresh restore thunk exceeds0900 page"
.segment "RODATA"
header_template:
.byte "LCA1",1,$A5,3,LC_OWNER
.res 20,0
.byte $18,$BC,0,0,0
.word $1000,$B600,$0000,$CA00,$0600,$B600,$0002,$0018,$BC00
.word 0
.res 9,0
.word 0
.assert *-header_template=64,error,"lifecycle header must be64B"
table_lo:.byte <(se_reu_map-$1000),<(se_reu_logical_owner-$1000),<(se_reu_physical_owner-$1000)
table_hi:.byte >(se_reu_map-$1000),>(se_reu_logical_owner-$1000),>(se_reu_physical_owner-$1000)
crc_lo:
.repeat 256,I
 V .set I<<8
 .repeat 8
  .if V&$8000
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
  .if V&$8000
   V .set ((V<<1)^$1021)&$FFFF
  .else
   V .set (V<<1)&$FFFF
  .endif
 .endrepeat
 .byte >V
.endrepeat
.assert se_reu_map>=$1000 && se_reu_map+256<=$C600,lderror,"provider table outside savedextent"
.assert se_reu_logical_owner>=$1000 && se_reu_logical_owner+256<=$C600,lderror,"provider table outside savedextent"
.assert se_reu_physical_owner>=$1000 && se_reu_physical_owner+256<=$C600,lderror,"provider table outside savedextent"
