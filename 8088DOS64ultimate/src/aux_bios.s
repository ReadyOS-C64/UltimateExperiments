.include "abi.inc"
.include "aux_bios.inc"
.macpack longbranch
.import dos64_guest, dos64_cpu_value, dos64_cpu_word_read, dos64_physical
.import dos64_mem_read
.importzp dos64_segment, dos64_offset
.export dos64_aux_bios_service, dos64_aux_bios_vector, dos64_aux_bios_host_error

; Original IBM XT BIOS, RS232_IO lines1538-1576 and PRINTER_IO3112-3140.
; pcjs b4a910e606d87137e977ec89ce816f05a31c366a, 1982-11-08/XTBIOS.ASM.
; Zero BDA base returns BEFORE AH dispatch, unchanged AX.
; A missing device is not a timeout. DX indexing is unchecked and wraps at
; 16 bits in the original guest, including DX=8000h aliasing device zero.
; This bounded service supports absent devices only, not serial/printer I/O.
.segment "DEVICESTATE"
dos64_aux_bios_vector: .res 1
dos64_aux_bios_host_error: .res 1

.segment "CODE"
; Vector descriptor:14h serial,17h printer. C=0 handled absent-device call;
; C=1 unsupported vector/nonzero device base or host cache failure. Separate
; host_error=1 only for a failed coherent read. Guest state is unchanged.
; Native P except carry preserved; A/X/Y and operand/address scratch clobbered.
dos64_aux_bios_service:
    php
    sei
    cld
    lda #0
    sta dos64_aux_bios_host_error
    lda dos64_aux_bios_vector
    cmp #AUX_BIOS_SERIAL
    beq @base
    cmp #AUX_BIOS_PRINTER
    bne @unsupported
    ; PRINTER_IO reads PRINT_TIM_OUT[DX] before its no-device check.
    clc
    lda dos64_guest+G_DX
    adc #$78
    sta dos64_offset
    lda dos64_guest+G_DX+1
    adc #0
    sta dos64_offset+1
    jsr aux_segment
    jsr dos64_physical
    jsr dos64_mem_read
    bcs @failed
@base:
    lda dos64_guest+G_DX
    asl
    sta dos64_offset
    lda dos64_guest+G_DX+1
    rol
    sta dos64_offset+1
    lda dos64_aux_bios_vector
    cmp #AUX_BIOS_PRINTER
    bne @read
    clc
    lda dos64_offset
    adc #8
    sta dos64_offset
    lda dos64_offset+1
    adc #0
    sta dos64_offset+1
@read:
    jsr aux_segment
    jsr dos64_cpu_word_read
    bcs @failed
    lda dos64_cpu_value
    ora dos64_cpu_value+1
    bne @unsupported
    plp
    clc
    rts
@failed:
    lda #1
    sta dos64_aux_bios_host_error
@unsupported:
    plp
    sec
    rts
aux_segment:
    lda #$40
    sta dos64_segment
    lda #0
    sta dos64_segment+1
    rts
