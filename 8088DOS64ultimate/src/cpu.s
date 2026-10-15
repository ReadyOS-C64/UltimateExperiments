.include "abi.inc"
.import dos64_guest, dos64_cpu_reset, dos64_mem_read, dos64_mem_write, dos64_physical
.importzp dos64_segment, dos64_offset, dos64_mem_value
.macpack longbranch
.export dos64_cpu_init, dos64_cpu_step, dos64_cpu_status, dos64_cpu_opcode
.export dos64_cpu_instructions, dos64_cpu_yield, dos64_cpu_pending, dos64_cpu_irq_shadow
.export dos64_cpu_value, dos64_cpu_word_read, dos64_cpu_word_write

.segment "BSS"
dos64_cpu_status: .res 1       ; 0 running, 1 halted, 2 unsupported, 3 host memory error
dos64_cpu_opcode: .res 1
dos64_cpu_instructions: .res 4
dos64_cpu_yield: .res 1
dos64_cpu_pending: .res 1
dos64_cpu_irq_shadow: .res 1
dos64_cpu_value: .res 2
cpu_start_ip: .res 2
cpu_override: .res 1
cpu_rep: .res 1
cpu_lock: .res 1
cpu_slice: .res 1
cpu_reg: .res 1
cpu_byte: .res 1
cpu_low: .res 1
cpu_jump: .res 2

.segment "RODATA"
cpu_byte_registers: .byte 0,2,4,6,1,3,5,7

.segment "CODE"
dos64_cpu_init:
    jsr dos64_cpu_reset
    lda #0
    ldx #8
@clear:
    sta dos64_cpu_status,x
    dex
    bpl @clear
    rts

; One instruction or bounded prefix slice. P except C preserved, A/X/Y clobbered.
; Running/halted/yield return C clear. Unsupported/host error latch and return C
; set; init is required to resume. Host errors can leave partial memory writes.
dos64_cpu_step:
    php
    sei
    cld
    lda dos64_cpu_status
    beq @running
    cmp #1
    jeq cpu_return
    jmp cpu_error_return
@running:
    lda #0
    sta dos64_cpu_yield
    sta cpu_slice
    lda dos64_cpu_pending
    bne cpu_prefix
    lda dos64_guest+G_IP
    sta cpu_start_ip
    lda dos64_guest+G_IP+1
    sta cpu_start_ip+1
    lda #$FF
    sta cpu_override
    lda #0
    sta cpu_rep
    sta cpu_lock
cpu_prefix:
    jsr cpu_fetch8
    jcs cpu_memory_error
    sta dos64_cpu_opcode
    cmp #$26
    beq @es
    cmp #$2E
    beq @cs
    cmp #$36
    beq @ss
    cmp #$3E
    beq @ds
    cmp #$F2
    beq @rep
    cmp #$F3
    beq @rep
    cmp #$F0
    beq @lock
    jmp cpu_dispatch
@es:
    lda #G_ES
    bne @segment
@cs:
    lda #G_CS
    bne @segment
@ss:
    lda #G_SS
    bne @segment
@ds:
    lda #G_DS
@segment:
    sta cpu_override
    jmp @next
@rep:
    sta cpu_rep
    jmp @next
@lock:
    sta cpu_lock
@next:
    inc cpu_slice
    lda cpu_slice
    cmp #64
    bcc cpu_prefix
    ; No invented 15-byte limit: yield and continue the same guest instruction.
    lda #1
    sta dos64_cpu_pending
    sta dos64_cpu_yield
    jmp cpu_return

cpu_dispatch:
    lda #0
    sta dos64_cpu_pending
    lda dos64_cpu_opcode
    cmp #$B0
    bcc @exchange
    cmp #$C0
    bcc cpu_mov_immediate
@exchange:
    cmp #$90
    bcc @moffs
    cmp #$98
    jcc cpu_exchange
@moffs:
    cmp #$A0
    bcc @control
    cmp #$A4
    jcc cpu_moffs
@control:
    cmp #$EA
    jeq cpu_far_jump
    cmp #$E9
    jeq cpu_near_jump
    cmp #$EB
    jeq cpu_short_jump
    cmp #$F4
    beq @halt
    cmp #$F5
    jeq cpu_cmc
    cmp #$F8
    jeq cpu_clc
    cmp #$F9
    jeq cpu_stc
    cmp #$FA
    jeq cpu_cli
    cmp #$FB
    jeq cpu_sti
    cmp #$FC
    jeq cpu_cld
    cmp #$FD
    jeq cpu_std
    lda #2
    jmp cpu_fault
@halt:
    lda #1
    sta dos64_cpu_status
    jmp cpu_complete

cpu_mov_immediate:
    and #7
    tax
    lda dos64_cpu_opcode
    cmp #$B8
    bcs @word
    lda cpu_byte_registers,x
    sta cpu_reg
    jsr cpu_fetch8
    jcs cpu_memory_error
    ldx cpu_reg
    sta dos64_guest,x
    jmp cpu_complete
@word:
    txa
    asl
    sta cpu_reg
    jsr cpu_fetch16
    jcs cpu_memory_error
    ldx cpu_reg
    lda dos64_cpu_value
    sta dos64_guest,x
    lda dos64_cpu_value+1
    sta dos64_guest+1,x
    jmp cpu_complete

cpu_exchange:
    and #7
    asl
    tax
    lda dos64_guest+G_AX
    pha
    lda dos64_guest,x
    sta dos64_guest+G_AX
    pla
    sta dos64_guest,x
    lda dos64_guest+G_AX+1
    pha
    lda dos64_guest+1,x
    sta dos64_guest+G_AX+1
    pla
    sta dos64_guest+1,x
    jmp cpu_complete

cpu_moffs:
    jsr cpu_fetch16
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta dos64_offset
    lda dos64_cpu_value+1
    sta dos64_offset+1
    ldx cpu_override
    cpx #$FF
    bne @segment
    ldx #G_DS
@segment:
    lda dos64_guest,x
    sta dos64_segment
    lda dos64_guest+1,x
    sta dos64_segment+1
    lda dos64_cpu_opcode
    and #2
    bne @write
    lda dos64_cpu_opcode
    and #1
    beq @read_byte
    jsr dos64_cpu_word_read
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta dos64_guest+G_AX
    lda dos64_cpu_value+1
    sta dos64_guest+G_AX+1
    jmp cpu_complete
@read_byte:
    jsr dos64_physical
    jsr dos64_mem_read
    jcs cpu_memory_error
    sta dos64_guest+G_AX
    jmp cpu_complete
@write:
    lda dos64_guest+G_AX
    sta dos64_cpu_value
    sta dos64_mem_value
    lda dos64_guest+G_AX+1
    sta dos64_cpu_value+1
    lda dos64_cpu_opcode
    and #1
    beq @write_byte
    jsr dos64_cpu_word_write
    jcs cpu_memory_error
    jmp cpu_complete
@write_byte:
    jsr dos64_physical
    jsr dos64_mem_write
    jcs cpu_memory_error
    jmp cpu_complete

cpu_short_jump:
    jsr cpu_fetch8
    jcs cpu_memory_error
    sta dos64_cpu_value
    ldx #0
    cmp #$80
    bcc @positive
    dex
@positive:
    stx dos64_cpu_value+1
    jmp cpu_relative
cpu_near_jump:
    jsr cpu_fetch16
    jcs cpu_memory_error
cpu_relative:
    clc
    lda dos64_guest+G_IP
    adc dos64_cpu_value
    sta dos64_guest+G_IP
    lda dos64_guest+G_IP+1
    adc dos64_cpu_value+1
    sta dos64_guest+G_IP+1
    jmp cpu_complete
cpu_far_jump:
    jsr cpu_fetch16
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta cpu_jump
    lda dos64_cpu_value+1
    sta cpu_jump+1
    jsr cpu_fetch16
    jcs cpu_memory_error
    lda dos64_cpu_value
    sta dos64_guest+G_CS
    lda dos64_cpu_value+1
    sta dos64_guest+G_CS+1
    lda cpu_jump
    sta dos64_guest+G_IP
    lda cpu_jump+1
    sta dos64_guest+G_IP+1
    jmp cpu_complete

cpu_cmc:
    lda dos64_guest+G_FLAGS
    eor #1
    bne cpu_low_flags
    beq cpu_low_flags
cpu_clc:
    lda dos64_guest+G_FLAGS
    and #$FE
    jmp cpu_low_flags
cpu_stc:
    lda dos64_guest+G_FLAGS
    ora #1
cpu_low_flags:
    sta dos64_guest+G_FLAGS
    jmp cpu_complete
cpu_cli:
    lda dos64_guest+G_FLAGS+1
    and #$FD
    jmp cpu_high_flags
cpu_sti:
    lda #2
    sta dos64_cpu_irq_shadow
    lda dos64_guest+G_FLAGS+1
    ora #2
    jmp cpu_high_flags
cpu_cld:
    lda dos64_guest+G_FLAGS+1
    and #$FB
    jmp cpu_high_flags
cpu_std:
    lda dos64_guest+G_FLAGS+1
    ora #4
cpu_high_flags:
    sta dos64_guest+G_FLAGS+1
cpu_complete:
    lda dos64_cpu_irq_shadow
    beq @count
    dec dos64_cpu_irq_shadow
@count:
    inc dos64_cpu_instructions
    bne cpu_return
    inc dos64_cpu_instructions+1
    bne cpu_return
    inc dos64_cpu_instructions+2
    bne cpu_return
    inc dos64_cpu_instructions+3
cpu_return:
    plp
    clc
    rts
cpu_memory_error:
    lda #3
cpu_fault:
    sta dos64_cpu_status
    lda cpu_start_ip
    sta dos64_guest+G_IP
    lda cpu_start_ip+1
    sta dos64_guest+G_IP+1
    lda #0
    sta dos64_cpu_pending
cpu_error_return:
    plp
    sec
    rts

cpu_fetch8:
    lda dos64_guest+G_CS
    sta dos64_segment
    lda dos64_guest+G_CS+1
    sta dos64_segment+1
    lda dos64_guest+G_IP
    sta dos64_offset
    lda dos64_guest+G_IP+1
    sta dos64_offset+1
    jsr dos64_physical
    jsr dos64_mem_read
    bcs @error
    sta cpu_byte
    inc dos64_guest+G_IP
    bne @read
    inc dos64_guest+G_IP+1
@read:
    lda cpu_byte
@error:
    rts
cpu_fetch16:
    jsr cpu_fetch8
    bcs @error
    sta cpu_low
    jsr cpu_fetch8
    bcs @error
    sta dos64_cpu_value+1
    lda cpu_low
    sta dos64_cpu_value
@error:
    rts

; Segmented word transfers wrap the offset before translating the second byte.
; Input segment/offset are preserved. Value is little endian; C reports memory
; failure. A failed high-byte store can leave a committed low byte.
dos64_cpu_word_read:
    php
    sei
    cld
    jsr dos64_physical
    jsr dos64_mem_read
    bcs word_failed
    sta dos64_cpu_value
    jsr word_next
    jsr dos64_physical
    jsr dos64_mem_read
    jsr word_previous
    bcs word_failed
    sta dos64_cpu_value+1
    plp
    clc
    rts
dos64_cpu_word_write:
    php
    sei
    cld
    lda dos64_cpu_value
    sta dos64_mem_value
    jsr dos64_physical
    jsr dos64_mem_write
    bcs word_failed
    jsr word_next
    lda dos64_cpu_value+1
    sta dos64_mem_value
    jsr dos64_physical
    jsr dos64_mem_write
    jsr word_previous
    bcs word_failed
    plp
    clc
    rts
word_failed:
    plp
    sec
    rts
word_next:
    inc dos64_offset
    bne @done
    inc dos64_offset+1
@done:
    rts
word_previous:
    ; Preserve A and carry from the transfer while restoring the input offset.
    pha
    lda dos64_offset
    bne @low
    dec dos64_offset+1
@low:
    dec dos64_offset
    pla
    rts
