.include "abi.inc"
.macpack longbranch
.import dos64_guest, dos64_cpu_opcode, cpu_override
.import cpu_fetch8, cpu_complete, cpu_memory_error, cpu_unsupported, dos64_interrupt_enter
.import dos64_physical, dos64_mem_read
.importzp dos64_segment, dos64_offset
.export dos64_adjust_execute

; Internal CPU tail entry: cpu_step has saved host P and cleared D. Scratch is
; outside the nearly full E000 BSS block. No additional zero-page ownership.
.segment "DEVICESTATE"
adjust_old: .res 1
adjust_flags: .res 1
adjust_base: .res 1
adjust_quotient: .res 1
adjust_result: .res 1
adjust_multiplier: .res 1

.segment "CODE"
dos64_adjust_execute:
    lda dos64_cpu_opcode
    cmp #$27
    jeq adjust_decimal
    cmp #$2F
    jeq adjust_decimal
    cmp #$37
    jeq adjust_ascii
    cmp #$3F
    jeq adjust_ascii
    cmp #$D4
    jeq adjust_aam
    cmp #$D5
    jeq adjust_aad
    cmp #$D6
    jeq adjust_salc
    cmp #$D7
    jeq adjust_xlat
    jmp cpu_unsupported

adjust_decimal:
    lda dos64_guest+G_AX
    sta adjust_old
    lda dos64_guest+G_FLAGS
    sta adjust_flags
    ; The original8088 high-digit test is >9F when incoming AF=1, >99
    ; otherwise. Hardware SST27/2F confirms this for all10,000 source rows
    ; each. Modern x86 pseudocode also incorrectly retains DAS low borrow.
    and #$10
    beq @threshold99
    lda adjust_old
    cmp #$A0
    jmp @high
@threshold99:
    lda adjust_old
    cmp #$9A
@high:
    lda #0
    rol
    sta adjust_result
    lda adjust_flags
    and #1
    ora adjust_result
    sta adjust_result             ; CF decision, independent of low correction
    lda dos64_guest+G_FLAGS
    and #$2A                     ; preserve reserved bits, clear SZP/AF/CF
    sta dos64_guest+G_FLAGS
    lda adjust_flags
    and #$10
    bne @low_adjust
    lda adjust_old
    and #$0F
    cmp #10
    bcc @high_adjust
@low_adjust:
    lda dos64_guest+G_FLAGS
    ora #$10
    sta dos64_guest+G_FLAGS
    lda dos64_cpu_opcode
    cmp #$2F
    beq @low_sub
    clc
    lda dos64_guest+G_AX
    adc #6
    jmp @low_store
@low_sub:
    sec
    lda dos64_guest+G_AX
    sbc #6
@low_store:
    sta dos64_guest+G_AX
@high_adjust:
    lda adjust_result
    beq @szp
    lda dos64_guest+G_FLAGS
    ora #1
    sta dos64_guest+G_FLAGS
    lda dos64_cpu_opcode
    cmp #$2F
    beq @high_sub
    clc
    lda dos64_guest+G_AX
    adc #$60
    jmp @high_store
@high_sub:
    sec
    lda dos64_guest+G_AX
    sbc #$60
@high_store:
    sta dos64_guest+G_AX
@szp:
    jmp adjust_szp

adjust_ascii:
    lda dos64_guest+G_FLAGS
    sta adjust_flags
    and #$EE
    sta dos64_guest+G_FLAGS
    lda adjust_flags
    and #$10
    bne @adjust
    lda dos64_guest+G_AX
    and #$0F
    cmp #10
    bcc @mask
@adjust:
    lda dos64_guest+G_FLAGS
    ora #$11
    sta dos64_guest+G_FLAGS
    lda dos64_cpu_opcode
    cmp #$3F
    beq @sub
    ; Original8088 AL+6 does not carry into AH. AH independently increments.
    inc dos64_guest+G_AX+1
    clc
    lda dos64_guest+G_AX
    adc #6
    jmp @store
@sub:
    dec dos64_guest+G_AX+1
    sec
    lda dos64_guest+G_AX
    sbc #6
@store:
    sta dos64_guest+G_AX
@mask:
    lda dos64_guest+G_AX
    and #$0F
    sta dos64_guest+G_AX
    ; SZPO undefined: retain input bits rather than inventing defined behavior.
    jmp cpu_complete

adjust_aam:
    jsr cpu_fetch8
    jcs cpu_memory_error
    sta adjust_base
    bne @divide
    ; CORD tests a zero high dividend against the divisor before faulting.
    ; Original8088 AAM0 hardware has SZP=zero (PF/ZF set, SF clear) even
    ; though AX remains unchanged. All47 zero-base rows at the SST pin agree.
    lda dos64_guest+G_FLAGS
    and #$2A
    ora #$44
    sta dos64_guest+G_FLAGS
    lda dos64_guest+G_FLAGS+1
    and #$F7
    sta dos64_guest+G_FLAGS+1
    ; Original8088 divide-error return IP follows the immediate byte.
    lda #0
    jmp dos64_interrupt_enter
@divide:
    lda dos64_guest+G_AX
    sta adjust_quotient
    lda #0
    sta adjust_result
    ldx #8
@bit:
    asl adjust_quotient
    rol adjust_result
    lda adjust_result
    cmp adjust_base
    bcc @next
    sbc adjust_base
    sta adjust_result
    inc adjust_quotient
@next:
    dex
    bne @bit
    lda adjust_quotient
    sta dos64_guest+G_AX+1
    lda adjust_result
    sta dos64_guest+G_AX
    jmp adjust_szp

adjust_aad:
    jsr cpu_fetch8
    jcs cpu_memory_error
    sta adjust_base
    lda dos64_guest+G_AX+1
    sta adjust_multiplier
    lda #0
    sta adjust_result
    ldx #8
@bit:
    lsr adjust_multiplier
    bcc @next
    clc
    lda adjust_result
    adc adjust_base
    sta adjust_result
@next:
    asl adjust_base
    dex
    bne @bit
    clc
    lda adjust_result
    adc dos64_guest+G_AX
    sta dos64_guest+G_AX
    lda #0
    sta dos64_guest+G_AX+1
    ; AAM/AAD call unsigned CORD/CORX directly: REP sign handling belongs to
    ; MUL/DIV callers, so REP has no effect here (microcode source evidence).
    jmp adjust_szp

adjust_salc:
    lda dos64_guest+G_FLAGS
    and #1
    beq @store
    lda #$FF
@store:
    sta dos64_guest+G_AX
    jmp cpu_complete

adjust_xlat:
    clc
    lda dos64_guest+G_BX
    adc dos64_guest+G_AX
    sta dos64_offset
    lda dos64_guest+G_BX+1
    adc #0
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
    jsr dos64_physical
    jsr dos64_mem_read
    jcs cpu_memory_error
    sta dos64_guest+G_AX
    jmp cpu_complete

; Set only SZP according to resulting AL. AF/CF/OF of AAM/AAD are undefined
; and retained, as is OF of DAA/DAS; hardware comparison uses declared masks.
adjust_szp:
    lda dos64_guest+G_FLAGS
    and #$3B
    sta adjust_flags
    lda dos64_guest+G_AX
    and #$80
    ora adjust_flags
    sta adjust_flags
    lda dos64_guest+G_AX
    bne @parity
    lda adjust_flags
    ora #$40
    sta adjust_flags
@parity:
    lda dos64_guest+G_AX
    ldx #8
    ldy #0
@count:
    lsr
    bcc @next
    iny
@next:
    dex
    bne @count
    tya
    and #1
    bne @store
    lda adjust_flags
    ora #4
    sta adjust_flags
@store:
    lda adjust_flags
    sta dos64_guest+G_FLAGS
    jmp cpu_complete
