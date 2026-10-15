.setcpu "6502"
.macpack longbranch
.include "files.inc"
.import dos64_uci_command,dos64_files_target,dos64_files_op,dos64_files_mode
.import dos64_files_path_len,dos64_files_handle,dos64_files_state,dos64_files_now
.import dos64_elapsed_now,dos64_overlay_files_start,dos64_overlay_files_poll
.import hdb_active,hdb_online,hd_uncertain
.import hdb_mount,hdb_boot_drive,hd_profile,hd_readonly,hd_slots
.import hd_state,hd_lba,hd_count,hd_op
.import dos64_overlay_hd_prepare,dos64_overlay_hd_advance
.export hdc_config,hdc_config_end,hdc_copy,hdc_begin,hdc_poll
.export hdc_enabled,hdc_flags,hdc_profile,hdc_readonly,hdc_boot,hdc_target,hdc_slots,hdc_path_len,hdc_path
.export hdc_phase,hdc_error,hdc_state_start,hdc_state_end
.segment "DEVICESTATE"
hdc_state_start:
hdc_enabled: .res 1
hdc_flags: .res 1
hdc_profile: .res 1
hdc_readonly: .res 1
hdc_boot: .res 1
hdc_target: .res 1
hdc_slots: .res 1
hdc_path_len: .res 1
hdc_path: .res 128
hdc_phase: .res 1 ;0 disabled,1 opening,2 mounted,3 failed
hdc_error: .res 1
hdc_state_end:
.segment "HDBIOS"
; Called after verified shadow load but before any cache/guest CPU access.
; Complete config is resident before bitmap/cold lifetime can change.
hdc_copy:
 lda #0
 sta hdc_phase
 sta hdc_error
 sta hdc_enabled
 lda hdc_config+4
 jeq @disabled
 cmp #$a5
 jne config_error
 ldx #3
@magic:
 lda hdc_config,x
 cmp config_magic,x
 jne config_error
 dex
 bpl @magic
 ldx #0
@copy:
 lda hdc_config+4,x
 sta hdc_state_start,x
 inx
 cpx #136
 bne @copy
 lda hdc_flags
 cmp #2
 jcs config_error
 lda hdc_profile
 cmp #2
 jcs config_error
 lda hdc_readonly
 cmp #2
 jcs config_error
 lda hdc_boot
 cmp #$80
 beq @boot_ok
 cmp #0
 jne config_error
 lda hdc_flags
 and #1
 jeq config_error
@boot_ok:
 lda hdc_target
 cmp #1
 jcc config_error
 cmp #3
 jcs config_error
 lda hdc_slots
 jeq config_error
 cmp #33
 jcs config_error
 lda hdc_path_len
 cmp #2
 jcc config_error
 cmp #129
 jcs config_error
 tax
 dex
 lda hdc_path,x
 jne config_error
 dex
@path:
 lda hdc_path,x
 jeq config_error
 dex
 bpl @path
@disabled:
 clc
 rts
config_error:
 lda #1
 sta hdc_error
 lda #3
 sta hdc_phase
 sec
 rts
; Called only after optional floppy importer has published DONE/known CLOSED,
; real BIOS/input initialized, and before timer initialization/cold release.
hdc_begin:
 lda hdc_enabled
 jeq @disabled
 lda hdb_active
 jne ownership_error
 lda hd_uncertain
 jne ownership_error
 lda dos64_files_handle
 jne ownership_error
 lda dos64_files_state
 cmp #FILES_BUSY
 jeq ownership_error
 lda #0
 sta hdb_online
 lda hdc_target
 sta dos64_files_target
 lda #FILES_OPEN
 sta dos64_files_op
 lda hdc_readonly
 beq @writable
 lda #1
 bne @mode
@writable:
 lda #3
@mode:
 sta dos64_files_mode
 lda hdc_path_len
 sta dos64_files_path_len
 tax
 dex
@path:
 lda hdc_path,x
 sta dos64_uci_command+3,x
 dex
 bpl @path
 jsr clock
 jsr dos64_overlay_files_start
 jcs operation_error
 lda #1
 sta hdc_phase
@disabled:
 clc
 rts
hdc_poll:
 lda hdc_phase
 cmp #4
 jeq warm_hd
 cmp #5
 jeq warm_file
 cmp #1
 bne @reject
 jsr clock
 jsr dos64_overlay_files_poll
 jcs operation_error
 lda dos64_files_state
 cmp #FILES_BUSY
 beq @defer
 cmp #FILES_DONE
 jne operation_error
 lda dos64_files_handle
 cmp #1
 jne ownership_error
 lda hdc_profile
 sta hd_profile
 lda hdc_readonly
 sta hd_readonly
 lda hdc_slots
 sta hd_slots
 jsr hdb_mount
 jcs mount_error
 lda #0
 sta hdb_online
 sta hd_lba
 sta hd_lba+1
 sta hd_op
 lda #1
 sta hd_count
 jsr dos64_overlay_hd_prepare
 jcs warm_error
 lda #4
 sta hdc_phase
@defer:
 clc
 rts
@reject:
 sec
 rts
warm_hd:
 lda hd_state
 cmp #1
 beq @file
 cmp #2
 jne warm_error
 lda hdc_boot
 sta hdb_boot_drive
 lda #1
 sta hdb_online
 lda #2
 sta hdc_phase
 clc
 rts
@file:
 jsr clock
 jsr dos64_overlay_files_start
 jcs warm_error
 lda #5
 sta hdc_phase
 clc
 rts
warm_file:
 jsr clock
 jsr dos64_overlay_files_poll
 jcs warm_error
 lda dos64_files_state
 cmp #FILES_BUSY
 beq @defer
 jsr dos64_overlay_hd_advance
 jcs warm_error
 lda #4
 sta hdc_phase
@defer:
 clc
 rts
warm_error:
 lda #5
 jmp failed
clock:
 lda dos64_elapsed_now
 sta dos64_files_now
 lda dos64_elapsed_now+1
 sta dos64_files_now+1
 rts
ownership_error:
 lda #2
 bne failed
operation_error:
 lda #3
 bne failed
mount_error:
 lda #4
failed:
 sta hdc_error
 lda #3
 sta hdc_phase
 sec
 rts
config_magic: .byte "D64H"
.segment "COLDRODATA"
; Explicit launch-only config. Both core D64N and this block must be enabled.
; magic4,enable,flags(bit0 importfloppy),profile,readonly,bootDL,target,slots,pathLen,path128.
; Defaultdisabled=0 preserves old floppy path/config behavior and ignores rest.
hdc_config:
 .byte "D64H",0,1,0,1,$80,1,2,0
 .res 128,0
hdc_config_end:
