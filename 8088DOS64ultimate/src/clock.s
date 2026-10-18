.include "abi.inc"
.include "clock.inc"
.macpack longbranch
.import dos64_guest, dos64_mem_read, dos64_mem_write
.importzp dos64_address, dos64_mem_value
.export dos64_clock_service, dos64_clock_advance
.export dos64_clock_count, dos64_clock_done, dos64_clock_host_error
.export dos64_clock_state_start, dos64_clock_state_end

; Independently authored from IBM XT TIME_OF_DAY and TIMER_INT facts.
; pcjs b4a910e606d87137e977ec89ce816f05a31c366a,
; machines/pcx86/ibm/5160/rom/bios/1982-11-08/src/XTBIOS.ASM.
; The original unknown-AH path decrements AH, and IRET preserves saved FLAGS.
.segment "DEVICESTATE"
dos64_clock_state_start:
dos64_clock_count: .res 2
dos64_clock_done: .res 2
dos64_clock_host_error: .res 1
clock_bytes: .res 5
clock_index: .res 1
clock_left: .res 2
dos64_clock_state_end:

.segment "DEVICECODE"
dos64_clock_service:
    php
    sei
    cld
    lda #0
    sta dos64_clock_host_error
    lda dos64_guest+G_AX+1
    beq clock_read
    cmp #1
    beq clock_set
    dec dos64_guest+G_AX+1
    jmp clock_success
clock_read:
    jsr clock_load
    jcs clock_failure
    lda #$70
    sta dos64_address
    lda #0
    sta dos64_mem_value
    jsr dos64_mem_write
    jcs clock_failure
    lda clock_bytes+4
    sta dos64_guest+G_AX
    lda clock_bytes
    sta dos64_guest+G_DX
    lda clock_bytes+1
    sta dos64_guest+G_DX+1
    lda clock_bytes+2
    sta dos64_guest+G_CX
    lda clock_bytes+3
    sta dos64_guest+G_CX+1
    jmp clock_success
clock_set:
    lda dos64_guest+G_DX
    sta clock_bytes
    lda dos64_guest+G_DX+1
    sta clock_bytes+1
    lda dos64_guest+G_CX
    sta clock_bytes+2
    lda dos64_guest+G_CX+1
    sta clock_bytes+3
    lda #0
    sta clock_bytes+4
    jsr clock_store
    jcs clock_failure
    dec dos64_guest+G_AX+1
    jmp clock_success

dos64_clock_advance:
    php
    sei
    cld
    lda #0
    sta dos64_clock_host_error
    sta dos64_clock_done
    sta dos64_clock_done+1
    lda dos64_clock_count
    ora dos64_clock_count+1
    jeq clock_success
    jsr clock_load
    jcs clock_failure
    lda dos64_clock_count+1
    beq @short
    lda #1
    sta dos64_clock_done+1
    sta clock_left+1
    lda #0
    beq @count
@short:
    lda #0
    sta clock_left+1
    lda dos64_clock_count
@count:
    sta dos64_clock_done
    sta clock_left
@tick:
    inc clock_bytes
    bne @day
    inc clock_bytes+1
    bne @day
    inc clock_bytes+2
    bne @day
    inc clock_bytes+3
@day:
    lda clock_bytes+3
    bne @next
    lda clock_bytes+2
    cmp #$18
    bne @next
    lda clock_bytes+1
    bne @next
    lda clock_bytes
    cmp #$B0
    bne @next
    lda #0
    sta clock_bytes
    sta clock_bytes+1
    sta clock_bytes+2
    sta clock_bytes+3
    lda #1
    sta clock_bytes+4
@next:
    lda clock_left
    bne @low
    dec clock_left+1
@low:
    dec clock_left
    lda clock_left
    ora clock_left+1
    bne @tick
    jsr clock_store
    bcs @failed
    sec
    lda dos64_clock_count
    sbc dos64_clock_done
    sta dos64_clock_count
    lda dos64_clock_count+1
    sbc dos64_clock_done+1
    sta dos64_clock_count+1
    jmp clock_success
@failed:
    lda #0
    sta dos64_clock_done
    sta dos64_clock_done+1
    jmp clock_failure

clock_address:
    lda #CLOCK_BDA_LOW
    sta dos64_address
    lda #4
    sta dos64_address+1
    lda #0
    sta dos64_address+2
    sta clock_index
    rts
clock_load:
    jsr clock_address
@byte:
    jsr dos64_mem_read
    bcs @return
    ldx clock_index
    sta clock_bytes,x
    inc dos64_address
    inc clock_index
    lda clock_index
    cmp #5
    bne @byte
    clc
@return:
    rts
clock_store:
    jsr clock_address
@byte:
    ldx clock_index
    lda clock_bytes,x
    sta dos64_mem_value
    jsr dos64_mem_write
    bcs @return
    inc dos64_address
    inc clock_index
    lda clock_index
    cmp #5
    bne @byte
    clc
@return:
    rts
clock_failure:
    lda #1
    sta dos64_clock_host_error
    plp
    sec
    rts
clock_success:
    plp
    clc
    rts
