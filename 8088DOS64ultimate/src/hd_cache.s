.setcpu "6502"
.macpack longbranch
.include "hd_cache.inc"
.include "files.inc"
.include "reu.inc"
.import dos64_reu_transfer,dos64_reu_request
.import dos64_files_op,dos64_files_offset,dos64_files_count,dos64_files_state
.import dos64_files_handle
.import dos64_files_actual,dos64_files_count_known,dos64_files_short
.import dos64_uci_command,dos64_uci_data
.export hd_init,hd_prepare,hd_advance,hd_retry
.export hd_state,hd_error,hd_request,hd_profile,hd_slots,hd_lba,hd_count,hd_op
.export hd_readonly
.export hd_uncertain,hd_agreement,hd_valid,hd_tags_lo,hd_tags_hi
.export hd_chs_to_lba,hd_ch,hd_cl,hd_dh
.export hd_state_start,hd_state_end,hd_code_start,hd_code_end
.segment "DEVICESTATE"
hd_state_start:
hd_state: .res 1
hd_error: .res 1
hd_request: .res 1
hd_profile: .res 1
hd_slots: .res 1
hd_lba: .res 2
hd_count: .res 1
hd_op: .res 1
hd_uncertain: .res 1
hd_agreement: .res 1
hd_valid: .res 32
hd_tags_lo: .res 32
hd_tags_hi: .res 32
h_extent: .res 2
h_sector: .res 1
h_slot: .res 1
h_victim: .res 1
h_phase: .res 1
h_fill: .res 1
hd_ch: .res 1
hd_cl: .res 1
hd_dh: .res 1
hd_readonly: .res 1
h_readonly: .res 1
h_profile: .res 1
h_slots: .res 1
h_saved_op: .res 1
h_mounted: .res 1
h_saved_lba: .res 2
h_offset: .res 4
hd_state_end:
.segment "HDCODE"
hd_code_start:
; Caller enters with RAM+I/O visible and exclusive overlay/REU/UCI ownership.
; All public calls preserve native P except carry, clobber A/X/Y.
.macro ENTER
 php
 sei
 cld
.endmacro
.macro OUT carry
 plp
 .if carry
 sec
 .else
 clc
 .endif
 rts
.endmacro
hd_init:
 ENTER
 lda dos64_files_handle
 cmp #1
 jne reject
 lda hd_readonly
 cmp #2
 jcs reject
 lda hd_state
 cmp #HD_WAIT
 jeq reject
 lda dos64_files_state
 cmp #FILES_BUSY
 jeq reject
 lda hd_uncertain
 jne reject
 lda hd_slots
 jeq reject
 cmp #33
 jcs reject
 lda hd_profile
 cmp #2
 jcs reject
 sta h_profile
 lda hd_readonly
 sta h_readonly
 lda hd_slots
 sta h_slots
 lda #0
 sta hd_state
 sta hd_error
 sta hd_request
 sta hd_agreement
 sta h_victim
 sta h_mounted
 ldx #31
@clear: sta hd_valid,x
 dex
 bpl @clear
 OUT 0
hd_prepare:
 ENTER
 lda dos64_files_handle
 cmp #1
 jne reject
 lda hd_readonly
 cmp h_readonly
 jne reject
 lda hd_state
 cmp #HD_WAIT
 jeq reject
 lda dos64_files_state
 cmp #FILES_BUSY
 jeq reject
 lda hd_uncertain
 jne reject
 lda hd_profile
 cmp h_profile
 jne reject
 lda hd_slots
 cmp h_slots
 jne reject
 lda hd_count
 cmp #1
 jne reject
 lda hd_slots
 jeq reject
 cmp #33
 jcs reject
 lda hd_profile
 cmp #2
 jcs reject
 lda hd_op
 cmp #2
 jcs reject
 lda hd_op
 beq :+
 lda h_readonly
 jne reject
:
 lda hd_profile
 beq @small
 lda hd_lba+1
 cmp #$a0
 jcs reject
 bcc @valid
@small:
 lda hd_lba+1
 cmp #$10
 jcs reject
@valid:
 lda hd_lba
 sta h_saved_lba
 and #63
 sta h_sector
 lda hd_lba+1
 sta h_saved_lba+1
 lsr
 sta h_extent+1
 lda hd_lba
 ror
 lsr h_extent+1
 ror
 lsr h_extent+1
 ror
 lsr h_extent+1
 ror
 lsr h_extent+1
 ror
 lsr h_extent+1
 ror
 sta h_extent
 lda #0
 sta hd_error
 sta hd_agreement
 sta hd_request
 lda hd_op
 sta h_saved_op
 jne write_begin
check_mount:
 lda h_mounted
 bne dispatch
 lda #$ff
 sta h_offset
 sta h_offset+1
 lda h_profile
 beq @length_small
 lda #$3f
 sta h_offset+2
 lda #1
 bne @length_top
@length_small:
 lda #$1f
 sta h_offset+2
 lda #0
@length_top:
 sta h_offset+3
 lda #7
 sta h_phase
 jmp request_seek
dispatch:
 lda h_saved_op
 jne write_seek
 ldx #0
@find:
 lda hd_valid,x
 beq @next
 lda hd_tags_lo,x
 cmp h_extent
 bne @next
 lda hd_tags_hi,x
 cmp h_extent+1
 bne @next
 stx h_slot
 jmp read_hit
@next:
 inx
 cpx hd_slots
 bne @find
 ldx h_victim
 stx h_slot
 inx
 cpx hd_slots
 bcc :+
 ldx #0
: stx h_victim
 ldx h_slot
 lda #0
 sta hd_valid,x
 sta h_fill
 ; extent aligned byte offset = extent *32768.
 lda #0
 sta h_offset
 lda h_extent
 lsr
 sta h_offset+2
 lda h_extent+1
 lsr
 sta h_offset+3
 lda h_extent
 and #1
 beq :+
 lda #$80
: sta h_offset+1
 lda h_extent+1
 and #1
 beq :+
 lda h_offset+2
 ora #$80
 sta h_offset+2
: lda #1
 sta h_phase
 jmp request_seek
reject:
 OUT 1
read_hit:
 lda h_sector
 sta h_fill
 jsr cache_address
 lda #1
 sta dos64_reu_request+R_DIRECTION
 jsr data_host
 jsr dma
 jcs dma_error
 lda #HD_DONE
 sta hd_state
 OUT 0
write_begin:
 ; Invalidate every alias before any possible backing-file mutation.
 ldx #0
@inv:
 lda hd_tags_lo,x
 cmp h_extent
 bne @next
 lda hd_tags_hi,x
 cmp h_extent+1
 bne @next
 lda #0
 sta hd_valid,x
@next:
 inx
 cpx hd_slots
 bne @inv
 jsr recovery_address
 lda #0
 sta dos64_reu_request+R_DIRECTION
 jsr command_host
 jsr dma
 jcs dma_error
 lda #1
 sta hd_uncertain
 jmp check_mount
hd_retry:
 ENTER
 lda dos64_files_handle
 cmp #1
 jne reject
 lda dos64_files_state
 cmp #FILES_BUSY
 jeq reject
 lda hd_state
 cmp #HD_FAILED
 jne reject
 lda hd_uncertain
 cmp #1
 jne reject
 lda #0
 sta hd_error
 sta hd_agreement
 jmp check_mount
write_seek:
 jsr sector_offset
 lda #3
 sta h_phase
request_seek:
 ldx #3
@copy: lda h_offset,x
 sta dos64_files_offset,x
 dex
 bpl @copy
 lda #FILES_SEEK
 sta dos64_files_op
 jmp publish
request_read:
 lda #FILES_READ
 sta dos64_files_op
request_count:
 lda #0
 sta dos64_files_count
 lda #2
 sta dos64_files_count+1
publish:
 ; No result from the preceding FILE transaction can satisfy this request.
 lda #FILES_IDLE
 sta dos64_files_state
 lda #0
 sta dos64_files_count_known
 lda #1
 sta hd_request
 lda #HD_WAIT
 sta hd_state
 OUT 0
hd_advance:
 ENTER
 lda hd_state
 cmp #HD_WAIT
 jne reject
 lda hd_request
 cmp #1
 jne reject
 lda dos64_files_state
 cmp #FILES_BUSY
 jeq reject
 cmp #FILES_DONE
 jne file_error
 lda #0
 sta hd_request
 lda h_phase
 cmp #1
 beq @fill_seek_done
 cmp #2
 jeq fill_read_done
 cmp #3
 jeq write_seek_done
 cmp #4
 jeq first_write_done
 cmp #5
 jeq verify_seek_done
 cmp #6
 jeq verify_read_done
 cmp #7
 jeq length_seek_done
 cmp #8
 jeq length_read_done
 cmp #9
 jeq write_done
 jmp file_error
@fill_seek_done:
 lda #2
 sta h_phase
 jmp request_read
length_seek_done:
 lda #8
 sta h_phase
 lda #2
 sta dos64_files_count
 lda #0
 sta dos64_files_count+1
 lda #FILES_READ
 sta dos64_files_op
 jmp publish
length_read_done:
 lda dos64_files_count_known
 cmp #1
 jne length_error
 lda dos64_files_short
 cmp #1
 jne length_error
 lda dos64_files_actual
 cmp #1
 jne length_error
 lda dos64_files_actual+1
 jne length_error
 lda #1
 sta h_mounted
 jmp dispatch
fill_read_done:
 jsr exact_read
 jcs short_error
 jsr cache_address
 lda #0
 sta dos64_reu_request+R_DIRECTION
 jsr data_host
 jsr dma
 jcs dma_error
 inc h_fill
 lda h_fill
 cmp #64
 bne @more
 ldx h_slot
 lda h_extent
 sta hd_tags_lo,x
 lda h_extent+1
 sta hd_tags_hi,x
 lda #1
 sta hd_valid,x
 jmp read_hit
@more:
 jmp request_read
write_seek_done:
 lda #4
 sta h_phase
write_half:
 ; Keep the complete original sector in350000..3501FF. Each independent
 ; FILE WRITE is256bytes; affected C64U firmware corrupts aligned512WRITE.
 ; SEEK overwrites command+4/5, so reload only AFTER seek/preceding WRITE.
 jsr recovery_address
 lda h_phase
 cmp #9
 bne :+
 inc dos64_reu_request+R_REU+1
: lda #1
 sta dos64_reu_request+R_DIRECTION
 jsr command_host
 lda #0
 sta dos64_reu_request+R_LENGTH
 lda #1
 sta dos64_reu_request+R_LENGTH+1
 jsr dos64_reu_transfer
 jcs dma_error
 lda #FILES_WRITE
 sta dos64_files_op
 lda #0
 sta dos64_files_count
 lda #1
 sta dos64_files_count+1
 jmp publish
first_write_done:
 lda #9
 sta h_phase
 jmp write_half
write_done:
 lda #5
 sta h_phase
 jsr sector_offset
 jmp request_seek
verify_seek_done:
 lda #6
 sta h_phase
 jmp request_read
verify_read_done:
 jsr exact_read
 jcs short_error
 jsr recovery_address
 lda #1
 sta dos64_reu_request+R_DIRECTION
 jsr command_host
 jsr dma
 jcs dma_error
 ldx #0
@compare:
 lda dos64_uci_data,x
 cmp dos64_uci_command+4,x
 jne verify_error
 lda dos64_uci_data+256,x
 cmp dos64_uci_command+260,x
 jne verify_error
 inx
 bne @compare
 lda #0
 sta hd_uncertain
 lda #1
 sta hd_agreement
 lda #HD_DONE
 sta hd_state
 OUT 0
exact_read:
 lda dos64_files_count_known
 cmp #1
 bne @bad
 lda dos64_files_short
 bne @bad
 lda dos64_files_actual
 bne @bad
 lda dos64_files_actual+1
 cmp #2
 bne @bad
 clc
 rts
@bad: sec
 rts
sector_offset:
 lda #0
 sta h_offset
 lda h_saved_lba
 asl
 sta h_offset+1
 lda h_saved_lba+1
 rol
 sta h_offset+2
 lda #0
 rol
 sta h_offset+3
 rts
cache_address:
 lda #0
 sta dos64_reu_request+R_REU
 lda h_fill
 asl
 sta dos64_reu_request+R_REU+1
 lda h_slot
 lsr
 clc
 adc #$20
 sta dos64_reu_request+R_REU+2
 lda h_slot
 and #1
 beq :+
 lda dos64_reu_request+R_REU+1
 ora #$80
 sta dos64_reu_request+R_REU+1
: rts
recovery_address:
 lda #0
 sta dos64_reu_request+R_REU
 sta dos64_reu_request+R_REU+1
 lda #$35
 sta dos64_reu_request+R_REU+2
 rts
data_host:
 lda #<dos64_uci_data
 sta dos64_reu_request+R_HOST
 lda #>dos64_uci_data
 sta dos64_reu_request+R_HOST+1
 rts
command_host:
 lda #<(dos64_uci_command+4)
 sta dos64_reu_request+R_HOST
 lda #>(dos64_uci_command+4)
 sta dos64_reu_request+R_HOST+1
 rts
dma:
 lda #0
 sta dos64_reu_request+R_LENGTH
 lda #2
 sta dos64_reu_request+R_LENGTH+1
 jmp dos64_reu_transfer
length_error:
 lda #6
 bne failure
file_error:
 lda #HD_ERR_FILE
 bne failure
short_error:
 lda #HD_ERR_SHORT
 bne failure
dma_error:
 lda #HD_ERR_DMA
 bne failure
verify_error:
 lda #HD_ERR_VERIFY
failure:
 sta hd_error
 lda #0
 sta hd_request
 lda #HD_FAILED
 sta hd_state
 OUT 0
hd_chs_to_lba:
 ENTER
 lda hd_state
 cmp #HD_WAIT
 jeq reject
 lda hd_uncertain
 jne reject
 lda hd_count
 cmp #1
 jne reject
 lda hd_cl
 and #$3f
 beq @invalid
 cmp #17
 bcs @invalid
 lda h_profile
 bne @large
 lda hd_cl
 and #$c0
 bne @invalid
 lda hd_ch
 cmp #128
 bcs @invalid
 lda hd_dh
 cmp #2
 bcs @invalid
 ldx #5
 bne @calculate
@large:
 lda hd_cl
 and #$c0
 cmp #$80
 bcc @head
 bne @invalid
 lda hd_ch
 cmp #128
 bcs @invalid
@head:
 lda hd_dh
 cmp #4
 bcs @invalid
 ldx #6
@calculate:
 lda hd_cl
 lsr
 lsr
 lsr
 lsr
 lsr
 lsr
 sta h_extent+1
 lda hd_ch
 sta h_extent
@shift:
 asl h_extent
 rol h_extent+1
 dex
 bne @shift
 lda hd_dh
 asl
 asl
 asl
 asl
 sta hd_lba
 lda hd_cl
 and #$3f
 sec
 sbc #1
 ora hd_lba
 ora h_extent
 sta hd_lba
 lda h_extent+1
 sta hd_lba+1
 OUT 0
@invalid:
 OUT 1
hd_code_end:
