.include "abi.inc"
.include "memory.inc"
.include "bios.inc"
.macpack longbranch
.import dos64_guest, dos64_cpu_value
.import dos64_mem_write, dos64_memory_mode, dos64_physical
.import dos64_cpu_word_read, dos64_cpu_word_write
.import dos64_disk_transfer, dos64_disk_spt, dos64_disk_host_error
.importzp dos64_address, dos64_segment, dos64_offset, dos64_mem_value
.export dos64_bios_init, dos64_bios_port
.export dos64_bios_ready, dos64_bios_host_error, dos64_bios_boot_status

.segment "BSS"
dos64_bios_ready: .res 1
dos64_bios_host_error: .res 1
dos64_bios_boot_status: .res 1
bios_mode: .res 1
bios_count: .res 2
bios_fill: .res 1
bios_port: .res 1

.segment "CODE"
; Cold BIOS ownership: IVT 00000..003FF, BDA 00400..004FF and the entire
; synthetic ROM F0000..FFFFF. Every byte goes through the coherent bus. Disk
; configuration and conventional RAM outside the IVT/BDA remain caller-owned.
; Host P except carry preserved, A/X/Y and public address scratch clobbered.
dos64_bios_init:
    php
    sei
    cld
    lda #0
    sta dos64_bios_ready
    sta dos64_bios_host_error
    sta dos64_bios_boot_status
    sta dos64_address
    sta dos64_address+1
    sta dos64_address+2
    sta bios_fill
    sta bios_count
    lda #5
    sta bios_count+1
    lda dos64_memory_mode
    sta bios_mode
    lda #MEM_ALL_RAM
    sta dos64_memory_mode
    jsr bios_fill_bytes
    jcs bios_init_failed
    lda #0
    sta dos64_address
    sta dos64_address+1
    lda #$0F
    sta dos64_address+2
    lda #$FF
    sta bios_fill
    ; A zero word count denotes exactly 65536 bytes for this private loop.
    jsr bios_fill_bytes
    jcs bios_init_failed
    lda #<bios_patches
    sta dos64_segment
    lda #>bios_patches
    sta dos64_segment+1
@patch:
    ldy #2
    lda (dos64_segment),y
    bmi @geometry
    sta dos64_address+2
    dey
    lda (dos64_segment),y
    sta dos64_address+1
    dey
    lda (dos64_segment),y
    sta dos64_address
    ldy #3
    lda (dos64_segment),y
    sta dos64_mem_value
    jsr dos64_mem_write
    jcs bios_init_failed
    clc
    lda dos64_segment
    adc #4
    sta dos64_segment
    bcc @patch
    inc dos64_segment+1
    jmp @patch
@geometry:
    lda #$04
    sta dos64_address
    lda #$03
    sta dos64_address+1
    lda #$0F
    sta dos64_address+2
    lda dos64_disk_spt
    sta dos64_mem_value
    jsr dos64_mem_write
    jcs bios_init_failed
    lda bios_mode
    sta dos64_memory_mode
    lda #BIOS_READY
    sta dos64_bios_ready
    plp
    clc
    rts
bios_init_failed:
    lda bios_mode
    sta dos64_memory_mode
    jmp bios_host_failed

bios_fill_bytes:
    lda bios_fill
    sta dos64_mem_value
    jsr dos64_mem_write
    bcs @return
    inc dos64_address
    bne @count
    inc dos64_address+1
    bne @count
    inc dos64_address+2
@count:
    lda bios_count
    bne @low
    dec bios_count+1
@low:
    dec bios_count
    lda bios_count
    ora bios_count+1
    bne bios_fill_bytes
    clc
@return:
    rts

; Called only by OUT imm8,AL dispatch, with A=port and IP after both bytes.
; A physical whitelist admits segment aliases of our exact opcode addresses.
; C clear means handled, including guest disk errors; C set with host_error=0
; means ordinary unsupported I/O, with host_error=1 a terminal cache failure.
dos64_bios_port:
    php
    sei
    cld
    sta bios_port
    lda #0
    sta dos64_bios_host_error
    lda dos64_bios_ready
    cmp #BIOS_READY
    jne bios_unrecognized
    lda dos64_guest+G_CS
    sta dos64_segment
    lda dos64_guest+G_CS+1
    sta dos64_segment+1
    sec
    lda dos64_guest+G_IP
    sbc #2
    sta dos64_offset
    lda dos64_guest+G_IP+1
    sbc #0
    sta dos64_offset+1
    jsr dos64_physical
    lda dos64_address+2
    cmp #$0F
    jne bios_unrecognized
    lda dos64_address+1
    cmp #1
    jne bios_unrecognized
    lda dos64_address
    bne @boot
    lda bios_port
    cmp #BIOS_DISK_PORT
    jne bios_unrecognized
    jsr dos64_disk_transfer
    lda dos64_disk_host_error
    jne bios_host_failed
    ; The primitive leaves BIOS status in guest AH. Saved FLAGS belongs to the
    ; normal INT or PUSHF/CALL FAR frame; the ROM's ordinary IRET consumes it.
    lda dos64_guest+G_AX+1
    beq @clear_carry
    lda #1
@clear_carry:
    sta bios_fill
    lda dos64_guest+G_SS
    sta dos64_segment
    lda dos64_guest+G_SS+1
    sta dos64_segment+1
    clc
    lda dos64_guest+G_SP
    adc #4
    sta dos64_offset
    lda dos64_guest+G_SP+1
    adc #0
    sta dos64_offset+1
    jsr dos64_cpu_word_read
    jcs bios_host_failed
    lda dos64_cpu_value
    and #$FE
    ora bios_fill
    sta dos64_cpu_value
    jsr dos64_cpu_word_write
    jcs bios_host_failed
    jmp bios_handled
@boot:
    cmp #$10
    jne bios_unrecognized
    lda bios_port
    cmp #BIOS_BOOT_PORT
    jne bios_unrecognized
    lda #0
    sta dos64_guest+G_ES
    sta dos64_guest+G_ES+1
    sta dos64_guest+G_BX
    sta dos64_guest+G_CX+1
    sta dos64_guest+G_DX
    sta dos64_guest+G_DX+1
    lda #$7C
    sta dos64_guest+G_BX+1
    lda #1
    sta dos64_guest+G_CX
    sta dos64_guest+G_AX
    lda #2
    sta dos64_guest+G_AX+1
    jsr dos64_disk_transfer
    sta dos64_bios_boot_status
    lda dos64_disk_host_error
    jne bios_host_failed
    lda dos64_bios_boot_status
    ; Loading the status above must not replace transfer's success/failure C.
    bcs bios_handled
    lda #0
    sta dos64_guest+G_CS
    sta dos64_guest+G_CS+1
    sta dos64_guest+G_IP
    sta dos64_guest+G_SS
    sta dos64_guest+G_SS+1
    sta dos64_guest+G_SP
    sta dos64_guest+G_DS
    sta dos64_guest+G_DS+1
    lda #$7C
    sta dos64_guest+G_IP+1
    sta dos64_guest+G_SP+1
    lda #2
    sta dos64_guest+G_FLAGS
    lda #$F2
    sta dos64_guest+G_FLAGS+1
bios_handled:
    plp
    clc
    rts
bios_host_failed:
    lda #1
    sta dos64_bios_host_error
bios_unrecognized:
    plp
    sec
    rts

.segment "RODATA"
.macro patch address, value
    .byte <address, >address, ^address, value
.endmacro
bios_patches:
    patch $00044, $20
    patch $00045, $01
    patch $00047, $F0
    patch $00048, $30
    patch $00049, $01
    patch $0004B, $F0
    patch $0004D, $01
    patch $0004F, $F0
    patch $00054, $40
    patch $00055, $01
    patch $00057, $F0
    patch $00064, $10
    patch $00065, $01
    patch $00067, $F0
    patch $00079, $03
    patch $0007B, $F0
    patch $00410, $21       ; one diskette, 80-column color display
    patch $00413, $80       ; 640 KiB conventional memory
    patch $00414, $02
    patch $0041A, $1E       ; empty keyboard queue
    patch $0041C, $1E
    patch $00449, $03       ; CGA mode 3, 80 columns, 4 KiB page
    patch $0044A, $50
    patch $0044D, $10
    patch $00460, $07       ; cursor scan lines 6..7
    patch $00461, $06
    patch $00463, $D4       ; CGA CRT controller base 03D4
    patch $00464, $03
    patch $00465, $29
    patch $F0100, $E6
    patch $F0101, BIOS_DISK_PORT
    patch $F0102, $CF
    patch $F0110, $E6
    patch $F0111, BIOS_BOOT_PORT
    patch $F0112, $F4
    ; Ordinary guest INT11/12 handlers preserve DS and let IRET restore the
    ; caller's saved FLAGS. Queries read mutable BDA words through the CPU bus.
    ; PUSH DS / XOR AX,AX / MOV DS,AX / MOV AX,[0410 or 0413] / POP DS / IRET.
    patch $F0120, $1E
    patch $F0121, $31
    patch $F0122, $C0
    patch $F0123, $8E
    patch $F0124, $D8
    patch $F0125, $A1
    patch $F0126, $10
    patch $F0127, $04
    patch $F0128, $1F
    patch $F0129, $CF
    patch $F0130, $1E
    patch $F0131, $31
    patch $F0132, $C0
    patch $F0133, $8E
    patch $F0134, $D8
    patch $F0135, $A1
    patch $F0136, $13
    patch $F0137, $04
    patch $F0138, $1F
    patch $F0139, $CF
    ; Original IBM 5160 11/08/82 XTBIOS.ASM defines INT15 as unsupported:
    ; AH=86h, CF=1. Independently authored guest frame update retains all
    ; caller registers except AH and all saved FLAGS except carry.
    ; Primary archive: diskettes.pcjs.org/pcx86/dev/rom/ibm/5160/
    ; IBM-BIOS-SRC-5160V1.json, XTBIOS.ASM cassette/system-service contract.
    ; PUSH BP / MOV BP,SP / OR WORD [BP+6],1 / MOV AH,86 / POP BP / IRET.
    patch $F0140, $55
    patch $F0141, $89
    patch $F0142, $E5
    patch $F0143, $83
    patch $F0144, $4E
    patch $F0145, $06
    patch $F0146, $01
    patch $F0147, $B4
    patch $F0148, $86
    patch $F0149, $5D
    patch $F014A, $CF
    ; IBM 5160 01/10/86 POST.ASM DISK_BASE field facts, independently
    ; encoded. Its compatibility default is 8 sectors; our owned profile
    ; substitutes the configured 9-sector 360 KiB geometry at init.
    ; Source archive: diskettes.pcjs.org/pcx86/dev/rom/ibm/5160/
    ; IBM-BIOS-SRC-5160V2.json (01/10/86 listing, not bundled ROM code).
    patch $F0300, $CF
    patch $F0301, $02
    patch $F0302, $25
    patch $F0303, $02
    patch $F0304, $09
    patch $F0305, $2A
    patch $F0306, $FF
    patch $F0307, $50
    patch $F0308, $F6
    patch $F0309, $19
    patch $F030A, $04
    patch $FFFF0, $EA
    patch $FFFF1, $10
    patch $FFFF2, $01
    patch $FFFF3, $00
    patch $FFFF4, $F0
    ; Synthetic build date at the original XT date location; model FE.
    patch $FFFF5, '1'
    patch $FFFF6, '0'
    patch $FFFF7, '/'
    patch $FFFF8, '1'
    patch $FFFF9, '5'
    patch $FFFFA, '/'
    patch $FFFFB, '2'
    patch $FFFFC, '6'
    patch $FFFFE, $FE
    .byte 0, 0, $FF, 0
