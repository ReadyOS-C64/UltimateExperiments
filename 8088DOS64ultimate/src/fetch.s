.include "abi.inc"
.include "memory.inc"
.macpack longbranch
.import dos64_guest, dos64_physical, dos64_mem_read
.importzp dos64_segment, dos64_offset, dos64_address, dos64_mem_pointer
.import dos64_cache_ready, dos64_cache_limit, dos64_memory_mode, dos64_memory_error
.import dos64_cache_selected, dos64_cache_flags, dos64_cache_tags_lo, dos64_cache_tags_hi
.import dos64_cache_generations_lo, dos64_cache_generations_hi
.export dos64_fetch_init, dos64_fast_fetch

.segment "ZEROPAGE"
fetch_pointer: .res 2
.segment "BSS"
; 11 BSS bytes + 2 ZP bytes. No acquired frame survives this routine.
fetch_valid: .res 1
fetch_cs: .res 2
fetch_ip: .res 2
fetch_frame: .res 1
fetch_tag: .res 2
fetch_generation: .res 2
fetch_mode: .res 1

.segment "CODE"
dos64_fetch_init:
    lda #0
    sta fetch_valid
    rts

; Internal CPU ABI: normal RAM/I/O mapping, CLD, synchronous/non-reentrant.
; A = fetched byte, C = memory failure, A/X/Y/P clobbered. IP advances only on
; success. The pointer is read-only and UNPINNED: operand accesses may evict it.
; Validate ownership before every dereference, including after cold cache init.
; Generation changes invalidate writes; valid/tag checks invalidate eviction.
; Reset counters can repeat, but valid+same tag still identifies the same guest
; page at this host frame, whose bytes are read now (never prefetched/copied).
dos64_fast_fetch:
    lda fetch_valid
    beq fetch_refill
    lda dos64_guest+G_IP
    cmp fetch_ip
    bne fetch_refill
    lda dos64_guest+G_IP+1
    cmp fetch_ip+1
    bne fetch_refill
    lda dos64_guest+G_CS
    cmp fetch_cs
    bne fetch_refill
    lda dos64_guest+G_CS+1
    cmp fetch_cs+1
    bne fetch_refill
    lda dos64_cache_ready
    cmp #$A5
    bne fetch_refill
    lda dos64_memory_mode
    cmp fetch_mode
    bne fetch_refill
    ldx fetch_frame
    cpx dos64_cache_limit
    bcs fetch_refill
    lda dos64_cache_flags,x
    and #MEM_VALID
    beq fetch_refill
    lda dos64_cache_tags_lo,x
    cmp fetch_tag
    bne fetch_refill
    lda dos64_cache_tags_hi,x
    cmp fetch_tag+1
    bne fetch_refill
    lda dos64_cache_generations_lo,x
    cmp fetch_generation
    bne fetch_refill
    lda dos64_cache_generations_hi,x
    cmp fetch_generation+1
    bne fetch_refill
    lda dos64_cache_flags,x
    ora #MEM_REFERENCED
    sta dos64_cache_flags,x
    ldy #0
    lda (fetch_pointer),y
    pha
    jmp fetch_advance

fetch_refill:
    lda #0
    sta fetch_valid
    lda dos64_guest+G_CS
    sta dos64_segment
    sta fetch_cs
    lda dos64_guest+G_CS+1
    sta dos64_segment+1
    sta fetch_cs+1
    lda dos64_guest+G_IP
    sta dos64_offset
    sta fetch_ip
    lda dos64_guest+G_IP+1
    sta dos64_offset+1
    sta fetch_ip+1
    jsr dos64_physical
    jsr dos64_mem_read
    bcc @success
    rts
@success:
    pha
    ; mem_read returns FF for PC holes without resolving a frame. Such bytes
    ; never establish a span, even if an earlier ALL_RAM frame still exists.
    lda dos64_memory_mode
    sta fetch_mode
    bne @cache
    lda dos64_address+2
    cmp #$0A
    bcc @cache
    cmp #$0F
    beq @cache
    cmp #$0B
    bne fetch_advance
    lda dos64_address+1
    cmp #$80
    bcc fetch_advance
    cmp #$C0
    bcs fetch_advance
@cache:
    ldx dos64_cache_selected
    stx fetch_frame
    lda dos64_cache_tags_lo,x
    sta fetch_tag
    lda dos64_cache_tags_hi,x
    sta fetch_tag+1
    lda dos64_cache_generations_lo,x
    sta fetch_generation
    lda dos64_cache_generations_hi,x
    sta fetch_generation+1
    lda dos64_mem_pointer
    sta fetch_pointer
    lda dos64_mem_pointer+1
    sta fetch_pointer+1
    lda #1
    sta fetch_valid
fetch_advance:
    inc fetch_pointer
    bne @ip
    inc fetch_pointer+1
    ; Frames start at even host pages and contain exactly two pages. Crossing
    ; to another even host page ends the 512-byte span, including FFFFF wrap.
    lda fetch_pointer+1
    and #1
    bne @ip
    sta fetch_valid
@ip:
    inc dos64_guest+G_IP
    bne @expected
    inc dos64_guest+G_IP+1
    lda dos64_guest+G_IP+1
    sta fetch_ip+1
    bne @expected
    ; Offset FFFF -> 0000 requires a fresh segmented translation even when
    ; the linear physical address would remain in this same cache page.
    sta fetch_valid
@expected:
    lda dos64_guest+G_IP
    sta fetch_ip
    lda #0
    sta dos64_memory_error
    pla
    clc
    rts
