; This routine returns C clear only for current native private PREPARE authority.
; Does not infer private stage from caller request; does not mutate native state.
insert_stage_check:
 jsr insert_broker_owner
 jcs @bad
 lda MI_KIND
 cmp #1
 jne @bad
 lda MI_FQ
 cmp #1
 jne @bad
 lda MI_FQ+1
 cmp #2
 jcs @bad
 cmp ML_DRIVE
 jne @bad
 cmp insert_stage_drive
 jne @bad
 lda MI_FQ+2
 cmp #4
 jcs @bad
 cmp insert_stage_flags
 jne @bad
 lda MI_FQ+3
 cmp #$a5
 jne @bad
 lda MI_FQ+4
 cmp dos64_overlay_reu_mib
 jne @bad
 lda MI_FQ+5
 ora MI_FQ+6
 ora MI_FQ+8
 jne @bad
 lda MI_FQ+9
 cmp #$a0
 jne @bad
 lda MI_FQ+10
 cmp #5
 jne @bad
 lda MI_FQ+7
 cmp dos64_floppy_stage_bank
 jne @bad
 lda dos64_floppy_stage_active
 cmp #$a5
 jne @bad
 ldx ML_DRIVE
 lda dos64_disk_dirty,x
 ora dos64_disk_exhausted,x
 beq :+
 lda MI_FQ+2
 and #2
 jeq @bad
: lda ML_DRIVE
 asl
 asl
 tay
 ldx #0
@proof:
 lda MI_FQ+11,x
 cmp dos64_floppy_token,x
 jne @bad
 lda MI_FQ+15,x
 cmp insert_stage_mount,x
 jne @bad
 cmp dos64_disk_mount_generation,y
 jne @bad
 lda MI_FQ+19,x
 cmp insert_stage_content,x
 jne @bad
 cmp dos64_disk_content_generation,y
 jne @bad
 lda MI_FQ+23,x
 cmp insert_stage_binding,x
 jne @bad
 cmp ML_CRC,x
 jne @bad
 inx
 iny
 cpx #4
 bne @proof
 ldx #26
@request:
 lda MI_FQ,x
 cmp dos64_floppy_request,x
 jne @bad
 dex
 bpl @request
 clc
 rts
@bad: sec
 rts
