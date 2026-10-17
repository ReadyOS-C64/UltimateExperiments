.setcpu "6502"
.macpack longbranch
.include "abi.inc"
.include "reu.inc"
 .include "floppy_format.inc"
.if DOS64_FLOPPY_FORMAT
.import dos64_guest,dos64_disk_host_error,dos64_disk_cf,dos64_disk_last_status
.import dos64_disk_reu_base,dos64_disk_b_descriptor,dos64_disk_readonly,dos64_disk_dirty,dos64_disk_exhausted,dos64_disk_content_generation
.import dos64_physical,dos64_mem_read,dos64_reu_request,dos64_reu_transfer,dos64_range_buffer
.importzp dos64_segment,dos64_offset,dos64_address
.export dos64_floppy_format_native
.segment "DEVICESTATE"
ff_drive:.res 1
ff_bank:.res 1
ff_track:.res 1
ff_head:.res 1
ff_left:.res 1
ff_seen:.res 1
ff_nine:.res 1
ff_fill:.res 1
ff_lba:.res 2
.segment "FORMATCODE"
; Called only from the resident selector8 veneer. No C900 DISK frame exists.
; Full supported360K track,9 unique N=2 IDs. No FDC/media-change emulation.
dos64_floppy_format_native:
 php
 sei
 cld
 lda dos64_guest+G_AX
 sta ff_left
 lda #0
 sta dos64_guest+G_AX
 sta dos64_disk_host_error
 sta ff_seen
 sta ff_nine
 lda dos64_guest+G_DX
 cmp #2
 jcs ff_not_ready
 sta ff_drive
 lda #<dos64_disk_reu_base
 ldx #>dos64_disk_reu_base
 ldy ff_drive
 beq :+
 lda #<dos64_disk_b_descriptor
 ldx #>dos64_disk_b_descriptor
: sta dos64_segment
 stx dos64_segment+1
 ldy #9
 lda (dos64_segment),y
 jeq ff_not_ready
: lda (dos64_segment),y
 cmp ff_geometry-3,y
 jne ff_sector
 dey
 cpy #2
 bne :-
 lda (dos64_segment),y
 sta ff_bank
 cmp #$10
 beq :+
 cmp #$18
 beq :+
 cmp #$38
 jne ff_controller
: dey
 lda (dos64_segment),y
 dey
 ora (dos64_segment),y
 jne ff_controller
 ldx ff_drive
 lda dos64_disk_readonly,x
 jne ff_protect
 lda dos64_guest+G_AX+1
 cmp #5
 jne ff_command
 ; Full supported track requires nine four-byte descriptors.
 lda ff_left
 cmp #9
 jne ff_sector
 lda dos64_guest+G_CX
 and #$c0
 jne ff_sector
 lda dos64_guest+G_CX+1
 cmp #40
 jcs ff_sector
 sta ff_track
 lda dos64_guest+G_DX+1
 cmp #2
 jcs ff_sector
 sta ff_head
 lda dos64_guest+G_ES
 sta dos64_segment
 lda dos64_guest+G_ES+1
 sta dos64_segment+1
 lda dos64_guest+G_BX
 sta dos64_offset
 lda dos64_guest+G_BX+1
 sta dos64_offset+1
 jsr dos64_physical
 clc
 lda dos64_address
 adc #35
 lda dos64_address+1
 adc #0
 jcs ff_dma
@id:
 jsr ff_get
 jcs ff_memory
 cmp ff_track
 jne ff_sector
 jsr ff_get
 jcs ff_memory
 cmp ff_head
 jne ff_sector
 jsr ff_get
 jcs ff_memory
 tax
 dex
 cpx #9
 jcs ff_sector
 lda ff_bits,x
 beq @nine
 and ff_seen
 jne ff_sector
 lda ff_bits,x
 ora ff_seen
 sta ff_seen
 jmp @size
@nine:
 inc ff_nine
 lda ff_nine
 cmp #1
 jne ff_sector
@size:
 jsr ff_get
 jcs ff_memory
 cmp #2
 jne ff_sector
 dec ff_left
 jne @id
 ; Honor the guest's current INT1Eh diskette parameter fill byte (offset8).
 lda #$78
 sta dos64_address
 lda #0
 sta dos64_address+1
 sta dos64_address+2
 jsr ff_get
 jcs ff_memory
 sta dos64_offset
 jsr ff_get
 jcs ff_memory
 sta dos64_offset+1
 jsr ff_get
 jcs ff_memory
 sta dos64_segment
 jsr ff_get
 jcs ff_memory
 sta dos64_segment+1
 clc
 lda dos64_offset
 adc #8
 sta dos64_offset
 bcc :+
 inc dos64_offset+1
: jsr dos64_physical
 jsr dos64_mem_read
 jcs ff_memory
 sta ff_fill
 ; Conservative dirty/generation policy matches ordinary disk writes.
 ldx ff_drive
 lda #1
 sta dos64_disk_dirty,x
 txa
 asl
 asl
 tax
 ldy #4
: inc dos64_disk_content_generation,x
 bne @marked
 inx
 dey
 bne :-
 ldx ff_drive
 lda #1
 sta dos64_disk_exhausted,x
 txa
 asl
 asl
 tax
 lda #$ff
 ldy #4
: sta dos64_disk_content_generation,x
 inx
 dey
 bne :-
@marked:
 ldx #0
 lda ff_fill
: sta dos64_range_buffer,x
 inx
 bne :-
 ; LBA=(track*2+head)*9; shift9 and add whole-owned arena bank.
 lda ff_track
 asl
 ora ff_head
 sta ff_lba
 lda #0
 sta ff_lba+1
 asl ff_lba
 rol ff_lba+1
 asl ff_lba
 rol ff_lba+1
 asl ff_lba
 rol ff_lba+1
 lda ff_track
 asl
 ora ff_head
 clc
 adc ff_lba
 sta ff_lba
 lda ff_lba+1
 adc #0
 sta ff_lba+1
 asl ff_lba
 rol ff_lba+1
 lda ff_lba
 sta dos64_reu_request+R_REU+1
 lda ff_lba+1
 clc
 adc ff_bank
 sta dos64_reu_request+R_REU+2
 lda #0
 sta dos64_reu_request+R_REU
 sta dos64_reu_request+R_LENGTH
 sta dos64_reu_request+R_DIRECTION
 lda #1
 sta dos64_reu_request+R_LENGTH+1
 lda #<dos64_range_buffer
 sta dos64_reu_request+R_HOST
 lda #>dos64_range_buffer
 sta dos64_reu_request+R_HOST+1
 lda #18
 sta ff_left
@page:
 jsr dos64_reu_transfer
 bcs ff_transfer
 inc dos64_reu_request+R_REU+1
 bne :+
 inc dos64_reu_request+R_REU+2
: dec ff_left
 bne @page
 lda #9
 sta dos64_guest+G_AX
 lda #0
 beq ff_return
ff_transfer:
 lda #18
 sec
 sbc ff_left
 lsr
 sta dos64_guest+G_AX
ff_controller:
 lda #$20
 bne ff_error
ff_memory:
 lda #1
 sta dos64_disk_host_error
 bne ff_controller
ff_not_ready:
 lda #$80
 bne ff_error
ff_protect:
 lda #3
 bne ff_error
ff_dma:
 lda #9
 bne ff_error
ff_sector:
 lda #4
 bne ff_error
ff_command:
 lda #1
ff_error:
 ldx #1
 stx dos64_disk_cf
 sec
 jmp ff_status
ff_return:
 ldx #0
 stx dos64_disk_cf
 clc
ff_status:
 sta dos64_guest+G_AX+1
 sta dos64_disk_last_status
 ldx dos64_disk_cf
 bne @carry
 plp
 clc
 rts
@carry:
 plp
 sec
 rts
ff_get:
 jsr dos64_mem_read
 bcs :+
 pha
 inc dos64_address
 bne @pop
 inc dos64_address+1
@pop:
 pla
: rts
ff_bits:.byte 1,2,4,8,16,32,64,128,0
ff_geometry:.byte $d0,2,40,0,2,9,1

.endif
