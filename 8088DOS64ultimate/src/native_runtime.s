.include "abi.inc"
.include "image_import.inc"
.include "host_clock.inc"
.include "host_input.inc"
.include "render_graphics.inc"
.macpack longbranch
.import dos64_mem_read
.importzp dos64_address
.import dos64_render_graphics_request, dos64_overlay_present_graphics_line
.import dos64_reu_transfer, dos64_reu_request
.import dos64_cold_open, dos64_cold_release
.import dos64_native_timer_step, dos64_native_timer_init, dos64_native_timer_resume
.import dos64_irq_callback_enabled, dos64_pit_poll_enabled, dos64_pit_poll_error, dos64_irq_result
.import dos64_cpu_init, dos64_cpu_step, dos64_cpu_status, dos64_cpu_opcode
.import dos64_cache_init, dos64_cache_limit, dos64_cache_flush, dos64_memory_error
.import dos64_disk_init, dos64_bios_init, dos64_bios_host_error
.import dos64_overlay_init, dos64_overlay_bootstrap, dos64_overlay_reu_mib, dos64_overlay_error
.import dos64_overlay_files_init, dos64_overlay_text_setup
.import dos64_overlay_input_init, dos64_overlay_input_poll, dos64_overlay_render_text_row
.import dos64_uci_init, dos64_uci_command, dos64_uci_timeout, dos64_uci_recovery_timeout
.import dos64_uci_base, dos64_files_target, dos64_files_path_len
.import dos64_import_init, dos64_import_start, dos64_import_poll
.import dos64_import_state, dos64_import_error, dos64_import_cleanup_error
.import dos64_import_now, dos64_import_timeout, dos64_import_expected_crc
.import dos64_host_clock_claim, dos64_host_clock_init, dos64_host_clock_status
.import dos64_elapsed_poll, dos64_elapsed_now
.import dos64_host_input_claim, dos64_host_input_status
.import dos64_render_text_request, dos64_keyboard_enqueue, dos64_keyboard_key, dos64_keyboard_status
.export dos64_native_start, dos64_native_cold_poll, dos64_native_tick, dos64_native_entry
.export dos64_native_config, dos64_native_config_end, dos64_native_diag, dos64_native_diag_end
.export dos64_native_started
.export dos64_native_idle
.export dos64_native_loop, dos64_native_nmi, dos64_native_cold_start
; Diagnostic ABI: stage,error,detail,command,ack,keyLE,heartbeatLE,render_row,
; last_scheduleLE,burst_remaining,initial_clock_attempts. Commands publish body
; first, command last; ack0 while accepted, then result (A5 success/E1 error).
; Stage1 initializing,2 import,3 BIOS,4 RUN,5 coherent PAUSED,E1 FAILED.
.segment "NATIVESTATE"
n_started: .byte 0
dos64_native_started = n_started
.segment "DEVICESTATE"
dos64_native_diag:
n_stage: .res 1
n_error: .res 1
n_detail: .res 1
n_command: .res 1
n_ack: .res 1
n_key: .res 2
n_heartbeat: .res 2
n_row: .res 1
n_last: .res 2
n_burst: .res 1
n_attempts: .res 1
n_far: .res 3
n_count: .res 2
dos64_native_diag_end:
n_present_mode: .res 1
.segment "CODE"
; Guard is resident and precedes any stack/CPU/cache/startup asset mutation.
; Second SYS is rejected by idle without changing phase or diagnostic evidence.
dos64_native_entry:
 lda dos64_cold_open
 cmp #$a5
 bne n_idle
 lda n_started
 bne n_idle
 sei
 cld
 ldx #$ff
 txs
 lda #$2f
 sta $00
 lda #$37
 sta $01
 jsr dos64_native_start
 bcs n_idle
dos64_native_loop:
 lda n_stage
 cmp #2
 bne :+
 jsr dos64_native_cold_poll
 jmp dos64_native_loop
: jsr dos64_native_tick
 jmp dos64_native_loop
dos64_native_idle:
n_idle:
 jmp n_idle
; Callable start rejects before mutations. Caller owns RAM+I/O, IRQ/NMI and D=0.
; Actual ENTRY retains KERNAL until vector/ICR takeover; rejected config idles37.
dos64_native_start:
 lda dos64_cold_open
 cmp #$a5
 bne n_reject
 lda n_started
 bne n_reject
 inc n_started
 jmp dos64_native_cold_start
n_reject:
 sec
 rts
dos64_native_cold_poll:
 lda dos64_cold_open
 cmp #$a5
 bne n_reject
 lda n_stage
 cmp #2
 bne n_reject
 jmp n_cold_poll_impl
dos64_native_nmi:
 rti
