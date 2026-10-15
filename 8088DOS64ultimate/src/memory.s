.include "abi.inc"
.include "reu.inc"
.include "memory.inc"
.macpack longbranch
.importzp dos64_address
.import dos64_reu_request, dos64_reu_transfer
.export dos64_cache_init, dos64_mem_read, dos64_mem_write, dos64_mem_write_span_byte
.export dos64_cache_acquire, dos64_cache_release, dos64_cache_flush
.export dos64_cache_limit, dos64_memory_mode, dos64_memory_error
.export dos64_cache_map, dos64_cache_tags_lo, dos64_cache_tags_hi
.export dos64_cache_flags, dos64_cache_pins, dos64_cache_generations_lo
.export dos64_cache_generations_hi, dos64_cache_hand, dos64_video_dirty
.export dos64_mem_value, dos64_mem_pointer, dos64_cache_selected
.export dos64_cache_ready, dos64_write_epoch

.segment "ZEROPAGE"
mem_map_pointer: .res 2
dos64_mem_pointer: .res 2
dos64_mem_value: .res 1

.segment "BSS"
dos64_cache_limit: .res 1
dos64_memory_mode: .res 1
dos64_memory_error: .res 1
dos64_cache_hand: .res 1
dos64_cache_selected: .res 1
dos64_cache_ready: .res 1
dos64_video_dirty: .res 1
dos64_write_epoch: .res 4
mem_want_lo: .res 1
mem_want_hi: .res 1
mem_scan: .res 1
mem_access_kind: .res 1
mem_flush_index: .res 1

.segment "PAGEMAP"
dos64_cache_map: .res 2048
.segment "CACHEMETA"
dos64_cache_tags_lo: .res MEM_FRAMES
dos64_cache_tags_hi: .res MEM_FRAMES
dos64_cache_flags: .res MEM_FRAMES
dos64_cache_pins: .res MEM_FRAMES
dos64_cache_generations_lo: .res MEM_FRAMES
dos64_cache_generations_hi: .res MEM_FRAMES
.assert dos64_cache_map = MEM_MAP_BASE, lderror, "page map must be aligned at E100"
.assert dos64_cache_tags_lo = $E900, lderror, "frame metadata must start at E900"
.assert MEM_FRAME_BASE + MEM_FRAMES*MEM_PAGE_SIZE = $C000, error, "guest frames must fit 8000-BFFF"

.segment "CODE"
; Cache entry points require RAM+I/O mapping ($01 low bits 5, outputs enabled).
; They are synchronous/non-reentrant, preserve P except C, clobber A/X/Y.
; Error is returned in carry + memory_error. Shared address/value remain input.
; REU guest arena [0,1 MiB) is owned here; no other arena can be addressed.

; Cold initialization only: caller must flush before discarding a live cache.
; In: cache_limit 1..32. Out: empty cache, PC bus mode, no backing RAM writes.
dos64_cache_init:
    php
    sei
    cld
    lda #0
    sta dos64_cache_ready
    lda dos64_cache_limit
    beq @invalid
    cmp #MEM_FRAMES+1
    bcs @invalid
    lda #0
    sta mem_map_pointer
    lda #>MEM_MAP_BASE
    sta mem_map_pointer+1
    ldx #8
    ldy #0
    lda #$FF
@page:
    sta (mem_map_pointer),y
    iny
    bne @page
    inc mem_map_pointer+1
    dex
    bne @page
    lda #0
    ldx #MEM_FRAMES-1
@frames:
    sta dos64_cache_flags,x
    sta dos64_cache_pins,x
    sta dos64_cache_tags_lo,x
    sta dos64_cache_tags_hi,x
    sta dos64_cache_generations_lo,x
    sta dos64_cache_generations_hi,x
    dex
    bpl @frames
    sta dos64_cache_hand
    sta dos64_memory_mode
    sta dos64_video_dirty
    sta dos64_write_epoch
    sta dos64_write_epoch+1
    sta dos64_write_epoch+2
    sta dos64_write_epoch+3
    lda #$A5
    sta dos64_cache_ready
    jmp mem_success
@invalid:
    lda #MEM_ERR_INIT
    jmp mem_failure

; Out: A byte; ignored/uninstalled reads are FF. Pointer not retained.
dos64_mem_read:
    php
    sei
    cld
    jsr mem_check
    jcs mem_failure
    lda mem_access_kind
    cmp #2
    beq @hole
    jsr mem_resolve
    jcs mem_failure
    ldy #0
    lda (dos64_mem_pointer),y
    pha
    lda #0
    sta dos64_memory_error
    pla
    plp
    clc
    rts
@hole:
    lda #0
    sta dos64_memory_error
    lda #$FF
    plp
    clc
    rts

; In: mem_value. ROM/hole writes ignored, PC CGA writes mark video dirty.
dos64_mem_write:
    php
    sei
    cld
    jsr mem_check
    jcs mem_failure
    lda mem_access_kind
    beq @write
    cmp #3
    beq @write
    jmp mem_success
@write:
    jsr mem_resolve
    jcs mem_failure
    ldy #0
mem_store:
    lda dos64_mem_value
    sta (dos64_mem_pointer),y
    ldx dos64_cache_selected
    lda dos64_cache_flags,x
    ora #MEM_DIRTY
    sta dos64_cache_flags,x
    inc dos64_cache_generations_lo,x
    bne @epoch
    inc dos64_cache_generations_hi,x
@epoch:
    inc dos64_write_epoch
    bne @video
    inc dos64_write_epoch+1
    bne @video
    inc dos64_write_epoch+2
    bne @video
    inc dos64_write_epoch+3
@video:
    lda mem_access_kind
    cmp #3
    jne mem_success
    lda #1
    sta dos64_video_dirty
    jmp mem_success

; Continuation of a successful writable RAM/CGA mem_write. ROM/hole ignored
; writes never establish this capability. No intervening bus/cache access.
; In: same selected frame, pointer, access kind; Y bounded within that page;
; mem_value byte. Caller guarantees no page/region seam or cache mutation.
; Same dirty/generation/epoch/video publication per byte as ordinary writes.
; Does not acquire or resolve; synchronous, preserve P except C, clobber A/X.
dos64_mem_write_span_byte:
    php
    sei
    cld
    jmp mem_store

; Read-only acquisition, including ROM. Pins selected frame and exposes pointer.
; Caller may read only through page end; must release before yielding. Writes
; must use mem_write (or a future explicit range commit), never this pointer.
dos64_cache_acquire:
    php
    sei
    cld
    jsr mem_check
    jcs mem_failure
    lda mem_access_kind
    cmp #2
    bne @resolve
    lda #MEM_ERR_ADDRESS
    jmp mem_failure
@resolve:
    jsr mem_resolve
    jcs mem_failure
    ldx dos64_cache_selected
    lda dos64_cache_pins,x
    cmp #$FF
    bne @pin
    lda #MEM_ERR_PIN_OVERFLOW
    jmp mem_failure
@pin:
    inc dos64_cache_pins,x
mem_success:
    lda #0
    sta dos64_memory_error
    plp
    clc
    rts
mem_failure:
    sta dos64_memory_error
    plp
    sec
    rts

; In: cache_selected frame handle returned by acquire; preserves other pins.
dos64_cache_release:
    php
    sei
    cld
    ldx dos64_cache_selected
    cpx dos64_cache_limit
    bcs @invalid
    lda dos64_cache_pins,x
    beq @invalid
    dec dos64_cache_pins,x
    jmp mem_success
@invalid:
    lda #MEM_ERR_RELEASE
    jmp mem_failure

; Flush all dirty valid frames, including pinned frames, without invalidation.
dos64_cache_flush:
    php
    sei
    cld
    lda dos64_cache_ready
    cmp #$A5
    beq @ready
    lda #MEM_ERR_INIT
    jmp mem_failure
@ready:
    lda #0
    sta mem_flush_index
@frame:
    ldx mem_flush_index
    stx dos64_cache_selected
    jsr mem_flush_frame
    bcc @next
    jmp mem_failure
@next:
    inc mem_flush_index
    lda mem_flush_index
    cmp dos64_cache_limit
    bcc @frame
    jmp mem_success

; Validate raw physical address, then classify PC bus behavior.
; kind: 0 RAM, 1 ROM, 2 hole, 3 CGA VRAM. ALL_RAM bypasses device rules.
mem_check:
    lda dos64_cache_ready
    cmp #$A5
    bne @init
    lda dos64_address+2
    cmp #$10
    bcs @address
    lda dos64_memory_mode
    cmp #MEM_ALL_RAM
    beq @ram
    bcs @mode
    lda dos64_address+2
    cmp #$0A
    bcc @ram
    cmp #$0F
    beq @rom
    cmp #$0B
    bne @hole
    lda dos64_address+1
    cmp #$80
    bcc @hole
    cmp #$C0
    bcs @hole
    lda #3
    bne @kind
@ram:
    lda #0
    beq @kind
@rom:
    lda #1
    bne @kind
@hole:
    lda #2
@kind:
    sta mem_access_kind
    clc
    rts
@init:
    lda #MEM_ERR_INIT
    sec
    rts
@address:
    lda #MEM_ERR_ADDRESS
    sec
    rts
@mode:
    lda #MEM_ERR_MODE
    sec
    rts

; Lookup is direct page->frame. Misses use bounded two-pass clock replacement.
mem_resolve:
    lda dos64_address+2
    lsr
    sta mem_want_hi
    lda dos64_address+1
    ror
    sta mem_want_lo
    jsr mem_want_map
    ldy #0
    lda (mem_map_pointer),y
    cmp #$FF
    beq @miss
    sta dos64_cache_selected
    tax
    jmp @found
@miss:
    lda dos64_cache_limit
    asl
    sta mem_scan
@candidate:
    ldx dos64_cache_hand
    inc dos64_cache_hand
    lda dos64_cache_hand
    cmp dos64_cache_limit
    bcc @hand
    lda #0
    sta dos64_cache_hand
@hand:
    lda dos64_cache_pins,x
    bne @skip
    lda dos64_cache_flags,x
    and #MEM_REFERENCED
    beq @victim
    lda dos64_cache_flags,x
    and #$FF-MEM_REFERENCED
    sta dos64_cache_flags,x
@skip:
    dec mem_scan
    bne @candidate
    lda #MEM_ERR_PINNED
    sec
    rts
@victim:
    stx dos64_cache_selected
    jsr mem_flush_frame
    bcc @flushed
    rts
@flushed:
    ldx dos64_cache_selected
    lda dos64_cache_flags,x
    and #MEM_VALID
    beq @load
    lda dos64_cache_tags_lo,x
    sta mem_map_pointer
    lda dos64_cache_tags_hi,x
    clc
    adc #>MEM_MAP_BASE
    sta mem_map_pointer+1
    ldy #0
    lda #$FF
    sta (mem_map_pointer),y
@load:
    ; Unpublish old ownership before DMA may overwrite any frame bytes.
    lda #0
    sta dos64_cache_flags,x
    jsr mem_dma_host
    lda mem_want_lo
    ldx mem_want_hi
    jsr mem_dma_far
    lda #1
    sta dos64_reu_request+R_DIRECTION
    jsr dos64_reu_transfer
    bcc @loaded
    lda #MEM_ERR_IO
    sec
    rts
@loaded:
    ldx dos64_cache_selected
    lda mem_want_lo
    sta dos64_cache_tags_lo,x
    lda mem_want_hi
    sta dos64_cache_tags_hi,x
    inc dos64_cache_generations_lo,x
    bne @publish
    inc dos64_cache_generations_hi,x
@publish:
    jsr mem_want_map
    ldy #0
    txa
    sta (mem_map_pointer),y
    lda #MEM_VALID
    sta dos64_cache_flags,x
@found:
    lda dos64_cache_flags,x
    ora #MEM_REFERENCED
    sta dos64_cache_flags,x
    txa
    asl
    clc
    adc #>MEM_FRAME_BASE
    sta dos64_mem_pointer+1
    lda dos64_address+1
    and #1
    ora dos64_mem_pointer+1
    sta dos64_mem_pointer+1
    lda dos64_address
    sta dos64_mem_pointer
    clc
    rts

mem_want_map:
    lda mem_want_lo
    sta mem_map_pointer
    lda mem_want_hi
    clc
    adc #>MEM_MAP_BASE
    sta mem_map_pointer+1
    rts

; X selected frame on entry. Leaves metadata intact if write-back fails.
mem_flush_frame:
    lda dos64_cache_flags,x
    and #MEM_VALID+MEM_DIRTY
    cmp #MEM_VALID+MEM_DIRTY
    beq @dirty
    clc
    rts
@dirty:
    jsr mem_dma_host
    ldx dos64_cache_selected
    lda dos64_cache_tags_lo,x
    pha
    lda dos64_cache_tags_hi,x
    tax
    pla
    jsr mem_dma_far
    lda #0
    sta dos64_reu_request+R_DIRECTION
    jsr dos64_reu_transfer
    bcc @clean
    lda #MEM_ERR_IO
    sec
    rts
@clean:
    ldx dos64_cache_selected
    lda dos64_cache_flags,x
    and #$FF-MEM_DIRTY
    sta dos64_cache_flags,x
    clc
    rts

mem_dma_host:
    lda #0
    sta dos64_reu_request+R_HOST
    sta dos64_reu_request+R_LENGTH
    lda #2
    sta dos64_reu_request+R_LENGTH+1
    lda dos64_cache_selected
    asl
    clc
    adc #>MEM_FRAME_BASE
    sta dos64_reu_request+R_HOST+1
    rts

; A low and X high physical page number (0..2047) -> aligned REU byte address.
mem_dma_far:
    asl
    sta dos64_reu_request+R_REU+1
    txa
    rol
    sta dos64_reu_request+R_REU+2
    lda #0
    sta dos64_reu_request+R_REU
    rts
