.include "abi.inc"
.include "disk.inc"
.include "reu.inc"
.include "range.inc"
.macpack longbranch
.import dos64_guest, dos64_physical
.importzp dos64_segment, dos64_offset, dos64_address
.import dos64_range_request, dos64_range_copy, dos64_range_buffer
.import dos64_reu_request, dos64_reu_transfer
.export dos64_disk_init, dos64_disk_transfer
.export dos64_disk_reu_base, dos64_disk_sectors, dos64_disk_cylinders
.export dos64_disk_heads, dos64_disk_spt, dos64_disk_loaded, dos64_disk_last_status
.export dos64_disk_host_error

.segment "BSS"
dos64_disk_reu_base: .res 3
dos64_disk_sectors: .res 2
dos64_disk_cylinders: .res 2
dos64_disk_heads: .res 1
dos64_disk_spt: .res 1
dos64_disk_loaded: .res 1
dos64_disk_last_status: .res 1
dos64_disk_host_error: .res 1 ; only fatal coherent guest-cache access failure
disk_function: .res 1
disk_count: .res 1
disk_lba: .res 2
disk_product: .res 2
disk_sector: .res 1
disk_end: .res 3

.segment "CODE"
; Explicit cold configuration. The caller owns loading the complete image
; before setting loaded. No data initializer or loader silently claims media.
dos64_disk_init:
    php
    sei
    cld
    lda #0
    sta dos64_disk_reu_base
    sta dos64_disk_reu_base+1
    sta dos64_disk_cylinders+1
    sta dos64_disk_loaded
    sta dos64_disk_last_status
    sta dos64_disk_host_error
    lda #$10
    sta dos64_disk_reu_base+2
    lda #<$02D0
    sta dos64_disk_sectors
    lda #>$02D0
    sta dos64_disk_sectors+1
    lda #40
    sta dos64_disk_cylinders
    lda #2
    sta dos64_disk_heads
    lda #9
    sta dos64_disk_spt
    plp
    clc
    rts

; Native INT13 sector primitive, not the interrupt-frame wrapper. Only guest
; AX is changed; A/AH=status, AL=completed sectors, host C reports failure.
; Guest FLAGS are untouched. PHP/SEI/CLD preserves host P except returned C.
; Status/DMA reference: IBM XT 1982-11-08 source archived in pcjs commit
; b4a910e606d87137e977ec89ce816f05a31c366a, XTBIOS.ASM status equates and
; DMA_SETUP/RW_OPN. Only interface behavior is used; no BIOS source copied.
; Policy: linear CHS requests may cross tracks/heads within the loaded image.
; Raw images have no stored physical CRC; verify proves readable REU data,
; without comparing a guest buffer or claiming magnetic-media CRC validation.
dos64_disk_transfer:
    php
    sei
    cld
    lda dos64_guest+G_AX
    sta disk_count
    lda dos64_guest+G_AX+1
    sta disk_function
    lda #0
    sta dos64_disk_host_error
    sta dos64_range_request+GR_ERROR
    sta dos64_range_request+GR_STATUS
    sta dos64_guest+G_AX
    lda disk_function
    beq @drive
    cmp #2
    jcc disk_bad_command
    cmp #5
    jcs disk_bad_command
@drive:
    lda dos64_guest+G_DX
    jne disk_not_ready
    lda disk_function
    jeq disk_success
    lda dos64_disk_loaded
    jeq disk_not_ready
    lda disk_count
    jeq disk_bad_sector
    cmp #128
    jcs disk_bad_sector
    ; Validate geometry and its exact configured image size before CHS math.
    lda dos64_disk_heads
    jeq disk_bad_sector
    lda dos64_disk_spt
    jeq disk_bad_sector
    cmp #64
    jcs disk_bad_sector
    lda dos64_disk_cylinders
    ora dos64_disk_cylinders+1
    jeq disk_bad_sector
    lda dos64_disk_cylinders+1
    cmp #4
    jcc @geometry
    jne disk_bad_sector
    lda dos64_disk_cylinders
    jne disk_bad_sector
@geometry:
    lda dos64_disk_cylinders
    sta disk_lba
    lda dos64_disk_cylinders+1
    sta disk_lba+1
    ldx dos64_disk_heads
    jsr disk_multiply
    jcs disk_bad_sector
    ldx dos64_disk_spt
    jsr disk_multiply
    jcs disk_bad_sector
    lda disk_lba
    cmp dos64_disk_sectors
    jne disk_bad_sector
    lda disk_lba+1
    cmp dos64_disk_sectors+1
    jne disk_bad_sector
    jsr disk_byte_address
    jcs disk_controller_error
    ; Whole slot must lie outside guest backing and inside minimum 4 MiB REU.
    lda dos64_disk_reu_base+2
    cmp #$10
    jcc disk_controller_error
    lda dos64_range_request+GR_REU
    sta disk_end
    lda dos64_range_request+GR_REU+1
    sta disk_end+1
    lda dos64_range_request+GR_REU+2
    sta disk_end+2
    cmp #$40
    jcc @chs
    jne disk_controller_error
    lda disk_end
    ora disk_end+1
    jne disk_controller_error
@chs:
    lda dos64_guest+G_CX
    and #$3F
    jeq disk_bad_sector
    cmp dos64_disk_spt
    bcc @sector
    jne disk_bad_sector
@sector:
    sec
    sbc #1
    sta disk_sector
    lda dos64_guest+G_CX+1
    sta disk_lba
    lda dos64_guest+G_CX
    lsr
    lsr
    lsr
    lsr
    lsr
    lsr
    sta disk_lba+1
    cmp dos64_disk_cylinders+1
    jcc @cylinder
    jne disk_bad_sector
    lda disk_lba
    cmp dos64_disk_cylinders
    jcs disk_bad_sector
@cylinder:
    lda dos64_guest+G_DX+1
    cmp dos64_disk_heads
    jcs disk_bad_sector
    ldx dos64_disk_heads
    jsr disk_multiply
    jcs disk_bad_sector
    clc
    lda disk_lba
    adc dos64_guest+G_DX+1
    sta disk_lba
    lda disk_lba+1
    adc #0
    sta disk_lba+1
    jcs disk_bad_sector
    ldx dos64_disk_spt
    jsr disk_multiply
    jcs disk_bad_sector
    clc
    lda disk_lba
    adc disk_sector
    sta disk_lba
    lda disk_lba+1
    adc #0
    sta disk_lba+1
    jcs disk_bad_sector
    clc
    lda disk_lba
    adc disk_count
    sta disk_product
    lda disk_lba+1
    adc #0
    sta disk_product+1
    jcs disk_bad_sector
    cmp dos64_disk_sectors+1
    jcc @address
    jne disk_bad_sector
    lda disk_product
    cmp dos64_disk_sectors
    bcc @address
    jne disk_bad_sector
@address:
    jsr disk_byte_address
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
@guest:
    lda dos64_address,x
    sta dos64_range_request+GR_GUEST,x
    dex
    bpl @guest
    lda #0
    sta dos64_range_request+GR_LENGTH
    sta dos64_range_request+GR_DONE
    sta dos64_range_request+GR_DONE+1
    lda disk_count
    asl
    sta dos64_range_request+GR_LENGTH+1
    ; The DMA page is physical, not merely the ES:BX offset window.
    clc
    adc dos64_address+1
    bcc @dispatch
    ora dos64_address
    jne disk_dma_error        ; exact end at 10000 is permitted
@dispatch:
    lda disk_function
    cmp #4
    jeq disk_verify
    cmp #3
    lda #0
    rol
    sta dos64_range_request+GR_DIRECTION
    jsr dos64_range_copy
    jcs disk_partial_error
    lda disk_count
    sta dos64_guest+G_AX
    jmp disk_success

; Checked unsigned 16-bit LBA *= X, bounded by at most 255 additions.
disk_multiply:
    lda #0
    sta disk_product
    sta disk_product+1
@add:
    clc
    lda disk_product
    adc disk_lba
    sta disk_product
    lda disk_product+1
    adc disk_lba+1
    sta disk_product+1
    bcs @overflow
    dex
    bne @add
    lda disk_product
    sta disk_lba
    lda disk_product+1
    sta disk_lba+1
    clc
@overflow:
    rts

; Compute configured REU base + LBA*512 with 24-bit checked addition.
disk_byte_address:
    lda disk_lba
    sta dos64_range_request+GR_REU
    lda disk_lba+1
    sta dos64_range_request+GR_REU+1
    lda #0
    sta dos64_range_request+GR_REU+2
    ldx #9
@shift:
    asl dos64_range_request+GR_REU
    rol dos64_range_request+GR_REU+1
    rol dos64_range_request+GR_REU+2
    bcs @overflow
    dex
    bne @shift
    clc
    lda dos64_range_request+GR_REU
    adc dos64_disk_reu_base
    sta dos64_range_request+GR_REU
    lda dos64_range_request+GR_REU+1
    adc dos64_disk_reu_base+1
    sta dos64_range_request+GR_REU+1
    lda dos64_range_request+GR_REU+2
    adc dos64_disk_reu_base+2
    sta dos64_range_request+GR_REU+2
@overflow:
    rts

disk_verify:
    ; Use <=256 byte aligned chunks, including arbitrary image base offsets.
    lda #0
    sta disk_product
    lda #1
    sta disk_product+1
    lda dos64_range_request+GR_REU
    beq @remaining
    eor #$FF
    clc
    adc #1
    sta disk_product
    lda #0
    sta disk_product+1
@remaining:
    lda dos64_range_request+GR_LENGTH+1
    cmp disk_product+1
    bcc @short
    bne @setup
    lda dos64_range_request+GR_LENGTH
    cmp disk_product
    bcs @setup
@short:
    lda dos64_range_request+GR_LENGTH
    sta disk_product
    lda dos64_range_request+GR_LENGTH+1
    sta disk_product+1
@setup:
    lda #<dos64_range_buffer
    sta dos64_reu_request+R_HOST
    lda #>dos64_range_buffer
    sta dos64_reu_request+R_HOST+1
    ldx #2
@reu:
    lda dos64_range_request+GR_REU,x
    sta dos64_reu_request+R_REU,x
    dex
    bpl @reu
    lda disk_product
    sta dos64_reu_request+R_LENGTH
    lda disk_product+1
    sta dos64_reu_request+R_LENGTH+1
    lda #1
    sta dos64_reu_request+R_DIRECTION
    jsr dos64_reu_transfer
    jcs disk_partial_error
    clc
    lda dos64_range_request+GR_REU
    adc disk_product
    sta dos64_range_request+GR_REU
    lda dos64_range_request+GR_REU+1
    adc disk_product+1
    sta dos64_range_request+GR_REU+1
    bcc @done
    inc dos64_range_request+GR_REU+2
@done:
    clc
    lda dos64_range_request+GR_DONE
    adc disk_product
    sta dos64_range_request+GR_DONE
    lda dos64_range_request+GR_DONE+1
    adc disk_product+1
    sta dos64_range_request+GR_DONE+1
    sec
    lda dos64_range_request+GR_LENGTH
    sbc disk_product
    sta dos64_range_request+GR_LENGTH
    lda dos64_range_request+GR_LENGTH+1
    sbc disk_product+1
    sta dos64_range_request+GR_LENGTH+1
    ora dos64_range_request+GR_LENGTH
    jne disk_verify
    lda disk_count
    sta dos64_guest+G_AX
disk_success:
    lda #DISK_OK
    beq disk_return
disk_bad_command:
    lda #DISK_ERR_COMMAND
    bne disk_return
disk_bad_sector:
    lda #DISK_ERR_SECTOR
    bne disk_return
disk_not_ready:
    lda #DISK_ERR_NOT_READY
    bne disk_return
disk_dma_error:
    lda #DISK_ERR_DMA
    bne disk_return
disk_partial_error:
    lda dos64_range_request+GR_ERROR
    cmp #GR_ERR_CACHE
    bne @progress
    lda #1
    sta dos64_disk_host_error
@progress:
    lda dos64_range_request+GR_DONE+1
    lsr
    sta dos64_guest+G_AX
disk_controller_error:
    lda #DISK_ERR_CONTROLLER
disk_return:
    sta dos64_disk_last_status
    sta dos64_guest+G_AX+1
    cmp #0
    bne @failed
    plp
    clc
    rts
@failed:
    plp
    sec
    rts
