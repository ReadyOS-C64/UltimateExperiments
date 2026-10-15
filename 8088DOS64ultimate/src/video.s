.include "abi.inc"
.include "video.inc"
.macpack longbranch
.import dos64_guest, dos64_mem_read, dos64_mem_write
.import dos64_mem_write_span_byte, dos64_cache_acquire, dos64_cache_release
.import dos64_cache_selected, dos64_cache_limit, dos64_memory_error
.importzp dos64_mem_pointer
.importzp dos64_address, dos64_mem_value, dos64_segment
.export dos64_video_service, dos64_video_host_error

; All persistent/scratch bytes are outside the scarce E000 BSS allocation.
.segment "DEVICESTATE"
dos64_video_host_error: .res 1
v_sp: .res 1
v_mode: .res 1
v_cols: .res 1
v_pages: .res 1
v_stride: .res 1
v_base: .res 1
v_page: .res 1
v_rowbytes: .res 1
v_row: .res 1
v_col: .res 1
v_ptr: .res 2
v_dst: .res 2
v_src: .res 2
v_count: .res 2
v_char: .res 1
v_attr: .res 1
v_byte: .res 1
v_top: .res 1
v_bottom: .res 1
v_left: .res 1
v_right: .res 1
v_lines: .res 1
v_down: .res 1
v_width: .res 1
v_fill: .res 1
v_shift: .res 1
v_mask: .res 1
v_bits: .res 1

.segment "DEVICECODE"
; Native INT10 callback, after the whitelisted ROM OUT, before ordinary IRET.
; In/out: dos64_guest registers, coherent BDA/VRAM. Guest FLAGS unchanged.
; Out C=0 handled; C=1 unsupported/bad bounded argument (host_error=0), or
; cache failure (host_error=1). A/X/Y, address/value/segment scratch clobbered;
; host P except C preserved, decimal disabled internally. Nonreentrant, no yield.
; Error exits restore the saved native SP to unwind private helper calls; this
; does not touch the guest stack or guest interrupt return frame.
dos64_video_service:
    php
    sei
    cld
    tsx
    stx v_sp
    lda #0
    sta dos64_video_host_error
    lda dos64_guest+G_AX+1
    cmp #$10
    jcs v_done
    asl
    tax
    lda v_dispatch,x
    sta dos64_segment
    lda v_dispatch+1,x
    sta dos64_segment+1
    jmp (dos64_segment)
v_done:
    ldx v_sp
    txs
    plp
    clc
    rts
v_failed:
    lda #1
    sta dos64_video_host_error
v_unsupported:
    ldx v_sp
    txs
    plp
    sec
    rts

; Helpers never bypass the coherent bus. Fatal errors unwind to entry.
v_read:
    jsr dos64_mem_read
    jcs v_failed
    rts
v_write:
    sta dos64_mem_value
    jsr dos64_mem_write
    jcs v_failed
    rts
v_bda_address:
    sta dos64_address
    lda #4
    sta dos64_address+1
    lda #0
    sta dos64_address+2
    rts
v_bda_read:
    jsr v_bda_address
    jmp v_read
v_bda_write:                 ; X=BDA low byte, A=value
    pha
    txa
    jsr v_bda_address
    pla
    jmp v_write
v_next:
    inc dos64_address
    bne @done
    inc dos64_address+1
    bne @segment_wrap
    inc dos64_address+2
@segment_wrap:
    ; Text repetitions are stores through B800:DI. Like REP STOSW, the
    ; 16-bit offset wraps after FFFF; the PC bus ignores the intervening hole.
    lda dos64_address+1
    cmp #$80
    bne @done
    lda dos64_address+2
    cmp #$0C
    bne @done
    lda #$0B
    sta dos64_address+2
@done:
    rts
v_vram_address:
    lda v_ptr
    sta dos64_address
    clc
    lda v_ptr+1
    adc #$80
    sta dos64_address+1
    lda #$0B
    adc #0
    sta dos64_address+2
    rts
v_vram_read:
    jsr v_vram_address
    jmp v_read
v_vram_write:
    pha
    jsr v_vram_address
    pla
    jmp v_write

; For services that use geometry, accept only the supported CGA modes and
; coherent 40/80-column state. AH0F intentionally queries raw mutable BDA.
v_state:
    lda #$49
    jsr v_bda_read
    sta v_mode
    cmp #7
    jcs v_unsupported
    lda #$4B
    jsr v_bda_read
    jne v_unsupported
    lda #$4A
    jsr v_bda_read
    sta v_cols
    cmp #40
    beq @forty
    cmp #80
    jne v_unsupported
    lda #4
    sta v_pages
    lda #$10
    bne @stride
@forty:
    lda #8
    sta v_pages
    lda #8
@stride:
    sta v_stride
    lda v_cols
    asl
    sta v_rowbytes
    lda v_mode
    cmp #4
    bcc @done
    lda #1
    sta v_pages
    lda #$40
    sta v_stride
@done:
    rts
v_text:
    jsr v_state
    lda v_mode
    cmp #4
    jcs v_unsupported
    rts
v_select:                  ; A=page, computes bounded page base
    cmp v_pages
    jcs v_unsupported
    sta v_page
    tax
    lda #0
@add:
    cpx #0
    beq @done
    clc
    adc v_stride
    dex
    bne @add
@done:
    sta v_base
    rts
v_bh_page:
    lda dos64_guest+G_BX+1
    jmp v_select
v_cursor:
    lda v_page
    asl
    clc
    adc #$50
    jsr v_bda_read
    sta v_col
    jsr v_next
    jsr v_read
    sta v_row
    cmp #VIDEO_ROWS
    jcs v_unsupported
    lda v_col
    cmp v_cols
    jcs v_unsupported
    rts
v_store_cursor:
    lda v_page
    asl
    clc
    adc #$50
    tax
    lda v_col
    jsr v_bda_write
    jsr v_next
    lda v_row
    jmp v_write
v_cell:                    ; A=row, v_col=column; out v_ptr
    tax
    lda v_col
    asl
    sta v_ptr
    lda v_base
    sta v_ptr+1
@row:
    cpx #0
    beq @done
    clc
    lda v_ptr
    adc v_rowbytes
    sta v_ptr
    bcc @no_carry
    inc v_ptr+1
@no_carry:
    dex
    bne @row
@done:
    rts

v_get_mode:
    lda #$49
    jsr v_bda_read
    sta v_mode
    lda #$4A
    jsr v_bda_read
    sta v_cols
    lda #$62
    jsr v_bda_read
    sta dos64_guest+G_BX+1
    lda v_mode
    sta dos64_guest+G_AX
    lda v_cols
    sta dos64_guest+G_AX+1
    jmp v_done

v_set_mode:
    lda dos64_guest+G_AX
    cmp #7                 ; no EGA preserve-memory bit or monochrome mode
    jcs v_unsupported
    sta v_mode
    tax
    lda v_mode_cols,x
    sta v_cols
    lda v_mode_stride,x
    sta v_stride
    ; Clear the whole 16 KiB CGA aperture, including text page padding.
    lda #0
    sta dos64_address
    lda #$80
    sta dos64_address+1
    lda #$0B
    sta dos64_address+2
@clear:
    lda #0
    ldx v_mode
    cpx #4
    bcs @store
    lda dos64_address
    and #1
    tax
    lda v_blank,x
@store:
    sta dos64_mem_value
    ldy dos64_address
    beq @resolve
    jsr dos64_mem_write_span_byte
    jmp @stored
@resolve:
    jsr v_write
@stored:
    jsr v_next
    lda dos64_address+1
    cmp #$C0
    bne @clear
    ldx #$49
    lda v_mode
    jsr v_bda_write
    ldx #$4A
    lda v_cols
    jsr v_bda_write
    ldx #$4B
    lda #0
    jsr v_bda_write
    ldx #$4C
    lda #0
    jsr v_bda_write
    ldx #$4D
    lda v_stride
    jsr v_bda_write
    lda #$4E
    jsr v_bda_address
@zero:
    lda #0
    jsr v_write
    jsr v_next
    lda dos64_address
    cmp #$60
    bne @zero
    lda #7
    jsr v_write          ; BDA460 end scanline
    jsr v_next
    lda #6
    jsr v_write          ; BDA461 start scanline
    jsr v_next
    lda #0
    jsr v_write          ; BDA462 active page
    jsr v_next
    lda #$D4
    jsr v_write
    jsr v_next
    lda #3
    jsr v_write
    jsr v_next
    ldx v_mode
    lda v_mode_control,x
    jsr v_write          ; BDA465 CGA mode register shadow
    jsr v_next
    lda #$30
    ldx v_mode
    cpx #6
    bne @palette
    lda #$3F
@palette:
    jsr v_write          ; BDA466 color register shadow, original XT defaults
    jmp v_done
v_shape:
    ldx #$60
    lda dos64_guest+G_CX
    jsr v_bda_write
    jsr v_next
    lda dos64_guest+G_CX+1
    jsr v_write
    jmp v_done
v_set_cursor:
    jsr v_state
    jsr v_bh_page
    lda dos64_guest+G_DX+1
    cmp #VIDEO_ROWS
    jcs v_unsupported
    sta v_row
    lda dos64_guest+G_DX
    cmp v_cols
    jcs v_unsupported
    sta v_col
    jsr v_store_cursor
    jmp v_done
v_get_cursor:
    jsr v_state
    jsr v_bh_page
    jsr v_cursor
    lda #$60
    jsr v_bda_read
    sta dos64_guest+G_CX
    jsr v_next
    jsr v_read
    sta dos64_guest+G_CX+1
    lda v_row
    sta dos64_guest+G_DX+1
    lda v_col
    sta dos64_guest+G_DX
    jmp v_done
v_active:
    jsr v_state
    lda dos64_guest+G_AX
    jsr v_select
    ldx #$62
    lda v_page
    jsr v_bda_write
    ldx #$4E
    lda #0
    jsr v_bda_write
    jsr v_next
    lda v_base
    jsr v_write
    jmp v_done
v_read_char:
    jsr v_text
    jsr v_bh_page
    jsr v_cursor
    lda v_row
    jsr v_cell
    jsr v_vram_read
    sta v_char
    jsr v_next
    jsr v_read
    sta dos64_guest+G_AX+1
    lda v_char
    sta dos64_guest+G_AX
    jmp v_done
v_write_char:
    jsr v_text
    jsr v_bh_page
    jsr v_cursor
    lda dos64_guest+G_CX
    sta v_count
    lda dos64_guest+G_CX+1
    sta v_count+1
    ora v_count
    jeq v_done
    lda v_row
    jsr v_cell
    jsr v_vram_address
@char:
    lda dos64_guest+G_AX
    jsr v_write
    jsr v_next
    lda dos64_guest+G_AX+1
    cmp #9
    bne @skip_attr
    lda dos64_guest+G_BX
    jsr v_write
@skip_attr:
    jsr v_next
    lda v_count
    bne @low
    dec v_count+1
@low:
    dec v_count
    lda v_count
    ora v_count+1
    bne @char
    jmp v_done

; Scrolls use only the active text page. Invalid/inverted rectangles are
; rejected before writes. Zero or >=height lines clears the entire window.
v_scroll_up:
    lda #0
    beq v_scroll
v_scroll_down:
    lda #1
v_scroll:
    sta v_down
    jsr v_text
    lda #$62
    jsr v_bda_read
    jsr v_select
    lda dos64_guest+G_CX+1
    sta v_top
    lda dos64_guest+G_DX+1
    sta v_bottom
    cmp #VIDEO_ROWS
    jcs v_unsupported
    cmp v_top
    jcc v_unsupported
    lda dos64_guest+G_CX
    sta v_left
    lda dos64_guest+G_DX
    sta v_right
    cmp v_cols
    jcs v_unsupported
    cmp v_left
    jcc v_unsupported
    lda dos64_guest+G_AX
    sta v_lines
    lda dos64_guest+G_BX+1
    sta v_attr
    jsr v_scroll_window
    jmp v_done
v_scroll_window:
    sec
    lda v_right
    sbc v_left
    clc
    adc #1
    asl
    sta v_width
    sec
    lda v_bottom
    sbc v_top
    clc
    adc #1
    cmp v_lines
    bcc @clear
    beq @clear
    lda v_lines
    bne @start
@clear:
    lda #$FF
    sta v_lines
@start:
    lda v_top
    ldx v_down
    beq @row
    lda v_bottom
@row:
    sta v_row
    lda v_left
    sta v_col
    lda v_row
    jsr v_cell
    lda v_ptr
    sta v_dst
    lda v_ptr+1
    sta v_dst+1
    lda #1
    sta v_fill
    lda v_lines
    bmi @bytes
    lda v_down
    bne @source_down
    clc
    lda v_row
    adc v_lines
    cmp v_bottom
    bcc @source
    beq @source
    bcs @bytes
@source_down:
    sec
    lda v_row
    sbc v_lines
    bcc @bytes
    cmp v_top
    bcc @bytes
@source:
    jsr v_cell
    lda v_ptr
    sta v_src
    lda v_ptr+1
    sta v_src+1
    lda #0
    sta v_fill
@bytes:
    lda v_width
    sta v_count
    lda v_fill
    bne @byte
    jsr v_copy_spans
    bcc @row_done
@byte:
    lda v_fill
    beq @copy
    lda v_count
    and #1
    beq @space
    lda v_attr
    bne @put
    beq @put
@space:
    lda #$20
    bne @put
@copy:
    lda v_src
    sta v_ptr
    lda v_src+1
    sta v_ptr+1
    jsr v_vram_read
    pha
    inc v_src
    bne @got
    inc v_src+1
@got:
    pla
@put:
    sta v_byte
    lda v_dst
    sta v_ptr
    lda v_dst+1
    sta v_ptr+1
    lda v_byte
    jsr v_vram_write
    inc v_dst
    bne @advance
    inc v_dst+1
@advance:
    dec v_count
    bne @byte
@row_done:
    lda v_down
    bne @previous
    lda v_row
    cmp v_bottom
    beq @done
    clc
    adc #1
    jmp @row
@previous:
    lda v_row
    cmp v_top
    beq @done
    sec
    sbc #1
    jmp @row
@done:
    rts

.segment "HDBIOS"
; Copy remaining row bytes in exact forward order. Source stays pinned while
; destination resolves. Zero spare frames/pin overflow falls back before any
; byte of the current span. Single-frame caches always use scalar traversal.
; v_char=chunk size; v_byte=source frame, segment=source pointer, Y=index.
v_copy_spans:
    lda dos64_cache_limit
    cmp #2
    jcc @fallback
@chunk:
    lda v_count
    sta v_char
    lda v_src
    beq @dst_bound
    eor #$FF
    clc
    adc #1
    cmp v_char
    bcs @dst_bound
    sta v_char
@dst_bound:
    lda v_dst
    beq @acquire
    eor #$FF
    clc
    adc #1
    cmp v_char
    bcs @acquire
    sta v_char
@acquire:
    lda v_src
    sta v_ptr
    lda v_src+1
    sta v_ptr+1
    jsr v_vram_address
    jsr dos64_cache_acquire
    bcc @pinned
    lda dos64_memory_error
    cmp #7                  ; pin overflow: scalar read needs no new pin
    jeq @fallback
    jmp v_failed
@pinned:
    lda dos64_cache_selected
    sta v_byte
    lda dos64_mem_pointer
    sta dos64_segment
    lda dos64_mem_pointer+1
    sta dos64_segment+1
    ldy #0
    lda (dos64_segment),y
    pha
    lda v_dst
    sta v_ptr
    lda v_dst+1
    sta v_ptr+1
    jsr v_vram_address
    pla
    sta dos64_mem_value
    jsr dos64_mem_write
    jcs @write_failed
    ldy #1
    cpy v_char
    beq @release
@copy:
    lda (dos64_segment),y
    sta dos64_mem_value
    jsr dos64_mem_write_span_byte
    iny
    cpy v_char
    bne @copy
@release:
    lda v_byte
    sta dos64_cache_selected
    jsr dos64_cache_release
    clc
    lda v_src
    adc v_char
    sta v_src
    bcc @dst
    inc v_src+1
@dst:
    clc
    lda v_dst
    adc v_char
    sta v_dst
    bcc @count
    inc v_dst+1
@count:
    sec
    lda v_count
    sbc v_char
    sta v_count
    jne @chunk
    clc
    rts
.segment "HDBIOS"
@write_failed:
    lda dos64_memory_error
    pha
    lda v_byte
    sta dos64_cache_selected
    jsr dos64_cache_release
    pla
    sta dos64_memory_error
    cmp #2                  ; no evictable destination while source pinned
    jeq @fallback
    jmp v_failed
@fallback:
    sec
    rts
.segment "HDBIOS"

.segment "DEVICECODE"
v_tty:
    jsr v_text
    ; Original XT teletype uses ACTIVE_PAGE, independent of caller BH.
    lda #$62
    jsr v_bda_read
    jsr v_select
    jsr v_cursor
    lda dos64_guest+G_AX
    cmp #7                  ; bell changes no logical video state; no sound
    jeq v_done
    sta v_char
    ; Character-only write preserves the exact existing attribute byte.
    lda v_row
    jsr v_cell
    lda v_char
    cmp #8
    beq @backspace
    cmp #13
    beq @cr
    cmp #10
    beq @lf
    lda v_char
    jsr v_vram_write
    inc v_col
    lda v_col
    cmp v_cols
    bcc @cursor
@cr:
    lda #0
    sta v_col
    lda v_char
    cmp #13
    beq @cursor
@lf:
    inc v_row
    lda v_row
    cmp #VIDEO_ROWS
    bcc @cursor
    ; XT obtains the blank-line attribute at the resulting cursor location
    ; in row24 (column0 after wrap, unchanged column for a linefeed).
    lda #24
    sta v_row
    jsr v_cell
    jsr v_vram_address
    jsr v_next
    jsr v_read
    sta v_attr
    lda #0
    sta v_top
    sta v_left
    sta v_down
    lda #24
    sta v_bottom
    lda v_cols
    sec
    sbc #1
    sta v_right
    lda #1
    sta v_lines
    ; scroll helper uses v_row/v_col for its traversal, save intended cursor.
    lda v_col
    pha
    jsr v_scroll_window
    pla
    sta v_col
    lda #24
    sta v_row
    jmp @cursor
@backspace:
    lda v_col
    beq @cursor
    dec v_col
@cursor:
    jsr v_store_cursor
    jmp v_done

v_pixel:
    jsr v_state
    lda v_mode
    cmp #4
    jcc v_unsupported
    lda dos64_guest+G_DX+1
    jne v_unsupported
    lda dos64_guest+G_DX
    cmp #200
    jcs v_unsupported
    ldx #1
    ldy #64
    lda v_mode
    cmp #6
    bne @bounds
    ldx #2
    ldy #128
@bounds:
    cpx dos64_guest+G_CX+1
    jcc v_unsupported
    bne @x_ok
    tya
    cmp dos64_guest+G_CX
    jcc v_unsupported
    jeq v_unsupported
@x_ok:
    ; Row offset uses 80 bytes, with odd rows in the second 8 KiB bank.
    lda #80
    sta v_rowbytes
    lda #0
    sta v_col
    sta v_base
    lda dos64_guest+G_DX
    lsr
    pha
    bcc @even
    lda #$20
    sta v_base
@even:
    pla
    jsr v_cell
    lda dos64_guest+G_CX
    sta v_src
    lda dos64_guest+G_CX+1
    sta v_src+1
    lda #3
    sta v_mask
    lda #6
    sta v_shift
    ldx #2
    lda v_mode
    cmp #6
    bne @x_byte
    lda #1
    sta v_mask
    lda #7
    sta v_shift
    ldx #3
@x_byte:
    lsr v_src+1
    ror v_src
    dex
    bne @x_byte
    clc
    lda v_ptr
    adc v_src
    sta v_ptr
    lda v_ptr+1
    adc v_src+1
    sta v_ptr+1
    lda dos64_guest+G_CX
    and #7
    ldx v_mode
    cpx #6
    beq @subtract
    and #3
    asl
@subtract:
    sta v_bits
    sec
    lda v_shift
    sbc v_bits
    sta v_shift
    jsr v_vram_read
    sta v_byte
    lda dos64_guest+G_AX+1
    cmp #$0D
    bne @write_pixel
    lda v_byte
    ldx v_shift
    beq @read_mask
@read_shift:
    lsr
    dex
    bne @read_shift
@read_mask:
    and v_mask
    sta dos64_guest+G_AX
    jmp v_done
@write_pixel:
    lda dos64_guest+G_AX
    and v_mask
    sta v_bits
    ldx v_shift
    beq @merge
@write_shift:
    asl v_bits
    asl v_mask
    dex
    bne @write_shift
@merge:
    lda dos64_guest+G_AX
    bmi @xor
    lda v_mask
    eor #$FF
    and v_byte
    ora v_bits
    jmp @put_pixel
@xor:
    lda v_byte
    eor v_bits
@put_pixel:
    jsr v_vram_write
    jmp v_done

.segment "RODATA"
v_dispatch:
    .word v_set_mode, v_shape, v_set_cursor, v_get_cursor
    .word v_unsupported, v_active, v_scroll_up, v_scroll_down
    .word v_read_char, v_write_char, v_write_char, v_unsupported
    .word v_pixel, v_pixel, v_tty, v_get_mode
v_mode_cols: .byte 40,40,80,80,40,40,80
v_mode_stride: .byte 8,8,$10,$10,$40,$40,$40
v_mode_control: .byte $2C,$28,$2D,$29,$2A,$2E,$1E
v_blank: .byte $20,7
