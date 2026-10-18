.setcpu "6502"
.macpack longbranch
.include "host_clock.inc"
.import dos64_uci_init,dos64_uci_command,dos64_uci_timeout,dos64_uci_recovery_timeout
.import dos64_files_init,dos64_files_path_len,dos64_files_handle
.import dos64_files_state,dos64_files_error,dos64_uci_error,dos64_reu_request
.import dos64_host_clock_claim,dos64_host_clock_init,dos64_host_clock_status
.import dos64_elapsed_poll,dos64_elapsed_now
.import dos64_restore_cold_init,dos64_restore_cold_start,dos64_restore_cold_poll
.import dos64_restore_state,dos64_restore_error,dos64_restore_cleanup_error
.import dos64_restore_now,dos64_restore_expected_crc,dos64_restore_crc,dos64_restore_phase
.import dos64_restore_sectors,dos64_restore_elapsed
.export restore_entry,restore_idle,restore_config,restore_config_end,fixture_return
.segment "LOADADDR"
 .word $0801
.segment "BASIC"
 .word $080b,10
 .byte $9e
 .asciiz "2061"
 .word 0
.segment "CODE"
restore_entry:
 ldx #3
@magic:
 lda restore_config,x
 cmp restore_magic,x
 jne restore_idle
 dex
 bpl @magic
 lda restore_config+4
 cmp #$a5
 jne restore_idle
 lda restore_config+5
 cmp #2
 jcc restore_idle
 cmp #129
 jcs restore_idle
 tax
 dex
 lda restore_config+10,x
 jne restore_idle
 dex
@path:
 lda restore_config+10,x
 jeq restore_idle
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
 lda #<restore_nmi
 sta $fffa
 lda #>restore_nmi
 sta $fffb
 lda #$7f
 sta $dd0d
 lda $dd0d
 lda #$35
 sta $01
 lda #0
 ldx #31
@clear:
 sta $6000,x
 dex
 bpl @clear
 lda #'D'
 sta $6000
 lda #'R'
 sta $6001
 lda #'F'
 sta $6002
 lda #'1'
 sta $6003
 lda #2
 sta $6008                         ; prior remote file ownership unknown
 lda #1
 sta $6004
 lda #HC_OWNED
 sta dos64_host_clock_claim
 jsr dos64_host_clock_init
 jcs restore_clock_failed
 ldx #0
@clock:
 jsr dos64_elapsed_poll
 bcc @clock_ready
 lda dos64_host_clock_status
 cmp #HC_ERR_SAMPLE
 jne restore_clock_failed
 dex
 bne @clock
 jmp restore_clock_failed
@clock_ready:
 jsr dos64_uci_init
 jsr dos64_files_init
 jsr dos64_restore_cold_init
 lda #0
 sta dos64_uci_timeout
 sta dos64_uci_recovery_timeout
 lda #4
 sta dos64_uci_timeout+1
 lda #$80
 sta dos64_uci_recovery_timeout
 lda restore_config+5
 sta dos64_files_path_len
 tax
 dex
@copy:
 lda restore_config+10,x
 sta dos64_uci_command+3,x
 dex
 bpl @copy
 ldx #3
@crc:
 lda restore_config+6,x
 sta dos64_restore_expected_crc,x
 dex
 bpl @crc
 jsr restore_clock_copy
 jsr dos64_restore_cold_start
 jcs restore_engine_failed
 lda #2
 sta $6004
restore_loop:
 jsr dos64_elapsed_poll
 bcc @tick
 lda dos64_host_clock_status
 cmp #HC_ERR_SAMPLE
 beq restore_loop
 jmp restore_clock_failed
@tick:
 jsr restore_clock_copy
 jsr dos64_restore_cold_poll
 jsr restore_publish
 lda dos64_restore_state
 cmp #1
 beq restore_loop
 cmp #2
 bne restore_engine_failed
 lda #$a5
 sta $6004
 jmp restore_idle
restore_engine_failed:
 lda dos64_restore_error
 sta $6005
 lda #$e1
 sta $6004
 jmp restore_idle
restore_clock_failed:
 lda #$20
 sta $6005
 lda dos64_host_clock_status
 sta $6006
 lda #$e1
 sta $6004
restore_idle:
 jmp restore_idle
fixture_return:
 nop
restore_nmi:
 rti
restore_clock_copy:
 lda dos64_elapsed_now
 sta dos64_restore_now
 lda dos64_elapsed_now+1
 sta dos64_restore_now+1
 rts
restore_publish:
 lda dos64_restore_phase
 sta $6007
 lda dos64_files_handle
 sta $6008
 lda dos64_restore_cleanup_error
 sta $6009
 lda dos64_files_error
 sta $600a
 lda dos64_uci_error
 sta $600b
 ldx #3
@longs:
 lda dos64_restore_expected_crc,x
 sta $6010,x
 lda dos64_restore_crc,x
 sta $6014,x
 lda dos64_restore_elapsed,x
 sta $6018,x
 dex
 bpl @longs
 lda dos64_restore_sectors
 sta $601c
 lda dos64_restore_sectors+1
 sta $601d
 rts
.segment "RODATA"
; Config magicDRF1, enabled, pathLenincludingNUL, CRC32LE, ASCIIpath128.
; Read-only source file, UCI target1/baseDF1C, exact4MiB REU000000..3FFFFF.
restore_magic:
 .byte "DRF1"
restore_config:
 .byte "DRF1",0,0
 .dword 0
 .res 128,0
restore_config_end:
