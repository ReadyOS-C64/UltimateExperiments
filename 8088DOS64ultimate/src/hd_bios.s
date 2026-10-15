.setcpu "6502"
.macpack longbranch
.include "abi.inc"
.include "range.inc"
.include "reu.inc"
.include "files.inc"
.include "hd_cache.inc"
.import dos64_guest,dos64_bios_waiting,dos64_disk_host_error
.import dos64_cpu_value,dos64_mem_read,dos64_mem_write,dos64_memory_mode,dos64_physical
.importzp dos64_segment,dos64_offset,dos64_address,dos64_mem_value
.import dos64_range_request,dos64_range_copy,dos64_reu_request,dos64_reu_transfer
.import dos64_overlay_hd_init,dos64_overlay_hd_prepare,dos64_overlay_hd_advance,dos64_overlay_hd_chs_to_lba
.import dos64_overlay_files_start,dos64_overlay_files_poll
.import dos64_files_state,dos64_files_now,dos64_uci_command,dos64_uci_data
.import hd_state,hd_error,hd_request,hd_profile,hd_slots,hd_readonly,hd_uncertain
.import hd_lba,hd_count,hd_op,hd_ch,hd_cl,hd_dh
.import dos64_elapsed_now
.import dos64_native_timer_step,n_cpu_error,n_tick_return,n_burst,n_timer_cpu_error
.export hdb_native_burst
.export hdb_startup,hdb_mount,hdb_service,hdb_runtime,hdb_code_start,hdb_code_end
.export hdb_active,hdb_online,hdb_cf,hdb_status,hdb_completed,hdb_boot_drive,hdb_error
.export hdb_state_start,hdb_state_end,hdb_snapshot
.segment "NATIVESTATE"
hdb_boot_drive: .byte 0
.segment "DEVICESTATE"
hdb_state_start:
hdb_active: .res 1 ;0 idle,1 pending,2 completed,3 terminal coherent/context fault
hdb_online: .res 1
hdb_cf: .res 1
hdb_status: .res 1
hdb_completed: .res 1
hdb_error: .res 1
hdb_phase: .res 1 ;0 prepare sector,1 HD pending,2 FILE pending
hdb_function: .res 1
hdb_remaining: .res 1
hdb_lba: .res 2
hdb_far: .res 3
hdb_live_flags: .res 2
hdb_snapshot: .res G_SIZE
hdb_work: .res 2
hdb_mode: .res 1
hdb_state_end:
.segment "HDBIOS"
hdb_code_start:
; Resident RAM under KERNAL: all callers own native RAM+I/O map ($01 low3=5).
; No KERNAL calls. Native IRQ/NMI ownership remains with current runtime.
hdb_startup:
 lda #0
 ldx #hdb_state_end-hdb_state_start-1
: sta hdb_state_start,x
 dex
 bpl :-
 sta hd_state
 sta hd_uncertain
 sta hdb_boot_drive
 rts
; Explicit mount AFTER FILE open and BIOS init; profile/slots/readonly supplied.
hdb_mount:
 lda hdb_active
 jne mount_fail
 lda #0
 sta hdb_online
 jsr dos64_overlay_hd_init
 jcs mount_fail
 ; Advertise one HD and its mutable INT41 vector / ROM parameter table.
 lda dos64_memory_mode
 sta hdb_mode
 lda #1 ; MEM_ALL_RAM, verified against memory.inc
 sta dos64_memory_mode
 lda #$75
 sta dos64_address
 lda #4
 sta dos64_address+1
 lda #0
 sta dos64_address+2
 lda #1
 sta dos64_mem_value
 jsr dos64_mem_write
 bcs @fail
 lda #$04
 sta dos64_address
 lda #1
 sta dos64_address+1
 ldx #0
@ivt:
 lda hdb_vector,x
 sta dos64_mem_value
 stx hdb_work
 jsr dos64_mem_write
 ldx hdb_work
 bcs @fail
 inc dos64_address
 inx
 cpx #4
 bne @ivt
 lda #$40
 sta dos64_address
 lda #3
 sta dos64_address+1
 lda #$0f
 sta dos64_address+2
 ldx #0
@table:
 lda hdb_table,x
 sta dos64_mem_value
@high:
 cpx #1
 beq @cylinder_high
 cpx #13
 bne @heads
@cylinder_high:
 lda hd_profile
 beq :+
 lda #2
: sta dos64_mem_value
@heads:
 cpx #2
 bne @write
 lda hd_profile
 asl
 clc
 adc #2
 sta dos64_mem_value
@write:
 stx hdb_work
 jsr dos64_mem_write
 ldx hdb_work
 bcs @fail
 inc dos64_address
 inx
 cpx #16
 bne @table
 lda hdb_mode
 sta dos64_memory_mode
 lda #1
 sta hdb_online
 clc
 rts
@fail:
 lda hdb_mode
 sta dos64_memory_mode
mount_fail:
 sec
 rts
hdb_vector: .byte $40,$03,$00,$f0
hdb_table: .byte $80,0,2,0,0,$ff,$ff,0,0,0,0,0,$80,0,16,0
hdb_service:
 lda #0
 sta dos64_disk_host_error
 sta hdb_cf
 lda hdb_active
 cmp #3
 jeq coherent_fault
 cmp #1
 beq @pending
 cmp #2
 beq @complete
 lda hdb_online
 jeq not_ready
 lda dos64_guest+G_AX+1
 jeq reset
 cmp #1
 jeq status
 cmp #8
 jeq parameters
 cmp #$15
 jeq drive_type
 cmp #2
 jcc bad_function
 cmp #5
 jcs bad_function
 jmp begin_transfer
@pending:
 jsr check_context
 jcs coherent_fault
 lda #1
 sta dos64_bios_waiting
 clc
 rts
@complete:
 jsr check_context
 jcs coherent_fault
 lda hdb_live_flags
 sta dos64_guest+G_FLAGS
 lda hdb_live_flags+1
 sta dos64_guest+G_FLAGS+1
 lda #0
 sta hdb_active
 lda hdb_status
 sta dos64_guest+G_AX+1
 lda hdb_completed
 sta dos64_guest+G_AX
 lda hdb_status
 beq @ok
 lda #1
 sta hdb_cf
@ok:
 jmp publish_status
reset:
 lda hd_uncertain
 jne controller_error
 lda #0
 sta hdb_status
 sta dos64_guest+G_AX
 sta dos64_guest+G_AX+1
 jmp publish_status
status:
 lda hdb_status
 sta dos64_guest+G_AX+1
 beq :+
 lda #1
 sta hdb_cf
: jmp publish_status
parameters:
 lda #16
 sta dos64_guest+G_CX
 lda hd_profile
 beq @small
 lda #$90 ; last cylinder639: CL high bits80 +16 sectors
 sta dos64_guest+G_CX
 lda #$7f
 sta dos64_guest+G_CX+1
 lda #3
 bne @head
@small:
 lda #$7f
 sta dos64_guest+G_CX+1
 lda #1
@head:
 sta dos64_guest+G_DX+1
 lda #1
 sta dos64_guest+G_DX
 lda #0
 sta dos64_guest+G_AX+1
 sta hdb_status
 jmp publish_status
drive_type:
 lda #0
 sta hdb_status
 lda #3
 sta dos64_guest+G_AX+1
 lda #0
 sta dos64_guest+G_CX
 sta dos64_guest+G_CX+1
 sta dos64_guest+G_DX
 lda hd_profile
 beq :+
 lda #$a0
 bne @size
: lda #$10
@size:
 sta dos64_guest+G_DX+1
 jmp publish_status
begin_transfer:
 sta hdb_function
 lda dos64_guest+G_AX
 jeq bad_sector
 cmp #128
 jcs bad_sector
 sta hdb_remaining
 lda #1
 sta hd_count
 lda dos64_guest+G_CX
 sta hd_cl
 lda dos64_guest+G_CX+1
 sta hd_ch
 lda dos64_guest+G_DX+1
 sta hd_dh
 jsr dos64_overlay_hd_chs_to_lba
 jcs bad_sector
 lda hd_lba
 sta hdb_lba
 clc
 adc hdb_remaining
 sta hdb_work
 lda hd_lba+1
 sta hdb_lba+1
 adc #0
 jcs bad_sector
 sta hdb_work+1
 lda hd_profile
 beq @small_limit
 lda #$a0
 bne @limit
@small_limit:
 lda #$10
@limit:
 cmp hdb_work+1
 jcc bad_sector
 bne @address
 lda hdb_work
 jne bad_sector
@address:
 lda dos64_guest+G_ES
 sta dos64_segment
 lda dos64_guest+G_ES+1
 sta dos64_segment+1
 lda dos64_guest+G_BX
 sta dos64_offset
 lda dos64_guest+G_BX+1
 sta dos64_offset+1
 jsr dos64_physical
 ldx #2
: lda dos64_address,x
 sta hdb_far,x
 dex
 bpl :-
 lda hdb_remaining
 asl
 clc
 adc hdb_far+1
 bcc @valid
 ora hdb_far
 jne dma_boundary
@valid:
 lda hdb_function
 cmp #3
 bne @context
 lda hd_readonly
 jne write_protect
@context:
 lda dos64_guest+G_FLAGS
 sta hdb_live_flags
 lda dos64_guest+G_FLAGS+1
 sta hdb_live_flags+1
 and #$fd ; do not admit INTR while an owned BIOS transfer is suspended
 sta dos64_guest+G_FLAGS+1
 ldx #G_SIZE-1
: lda dos64_guest,x
 sta hdb_snapshot,x
 dex
 bpl :-
 lda #0
 sta hdb_completed
 sta hdb_status
 sta hdb_error
 sta hdb_phase
 lda #1
 sta hdb_active
 sta dos64_bios_waiting
 clc
 rts
check_context:
 ldx #G_SIZE-1
: lda dos64_guest,x
 cmp hdb_snapshot,x
 bne @bad
 dex
 bpl :-
 clc
 rts
@bad: sec
 rts
not_ready:
 lda #$80
 jne immediate_error
bad_function:
 lda #1
 jne immediate_error
bad_sector:
 lda #4
 jne immediate_error
dma_boundary:
 lda #9
 jne immediate_error
write_protect:
 lda #3
 jne immediate_error
controller_error:
 lda #$20
immediate_error:
 sta hdb_status
 sta dos64_guest+G_AX+1
 lda #0
 sta dos64_guest+G_AX
 lda #1
 sta hdb_cf
 jmp publish_status
publish_status:
 lda #$74
 sta dos64_address
 lda #4
 sta dos64_address+1
 lda #0
 sta dos64_address+2
 lda hdb_status
 sta dos64_mem_value
 jsr dos64_mem_write
 jcs coherent_fault
 clc
 rts
coherent_fault:
 lda #3
 sta hdb_active
 lda #1
 sta hdb_error
 sta dos64_disk_host_error
 sec
 rts
; One bounded resident continuation per native tick. No guest register writes
; until gate completion. FILE and HD leases have returned before the next call.
hdb_runtime:
 lda hdb_active
 cmp #1
 bne @idle
 lda hdb_phase
 jeq prepare_sector
 cmp #2
 jeq file_poll
 lda hd_state
 cmp #HD_WAIT
 jeq launch_file
 cmp #HD_DONE
 jeq consume_sector
 jmp transfer_error
@idle:
 clc
 rts
launch_file:
 lda dos64_elapsed_now
 sta dos64_files_now
 lda dos64_elapsed_now+1
 sta dos64_files_now+1
 jsr dos64_overlay_files_start
 jcs coherent_fault
 lda #2
 sta hdb_phase
 clc
 rts
file_poll:
 lda dos64_elapsed_now
 sta dos64_files_now
 lda dos64_elapsed_now+1
 sta dos64_files_now+1
 jsr dos64_overlay_files_poll
 jcs coherent_fault
 lda dos64_files_state
 cmp #FILES_BUSY
 beq @return
 jsr dos64_overlay_hd_advance
 jcs coherent_fault
 lda #1
 sta hdb_phase
@return:
 clc
 rts
prepare_sector:
 lda hdb_function
 cmp #3
 bne @read
 lda #GR_TO_REU
 jsr coherent_sector
 jcs coherent_fault
 jsr staging_address
 lda #1
 sta dos64_reu_request+R_DIRECTION
 jsr command_host
 jsr sector_dma
 jcs coherent_fault
 lda #1
 bne @op
@read:
 lda #0
@op:
 sta hd_op
 lda #1
 sta hd_count
 lda hdb_lba
 sta hd_lba
 lda hdb_lba+1
 sta hd_lba+1
 jsr dos64_overlay_hd_prepare
 jcs transfer_error
 lda #1
 sta hdb_phase
 clc
 rts
consume_sector:
 lda hdb_function
 cmp #2
 bne @count
 jsr staging_address
 lda #0
 sta dos64_reu_request+R_DIRECTION
 lda #<dos64_uci_data
 sta dos64_reu_request+R_HOST
 lda #>dos64_uci_data
 sta dos64_reu_request+R_HOST+1
 jsr sector_dma
 jcs coherent_fault
 lda #GR_FROM_REU
 jsr coherent_sector
 jcs coherent_fault
@count:
 inc hdb_completed
 dec hdb_remaining
 beq @done
 inc hdb_lba
 bne :+
 inc hdb_lba+1
: clc
 lda hdb_far+1
 adc #2
 sta hdb_far+1
 bcc :+
 inc hdb_far+2
: lda #0
 sta hdb_phase
 clc
 rts
@done:
 lda #0
 sta hdb_status
 lda #2
 sta hdb_active
 clc
 rts
transfer_error:
 lda #$20
 sta hdb_status
 lda #2
 sta hdb_active
 clc
 rts
coherent_sector:
 sta dos64_range_request+GR_DIRECTION
 ldx #2
: lda hdb_far,x
 sta dos64_range_request+GR_GUEST,x
 dex
 bpl :-
 lda #0
 sta dos64_range_request+GR_REU
 sta dos64_range_request+GR_REU+1
 sta dos64_range_request+GR_LENGTH
 lda #$35
 sta dos64_range_request+GR_REU+2
 lda #$20
 sta dos64_range_request+GR_REU+1
 lda #2
 sta dos64_range_request+GR_LENGTH+1
 jmp dos64_range_copy
staging_address:
 lda #0
 sta dos64_reu_request+R_REU
 lda #$20
 sta dos64_reu_request+R_REU+1
 lda #$35
 sta dos64_reu_request+R_REU+2
 rts
command_host:
 lda #<(dos64_uci_command+4)
 sta dos64_reu_request+R_HOST
 lda #>(dos64_uci_command+4)
 sta dos64_reu_request+R_HOST+1
 rts
sector_dma:
 lda #0
 sta dos64_reu_request+R_LENGTH
 lda #2
 sta dos64_reu_request+R_LENGTH+1
 jmp dos64_reu_transfer
hdb_native_burst:
 jsr hdb_runtime
 bcs @error
 lda #16
 sta n_burst
@next:
 jsr dos64_native_timer_step
 bcs @timer_error
 dec n_burst
 bne @next
 jmp n_tick_return
@timer_error:
 jmp n_timer_cpu_error
@error:
 jmp n_cpu_error
hdb_code_end:
.assert hdb_code_end <= $fe00, lderror,"HD continuation overlaps vector reserve"