; A=error category, X=detail. Never touches cold state after display ownership.
n_fail:
 sta n_error
 stx n_detail
 lda #$e1
 sta n_ack
 sta n_stage
 lda #0
 sta n_command
 sec
 rts
.segment "DEVICECODE"
; Between CPU calls, no pending native callback or overlay owner.
dos64_native_tick:
 lda n_command
 jeq n_run
 lda #0
 sta n_ack
 lda n_command
 cmp #4
 jeq n_read_request
 cmp #1
 beq n_key_request
 cmp #2
 beq n_snapshot
 cmp #3
 bne n_bad_request
 lda n_stage
 cmp #5
 bne n_bad_request
 jsr n_timer_resume
 jcs n_resume_defer
 lda #4
 sta n_stage
 bne n_ack_ok
n_key_request:
 lda n_stage
 cmp #4
 bne n_bad_request
 lda n_key
 sta dos64_keyboard_key
 lda n_key+1
 sta dos64_keyboard_key+1
 jsr dos64_keyboard_enqueue
 bcs n_bad_request
 bcc n_ack_ok
n_snapshot:
 lda n_stage
 cmp #4
 beq :+
 cmp #5
 bne n_bad_request
: lda #0
 sta n_row
 lda #1
 sta dos64_render_text_request+1
@final_redraw:
 jsr n_present
 jcs n_render_error
 lda n_row
 bne @final_redraw
 jsr dos64_cache_flush
 bcs n_snapshot_error
 lda #5
 sta n_stage
n_ack_ok:
 lda #$a5
 bne n_ack_done
n_bad_request:
 lda #$e1
n_ack_done:
 sta n_ack
 lda #0
 sta n_command
n_run:
 lda n_stage
 cmp #4
 jne n_tick_return
 inc n_heartbeat
 bne :+
 inc n_heartbeat+1
: jsr dos64_elapsed_poll
 bcc n_clock_ok
 lda dos64_host_clock_status
 cmp #HC_ERR_SAMPLE
 beq n_tick_return
 tax
 lda #3
 jmp n_fail
n_snapshot_error:
 ldx dos64_memory_error
 lda #8
 jmp n_fail
n_clock_ok:
 sec
 lda dos64_elapsed_now
 sbc n_last
 tay
 lda dos64_elapsed_now+1
 sbc n_last+1
 bne n_schedule
 cpy #4
 bcc n_cpu
n_schedule:
 lda dos64_elapsed_now
 sta n_last
 lda dos64_elapsed_now+1
 sta n_last+1
 jsr dos64_overlay_input_poll
 bcc :+
 lda dos64_host_input_status
 cmp #HI_ERR_GHOST
 beq :+
 cmp #HI_ERR_QUEUE
 beq :+
 tax
 lda #6
 jmp n_fail
: lda dos64_elapsed_now
 asl                              ; expose phase bit7 as carry
 lda #0
 rol                              ; exact renderer boolean
 sta dos64_render_text_request+1
 jsr n_present_slice
 jcs n_render_error
n_cpu:
 jmp n_cpu_burst
n_tick_return:
 clc
 rts
n_cpu_error:
 ldx dos64_cpu_opcode
 lda #7
 jmp n_fail
n_render_error:
 ldx dos64_render_text_request+4
 lda #9
 jmp n_fail
n_display_error:
 ldx dos64_overlay_error
 lda #9
 jmp n_fail
; This resident continuation is reached by JMP from cold code. Its return
; address belongs to the resident caller. TEXT may overwrite all7000–7FFF.
.segment "CODE"
n_activate:
 jsr dos64_overlay_text_setup
 jcs n_display_error
 lda #$ff
 sta n_present_mode
 lda #0
 sta n_row
 lda #4
 sta n_stage
 clc
 rts
.segment "CODE"
n_present_slice:
 lda #8
 sta n_burst
@line:
 jsr n_present
 bcs @return
 lda n_present_mode
 cmp #4
 bcc @return
 dec n_burst
 bne @line
 clc
@return:
 rts
n_present:
 lda #$49
 sta dos64_address
 lda #4
 sta dos64_address+1
 lda #0
 sta dos64_address+2
 jsr dos64_mem_read
 bcs @cache
 cmp #7
 bcs @argument
 cmp n_present_mode
 beq @render
 sta n_present_mode
 lda #0
 sta n_row
 lda n_present_mode
 cmp #4
 bcs @render
 jsr dos64_overlay_text_setup
 bcs @argument
@render:
 lda n_present_mode
 cmp #4
 bcs @graphics
 lda n_row
 sta dos64_render_text_request
 jsr dos64_overlay_render_text_row
 bcs @return
 ldx #25
 bne @advance
@graphics:
 lda n_row
 sta dos64_render_graphics_request+RG_LINE
 jsr dos64_overlay_present_graphics_line
 bcc :+
 lda dos64_overlay_error
 bne @gfx_error
 lda dos64_render_graphics_request+RG_ERROR
@gfx_error:
 sta dos64_render_text_request+4
 sec
 rts
: ldx #200
@advance:
 inc n_row
 cpx n_row
 bne @ok
 lda #0
 sta n_row
@ok:
 clc
@return:
 rts
@cache:
 lda #RG_ERR_CACHE
 bne @error
@argument:
 lda #RG_ERR_ARGUMENT
@error:
 sta dos64_render_text_request+4
 sec
 rts
.segment "CODE"
n_cpu_burst:
 lda #16
 sta n_burst
@next:
 jsr dos64_native_timer_step
 bcs n_timer_cpu_error
 dec n_burst
 bne @next
 jmp n_tick_return
n_timer_cpu_error:
 lda dos64_irq_result
 cmp #2
 jcc n_cpu_error
 ldx dos64_irq_result
 lda #10
 jmp n_fail
n_resume_defer:
 lda n_stage
 cmp #$e1
 bne :+
 sec
 rts
: jmp n_tick_return
n_timer_resume:
 jsr dos64_native_timer_resume
 bcc @return
 lda dos64_host_clock_status
 cmp #HC_ERR_SAMPLE
 beq @defer
 ldx dos64_overlay_error
 lda #10
 jmp n_fail
@defer:
 sec
@return:
 rts
.segment "CODE"
n_read_request:
 lda n_far+2
 cmp #$10
 jcs n_bad_request
 lda n_stage
 cmp #5
 jne n_bad_request
 lda n_count
 ora n_count+1
 jeq n_bad_request
 lda n_count+1
 cmp #8
 bcc @size_ok
 jne n_bad_request
 lda n_count
 jne n_bad_request
@size_ok:
 clc
 lda n_far
 adc n_count
 tay
 lda n_far+1
 adc n_count+1
 tax
 lda n_far+2
 adc #0
 cmp #$10
 bcc @range_ok
 jne n_bad_request
 txa
 jne n_bad_request
 tya
 jne n_bad_request
@range_ok:
 lda #0
 sta dos64_reu_request
 lda #$c1
 sta dos64_reu_request+1
 ldx #4
@descriptor:
 lda n_far,x
 sta dos64_reu_request+2,x
 dex
 bpl @descriptor
 lda #1
 sta dos64_reu_request+7
 jsr dos64_reu_transfer
 jcs n_bad_request
 jmp n_ack_ok
.segment "COLDINIT"
dos64_native_cold_start:
 lda #0
 sta dos64_irq_callback_enabled
 sta dos64_pit_poll_enabled
 lda #0
 ldx #dos64_native_diag_end-dos64_native_diag-1
: sta dos64_native_diag,x
 dex
 bpl :-
 lda #1
 sta n_stage
 ldx #3
@magic:
 lda dos64_native_config,x
 cmp n_magic,x
 jne n_config_bad
 dex
 bpl @magic
 lda dos64_native_config+8
 cmp #$1c
 beq @normal_base
 cmp #$fc
 jne n_config_bad
 lda dos64_native_config+9
 cmp #$df
 jne n_config_bad
 beq @base_ok
@normal_base:
 lda dos64_native_config+9
 cmp #$df
 beq @base_ok
 cmp #$de
 jne n_config_bad
@base_ok:
 lda dos64_native_config+4
 cmp #$a5
 jne n_config_bad
 lda dos64_native_config+5
 cmp #4
 jcc n_config_bad
 cmp #17
 jcs n_config_bad
 lda dos64_native_config+6
 cmp #1
 jcc n_config_bad
 cmp #3
 jcs n_config_bad
 lda dos64_native_config+7
 cmp #2
 jcc n_config_bad
 cmp #129
 jcs n_config_bad
 tax
 dex
 lda dos64_native_config+14,x
 jne n_config_bad
 dex
@path_check:
 lda dos64_native_config+14,x
 jeq n_config_bad
 dex
 bpl @path_check
 ; Destructive machine takeover, prior machine state recovered by developer
 ; harness reset, never claimed resumable. Mask CIA interrupts before owning
 ; timer/NMI. RAM NMI vector points only at resident RTI.
 lda #<dos64_native_nmi
 sta $fffa
 lda #>dos64_native_nmi
 sta $fffb
 lda #$7f
 sta $dc0d
 sta $dd0d
 lda $dc0d
 lda $dd0d
 lda $dc0e
 and #$fd
 sta $dc0e
 lda $dc0f
 and #$fd
 sta $dc0f
 lda #$35
 sta $01
 lda #$a5
 sta dos64_host_clock_claim
 sta dos64_host_input_claim
 jsr dos64_host_clock_init
 jcs n_clock_bad
 lda #0
 sta n_attempts
