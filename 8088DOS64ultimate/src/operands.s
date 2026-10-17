.include "abi.inc"
.macpack longbranch
.import dos64_guest, cpu_fetch8, cpu_fetch8_owned, cpu_fetch16, dos64_cpu_value, cpu_override, cpu_byte_registers
.import dos64_cpu_word_read, dos64_cpu_word_write, dos64_physical, dos64_mem_read, dos64_mem_write
.importzp dos64_segment, dos64_offset, dos64_mem_value
.export dos64_decode_rm, dos64_decode_rm_owned, dos64_operand_read, dos64_operand_write, dos64_map_register
.export dos64_operand_width, dos64_operand_kind, dos64_operand_reg
.export dos64_operand_offset, dos64_operand_segment, dos64_modrm_reg, dos64_modrm_mod

.segment "BSS"
dos64_operand_width: .res 1
dos64_operand_kind: .res 1    ; 0 register, 1 memory
dos64_operand_reg: .res 1     ; packed general-register byte offset
dos64_operand_offset: .res 2
dos64_operand_segment: .res 2
dos64_modrm_reg: .res 1       ; unscaled reg/opcode-extension field
dos64_modrm_mod: .res 1
operand_rm: .res 1
operand_modrm: .res 1

.segment "RODATA"
operand_base: .byte G_BX,G_BX,G_BP,G_BP,G_SI,G_DI,G_BP,G_BX
operand_index: .byte G_SI,G_DI,G_SI,G_DI,$FF,$FF,$FF,$FF
operand_stack_segment: .byte 0,0,1,1,0,0,1,0

.segment "CODE"
; Internal decode under the CPU's normal mapping/CLD/non-reentrant contract.
; Descriptor survives immediate fetch and page eviction; no raw frame pointer
; is retained. ModR/M effective offsets wrap at 16 bits before translation.
; CPU-private alternate entry. Opcode fetch still owns the live frame;
; callers listed in the handoff have done no intervening memory/cache/device
; operation or guest-state mutation. The ordinary public entry stays checked.
dos64_decode_rm_owned:
    jsr cpu_fetch8_owned
    bcc decode_body
    rts
dos64_decode_rm:
    jsr cpu_fetch8
    jcs decode_failed
decode_body:
    sta operand_modrm
    and #7
    sta operand_rm
    lda operand_modrm
    lsr
    lsr
    lsr
    and #7
    sta dos64_modrm_reg
    lda operand_modrm
    lsr
    lsr
    lsr
    lsr
    lsr
    lsr
    sta dos64_modrm_mod
    cmp #3
    bne @memory
    lda #0
    sta dos64_operand_kind
    lda operand_rm
    jsr dos64_map_register
    sta dos64_operand_reg
    clc
    rts
@memory:
    lda #1
    sta dos64_operand_kind
    lda dos64_modrm_mod
    bne @base
    lda operand_rm
    cmp #6
    bne @base
    jsr cpu_fetch16
    jcs decode_failed
    lda dos64_cpu_value
    sta dos64_operand_offset
    lda dos64_cpu_value+1
    sta dos64_operand_offset+1
    ldx #G_DS
    jmp @segment
@base:
    ldx operand_rm
    lda operand_base,x
    tax
    lda dos64_guest,x
    sta dos64_operand_offset
    lda dos64_guest+1,x
    sta dos64_operand_offset+1
    ldx operand_rm
    lda operand_index,x
    cmp #$FF
    beq @displacement
    tax
    clc
    lda dos64_operand_offset
    adc dos64_guest,x
    sta dos64_operand_offset
    lda dos64_operand_offset+1
    adc dos64_guest+1,x
    sta dos64_operand_offset+1
@displacement:
    lda dos64_modrm_mod
    beq @default_segment
    cmp #1
    bne @word_disp
    jsr cpu_fetch8_owned
    jcs decode_failed
    sta dos64_cpu_value
    ldx #0
    cmp #$80
    bcc @positive
    dex
@positive:
    stx dos64_cpu_value+1
    jmp @add_disp
@word_disp:
    jsr cpu_fetch16
    jcs decode_failed
@add_disp:
    clc
    lda dos64_operand_offset
    adc dos64_cpu_value
    sta dos64_operand_offset
    lda dos64_operand_offset+1
    adc dos64_cpu_value+1
    sta dos64_operand_offset+1
@default_segment:
    ldx operand_rm
    lda operand_stack_segment,x
    ldx #G_DS
    cmp #0
    beq @segment
    ldx #G_SS
@segment:
    lda cpu_override
    cmp #$FF
    beq @selected
    tax
@selected:
    lda dos64_guest,x
    sta dos64_operand_segment
    lda dos64_guest+1,x
    sta dos64_operand_segment+1
    clc
decode_failed:
    rts

; A raw general register index -> A packed byte offset according to width.
dos64_map_register:
    ldx dos64_operand_width
    bne @word
    tax
    lda cpu_byte_registers,x
    rts
@word:
    asl
    rts

dos64_operand_read:
    lda dos64_operand_kind
    bne @memory
    ldx dos64_operand_reg
    lda dos64_guest,x
    sta dos64_cpu_value
    lda #0
    ldy dos64_operand_width
    beq @high
    lda dos64_guest+1,x
@high:
    sta dos64_cpu_value+1
    clc
    rts
@memory:
    jsr operand_address
    lda dos64_operand_width
    bne @word
    jsr dos64_physical
    jsr dos64_mem_read
    bcs @failed
    sta dos64_cpu_value
    lda #0
    sta dos64_cpu_value+1
    clc
@failed:
    rts
@word:
    jmp dos64_cpu_word_read

dos64_operand_write:
    lda dos64_operand_kind
    bne @memory
    ldx dos64_operand_reg
    lda dos64_cpu_value
    sta dos64_guest,x
    lda dos64_operand_width
    beq @done
    lda dos64_cpu_value+1
    sta dos64_guest+1,x
@done:
    clc
    rts
@memory:
    jsr operand_address
    lda dos64_operand_width
    bne @word
    lda dos64_cpu_value
    sta dos64_mem_value
    jsr dos64_physical
    jmp dos64_mem_write
@word:
    jmp dos64_cpu_word_write

operand_address:
    lda dos64_operand_segment
    sta dos64_segment
    lda dos64_operand_segment+1
    sta dos64_segment+1
    lda dos64_operand_offset
    sta dos64_offset
    lda dos64_operand_offset+1
    sta dos64_offset+1
    rts
