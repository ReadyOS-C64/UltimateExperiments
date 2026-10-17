.setcpu "6502"
.macpack longbranch
.export _c32_init,_c32_reset,_c32_update,_c32_finish
.export _c32_crc,_c32_address,_c32_length,_c32_error
.export c32_state_start,c32_state_end,c32_table0,c32_table1,c32_table2,c32_table3
.segment "ZEROPAGE"
c32_ptr: .res 2
.segment "RMBSS"
c32_state_start:
_c32_crc: .res 4
_c32_address: .res 2
_c32_length: .res 2
_c32_error: .res 1
c32_ready: .res 1
c32_remaining: .res 2
c32_state_end:
.segment "CRC_TABLES"
c32_table0: .res 256
c32_table1: .res 256
c32_table2: .res 256
c32_table3: .res 256
.assert <c32_table0=0,lderror,"CRC table must be page aligned"
.segment "RM_CODE"
_c32_init:
 php
 cld
 lda #0
 sta c32_ready
 sta _c32_error
 ldx #0
@entry:
 stx _c32_crc
 lda #0
 sta _c32_crc+1
 sta _c32_crc+2
 sta _c32_crc+3
 ldy #8
@bit:
 lsr _c32_crc+3
 ror _c32_crc+2
 ror _c32_crc+1
 ror _c32_crc
 bcc @next
 lda _c32_crc
 eor #$20
 sta _c32_crc
 lda _c32_crc+1
 eor #$83
 sta _c32_crc+1
 lda _c32_crc+2
 eor #$b8
 sta _c32_crc+2
 lda _c32_crc+3
 eor #$ed
 sta _c32_crc+3
@next:
 dey
 bne @bit
 lda _c32_crc
 sta c32_table0,x
 lda _c32_crc+1
 sta c32_table1,x
 lda _c32_crc+2
 sta c32_table2,x
 lda _c32_crc+3
 sta c32_table3,x
 inx
 bne @entry
 lda #$a5
 sta c32_ready
 jmp reset_body
_c32_reset:
 php
 cld
 jsr check_ready
 bcs failure
reset_body:
 lda #$ff
 sta _c32_crc
 sta _c32_crc+1
 sta _c32_crc+2
 sta _c32_crc+3
 jmp success
_c32_finish:
 php
 cld
 jsr check_ready
 bcs failure
 ldx #3
@xor:
 lda _c32_crc,x
 eor #$ff
 sta _c32_crc,x
 dex
 bpl @xor
 jmp success
check_ready:
 lda #0
 sta _c32_error
 lda c32_ready
 cmp #$a5
 beq @yes
 lda #1
 sta _c32_error
 sec
 rts
@yes:
 clc
 rts
failure:
 plp
 ldx #0
 lda #0
 rts
success:
 plp
 ldx #0
 lda #1
 rts
_c32_update:
 php
 cld
 jsr check_ready
 jcs failure
 lda _c32_length
 ora _c32_length+1
 jeq success
 lda _c32_length+1
 cmp #$80
 bcc @count_ok
 jne range_error
 lda _c32_length
 jne range_error
@count_ok:
 lda _c32_address+1
 cmp #2
 jcc range_error
 clc
 lda _c32_address
 adc _c32_length
 sta c32_ptr
 lda _c32_address+1
 adc _c32_length+1
 sta c32_ptr+1
 jcs range_error
 cmp #$d0
 bcc @metadata
 jne range_error
 lda c32_ptr
 jne range_error
@metadata:
 ; Source end<=state start OR source start>=state end.
 lda c32_ptr+1
 cmp #>c32_state_start
 bcc @valid
 bne @start
 lda c32_ptr
 cmp #<c32_state_start
 bcc @valid
 beq @valid
@start:
 lda _c32_address+1
 cmp #>c32_state_end
 jcc range_error
 bne @valid
 lda _c32_address
 cmp #<c32_state_end
 jcc range_error
@valid:
 lda _c32_address
 sta c32_ptr
 lda _c32_address+1
 sta c32_ptr+1
 lda _c32_length
 sta c32_remaining
 lda _c32_length+1
 sta c32_remaining+1
 lda c32_remaining
 beq :+
 inc c32_remaining+1
:
 ldy #0
@byte:
 lda (c32_ptr),y
 eor _c32_crc
 tax
 lda _c32_crc+1
 eor c32_table0,x
 sta _c32_crc
 lda _c32_crc+2
 eor c32_table1,x
 sta _c32_crc+1
 lda _c32_crc+3
 eor c32_table2,x
 sta _c32_crc+2
 lda c32_table3,x
 sta _c32_crc+3
 inc c32_ptr
 bne :+
 inc c32_ptr+1
:
 dec c32_remaining
 bne @byte
 dec c32_remaining+1
 bne @byte
 jmp success
range_error:
 lda #2
 sta _c32_error
 jmp failure