@first_clock:
 jsr dos64_elapsed_poll
 bcc @clock_ready
 lda dos64_host_clock_status
 cmp #HC_ERR_SAMPLE
 jne n_clock_bad
 dec n_attempts
 bne @first_clock
 jmp n_clock_bad
@clock_ready:
 jsr dos64_overlay_init
 lda dos64_native_config+5
 sta dos64_overlay_reu_mib
 jsr dos64_overlay_bootstrap
 jcs n_overlay_bad
 ; INPUT source8000 is now committed before cache frames can overwrite it.
 jsr dos64_cpu_init
 lda #32
 sta dos64_cache_limit
 jsr dos64_cache_init
 jsr dos64_disk_init
 jsr dos64_uci_init
 lda dos64_native_config+8
 sta dos64_uci_base
 lda dos64_native_config+9
 sta dos64_uci_base+1
 lda #0
 sta dos64_uci_timeout
 lda #4
 sta dos64_uci_timeout+1
 lda #128
 sta dos64_uci_recovery_timeout
 lda #0
 sta dos64_uci_recovery_timeout+1
 jsr dos64_overlay_files_init
 jcs n_overlay_bad
 jsr dos64_import_init
 jcs n_import_bad
 lda dos64_native_config+6
 sta dos64_files_target
 lda dos64_native_config+7
 sta dos64_files_path_len
 tax
 dex
@copy_path:
 lda dos64_native_config+14,x
 sta dos64_uci_command+3,x
 dex
 bpl @copy_path
 ldx #3
@crc:
 lda dos64_native_config+10,x
 sta dos64_import_expected_crc,x
 dex
 bpl @crc
 lda #<30000
 sta dos64_import_timeout
 lda #>30000
 sta dos64_import_timeout+1
 jsr n_import_clock
 jsr dos64_import_start
 jcs n_import_bad
 lda #2
 sta n_stage
 clc
 rts
n_config_bad:
 ldx #0
 lda #1
 jmp n_fail
n_clock_bad:
 ldx dos64_host_clock_status
 lda #3
 jmp n_fail
n_overlay_bad:
 ldx dos64_overlay_error
 lda #2
 jmp n_fail
n_import_bad:
 ldx dos64_import_error
 lda #4
 jmp n_fail
n_import_clock:
 lda dos64_elapsed_now
 sta dos64_import_now
 lda dos64_elapsed_now+1
 sta dos64_import_now+1
 rts
; Called only while cold-open A5 and stage2. Resident loop owns phase dispatch.
n_cold_poll_impl:
 jsr dos64_elapsed_poll
 bcc :+
 lda dos64_host_clock_status
 cmp #HC_ERR_SAMPLE
 beq @defer
 jmp n_clock_bad
: jsr n_import_clock
 jsr dos64_import_poll
 jcs n_import_bad
 lda dos64_import_state
 cmp #IMPORT_BUSY
 beq @defer
 cmp #IMPORT_DONE
 jne n_import_bad
 lda #3
 sta n_stage
 jsr dos64_bios_init
 bcs @bios_bad
 jsr dos64_overlay_input_init
 jcs n_overlay_bad
 lda #0
 sta n_attempts
@timer_sample:
 jsr dos64_elapsed_poll
 bcc @timer_ready
 lda dos64_host_clock_status
 cmp #HC_ERR_SAMPLE
 bne @timer_clock_failed
 inc n_attempts
 bne @timer_sample
@timer_clock_failed:
 ldx dos64_host_clock_status
 lda #3
 jmp n_fail
@timer_ready:
 jsr dos64_native_timer_init
 bcc :+
 ldx dos64_overlay_error
 lda #10
 jmp n_fail
:
 jsr dos64_cold_release
 bcs @phase_bad
 jmp n_activate
@defer:
 clc
 rts
@bios_bad:
 ldx dos64_bios_host_error
 lda #5
 jmp n_fail
@phase_bad:
 ldx #0
 lda #10
 jmp n_fail
.segment "COLDRODATA"
; Externally patched only before launch, immutable throughout cold execution.
; Magic4,enable,REUMiB,target,pathLen,UCIbaseLE,expectedCRC32LE,path128.
; Default DISABLED; image source is never inferred from an unrelated user path.
n_magic: .byte "D64N"
dos64_native_config:
 .byte "D64N",0,4,1,0
 .word $df1c
 .dword $30770a37
 .res 128,0
dos64_native_config_end:
