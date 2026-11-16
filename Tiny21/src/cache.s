.setcpu "6502"
.import reu_transfer, REU_TILE
.importzp reu_addr, reu_ram, reu_size, reu_direction
.import vector_count, vector_cache
.importzp vector_source, vector_dest
.import key, value, layer_id, token_pos
.export cache_store, cache_slot_address

; One 32 KiB slot per layer. Each indexed position has a 100-byte K
; record followed by a 100-byte V record. Only slots at positions at or
; below the current valid position may be consumed by causal attention.
CACHE_BASE = $080000
CACHE_STRIDE = 200
.assert 128*CACHE_STRIDE <= $8000, error, "cache layer must fit a stride"

.segment "CODE"
; Set reu_addr to the current layer's slot at A (0..127).
.proc cache_slot_address
    cmp #128
    bcs fail
    ldx layer_id
    cpx #4
    bcs fail
    tay
    lda #0
    sta reu_addr
    ; LSR's original bit selects the upper half of the layer bank.
    txa
    lsr
    sta reu_addr+2
    lda #0
    ror
    sta reu_addr+1
    lda reu_addr+2
    clc
    adc #^CACHE_BASE
    sta reu_addr+2
    cpy #0
    beq finish
seek:
    clc
    lda reu_addr
    adc #CACHE_STRIDE
    sta reu_addr
    bcc :+
    inc reu_addr+1
:
    dey
    bne seek
finish:
    clc
    rts
fail:
    sec
    rts
.endproc

.macro ADDRESS ptr, addr
    lda #<(addr)
    sta ptr
    lda #>(addr)
    sta ptr+1
.endmacro

.proc cache_store
    lda token_pos
    jsr cache_slot_address
    bcs done
    ADDRESS vector_source, key
    ADDRESS vector_dest, REU_TILE
    lda #96
    sta vector_count
    jsr vector_cache
    bcs done
    ADDRESS vector_source, value
    ADDRESS vector_dest, REU_TILE+100
    jsr vector_cache
    bcs done
    ADDRESS reu_ram, REU_TILE
    ADDRESS reu_size, CACHE_STRIDE
    lda #0
    sta reu_direction
    jmp reu_transfer
done:
    rts
.endproc

.import attention
.import wide_a, wide_b, wide_product, wide_mul_byte, wide_round_divide
.export cache_attention_first

.segment "BSS"
channel: .res 1
cache_sign: .res 1

.segment "ZEROPAGE"
attention_dest: .res 2

.segment "CODE"
; At position zero each head has one value and its softmax weight is
; exactly one. Decode the V record through the real REU transfer path.
.proc cache_attention_first
    lda token_pos
    beq read
    sec
    rts
read:
    jsr cache_slot_address
    bcc :+
    rts
:
    clc
    lda reu_addr
    adc #100
    sta reu_addr
    bcc :+
    inc reu_addr+1
:
    ADDRESS reu_ram, REU_TILE
    ADDRESS reu_size, 100
    lda #1
    sta reu_direction
    jsr reu_transfer
    bcc :+
    rts
:
    ADDRESS attention_dest, attention
    lda #0
    sta channel
decode:
    lda #0
    ldx #11
clear:
    sta wide_a,x
    sta wide_b,x
    dex
    bpl clear
    .repeat 4, I
        lda REU_TILE+I
        sta wide_a+I
    .endrepeat
    ldx channel
    lda REU_TILE+4,x
    sta cache_sign
    bpl positive
    eor #$ff
    clc
    adc #1
positive:
    sta wide_b
    jsr wide_mul_byte
    ldx #11
copy:
    lda wide_product,x
    sta wide_a,x
    dex
    bpl copy
    lda #127
    sta wide_b
    jsr wide_round_divide
    bcs done
    ldy #0
    lda cache_sign
    bmi negative
    .repeat 4, I
        lda wide_a+I
        sta (attention_dest),y
        iny
    .endrepeat
    jmp advance
negative:
    sec
    .repeat 4, I
        lda #0
        sbc wide_a+I
        sta (attention_dest),y
        iny
    .endrepeat
advance:
    clc
    lda attention_dest
    adc #4
    sta attention_dest
    bcc :+
    inc attention_dest+1
:
    inc channel
    lda channel
    cmp #96
    beq :+
    jmp decode
:
    clc
done:
    rts
.endproc
