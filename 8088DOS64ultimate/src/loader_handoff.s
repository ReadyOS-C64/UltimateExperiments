.setcpu "6502"
.macpack longbranch
.include "reu.inc"
.include "disk.inc"
.include "overlays.inc"
.import dos64_reu_request,dos64_reu_transfer
.import dos64_native_config,hdc_config
.import dos64_floppy_request,dos64_floppy_control,dos64_files_handle
.import __FILECODE_SIZE__,__LOADERADOPT_SIZE__,__LOADERADOPT_LOAD__
.importzp dos64_segment,dos64_offset,dos64_address
.export dos64_loader_required,dos64_loader_validate,dos64_loader_adopt
.export dos64_options_required,dos64_options_validate
.import dos64_bios_initial_mode
.export dos64_loader_code_start,dos64_loader_code_end
.export dos64_loader_install,dos64_loader_adopt_end
.segment "NATIVESTATE"
dos64_loader_required: .byte 0
dos64_options_required: .byte 0
.segment "LOADERCOLD"
dos64_loader_code_start:
; This initialized RAM is discarded only when native text/bitmap takes over.
lh_crc_value: .res 4,0
lh_cfg_crc: .res 4,0
lh_lengths: .res 4,0
lh_last: .byte 0
lh_field: .byte 0
lh_drive: .byte 0
lh_pages: .word 0
lh_poly: .byte $20,$83,$b8,$ed
lh_header: .byte "D64R",1,$a5,32,0
lh_cfg_header: .byte "D64C",1,$40,2,0
lh_field_mask: .byte 1,1,2,4
lh_illegal: .byte $5c,$3a,$22,$2a,$3c,$3e,$3f,$7c
lh_bad:
 sec
 rts
lh_ok:
 clc
 rts
; Standard reflected CRC32. Pointer/length are exclusive CPU address scratch.
lh_crc_init:
 lda #$ff
 ldx #3
: sta lh_crc_value,x
 dex
 bpl :-
 rts
lh_crc_run:
@byte:
 ldy #0
 lda (dos64_segment),y
 eor lh_crc_value
 sta lh_crc_value
 ldy #8
@bit:
 lsr lh_crc_value+3
 ror lh_crc_value+2
 ror lh_crc_value+1
 ror lh_crc_value
 bcc @shifted
 ldx #3
@xor:
 lda lh_crc_value,x
 eor lh_poly,x
 sta lh_crc_value,x
 dex
 bpl @xor
@shifted:
 dey
 bne @bit
@next:
 inc dos64_segment
 bne :+
 inc dos64_segment+1
: lda dos64_offset
 bne :+
 dec dos64_offset+1
: dec dos64_offset
 lda dos64_offset
 ora dos64_offset+1
 bne @byte
 rts
lh_crc_check:
 ldy #3
: lda lh_crc_value,y
 eor #$ff
 cmp (dos64_address),y
 bne lh_bad
 dey
 bpl :-
 clc
 rts
; CFG body bytes0..571. Caller separately checks its stored checksum.
lh_crc_cfg:
 jsr lh_crc_init
 lda #$20
 sta dos64_segment
 lda #$c1
 sta dos64_segment+1
 lda #<$23c
 sta dos64_offset
 lda #>$23c
 sta dos64_offset+1
 jmp lh_crc_run
 ; Anchor DMA: A=low offset, X/Y=countLE, C=1fetch/0stash.
lh_anchor:
 sta dos64_reu_request+R_HOST
 sta dos64_reu_request+R_REU
 lda #$c1
 sta dos64_reu_request+R_HOST+1
 lda #$f0
 sta dos64_reu_request+R_REU+1
 lda #$3f
 sta dos64_reu_request+R_REU+2
 stx dos64_reu_request+R_LENGTH
 sty dos64_reu_request+R_LENGTH+1
 lda #0
 rol
 sta dos64_reu_request+R_DIRECTION
 jmp dos64_reu_transfer
dos64_loader_validate:
 lda dos64_loader_required
 jeq lh_ok
 cmp #$a5
 bne @invalid1
 lda $fffa
 cmp #$82
 bne @invalid1
 lda $fffb
 cmp #$58
 bne @invalid1
 lda $5882
 cmp #$40
 bne @invalid1
 ; Fetch header+CFG as one bounded read from the fixed anchor.
 lda #0
 ldx #$60
 ldy #2
 sec
 jsr lh_anchor
 bcs @invalid1
 jmp @header_begin
@invalid1:
 sec
 rts
@header_begin:
 ldx #7
@headers:
 lda $c100,x
 cmp lh_header,x
 bne @invalid1
 lda $c120,x
 cmp lh_cfg_header,x
 bne @invalid1
 dex
 bpl @headers
 jsr lh_crc_init
 lda #0
 sta dos64_segment
 lda #$c1
 sta dos64_segment+1
 lda #28
 sta dos64_offset
 lda #0
 sta dos64_offset+1
 jsr lh_crc_run
 lda #$1c
 sta dos64_address
 lda #$c1
 sta dos64_address+1
 jsr lh_crc_check
 bcs @invalid2
 jmp @cfg_checksum
@invalid2:
 sec
 rts
@cfg_checksum:
 jsr lh_crc_cfg
 lda #$5c
 sta dos64_address
 lda #$c3
 sta dos64_address+1
 jsr lh_crc_check
 bcs @invalid2
 lda #8
 sta dos64_address
 lda #$c1
 sta dos64_address+1
 jsr lh_crc_check
 bcs @invalid2
 ldx #3
@capture:
 lda $c108,x
 sta lh_cfg_crc,x
 dex
 bpl @capture
 ; Reserved fields and semantic flags/profile/capacity.
 lda $c32e
 ora $c32f
 bne @invalid3
 ldx #29
@reserved:
 lda $c33e,x
 bne @invalid3
 dex
 bpl @reserved
 lda $c338
 cmp #1
 bne @invalid3
 lda $c339
 ora $c328
 ora $c329
 ora $c32b
 ora $c33a
 ora $c33b
 bne @invalid3
 lda $c32d
 and #$f9
 cmp #1
 bne @invalid3
 lda $c32c
 and #$f8
 bne @invalid3
 lda $c32d
 eor #$ff
 and $c32c
 bne @invalid3
 lda $c32a
 cmp #2
 bcs @invalid3
 cmp #0
 beq @profile_ok
 lda $c32d
 and #4
 beq @invalid3
@profile_ok:
 jmp @capacity
@invalid3:
 sec
 rts
@capacity:
 lda $c33d
 cmp #2
 bcs @invalid3
 cmp #1
 beq @capacity16
 lda $c33c
 cmp #$40
 bcc @invalid3
 jmp @capacity_ok
@capacity16:
 lda $c33c
 bne @invalid3
@capacity_ok:
 lda $c32d
 and #2
 bne @crc_bind
 lda $c334
 ora $c335
 ora $c336
 ora $c337
 bne @invalid3
@crc_bind:
 ldx #7
: lda $c110,x
 cmp $c330,x
 bne @invalid4
 dex
 bpl :-
 lda $c11a
 cmp #1
 bne @invalid4
 lda $c11b
 cmp #2
 bne @invalid4
 lda $c118
 cmp #$1c
 beq @base_normal
 cmp #$fc
 bne @invalid4
 lda $c119
 cmp #$df
 bne @invalid4
 beq @paths
@base_normal:
 lda $c119
 cmp #$de
 beq @paths
 cmp #$df
 bne @invalid4
 jmp @paths
@invalid4:
 sec
 rts
@paths:
 lda #$28
 sta dos64_segment
 lda #$c1
 sta dos64_segment+1
 lda #0
 sta lh_field
@field:
 ldx lh_field
 lda lh_field_mask,x
 and $c32d
 tax
 jsr lh_path
 bcs @invalid4
 ldx lh_field
 tya
 sta lh_lengths,x
 cpx #0
 beq :+
 cpy #2
 bcs :+
 lda lh_field_mask,x
 and $c32d
 bne @invalid4
: clc
 lda dos64_segment
 adc #128
 sta dos64_segment
 bcc :+
 inc dos64_segment+1
: inc lh_field
 lda lh_field
 cmp #4
 bne @field
 ; All CFG semantics validated before changing D64N/D64H.
 lda #$a5
 sta dos64_native_config+4
 lda $c33d
 bne @sixteen
 lda $c33c
 lsr
 lsr
 lsr
 lsr
 bne @mib
@sixteen:
 lda #16
@mib:
 sta dos64_native_config+5
 lda #1
 sta dos64_native_config+6
 sta hdc_config+5
 lda lh_lengths+1
 clc
 adc #1
 sta dos64_native_config+7
 lda $c118
 sta dos64_native_config+8
 lda $c119
 sta dos64_native_config+9
 ldx #3
: lda $c330,x
 sta dos64_native_config+10,x
 dex
 bpl :-
 ldx #127
: lda $c1a8,x
 sta dos64_native_config+14,x
 lda $c2a8,x
 sta hdc_config+12,x
 dex
 bpl :-
 lda $c32d
 and #4
 beq :+
 lda #$a5
: sta hdc_config+4
 lda $c32a
 sta hdc_config+6
 lda $c32c
 lsr
 lsr
 and #1
 sta hdc_config+7
 lda #0
 sta hdc_config+8
 lda #2
 sta hdc_config+9
 lda #32
 sta hdc_config+10
 lda lh_lengths+3
 clc
 adc #1
 sta hdc_config+11
 ; Consume only a completely validated handoff, before native takeover.
 lda #0
 sta $c105
 lda #5
 ldx #1
 ldy #0
 clc
 jmp lh_anchor
; X=presence, ptr=one128-byte field. Y=length. Canonical ASCII/padding.
lh_path:
 ldy #0
 cpx #0
 beq @padding
 lda (dos64_segment),y
 cmp #$2f
 bne @bad
 iny
 lda #0
 sta lh_last
@char:
 lda (dos64_segment),y
 beq @end
 cmp #$2f
 beq @separator
 cmp #$20
 bcc @bad
 cmp #$7f
 bcs @bad
 ldx #7
@illegal:
 cmp lh_illegal,x
 beq @bad
 dex
 bpl @illegal
 sta lh_last
 bne @advance
@separator:
 jsr lh_component
 bcs @bad
 lda #0
 sta lh_last
@advance:
 iny
 bpl @char
@bad:
 sec
 rts
@end:
 cpy #1
 beq @root
 jsr lh_component
 bcs @bad
@root:
 tya
 pha
 iny
 bpl @padding_present
 pla
 tay
 clc
 rts
@padding_present:
 lda (dos64_segment),y
 bne @padding_bad
 iny
 bpl @padding_present
 pla
 tay
 clc
 rts
@padding_bad:
 pla
 jmp @bad
@padding:
 lda (dos64_segment),y
 bne @bad
 iny
 bpl @padding
 ldy #0
 clc
 rts
lh_component:
 lda lh_last
 beq @bad
 cmp #$20
 beq @bad
 cmp #$2e
 beq @bad
 clc
 rts
@bad:
 sec
 rts
; Bootstrap has committed all startup images to REU. Move the separately linked
; trailing FILE data to6000, then compare every byte to untouched packaged RAM.
; Only the required START path may call this: START verified the full PRG CRC.
dos64_loader_install:
 ldx #7
: lda lh_install_request,x
 sta dos64_reu_request,x
 dex
 bpl :-
 jsr dos64_reu_transfer
 jcs lh_bad
 ldx #0
@page:
 lda OV_SOURCE+OV_HEADER+__FILECODE_SIZE__,x
 cmp $6000,x
 jne lh_bad
 inx
 bne @page
 ldx #<(__LOADERADOPT_SIZE__-$100)-1
@tail:
 lda OV_SOURCE+OV_HEADER+__FILECODE_SIZE__+$100,x
 cmp $6100,x
 jne lh_bad
 dex
 bpl @tail
 clc
 rts
lh_install_request:
 .word $6000
 .faraddr OV_ASSETS+OV_HEADER+__FILECODE_SIZE__
 .word __LOADERADOPT_SIZE__
 .byte 1
dos64_loader_code_end:
.assert __LOADERADOPT_SIZE__ > $100 .and __LOADERADOPT_SIZE__ <= $180,lderror,"helper compare loop bounds"
.assert $6000+__LOADERADOPT_SIZE__ <= OV_SOURCE+OV_HEADER+__FILECODE_SIZE__,lderror,"helper copy overlaps untouched packaged source"
.assert __LOADERADOPT_LOAD__ = OV_WINDOW+__FILECODE_SIZE__,lderror,"helper must be FILE trailing data"
.segment "LOADERADOPT"
dos64_loader_adopt:
 ; Cold-only caller has initialized FILES but has not submitted a command.
 lda dos64_files_handle
 jne lh_bad
 lda #$20
 ldx #$40
 ldy #2
 sec
 jsr lh_anchor
 jcs lh_bad
 jsr lh_crc_cfg
 lda #<lh_cfg_crc
 sta dos64_address
 lda #>lh_cfg_crc
 sta dos64_address+1
 jsr lh_crc_check
 jcs lh_bad
 ldx #3
: lda $c35c,x
 cmp lh_cfg_crc,x
 jne lh_bad
 dex
 bpl :-
 lda #0
 sta lh_drive
@drive:
 lda #0
 ldx #FQ_SIZE-1
: sta dos64_floppy_request,x
 dex
 bpl :-
 lda #FOP_PREPARE
 sta dos64_floppy_request+FQ_OP
 lda lh_drive
 sta dos64_floppy_request+FQ_DRIVE
 tax
 lda $c32c
 cpx #0
 beq :+
 lsr
: and #1
 sta dos64_floppy_request+FQ_FLAGS
 lda dos64_native_config+5
 sta dos64_floppy_request+FQ_CAPACITY
 jsr dos64_floppy_control
 jcs lh_bad
 lda dos64_floppy_request+FQ_BASE
 ora dos64_floppy_request+FQ_BASE+1
 jne lh_bad
 lda lh_drive
 beq @bank_a
 lda #$18
 bne @bank
@bank_a:
 lda #$10
@bank:
 cmp dos64_floppy_request+FQ_BASE+2
 jne lh_bad
 sta dos64_reu_request+R_REU+2
 lda #0
 sta dos64_reu_request+R_REU
 sta dos64_reu_request+R_REU+1
 sta dos64_reu_request+R_HOST
 sta dos64_reu_request+R_LENGTH
 lda #$c4
 sta dos64_reu_request+R_HOST+1
 lda #1
 sta dos64_reu_request+R_LENGTH+1
 sta dos64_reu_request+R_DIRECTION
 lda #$a0
 sta lh_pages
 lda #5
 sta lh_pages+1
 jsr lh_crc_init
@page:
 jsr dos64_reu_transfer
 jcs lh_bad
 lda #0
 sta dos64_segment
 sta dos64_offset
 lda #$c4
 sta dos64_segment+1
 lda #1
 sta dos64_offset+1
 jsr lh_crc_run
 inc dos64_reu_request+R_REU+1
 bne :+
 inc dos64_reu_request+R_REU+2
: lda lh_pages
 bne :+
 dec lh_pages+1
: dec lh_pages
 lda lh_pages
 ora lh_pages+1
 bne @page
 lda lh_drive
 asl
 asl
 clc
 adc #$30
 sta dos64_address
 lda #$c3
 sta dos64_address+1
 jsr lh_crc_check
 jcs lh_bad
 ldy #3
: lda (dos64_address),y
 sta dos64_floppy_request+FQ_BIND,y
 dey
 bpl :-
 lda #FOP_COMMIT
 sta dos64_floppy_request+FQ_OP
 lda #$a5
 sta dos64_floppy_request+FQ_COMPLETE
 jsr dos64_floppy_control
 jcs lh_bad
 lda lh_drive
 bne @done
 lda $c32d
 and #2
 beq @done
 inc lh_drive
 jmp @drive
@done:
 clc
 rts
dos64_loader_adopt_end:

.segment "COLDINIT"
options_header: .byte "D64O",1,$a5,32,0
options_request: .byte 0,$c4,0,$f5,$3f,32,0,1
options_bad:
 sec
 rts
options_ok:
 clc
 rts
; Current validated D64R header remains C100 until FILES initialization.
; The initial setting is consumed only on the matched required path; legacy
; entry restores mode3 and ignores surviving REU options without reading them.
dos64_options_validate:
 lda #3
 sta dos64_bios_initial_mode
 lda dos64_options_required
 beq options_ok
 cmp #$a5
 bne options_bad
 lda dos64_loader_required
 cmp #$a5
 bne options_bad
 lda #0
 ldx #31
@poison_options:
 sta $c400,x
 dex
 bpl @poison_options
 ldx #7
@request:
 lda options_request,x
 sta dos64_reu_request,x
 dex
 bpl @request
 jsr dos64_reu_transfer
 jcs options_bad
 ldx #7
@header:
 lda $c400,x
 cmp options_header,x
 bne options_bad
 lda $c408,x
 cmp $c108,x
 bne options_bad
 dex
 bpl @header
 ldx #27
@reserved:
 lda $c400,x
 bne options_bad
 dex
 cpx #16
 bne @reserved
 lda $c410
 cmp #40
 beq @value_ok
 cmp #80
 bne options_bad
@value_ok:
 jsr lh_crc_init
 lda #0
 sta dos64_segment
 lda #$c4
 sta dos64_segment+1
 lda #28
 sta dos64_offset
 lda #0
 sta dos64_offset+1
 jsr lh_crc_run
 lda #$1c
 sta dos64_address
 lda #$c4
 sta dos64_address+1
 jsr lh_crc_check
 jcs options_bad
 ; Consume readiness before publishing the validated frequent setting.
 lda #0
 sta $c405
 lda #5
 sta dos64_reu_request+R_HOST
 sta dos64_reu_request+R_REU
 lda #1
 sta dos64_reu_request+R_LENGTH
 lda #0
 sta dos64_reu_request+R_DIRECTION
 jsr dos64_reu_transfer
 jcs options_bad
 ; Prove one-shot consumption independently, including suppressed DMA writes.
 lda #$a5
 sta $c405
 lda #1
 sta dos64_reu_request+R_DIRECTION
 jsr dos64_reu_transfer
 jcs options_bad
 lda $c405
 jne options_bad
 lda $c410
 cmp #40
 jne options_ok
 lda #1
 sta dos64_bios_initial_mode
 clc
 rts
