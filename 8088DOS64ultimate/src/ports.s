.include "abi.inc"
.include "ports.inc"
.macpack longbranch
.export dos64_io_init, dos64_io_read, dos64_io_write
.export dos64_io_port, dos64_io_value, dos64_io_width
.export dos64_pic_imr, dos64_pic_irr, dos64_pic_isr, dos64_pic_base
.export dos64_pic_icw1, dos64_pic_icw2, dos64_pic_icw3, dos64_pic_icw4
.export dos64_pic_phase, dos64_pic_priority, dos64_pic_read_isr
.export dos64_pic_special_mask, dos64_pic_rotate_auto
.export dos64_io_state_start, dos64_io_state_end
.export dos64_ppi_port_b, dos64_pit_write_phase
.export dos64_cga_index, dos64_cga_registers, dos64_cga_control, dos64_cga_control_valid
.export io_read_body, io_write_body, io_success, io_unsupported
.import dos64_cga_read_gate, dos64_cga_write_gate

; Independent implementation from Intel8259A231468-003 pp9–17 and original
; IBM5160 XTBIOS.ASM PIC setup:13h/08h/09h, then BIOS maskFCh. References
; and hashes: agentworking/scratch/pc-io-20261015/references.json.
.segment "DEVICESTATE"
dos64_io_state_start:
dos64_io_port: .res 2
dos64_io_value: .res 2
dos64_io_width: .res 1
dos64_pic_imr: .res 1
dos64_pic_irr: .res 1
dos64_pic_isr: .res 1
dos64_pic_base: .res 1
dos64_pic_icw1: .res 1
dos64_pic_icw2: .res 1
dos64_pic_icw3: .res 1
dos64_pic_icw4: .res 1
dos64_pic_phase: .res 1
dos64_pic_priority: .res 1
dos64_pic_read_isr: .res 1
dos64_pic_special_mask: .res 1
dos64_pic_rotate_auto: .res 1
io_command: .res 1
io_candidates: .res 1
; XT8255 port B mode0 output latch; no speaker waveform/keyboard wire model.
dos64_ppi_port_b: .res 1
dos64_pit_write_phase: .res 1 ; next40h byte:0=LSB,1=MSB; onlyzero divisor supported
dos64_cga_index: .res 1
dos64_cga_registers: .res 18
dos64_cga_control: .res 1
dos64_cga_control_valid: .res 1
dos64_io_state_end:

.segment "DEVICECODE"
dos64_io_init:
    php
    sei
    cld
    lda #0
    ldx #dos64_io_state_end-dos64_io_state_start-1
@clear:
    sta dos64_io_state_start,x
    dex
    bpl @clear
    lda #$48
    sta dos64_ppi_port_b
    lda #$FC
    sta dos64_pic_imr
    lda #8
    sta dos64_pic_base
    sta dos64_pic_icw2
    lda #$13
    sta dos64_pic_icw1
    ; Original XT sets ICW4=09h:8088,buffered slave mode; retain that
    ; BIOS programming even though physical bus buffering is not modeled.
    lda #9
    sta dos64_pic_icw4
    lda #7
    sta dos64_pic_priority
    jmp io_success

.segment "CODE"
; Preflight all byte ports before either bus cycle. For the bounded port set,
; consecutive16-bit wrap cannot succeed; FFFF is not a supported first port.
io_validate:
    lda dos64_io_width
    cmp #2
    bcs @fail
    lda dos64_io_port+1
    bne @fail
    lda dos64_io_port
    cmp #$20
    beq @ok
    cmp #$61
    beq @byte
    cmp #$21
    bne @fail
@byte:
    lda dos64_io_width
    bne @fail
@ok:
    clc
    rts
@fail:
    sec
    rts

dos64_io_read:
    jmp dos64_cga_read_gate
io_read_body:
    ; No game adapter is installed. Its byte input is the pulled-up XT
    ; expansion bus (FFh), not simulated joystick movement/buttons.
    lda dos64_io_width
    bne @pic
    lda dos64_io_port+1
    cmp #2
    bne @pic
    lda dos64_io_port
    cmp #1
    bne @pic
    lda #$ff
    sta dos64_io_value
    jmp io_success
@pic:
    jsr io_validate
    jcs io_unsupported
    lda dos64_io_port
    cmp #$61
    beq @ppi
    cmp #$21
    beq @imr
    lda dos64_pic_read_isr
    beq @irr
    lda dos64_pic_isr
    jmp @value
@irr:
    lda dos64_pic_irr
    jmp @value
@ppi:
    lda dos64_ppi_port_b
    jmp @value
@imr:
    lda dos64_pic_imr
@value:
    sta dos64_io_value
    lda dos64_io_width
    beq io_success
    lda dos64_pic_imr
    sta dos64_io_value+1
io_success:
    plp
    clc
    rts
io_unsupported:
    plp
    sec
    rts

dos64_io_write:
    jmp dos64_cga_write_gate
io_write_body:
    ; DOS3.30 SYSINIT broadcasts GLOBAL REARM to shared-IRQ2..7 boards
    ; at02F2..02F7; data is arbitrary. Our XT has none: these six byte
    ; broadcasts have no device/PIC effect. Reads/words stay unsupported.
    ; Primary Microsoft MS-DOS SYSINIT1.ASM, commit2d04cacc5322951f187bb17e017c12920ac8ebe2.
    lda dos64_io_width
    bne @pic
    lda dos64_io_port+1
    cmp #2
    bne @pic
    lda dos64_io_port
    cmp #$F2
    bcc @pic
    cmp #$F8
    bcs @pic
    jmp io_success
@pic:
    ; Fixed BIOS counter0 binary mode3/RWlohi profile. Rewriting the SAME
    ; zero=>65536 divisor does not restart current mode3 counting. Track the
    ; two-byte write sequence; reject all other divisors/reads/control words.
    lda dos64_io_width
    bne @validate
    lda dos64_io_port+1
    bne @validate
    lda dos64_io_port
    cmp #$40
    bne @validate
    lda dos64_io_value
    bne @bad_pit
    lda dos64_pit_write_phase
    eor #1
    sta dos64_pit_write_phase
    jmp io_success
@bad_pit:
    jmp io_unsupported
@validate:
    jsr io_validate
    bcs io_unsupported
    lda dos64_io_port
    cmp #$61
    beq @ppi
    cmp #$21
    beq @data
    lda dos64_io_value
    ; Poll is a real acknowledge operation, not an empty status response.
    ; Reject before changing selection or special-mask state.
    and #$10
    bne @command
    lda dos64_io_value
    and #$0C
    cmp #$0C
    beq io_unsupported
@command:
    lda dos64_io_value
    jsr pic_command
    lda dos64_io_width
    beq io_success
    lda dos64_io_value+1
    jsr pic_data
    jmp io_success
@ppi:
    lda dos64_io_value
    sta dos64_ppi_port_b
    jmp io_success
@data:
    lda dos64_io_value
    jsr pic_data
    jmp io_success

pic_data:
    ldx dos64_pic_phase
    beq @mask
    cpx #2
    beq @icw2
    cpx #3
    beq @icw3
    and #$1F
    sta dos64_pic_icw4
    lda #0
    sta dos64_pic_phase
    rts
@mask:
    sta dos64_pic_imr
    rts
@icw2:
    sta dos64_pic_icw2
    and #$F8
    sta dos64_pic_base
    lda dos64_pic_icw1
    and #2
    bne @after3
    lda #3
    sta dos64_pic_phase
    rts
@icw3:
    sta dos64_pic_icw3
@after3:
    lda dos64_pic_icw1
    and #1
    beq @phase
    lda #4
@phase:
    sta dos64_pic_phase
    rts

pic_command:
    sta io_command
    and #$10
    bne pic_initialize
    lda io_command
    and #8
    bne pic_ocw3
    ; OCW2: bits7/6/5=R/SL/EOI. L2..0 are don't-care unless SL=1.
    lda io_command
    and #$20
    bne pic_eoi
    lda io_command
    and #$40
    bne @set_priority
    lda io_command
    and #$80
    beq @auto
    lda #1
@auto:
    sta dos64_pic_rotate_auto
    rts
@set_priority:
    lda io_command
    bpl @done                 ;010 is a no-op
    and #7                   ;110 sets lowest priority
    sta dos64_pic_priority
@done:
    rts

pic_initialize:
    lda io_command
    sta dos64_pic_icw1
    lda #0
    sta dos64_pic_imr
    sta dos64_pic_irr
    sta dos64_pic_isr
    sta dos64_pic_read_isr
    sta dos64_pic_special_mask
    sta dos64_pic_rotate_auto
    sta dos64_pic_icw4
    lda #7
    sta dos64_pic_priority
    sta dos64_pic_icw3         ;slave address reset, Intel p10
    lda #2
    sta dos64_pic_phase
    rts

pic_ocw3:
    lda io_command
    and #2
    beq @mask
    lda io_command
    and #1
    sta dos64_pic_read_isr
@mask:
    lda io_command
    and #$40
    beq @done
    lda io_command
    and #$20
    beq @store
    lda #1
@store:
    sta dos64_pic_special_mask
@done:
    rts

pic_eoi:
    lda io_command
    and #$40
    bne @specific
    lda dos64_pic_isr
    sta io_candidates
    lda dos64_pic_special_mask
    beq @scan
    lda dos64_pic_imr
    eor #$FF
    and io_candidates
    sta io_candidates
@scan:
    ldx dos64_pic_priority
    ldy #8
@next:
    inx
    txa
    and #7
    tax
    lda pic_bits,x
    and io_candidates
    bne @clear
    dey
    bne @next
    rts                     ;no active eligible ISR bit: no rotation
@specific:
    lda io_command
    and #7
    tax
@clear:
    lda pic_bits,x
    eor #$FF
    and dos64_pic_isr
    sta dos64_pic_isr
    lda io_command
    bpl @done
    stx dos64_pic_priority
@done:
    rts

.segment "RODATA"
pic_bits: .byte 1,2,4,8,16,32,64,128
