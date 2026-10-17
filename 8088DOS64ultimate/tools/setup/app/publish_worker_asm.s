.ifndef DOS64_SETUP_MNU_56K
DOS64_SETUP_MNU_56K=0
.endif
.setcpu "6502"
.macpack longbranch
.include "coordinator_internal.inc"
.ifdef DOS64_SETUP_COLD_INVENTORY
.if DOS64_SETUP_COLD_INVENTORY
.include "cold_assets.inc"
.import _rw_begin_existing,_rc_inventory_ready
.endif
.endif
.importzp ptr1,sreg
.import _rc_retained,_fw_internal,_so_publish_ticket,_so_capacity
.import _bc_files_closed,_ps_clock_poll,_ps_ticks,_c32_init
.import _sq_page,_sq_read,_sq_bytes
.import _rw_request,_rw_result,_rw_begin,_rw_poll,_rw_state,_rw_cancel,_rw_closed_quiet,_rw_rearm,_rw_expect_cfg
.import _pb_build,_pb_ready,_pb_cfg_identity,_pb_cfg_crc,_pb_start_crc,_pb_start_bytes
.import _ps_put,_ps_row,_ps_col,_ps_color,_ps_ascii
.import _pw_fail,_pw_service
.import _nf_store_read,_nf_sector,_c32_crc,_c32_address,_c32_length,_c32_update,pusheax,pushax
.export _pw_crc_stream
.export _pw_run,_pw_state,_pw_error,_pw_stage,_pw_closed_quiet
.export _pw_private_state,_pw_private_error,_pw_private_stage,_pw_ticket,_pw_last,_pw_address,_pw_bytes,_pw_crc
.segment "PUBBSS"
_pw_private_state:.res 1
_pw_private_error:.res 1
_pw_private_stage:.res 1
_pw_ticket:.res 2
_pw_last:.res 2
_pw_address:.res 4
_pw_bytes:.res 4
_pw_crc:.res 4
a_crc:.res 4
job_crc:.res 4
kind:.res 1
guard:.res 2
.segment "PUB_CODE"
_pw_state: lda _pw_private_state
 ldx #0
 rts
_pw_error: lda _pw_private_error
 ldx #0
 rts
_pw_stage: lda _pw_private_stage
 ldx #0
 rts
_pw_closed_quiet:
 lda _pw_private_state
 cmp #1
 beq no
 jmp _rw_closed_quiet
no: lda #0
 tax
 rts
input_fail: lda #1
 jmp _pw_fail
raw_fail: lda #5
 jmp _pw_fail
pb_fail: lda #7
 jmp _pw_fail
.macro MUST
 cmp #1
 jne no
.endmacro
_pw_run:
 lda _pw_private_state
 jne no
 lda #1
 sta _pw_private_state
 jsr _so_publish_ticket
 sta _pw_ticket
 stx _pw_ticket+1
 ora _pw_ticket+1
 jeq input_fail
 lda _fw_internal
 cmp #2
 jne input_fail
 lda _fw_internal+1
 jne input_fail
 lda _fw_internal+5
 cmp #1
 jne input_fail
 lda _rc_retained+181
 cmp #1
 jne input_fail
 lda _rc_retained+179
 cmp #31
 jne input_fail
 lda _rc_retained+180
 cmp #(RC_C_MASK|RC_B_MASK)
 jne input_fail
 jsr _bc_files_closed
 cmp #1
 jne input_fail
 jsr _ps_clock_poll
 cmp #1
 beq :+
 lda #2
 jmp _pw_fail
:
 lda _ps_ticks
 sta _pw_last
 lda _ps_ticks+1
 sta _pw_last+1
 jsr _c32_init
 cmp #1
 beq :+
 lda #4
 jmp _pw_fail
:
 jsr _pw_service
 MUST
 lda #0
 sta _sq_page
 jsr _sq_read
 cmp #0
 jne input_fail
 cpx #2
 jne input_fail
 lda _sq_bytes
 sta ptr1
 lda _sq_bytes+1
 sta ptr1+1
 ldy #8
 lda (ptr1),y
 cmp _rc_retained+128
 jne input_fail
 iny
 lda (ptr1),y
 cmp _rc_retained+129
 jne input_fail
 lda ptr1
 clc
 adc #32
 sta ptr1
 bcc :+
 inc ptr1+1
:
 ldy #0
@home:
 lda _rc_retained,y
 cmp (ptr1),y
 jne input_fail
 iny
 cpy #128
 bne @home
 lda #1
 sta _sq_page
 jsr _sq_read
 cmp #192
 jne input_fail
 cpx #0
 jne input_fail
 lda _sq_bytes
 sta ptr1
 lda _sq_bytes+1
 sta ptr1+1
 ldy #188
 ldx #0
@identity:
 lda (ptr1),y
 cmp _rc_retained+130,x
 jne input_fail
 iny
 inx
 cpx #4
 bne @identity
 ldy #161
 lda (ptr1),y
 asl a
 dey
 ora (ptr1),y
 cmp _rc_retained+178
 jne input_fail
 ; Exact privately captured B/C profile counts.
 ldx #3
@counts:
 lda _rc_retained+154+RC_B_PAIR*4,x
 cmp sizes,x
 jne input_fail
 lda _rc_retained+178
 and #1
 tay
 lda c_size0,x
 cpy #0
 beq :+
 lda c_size1,x
:
 cmp _rc_retained+154+RC_C_PAIR*4,x
 jne input_fail
 dex
 bpl @counts
 lda #1
 sta _pw_private_stage
 ldx #3
@a_source:
 lda a_source,x
 sta _pw_address,x
 lda sizes,x
 sta _pw_bytes,x
 dex
 bpl @a_source
 jsr _pw_crc_stream
 MUST
 ldx #3
@a_crc:
 lda _pw_crc,x
 sta a_crc,x
 dex
 bpl @a_crc
 lda #0
 jsr raw_file
 MUST
 ldx #3
@a_fact:
 lda sizes,x
 sta _rc_retained+154+RC_A_PAIR*4,x
 lda a_crc,x
 sta _rc_retained+154+(RC_A_PAIR+1)*4,x
 dex
 bpl @a_fact
 lda _rc_retained+180
 ora #RC_A_MASK
 sta _rc_retained+180
 jsr _rw_rearm
 cmp #1
 jne raw_fail
 lda #2
 sta _pw_private_stage
 ldx #3
@tpl:
 lda template_source,x
 sta _pw_address,x
 lda sizes+4,x
 sta _pw_bytes,x
 dex
 bpl @tpl
 jsr _pw_crc_stream
 MUST
 ldx #3
@tplcrc:
 lda _pw_crc,x
 cmp _rc_retained+134+3*4,x
 jne input_fail
 dex
 bpl @tplcrc
 ldx #3
@desc:
 lda descriptor_source,x
 sta _pw_address,x
 lda descriptor_size,x
 sta _pw_bytes,x
 dex
 bpl @desc
 jsr _pw_crc_stream
 MUST
 ldx #3
@desccrc:
 lda _pw_crc,x
 cmp _rc_retained+134+4*4,x
 jne input_fail
 dex
 bpl @desccrc
 jsr _pb_build
 cmp #1
 jne pb_fail
 jsr _pb_ready
 cmp #1
 jne pb_fail
 lda #3
 sta _pw_private_stage
 lda #1
 jsr raw_file
 MUST
 lda _rc_retained+180
 ora #RC_START_MASK
 sta _rc_retained+180
 jsr _rw_rearm
 cmp #1
 jne raw_fail
.ifdef DOS64_SETUP_COLD_INVENTORY
.if DOS64_SETUP_COLD_INVENTORY
 lda _rc_inventory_ready
 cmp #1
 jne input_fail
 lda #3
@existing:
 jsr raw_file
 MUST
 jsr _rw_rearm
 cmp #1
 jne raw_fail
 lda kind
 clc
 adc #1
 cmp #6
 bcc @existing
.endif
.endif
 lda #4
 sta _pw_private_stage
 jsr _pb_ready
 cmp #1
 jne pb_fail
 jsr _pb_cfg_identity
 jsr _rw_expect_cfg
 cmp #1
 jne raw_fail
 lda #2
 jsr raw_file
 MUST
 jsr _pw_service
 MUST
 jsr _bc_files_closed
 cmp #1
 jne input_fail
 jsr _rw_closed_quiet
 cmp #1
 jne raw_fail
 jsr _pb_ready
 cmp #1
 jne pb_fail
 jsr completion
 MUST
 lda _rc_retained+180
 cmp #(RC_C_MASK|RC_B_MASK|RC_A_MASK|RC_START_MASK)
 jne input_fail
 ora #RC_CFG_MASK
 sta _rc_retained+180
 lda #5
 sta _pw_private_stage
 lda #2
 sta _pw_private_state
 lda #1
 ldx #0
 rts
; Constructor snapshots fixed current private receipts. RAW captures its own
; immutable request. After private state refresh, compare to private job CRC
; and exact native geometry, never mutable caller request fields.
raw_file:
 sta kind
 lda #0
 sta guard
 sta guard+1
 ldx #0
