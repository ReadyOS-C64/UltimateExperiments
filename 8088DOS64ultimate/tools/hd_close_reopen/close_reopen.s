.setcpu "6502"
.macpack longbranch
.include "files.inc"
.include "host_clock.inc"
.import dos64_uci_init,dos64_uci_command,dos64_uci_data,dos64_uci_error
.import dos64_uci_timeout,dos64_uci_recovery_timeout
.import dos64_files_init,dos64_files_start,dos64_files_poll
.import dos64_files_state,dos64_files_error,dos64_files_now,dos64_files_op,dos64_files_handle,dos64_files_target,dos64_files_owned_target
.import dos64_files_mode,dos64_files_path_len,dos64_files_count,dos64_files_offset,dos64_files_actual
.import dos64_host_clock_claim,dos64_host_clock_init,dos64_host_clock_status
.import dos64_elapsed_poll,dos64_elapsed_now
.export helper_entry,helper_idle,helper_ready,helper_config,helper_config_end,helper_read_done,fixture_return
M=$6000
.segment "LOADADDR"
.word $0801
.segment "BASIC"
.word $080b,10
.byte $9e
.asciiz "2061"
.word 0
.segment "CODE"
helper_entry:
 lda helper_config+4
 cmp #$a5
 jne helper_idle
 ldx #3
@magic:
 lda helper_config,x
 cmp helper_magic,x
 jne helper_idle
 dex
 bpl @magic
 lda helper_config+5
 cmp #2
 jcc helper_idle
 cmp #129
 jcs helper_idle
 tax
 dex
 lda helper_config+6,x
 jne helper_idle
 dex
@path:
 lda helper_config+6,x
 jeq helper_idle
 dex
 bpl @path
 sei
 cld
 ldx #$ff
 txs
 lda #$2f
 sta $00
 lda #$37
 sta $01
 lda #<helper_nmi
 sta $fffa
 lda #>helper_nmi
 sta $fffb
 lda #$7f
 sta $dd0d
 lda $dd0d
 lda #$35
 sta $01
 lda #0
 ldx #31
@clear:
 sta M,x
 dex
 bpl @clear
 ldx #3
@publish:
 lda helper_magic,x
 sta M,x
 dex
 bpl @publish
 lda #$47
 sta M+4
 lda #HC_OWNED
 sta dos64_host_clock_claim
 jsr dos64_host_clock_init
 jcs helper_clock_error
 jsr dos64_uci_init
 jsr dos64_files_init
 lda #0
 sta dos64_uci_timeout
 sta dos64_uci_recovery_timeout
 lda #4
 sta dos64_uci_timeout+1
 lda #$80
 sta dos64_uci_recovery_timeout
 lda #2
 sta dos64_files_target
 sta dos64_files_owned_target
 sta dos64_files_handle
 lda #FILES_CLOSE
 sta dos64_files_op
 lda #1
 sta M+7
 jsr helper_transaction
 jcs helper_fail
 lda #$a5
 sta M+19
 lda #1
 sta dos64_files_mode
 lda helper_config+5
 sta dos64_files_path_len
 tax
 dex
@copy:
 lda helper_config+6,x
 sta dos64_uci_command+3,x
 dex
 bpl @copy
 lda #FILES_OPEN
 sta dos64_files_op
 lda #2
 sta M+7
 jsr helper_transaction
 jcs helper_fail
 lda #$a5
 sta M+20
 lda #FILES_INFO
 sta dos64_files_op
 lda #3
 sta M+7
 jsr helper_transaction
 jcs helper_fail
 lda dos64_uci_data
 ora dos64_uci_data+1
 jne helper_info_error
 lda dos64_uci_data+2
 cmp #$40
 jne helper_info_error
 lda dos64_uci_data+3
 cmp #1
 jne helper_info_error
 ldx #75
@info:
 lda dos64_uci_data,x
 sta $6100,x
 dex
 bpl @info
 lda dos64_files_actual
 sta M+28
 lda dos64_files_handle
 sta M+8
 lda $00
 sta M+23
 lda $01
 sta M+24
 php
 pla
 sta M+25
 lda #$11
 sta M+4
helper_ready:
 lda M+4
 cmp #$47
 bne helper_ready
 lda M+10
 cmp #2
 jeq helper_finish
 cmp #1
 jne helper_bounds_error
 lda M+12
 cmp #2
 jcs @max_count
 ora M+11
 jeq helper_bounds_error
 jmp @offset
@max_count:
 cmp #2
 jne helper_bounds_error
 lda M+11
 jne helper_bounds_error
@offset:
 lda M+16
 cmp #1
 jcc @valid_offset
 jne helper_bounds_error
 lda M+15
 cmp #$40
 jcc @valid_offset
 jne helper_bounds_error
 lda M+14
 ora M+13
 jne helper_bounds_error
@valid_offset:
 ldx #3
@offset_copy:
 lda M+13,x
 sta dos64_files_offset,x
 dex
 bpl @offset_copy
 lda #FILES_SEEK
 sta dos64_files_op
 lda #4
 sta M+7
 jsr helper_transaction
 jcs helper_fail
 lda M+11
 sta dos64_files_count
 lda M+12
 sta dos64_files_count+1
 lda #FILES_READ
 sta dos64_files_op
 lda #5
 sta M+7
 jsr helper_transaction
 jcs helper_fail
 lda dos64_files_actual
 sta M+17
 lda dos64_files_actual+1
 sta M+18
 ldx #0
@data:
 lda dos64_uci_data,x
 sta $6200,x
 lda dos64_uci_data+256,x
 sta $6300,x
 inx
 bne @data
 inc M+21
 bne :+
 inc M+22
: lda dos64_files_handle
 sta M+8
 lda #$a5
 sta M+4
helper_read_done:
 jmp helper_ready
helper_finish:
 lda #FILES_CLOSE
 sta dos64_files_op
 lda #6
 sta M+7
 jsr helper_transaction
 jcs helper_fail
 lda dos64_files_handle
 sta M+8
 lda #$a5
 sta M+31
 sta M+4
 jmp helper_idle
helper_bounds_error:
 lda #$23
 bne helper_fail_a
helper_info_error:
 lda #$24
 bne helper_fail_a
helper_clock_error:
 lda #$20
 bne helper_fail_a
helper_fail:
 lda #$21
helper_fail_a:
 sta M+5
 lda dos64_files_error
 sta M+26
 lda dos64_uci_error
 sta M+27
 lda #FILES_CLOSE
 sta dos64_files_op
 jsr helper_transaction
 bcc @closed
 lda #$e1
 sta M+6
@closed:
 lda dos64_files_handle
 sta M+8
 lda #$e1
 sta M+4
helper_idle:
 jmp helper_idle
helper_nmi:
 rti
fixture_return:
 nop
helper_clock:
 jsr dos64_elapsed_poll
 bcc @copy
 lda dos64_host_clock_status
 cmp #HC_ERR_SAMPLE
 beq helper_clock
 sec
 rts
@copy:
 lda dos64_elapsed_now
 sta dos64_files_now
 lda dos64_elapsed_now+1
 sta dos64_files_now+1
 clc
 rts
helper_transaction:
 jsr helper_clock
 bcs @bad
 jsr dos64_files_start
 bcs @bad
@poll:
 jsr helper_clock
 bcs @bad
 jsr dos64_files_poll
 bcs @bad
 lda dos64_files_state
 cmp #FILES_BUSY
 beq @poll
 cmp #FILES_DONE
 bne @bad
 clc
 rts
@bad:
 sec
 rts
.segment "RODATA"
helper_magic:.byte "DHC1"
helper_config:.byte "DHC1",0,0
.res 128,0
helper_config_end:
