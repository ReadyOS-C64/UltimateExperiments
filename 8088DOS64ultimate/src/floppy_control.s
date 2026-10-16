.include "abi.inc"
.include "disk.inc"
.include "reu.inc"
.macpack longbranch
.import dos64_disk_reu_base,dos64_disk_b_descriptor,dos64_disk_loaded
.import dos64_disk_readonly,dos64_disk_dirty,dos64_disk_exhausted
.import dos64_disk_mount_generation,dos64_disk_content_generation
.import dos64_disk_clean_mount,dos64_disk_clean_content,dos64_disk_binding
.import dos64_cold_open,dos64_native_diag,dos64_overlay_floppy_control,dos64_overlay_error
.import dos64_reu_request,dos64_reu_transfer,dos64_range_buffer
.export dos64_floppy_control,dos64_floppy_control_init,dos64_floppy_request,dos64_floppy_status
.export dos64_floppy_stage_active,dos64_floppy_stage_bank,dos64_floppy_token
.export dos64_floppy_validate,dos64_floppy_native_control
.importzp dos64_segment
; Exclusive native control uses public address scratch, never nested CPU math.
ctl_ptr = dos64_segment
.segment "DEVICESTATE"
dos64_floppy_request: .res FQ_SIZE
dos64_floppy_status: .res 1
ctl_drive: .res 1
ctl_offset: .res 1
ctl_scan: .res 1
dos64_floppy_stage_active: .res 1
dos64_floppy_stage_bank: .res 1
stage_drive: .res 1
stage_flags: .res 1
stage_mount: .res 4
stage_content: .res 4
stage_binding: .res 4
dos64_floppy_token: .res 4
ctl_end:
.segment "CODE"
dos64_floppy_control_init:
 lda #0
 ldx #ctl_end-dos64_floppy_request-1
: sta dos64_floppy_request,x
 dex
 bpl :-
 rts
; Native menu/kernel operation only. Caller owns paused or cold exclusive time;
; the guest cannot reach this through INT13. Public request is not retained as
; a mutable capability: PREPARE latches its policy, old generations and token.
dos64_floppy_control:
 php
 lda dos64_cold_open
 cmp #$a5
 beq @call
 lda dos64_native_diag
 cmp #5
 bne @guard
@call:
 jsr dos64_overlay_floppy_control
 lda dos64_overlay_error
 beq @status
 lda #FERR_IO
 sta dos64_floppy_status
@status:
 lda dos64_floppy_status
 beq @ok
 plp
 sec
 rts
@guard:
 lda #FERR_GUARD
 sta dos64_floppy_status
 plp
 sec
 rts
@ok:
 plp
 clc
 rts
dos64_floppy_native_control:
 php
 sei
 cld
 lda dos64_cold_open
 cmp #$a5
 beq @guarded
 lda dos64_native_diag
 cmp #5
 jne ctl_guard
@guarded:
 ldx dos64_floppy_request+FQ_DRIVE
 cpx #2
 jcs ctl_input
 stx ctl_drive
 jsr ctl_descriptor
 txa
 asl
 asl
 sta ctl_offset
 lda dos64_floppy_request+FQ_OP
 cmp #FOP_COMMIT
 jeq ctl_commit
 cmp #FOP_CANCEL
 jeq ctl_cancel
 lda dos64_floppy_stage_active
 jne ctl_busy
 lda dos64_floppy_request+FQ_OP
 cmp #FOP_PREPARE
 jeq ctl_prepare
 cmp #FOP_EJECT
 jeq ctl_eject
 cmp #FOP_CLEAN
 jeq ctl_clean
 jmp ctl_input
ctl_descriptor:
 lda #<dos64_disk_reu_base
 ldy #>dos64_disk_reu_base
 cpx #0
 beq :+
 lda #<dos64_disk_b_descriptor
 ldy #>dos64_disk_b_descriptor
: sta ctl_ptr
 sty ctl_ptr+1
 rts
ctl_prepare:
 lda dos64_floppy_request+FQ_FLAGS
 and #$fc
 jne ctl_input
 lda dos64_floppy_request+FQ_CAPACITY
 cmp #4
 jcc ctl_input
 cmp #17
 jcs ctl_input
 jsr ctl_dirty_check
 jcs ctl_dirty
 ; Native-mounted descriptors always name one aligned full-capacity arena.
 ; Reject foreign legacy direct configurations rather than guessing overlap.
 ldx #1
@descriptors:
 jsr ctl_descriptor
 ldy #9
 lda (ctl_ptr),y
 beq @next
 ldy #0
 lda (ctl_ptr),y
 iny
 ora (ctl_ptr),y
 jne ctl_context
 iny
 lda (ctl_ptr),y
 jsr ctl_bank_valid
 jcs ctl_context
@next:
 dex
 bpl @descriptors
 lda dos64_disk_loaded
 beq @find
 lda dos64_disk_b_descriptor+9
 beq @find
 lda dos64_disk_reu_base+2
 cmp dos64_disk_b_descriptor+2
 jeq ctl_context
@find:
 ldy #0
@candidate:
 lda ctl_banks,y
 ldx dos64_disk_loaded
 beq :+
 cmp dos64_disk_reu_base+2
 beq @skip
: ldx dos64_disk_b_descriptor+9
 beq @free
 cmp dos64_disk_b_descriptor+2
 bne @free
@skip:
 iny
 cpy #3
 bcc @candidate
 jmp ctl_busy
@free:
 sta dos64_floppy_stage_bank
 lda dos64_floppy_token
 and dos64_floppy_token+1
 and dos64_floppy_token+2
 and dos64_floppy_token+3
 cmp #$ff
 jeq ctl_generation
 ldx #0
@token:
 inc dos64_floppy_token,x
 bne @latch
 inx
 cpx #4
 bne @token
@latch:
 ldx ctl_drive
 stx stage_drive
 jsr ctl_descriptor
 lda dos64_floppy_request+FQ_FLAGS
 sta stage_flags
 ldx ctl_offset
 ldy #0
@copy:
 lda dos64_disk_mount_generation,x
 sta stage_mount,y
 sta dos64_floppy_request+FQ_MOUNT,y
 lda dos64_disk_content_generation,x
 sta stage_content,y
 sta dos64_floppy_request+FQ_CONTENT,y
 lda dos64_floppy_request+FQ_BIND,y
 sta stage_binding,y
 lda dos64_floppy_token,y
 sta dos64_floppy_request+FQ_TOKEN,y
 inx
 iny
 cpy #4
 bne @copy
 lda #0
 sta dos64_floppy_request+FQ_COMPLETE
 sta dos64_floppy_request+FQ_BASE
 sta dos64_floppy_request+FQ_BASE+1
 sta dos64_floppy_request+FQ_LENGTH
 lda #$a0
 sta dos64_floppy_request+FQ_LENGTH+1
 lda #5
 sta dos64_floppy_request+FQ_LENGTH+2
 lda dos64_floppy_stage_bank
 sta dos64_floppy_request+FQ_BASE+2
 lda #$a5
 sta dos64_floppy_stage_active
 jmp ctl_ok
.segment "DISKCODE"
ctl_bank_valid:
 cmp #$10
 beq @ok
 cmp #$18
 beq @ok
 cmp #$38
 beq @ok
 sec
 rts
@ok:
 clc
 rts
ctl_check_token:
 lda dos64_floppy_stage_active
 cmp #$a5
 bne @bad
 lda stage_drive
 cmp ctl_drive
 bne @bad
 ldx #3
: lda dos64_floppy_request+FQ_TOKEN,x
 cmp dos64_floppy_token,x
 bne @bad
 dex
 bpl :-
 clc
 rts
@bad:
 sec
 rts
.segment "CODE"
ctl_cancel:
 jsr ctl_check_token
 jcs ctl_context
 lda #0
 sta dos64_floppy_stage_active
 jmp ctl_ok
ctl_commit:
 jsr ctl_check_token
 jcs ctl_context
 lda dos64_floppy_request+FQ_COMPLETE
 cmp #$a5
 jne ctl_input
 lda dos64_floppy_request+FQ_LENGTH
 ora dos64_floppy_request+FQ_BASE
 ora dos64_floppy_request+FQ_BASE+1
 jne ctl_input
 lda dos64_floppy_request+FQ_LENGTH+1
 cmp #$a0
 jne ctl_input
 lda dos64_floppy_request+FQ_LENGTH+2
 cmp #5
 jne ctl_input
 lda dos64_floppy_request+FQ_BASE+2
 cmp dos64_floppy_stage_bank
 jne ctl_context
 ldx ctl_offset
 ldy #0
@snapshot:
 lda dos64_disk_mount_generation,x
 cmp stage_mount,y
 jne ctl_context
 lda dos64_disk_content_generation,x
 cmp stage_content,y
 jne ctl_context
 inx
 iny
 cpy #4
 bne @snapshot
 lda stage_flags
 sta dos64_floppy_request+FQ_FLAGS
 jsr ctl_dirty_check
 jcs ctl_dirty
 jsr ctl_mount_available
 jcs ctl_generation
 jsr dos64_floppy_validate
 jcs ctl_return_error
 ; No calls which can fail occur after descriptor publication begins.
 ldy #9
@descriptor:
 lda ctl_image,y
 sta (ctl_ptr),y
 dey
 bpl @descriptor
 ldy #2
 lda dos64_floppy_stage_bank
 sta (ctl_ptr),y
 jsr ctl_new_mount
 ldx ctl_drive
 lda stage_flags
 and #1
 sta dos64_disk_readonly,x
 ldx ctl_offset
 ldy #0
@binding:
 lda stage_binding,y
 sta dos64_disk_binding,x
 inx
 iny
 cpy #4
 bne @binding
 lda #0
 sta dos64_floppy_stage_active
 jmp ctl_ok
.segment "DISKCODE"
ctl_dirty_check:
 ldx ctl_drive
 lda dos64_disk_dirty,x
 beq @clean
 lda dos64_floppy_request+FQ_FLAGS
 and #2
 bne @clean
 sec
 rts
@clean:
 clc
 rts
ctl_match_snapshot:
 ldx ctl_offset
 ldy #0
: lda dos64_floppy_request+FQ_MOUNT,y
 cmp dos64_disk_mount_generation,x
 bne @bad
 lda dos64_floppy_request+FQ_CONTENT,y
 cmp dos64_disk_content_generation,x
 bne @bad
 inx
 iny
 cpy #4
 bne :-
 clc
 rts
@bad:
 sec
 rts
ctl_mount_available:
 ldx ctl_offset
 lda dos64_disk_mount_generation,x
 and dos64_disk_mount_generation+1,x
 and dos64_disk_mount_generation+2,x
 and dos64_disk_mount_generation+3,x
 cmp #$ff
 beq @bad
 clc
 rts
@bad:
 sec
 rts
.segment "DISKCODE"
ctl_eject:
 jsr ctl_match_snapshot
 jcs ctl_context
 jsr ctl_dirty_check
 jcs ctl_dirty
 jsr ctl_mount_available
 jcs ctl_generation
 ldy #9
 lda #0
 sta (ctl_ptr),y
 jsr ctl_new_mount
 jmp ctl_ok
.segment "DISKCODE"
ctl_new_mount:
 ldx ctl_offset
@increment:
 inc dos64_disk_mount_generation,x
 bne @zero
 inx
 bne @increment
@zero:
 ldx ctl_drive
 lda #0
 sta dos64_disk_dirty,x
 sta dos64_disk_readonly,x
 sta dos64_disk_exhausted,x
 ldx ctl_offset
 ldy #4
@meta:
 lda #0
 sta dos64_disk_content_generation,x
 sta dos64_disk_clean_content,x
 sta dos64_disk_binding,x
 lda dos64_disk_mount_generation,x
 sta dos64_disk_clean_mount,x
 inx
 dey
 bne @meta
 rts
.segment "DISKCODE"
ctl_clean:
 lda dos64_floppy_request+FQ_COMPLETE
 cmp #$a5
 jne ctl_input
 ldy #9
 lda (ctl_ptr),y
 jeq ctl_input
 jsr ctl_match_snapshot
 jcs ctl_context
 ldx ctl_drive
 lda dos64_disk_exhausted,x
 jne ctl_generation
 lda #0
 sta dos64_disk_dirty,x
 ldx ctl_offset
 ldy #0
: lda dos64_disk_mount_generation,x
 sta dos64_disk_clean_mount,x
 lda dos64_disk_content_generation,x
 sta dos64_disk_clean_content,x
 lda dos64_floppy_request+FQ_BIND,y
 sta dos64_disk_binding,x
 inx
 iny
 cpy #4
 bne :-
 jmp ctl_ok
.segment "CODE"
ctl_ok:
 lda #0
 sta dos64_floppy_status
 plp
 clc
 rts
ctl_input:
 lda #FERR_INPUT
 bne ctl_return_error
ctl_busy:
 lda #FERR_BUSY
 bne ctl_return_error
ctl_dirty:
 lda #FERR_DIRTY
 bne ctl_return_error
ctl_context:
 lda #FERR_CONTEXT
 bne ctl_return_error
ctl_guard:
 lda #FERR_GUARD
 bne ctl_return_error
ctl_generation:
 lda #FERR_GENERATION
ctl_return_error:
 sta dos64_floppy_status
 plp
 sec
 rts
ctl_banks: .byte $10,$18,$38
ctl_image: .byte 0,0,0,$d0,2,40,0,2,9,1

.segment "DISKCODE"
; Validate only read-only candidate bytes. Whole-file size/CRC and known CLOSE
; are the loader's COMPLETE contract, never inferred from one valid boot sector.
dos64_floppy_validate:
 lda #<dos64_range_buffer
 sta dos64_reu_request+R_HOST
 lda #>dos64_range_buffer
 sta dos64_reu_request+R_HOST+1
 lda #0
 sta dos64_reu_request+R_REU
 sta dos64_reu_request+R_REU+1
 sta dos64_reu_request+R_LENGTH+1
 lda dos64_floppy_stage_bank
 sta dos64_reu_request+R_REU+2
 lda #32
 sta dos64_reu_request+R_LENGTH
 lda #1
 sta dos64_reu_request+R_DIRECTION
 jsr dos64_reu_transfer
 bcs @io
 ldx #11
@bpb:
 ldy ctl_bpb_offsets,x
 lda dos64_range_buffer,y
 cmp ctl_bpb_values,x
 bne @geometry
 dex
 bpl @bpb
 clc
 rts
@io:
 lda #FERR_IO
 sec
 rts
@geometry:
 lda #FERR_GEOMETRY
 sec
 rts
ctl_bpb_offsets: .byte $0b,$0c,$13,$14,$15,$18,$19,$1a,$1b,$0e,$0f,$10
ctl_bpb_values: .byte 0,2,$d0,2,$fd,9,0,2,0,1,0,2