@clear:
 sta _rw_request,x
 sta _rw_request+19,x
 inx
 bne @clear
 lda #$a5
 sta _rw_request
 jsr _so_capacity
 sta _rw_request+1
 stx _rw_request+2
 lda sreg
 sta _rw_request+3
 lda sreg+1
 sta _rw_request+4
 lda #<$2710
 sta _rw_request+5
 lda #>$2710
 sta _rw_request+6
 ldx kind
 lda sources_lo,x
 sta _rw_request+7
 lda sources_hi,x
 sta _rw_request+8
 lda sources_bank,x
 sta _rw_request+9
 txa
 asl a
 asl a
 tax
 ldy #0
@size:
 lda sizes,x
 sta _rw_request+11,y
 inx
 iny
 cpy #4
 bne @size
 lda kind
.ifdef DOS64_SETUP_COLD_INVENTORY
.if DOS64_SETUP_COLD_INVENTORY
 cmp #3
 bcc :+
 sec
 sbc #3
 asl a
 asl a
 tax
 lda extra_crc,x
 ldy extra_crc+2,x
 sty sreg
 ldy extra_crc+3,x
 sty sreg+1
 pha
 lda extra_crc+1,x
 tax
 pla
 jmp @savecrc
:
.endif
.endif
.ifdef DOS64_SETUP_COLD_INVENTORY
.if DOS64_SETUP_COLD_INVENTORY
 lda kind
.endif
.endif
 beq @acr
 cmp #1
 bne @cfgcrc
 jsr _pb_start_bytes
 cmp sizes+4
 jne input_fail
 cpx sizes+5
 jne input_fail
 lda sreg
 cmp sizes+6
 jne input_fail
 lda sreg+1
 cmp sizes+7
 jne input_fail
 jsr _pb_start_crc
 jmp @savecrc
@cfgcrc:
 jsr _pb_cfg_crc
 jmp @savecrc
@acr:
 lda a_crc
 ldx a_crc+1
 pha
 lda a_crc+2
 sta sreg
 lda a_crc+3
 sta sreg+1
 pla
@savecrc:
 sta job_crc
 sta _rw_request+15
 stx job_crc+1
 stx _rw_request+16
 lda sreg
 sta job_crc+2
 sta _rw_request+17
 lda sreg+1
 sta job_crc+3
 sta _rw_request+18
 ldy #0
@root:
 lda _rc_retained,y
 sta _rw_request+19,y
 sta _rw_request+147,y
 iny
 cpy #128
 bne @root
 ldy #0
@length:
 lda _rc_retained,y
 beq @suffix
 iny
 cpy #118
 jne @length
 jmp input_fail
@suffix:
 lda #'/'
 sta _rw_request+147,y
 iny
 ldx kind
 lda names_lo,x
 sta ptr1
 lda names_hi,x
 sta ptr1+1
 tya
 tax
 ldy #0
@name:
 lda (ptr1),y
 sta _rw_request+147,x
 beq @begin
 inx
 iny
 jmp @name
@begin:
.ifdef DOS64_SETUP_COLD_INVENTORY
.if DOS64_SETUP_COLD_INVENTORY
 lda kind
 cmp #3
 bcc :+
 jsr _rw_begin_existing
 jmp @begun
:
.endif
.endif
 jsr _rw_begin
@begun:
 cmp #1
 jne raw_fail
@poll:
 jsr _rw_poll
 jsr _rw_state
 cmp #1
 bne @done
 inc guard
 bne @poll
 inc guard+1
 bne @poll
 jsr _rw_cancel
 lda #6
 jmp _pw_fail
@done:
 cmp #2
 jne raw_fail
 jsr _rw_closed_quiet
 cmp #1
 jne raw_fail
 ldx kind
 txa
 asl a
 asl a
 tax
 ldy #0
@facts:
 lda sizes,x
.ifdef DOS64_SETUP_COLD_INVENTORY
.if DOS64_SETUP_COLD_INVENTORY
 pha
 lda kind
 cmp #3
 bcc @written
 lda _rw_result+8,y
 bne @existing_bad
 pla
 jmp @verified
@existing_bad:
 pla
 jmp raw_fail
@written:
 pla
.endif
.endif
 cmp _rw_result+8,y
 jne raw_fail
@verified:
 cmp _rw_result+12,y
 jne raw_fail
 lda job_crc,y
 cmp _rw_result+16,y
 jne raw_fail
 inx
 iny
 cpy #4
 bne @facts
 lda #1
 ldx #0
 rts
completion:
 ldx #31
@next:
 lda complete_text,x
 sta $0400+23*40,x
 lda #1
 sta $d800+23*40,x
 dex
 bpl @next
 jmp _pw_service
_pw_crc_stream:
 lda #$ff
 ldx #3
@init:
 sta _pw_crc,x
 dex
 bpl @init
@next:
 lda _pw_bytes
 ora _pw_bytes+1
 ora _pw_bytes+2
 ora _pw_bytes+3
 jeq @finish
 jsr _pw_service
 cmp #1
 jne no
 lda #0
 sta _c32_length
 lda #2
 sta _c32_length+1
 lda _pw_bytes+2
 ora _pw_bytes+3
 bne @read
 lda _pw_bytes+1
 cmp #2
 bcs @read
 sta _c32_length+1
 lda _pw_bytes
 sta _c32_length
@read:
 lda _pw_address+2
 sta sreg
 lda _pw_address+3
 sta sreg+1
 lda _pw_address
 ldx _pw_address+1
 jsr pusheax
 lda #<_nf_sector
 ldx #>_nf_sector
 jsr pushax
 lda _c32_length
 ldx _c32_length+1
 jsr _nf_store_read
 cmp _c32_length
 bne @bad
 cpx _c32_length+1
 bne @bad
 lda #<_nf_sector
 sta _c32_address
 lda #>_nf_sector
 sta _c32_address+1
 ldx #3
@crc:
 lda _pw_crc,x
 sta _c32_crc,x
 dex
 bpl @crc
 jsr _c32_update
 cmp #1
 bne @bad
 ldx #3
@crc_save:
 lda _c32_crc,x
 sta _pw_crc,x
 dex
 bpl @crc_save
 clc
 lda _pw_address
 adc _c32_length
 sta _pw_address
 lda _pw_address+1
 adc _c32_length+1
 sta _pw_address+1
 lda _pw_address+2
 adc #0
 sta _pw_address+2
 lda _pw_address+3
 adc #0
 sta _pw_address+3
 sec
 lda _pw_bytes
 sbc _c32_length
 sta _pw_bytes
 lda _pw_bytes+1
 sbc _c32_length+1
 sta _pw_bytes+1
 lda _pw_bytes+2
 sbc #0
 sta _pw_bytes+2
 lda _pw_bytes+3
 sbc #0
 sta _pw_bytes+3
 jmp @next
@bad:
 lda #4
 jmp _pw_fail
@finish:
 ldx #3
@xor:
 lda _pw_crc,x
 eor #$ff
 sta _pw_crc,x
 dex
 bpl @xor
 jmp _pw_service
.segment "PUB_RO"
a_source:.dword $200000
template_source:.dword $2e0000
descriptor_source:.dword $3fec00
descriptor_size:.dword 64
.ifndef DOS64_START_TEMPLATE_20K
DOS64_START_TEMPLATE_20K=0
.endif
.if DOS64_START_TEMPLATE_20K
sizes:.dword 368640,20480,576
.else
sizes:.dword 368640,18432,576
.endif
.ifdef DOS64_SETUP_COLD_INVENTORY
.if DOS64_SETUP_COLD_INVENTORY
.dword CI_MNU_BYTES,CI_RCV_BYTES,CI_RFW_BYTES
.endif
.endif
c_size0:.dword $200000
c_size1:.dword $1400000
.ifdef DOS64_SETUP_COLD_INVENTORY
.if DOS64_SETUP_COLD_INVENTORY
sources_lo:.byte $00,$00,$00,$00,$00,$00
.if DOS64_SETUP_MNU_56K
sources_hi:.byte $00,$80,$d0,$00,$e0,$00
sources_bank:.byte $20,$3f,$3f,$08,$08,$09
.else
sources_hi:.byte $00,$80,$d0,$00,$a0,$c0
sources_bank:.byte $20,$3f,$3f,$08,$08,$08
.endif
names_lo:.byte <name_a,<name_start,<name_cfg,<name_mnu,<name_rcv,<name_rfw
names_hi:.byte >name_a,>name_start,>name_cfg,>name_mnu,>name_rcv,>name_rfw
extra_crc:.dword CI_MNU_CRC,CI_RCV_CRC,CI_RFW_CRC
name_mnu:.asciiz "DOS64.MNU"
name_rcv:.asciiz "START.RCV"
name_rfw:.asciiz "START.RFW"
.else
sources_lo:.byte $00,$00,$00
sources_hi:.byte $00,$80,$d0
sources_bank:.byte $20,$3f,$3f
names_lo:.byte <name_a,<name_start,<name_cfg
names_hi:.byte >name_a,>name_start,>name_cfg
.endif
.else
sources_lo:.byte $00,$00,$00
sources_hi:.byte $00,$80,$d0
sources_bank:.byte $20,$3f,$3f
names_lo:.byte <name_a,<name_start,<name_cfg
names_hi:.byte >name_a,>name_start,>name_cfg
.endif
name_a:.asciiz "A.IMG"
name_start:.asciiz "START.PRG"
name_cfg:.asciiz "DOS64.CFG"
complete_text:.asciiz "INSTALL COMPLETE - RUN START.PRG"
.assert *-complete_text=33,error,"caption length"
