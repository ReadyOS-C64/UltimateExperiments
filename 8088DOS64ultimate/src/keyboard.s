.include "abi.inc"
.include "keyboard.inc"
.macpack longbranch
.import dos64_guest, dos64_mem_read, dos64_mem_write
.importzp dos64_address, dos64_mem_value
.export dos64_keyboard_service, dos64_keyboard_enqueue
.export dos64_keyboard_key, dos64_keyboard_waiting, dos64_keyboard_host_error
.export dos64_keyboard_status, dos64_keyboard_flags_mask, dos64_keyboard_flags_value
.export dos64_keyboard_flags_mask_high, dos64_keyboard_flags_value_high
.export dos64_keyboard_state_start, dos64_keyboard_state_end

; Independently authored from original IBM XT KEYBOARD_IO/K4/K61 listing:
; pcjs commit b4a910e606d87137e977ec89ce816f05a31c366a,
; machines/pcx86/ibm/5160/rom/bios/1982-11-08/src/XTBIOS.ASM,
; SHA256 2e55fa806f84aa332f46dfc0f09d92fd6034cd9f177134b0d11c44241bc83514.
; AH01 loads AX even for an empty ring and RET2 exposes CMP flags, IF=1,
; TF=0. Other handled services IRET and preserve caller FLAGS. The returned
; word mask/value describes the caller's saved-frame patch; guest FLAGS here
; are untouched. No scan translation, native keyboard polling or IRQ delivery.
.segment "DEVICESTATE"
dos64_keyboard_state_start:
dos64_keyboard_key: .res 2
dos64_keyboard_waiting: .res 1
dos64_keyboard_host_error: .res 1
dos64_keyboard_status: .res 1
dos64_keyboard_flags_mask: .res 1
dos64_keyboard_flags_value: .res 1
dos64_keyboard_flags_mask_high: .res 1
dos64_keyboard_flags_value_high: .res 1
k_sp: .res 1
k_head: .res 1
k_tail: .res 1
k_next: .res 1
k_low: .res 1
k_high: .res 1
k_diff: .res 1
k_flags: .res 1
k_operation: .res 1
dos64_keyboard_state_end:

.segment "CODE"
; Nonreentrant bounded calls. A/X/Y and existing memory bus scratch clobbered;
; native P except C preserved, decimal disabled internally. C=1 means status
; FULL/BAD_STATE/UNSUPPORTED/CACHE; only CACHE sets host_error. Empty AH00 is
; handled C=0, waiting=1, with AX/head unchanged so an owned ROM gate can yield.
dos64_keyboard_service:
    php
    sei
    cld
    tsx
    stx k_sp
    jsr k_clear
    lda dos64_guest+G_AX+1
    sta k_operation
    cmp #2
    jeq k_shift
    jcs k_unsupported
    jsr k_ring
    lda k_operation
    beq k_read_key
    ; Original CMP BX,tail supplies the six arithmetic result flags.
    lda #$D5
    sta dos64_keyboard_flags_mask
    lda #$0B
    sta dos64_keyboard_flags_mask_high
    lda #2
    sta dos64_keyboard_flags_value_high
    lda #0
    sta k_flags
    lda k_head
    sec
    sbc k_tail
    sta k_diff
    bcs @no_carry
    inc k_flags
@no_carry:
    lda k_diff
    bne @nonzero
    lda k_flags
    ora #$40
    sta k_flags
@nonzero:
    lda k_diff
    and #$80
    ora k_flags
    sta k_flags
    lda k_head
    eor k_tail
    eor k_diff
    and #$10
    ora k_flags
    sta k_flags
    lda k_diff
    ldx #8
    ldy #0
@parity:
    lsr
    bcc @even_bit
    iny
@even_bit:
    dex
    bne @parity
    tya
    and #1
    bne @odd
    lda k_flags
    ora #4
    sta k_flags
@odd:
    lda k_flags
    sta dos64_keyboard_flags_value
    jsr k_head_word
    jmp k_publish_ax
k_read_key:
    lda k_head
    cmp k_tail
    bne @available
    lda #1
    sta dos64_keyboard_waiting
    jmp k_done
@available:
    jsr k_head_word
    lda k_head
    jsr k_advance
    ; Publish consumption before AX; a cache failure must not invent a read.
    ldx #$1A
    jsr k_bda_write
k_publish_ax:
    lda k_low
    sta dos64_guest+G_AX
    lda k_high
    sta dos64_guest+G_AX+1
    jmp k_done
k_shift:
    lda #$17
    jsr k_bda_read
    sta dos64_guest+G_AX
    lda #0
    sta dos64_guest+G_AX+1
    jmp k_done
k_unsupported:
    lda #KB_UNSUPPORTED
    jmp k_error

; Inputs key ASCII low/scancode high are already translated XT words. Full
; queues are unchanged. Publish tail only after both coherent word stores.
dos64_keyboard_enqueue:
    php
    sei
    cld
    tsx
    stx k_sp
    jsr k_clear
    jsr k_ring
    lda k_tail
    jsr k_advance
    sta k_next
    cmp k_head
    bne @space
    lda #KB_FULL
    jmp k_error
@space:
    lda k_tail
    jsr k_buffer_address
    lda dos64_keyboard_key
    jsr k_write
    inc dos64_address
    lda dos64_keyboard_key+1
    jsr k_write
    lda k_next
    ldx #$1C
    jsr k_bda_write
k_done:
    ldx k_sp
    txs
    plp
    clc
    rts
k_bad_state:
    lda #KB_BAD_STATE
    bne k_error
k_failed:
    lda #1
    sta dos64_keyboard_host_error
    lda #KB_CACHE
k_error:
    sta dos64_keyboard_status
    ; A failed call has no saved-return FLAGS patch to apply.
    lda #0
    sta dos64_keyboard_flags_mask
    sta dos64_keyboard_flags_mask_high
    ldx k_sp
    txs
    plp
    sec
    rts
k_clear:
    lda #0
    sta dos64_keyboard_waiting
    sta dos64_keyboard_host_error
    sta dos64_keyboard_status
    sta dos64_keyboard_flags_mask
    sta dos64_keyboard_flags_value
    sta dos64_keyboard_flags_mask_high
    sta dos64_keyboard_flags_value_high
    rts
k_ring:
    lda #$1B
    jsr k_bda_read
    cmp #0
    jne k_bad_state
    lda #$1D
    jsr k_bda_read
    cmp #0
    jne k_bad_state
    lda #$1A
    jsr k_bda_read
    jsr k_validate
    sta k_head
    lda #$1C
    jsr k_bda_read
    jsr k_validate
    sta k_tail
    rts
k_validate:
    cmp #KB_START
    jcc k_bad_state
    cmp #KB_END
    jcs k_bad_state
    pha
    and #1
    jne k_bad_state
    pla
    rts
k_advance:
    clc
    adc #2
    cmp #KB_END
    bne @done
    lda #KB_START
@done:
    rts
k_head_word:
    lda k_head
    jsr k_buffer_address
    jsr k_bus_read
    sta k_low
    inc dos64_address
    jsr k_bus_read
    sta k_high
    rts
k_buffer_address:            ; A = pointer offset in segment0040
    sta dos64_address
    lda #4
    sta dos64_address+1
    lda #0
    sta dos64_address+2
    rts
k_bda_read:
    jsr k_buffer_address
k_bus_read:
    jsr dos64_mem_read
    jcs k_failed
    rts
k_bda_write:                 ; X=BDA offset,A=value
    pha
    txa
    jsr k_buffer_address
    pla
k_write:
    sta dos64_mem_value
    jsr dos64_mem_write
    jcs k_failed
    rts
