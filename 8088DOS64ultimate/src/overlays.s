.include "overlays.inc"
.include "reu.inc"
.import dos64_pit_init, dos64_pit_rebase, dos64_pit_advance, dos64_pit_poll
.import dos64_irq_pulse, dos64_irq_select, dos64_irq_try, dos64_irq_repeat
.import __IRQMAIN_SIZE__, __IRQDEVICE_SIZE__, __PITCODE_SIZE__
PIT_SIZE = __IRQMAIN_SIZE__+__IRQDEVICE_SIZE__+__PITCODE_SIZE__
.assert PIT_SIZE <= OV_WINDOW_SIZE, lderror, "PIT too large"

.import dos64_render_graphics_line, dos64_present_graphics_line, __GFXCODE_SIZE__
.assert __GFXCODE_SIZE__ <= OV_WINDOW_SIZE, lderror, "GFX too large"

.macpack longbranch
.import dos64_reu_transfer, dos64_reu_request
.import dos64_files_init, dos64_files_start, dos64_files_poll, dos64_render_text_row
.import __FILECODE_SIZE__, __RENDERCODE_SIZE__, __DISPLAYCODE_SIZE__, __DISPLAYCODE_RUN__, __INPUTCODE_SIZE__
.import dos64_native_text_setup, dos64_native_text_restore, dos64_native_text_state
TEXT_SIZE = __RENDERCODE_SIZE__ + __DISPLAYCODE_SIZE__
.assert __RENDERCODE_SIZE__ = 718, lderror, "renderer canonical length changed"
.assert __DISPLAYCODE_SIZE__ = 245, lderror, "display canonical length changed"
.assert TEXT_SIZE = 963, lderror, "combined TEXT canonical length changed"
.assert __DISPLAYCODE_RUN__ = OV_WINDOW+__RENDERCODE_SIZE__, lderror, "TEXT display segment must immediately follow renderer"
.import dos64_host_input_init, dos64_host_input_poll, dos64_cold_open
.export dos64_overlay_input_init, dos64_overlay_input_poll
.export dos64_overlay_init, dos64_overlay_bootstrap, dos64_overlay_acquire, dos64_overlay_release
.export dos64_overlay_files_init, dos64_overlay_files_start, dos64_overlay_files_poll
.export dos64_overlay_render_text_row, dos64_overlay_text_setup, dos64_overlay_text_restore
.export dos64_overlay_ready, dos64_overlay_current, dos64_overlay_busy
.export dos64_overlay_requested, dos64_overlay_error, dos64_overlay_reu_mib
.export dos64_overlay_code_start, dos64_overlay_code_end
.export dos64_overlay_boot_code_start, dos64_overlay_boot_code_end
.export dos64_overlay_headers
.assert OV_ASSETS >= $340000, error, "overlay assets below owned staging slice"
.assert OV_ASSETS+5*OV_SLOT_SIZE <= $380000, error, "overlay assets exceed owned staging slice"
.assert (OV_ASSETS & (OV_SLOT_SIZE-1)) = 0, error, "overlay slots require 2 KiB alignment"
.assert OV_HEADER+OV_WINDOW_SIZE <= OV_SLOT_SIZE, error, "overlay header/payload exceeds slot"
.assert __FILECODE_SIZE__ > 0, lderror, "empty file overlay"
.assert __RENDERCODE_SIZE__ > 0, lderror, "empty text overlay"
.assert __FILECODE_SIZE__ <= OV_WINDOW_SIZE, lderror, "file overlay exceeds window"
.assert TEXT_SIZE <= OV_WINDOW_SIZE, lderror, "text overlay exceeds window"

.segment "DEVICESTATE"
dos64_overlay_ready: .res 1
dos64_overlay_current: .res 1
dos64_overlay_busy: .res 1
dos64_overlay_requested: .res 1
dos64_overlay_error: .res 1
dos64_overlay_reu_mib: .res 1

.segment "CODE"
dos64_overlay_code_start:
; PHP precedes CLD so decimal/IRQ/other native flags survive every public exit.
dos64_overlay_acquire:
    php
    sei
    cld
    tsx
    lda $0103,x                 ; immediate native return address high byte
    cmp #>OV_WINDOW
    bcc :+
    cmp #>(OV_WINDOW+OV_WINDOW_SIZE)
    bcc ov_origin
:   lda dos64_overlay_busy
    jne ov_busy
    lda dos64_overlay_ready
    cmp #OV_READY
    bne ov_unready
    lda dos64_overlay_requested
    cmp #OV_FILE
    bcc ov_bad_id
    cmp #6
    bcs ov_bad_id
    inc dos64_overlay_busy
    cmp dos64_overlay_current
    beq ov_ok
    lda #0
    sta dos64_overlay_current
    lda dos64_overlay_requested
    asl
    asl
    asl
    clc
    adc #32                      ; variant header descriptor base
    tax
    jsr ov_dma
    bcs ov_dma_failed
    lda dos64_overlay_requested
    asl
    asl
    asl
    asl
    sec
    sbc #OV_HEADER
    tax
    ldy #0
@header:
    lda dos64_overlay_headers,x
    cmp $C000,y
    bne ov_header_failed
    inx
    iny
    cpy #OV_HEADER
    bne @header
    lda dos64_overlay_requested
    asl
    asl
    asl
    clc
    adc #72                      ; variant payload descriptor base
    tax
    jsr ov_dma
    bcs ov_dma_failed
    lda dos64_overlay_requested
    sta dos64_overlay_current
ov_ok:
    lda #0
    sta dos64_overlay_error
    plp
    clc
    rts
ov_busy:
    lda #OV_ERR_BUSY
    bne ov_error                 ; never steal another owner's lock
ov_unready:
    lda #OV_ERR_UNREADY
    bne ov_error
ov_origin:
    lda #OV_ERR_ORIGIN
    bne ov_error
ov_cold:
    lda #OV_ERR_COLD
    bne ov_error
ov_capacity:
    lda #OV_ERR_CAPACITY
    bne ov_error
ov_bad_id:
    lda #OV_ERR_ID
    bne ov_error
ov_header_failed:
    lda #OV_ERR_HEADER
    bne ov_failed
ov_dma_failed:
    lda #OV_ERR_DMA
ov_failed:
    ldx #0
    stx dos64_overlay_busy
ov_error:
    sta dos64_overlay_error
    plp
    sec
    rts

dos64_overlay_release:
    php
    sei
    lda #0
    sta dos64_overlay_busy
    plp
    rts                          ; preserve wrapped target carry

; Entry wrappers keep all native returns outside C900–CFFF during replacement.
; An overlaid callback cannot recursively enter any wrapper while busy is held.
.macro WRAP name, id, target, display_phase
name:
    php
    sei
    lda dos64_overlay_busy
    jne ov_busy
    .if .paramcount = 4
    .if display_phase
        lda dos64_cold_open
        jne ov_cold
    .endif
    .endif
    lda #id
    sta dos64_overlay_requested
    plp
    jsr dos64_overlay_acquire
    bcs :+
    jsr target
    jmp dos64_overlay_release
:   rts
.endmacro
WRAP dos64_overlay_files_init, OV_FILE, dos64_files_init
WRAP dos64_overlay_files_start, OV_FILE, dos64_files_start
WRAP dos64_overlay_files_poll, OV_FILE, dos64_files_poll
WRAP dos64_overlay_render_text_row, OV_TEXT, dos64_render_text_row, 1
.segment "DEVICECODE"
WRAP dos64_overlay_text_setup, OV_TEXT, dos64_native_text_setup, 1
WRAP dos64_overlay_text_restore, OV_TEXT, dos64_native_text_restore, 1
.segment "CODE"
WRAP dos64_overlay_input_init, OV_INPUT, dos64_host_input_init
WRAP dos64_overlay_input_poll, OV_INPUT, dos64_host_input_poll


.export dos64_overlay_pit_init
WRAP dos64_overlay_pit_init, OV_PIT, dos64_pit_init
.export dos64_overlay_pit_rebase
WRAP dos64_overlay_pit_rebase, OV_PIT, dos64_pit_rebase
.export dos64_overlay_pit_advance
WRAP dos64_overlay_pit_advance, OV_PIT, dos64_pit_advance
.export dos64_overlay_pit_poll
WRAP dos64_overlay_pit_poll, OV_PIT, dos64_pit_poll
.export dos64_overlay_irq_pulse
WRAP dos64_overlay_irq_pulse, OV_PIT, dos64_irq_pulse
.export dos64_overlay_irq_select
WRAP dos64_overlay_irq_select, OV_PIT, dos64_irq_select
.export dos64_overlay_irq_try
WRAP dos64_overlay_irq_try, OV_PIT, dos64_irq_try
.export dos64_overlay_irq_repeat
WRAP dos64_overlay_irq_repeat, OV_PIT, dos64_irq_repeat
.export dos64_overlay_render_graphics_line
WRAP dos64_overlay_render_graphics_line, OV_GFX, dos64_render_graphics_line, 1
.export dos64_overlay_present_graphics_line
WRAP dos64_overlay_present_graphics_line, OV_GFX, dos64_present_graphics_line, 1

; Descriptors are reversed for the eight-byte loop into request[7..0].
ov_dma:
    ldy #7
:   lda ov_requests,x
    sta dos64_reu_request,y
    inx
    dey
    bpl :-
    jmp dos64_reu_transfer
ov_requests:
.macro REQUEST host, far, length, direction
    .byte direction, .hibyte(length), .lobyte(length), .bankbyte(far), .hibyte(far), .lobyte(far), .hibyte(host), .lobyte(host)
.endmacro
    REQUEST OV_SOURCE, OV_ASSETS, OV_SLOT_SIZE, 0
    REQUEST OV_SOURCE+OV_SLOT_SIZE, OV_ASSETS+OV_SLOT_SIZE, OV_SLOT_SIZE, 0
    REQUEST OV_INPUT_SOURCE, OV_ASSETS+2*OV_SLOT_SIZE, OV_SLOT_SIZE, 0
    REQUEST OV_PIT_SOURCE, OV_ASSETS+3*OV_SLOT_SIZE, OV_SLOT_SIZE, 0
    REQUEST OV_GFX_SOURCE, OV_ASSETS+4*OV_SLOT_SIZE, OV_SLOT_SIZE, 0
    REQUEST $C000, OV_ASSETS, OV_HEADER, 1
    REQUEST $C000, OV_ASSETS+OV_SLOT_SIZE, OV_HEADER, 1
    REQUEST $C000, OV_ASSETS+2*OV_SLOT_SIZE, OV_HEADER, 1
    REQUEST $C000, OV_ASSETS+3*OV_SLOT_SIZE, OV_HEADER, 1
    REQUEST $C000, OV_ASSETS+4*OV_SLOT_SIZE, OV_HEADER, 1
    REQUEST OV_WINDOW, OV_ASSETS+OV_HEADER, __FILECODE_SIZE__, 1
    REQUEST OV_WINDOW, OV_ASSETS+OV_SLOT_SIZE+OV_HEADER, TEXT_SIZE, 1
    REQUEST OV_WINDOW, OV_ASSETS+2*OV_SLOT_SIZE+OV_HEADER, __INPUTCODE_SIZE__, 1
    REQUEST OV_WINDOW, OV_ASSETS+3*OV_SLOT_SIZE+OV_HEADER, PIT_SIZE, 1
    REQUEST OV_WINDOW, OV_ASSETS+4*OV_SLOT_SIZE+OV_HEADER, __GFXCODE_SIZE__, 1
dos64_overlay_headers:
    .byte "D64O",1,OV_FILE
    .word __FILECODE_SIZE__,OV_WINDOW
    .word 0
    .byte "FILE"
    .byte "D64O",1,OV_TEXT
    .word TEXT_SIZE,OV_WINDOW
    .word 0
    .byte "TEXT"
    .byte "D64O",1,OV_INPUT
    .word __INPUTCODE_SIZE__,OV_WINDOW
    .word 0
    .byte "KEYS"
    .byte "D64O",1,OV_PIT
    .word PIT_SIZE,OV_WINDOW
    .word 0
    .byte "TIME"
    .byte "D64O",1,OV_GFX
    .word __GFXCODE_SIZE__,OV_WINDOW
    .word 0
    .byte "CGA "
dos64_overlay_code_end:

; Bootstrap is cold resident CODE to keep DEVICECODE budget below 400 bytes.
.segment "CODE"
dos64_overlay_init:
    php
    sei
    lda dos64_cold_open
    cmp #$a5
    jne ov_cold
    lda #0
    sta dos64_overlay_ready
    sta dos64_overlay_current
    sta dos64_overlay_busy
    sta dos64_overlay_requested
    sta dos64_overlay_reu_mib
    sta dos64_overlay_error
    sta dos64_native_text_state
    plp
    clc
    rts

dos64_overlay_bootstrap:
    php
    sei
    lda dos64_overlay_busy
    jne ov_busy
    lda dos64_overlay_ready
    cmp #OV_READY
    jeq ov_ok
    lda dos64_cold_open
    cmp #$a5
    jne ov_cold
    plp
    jmp dos64_overlay_cold_bootstrap
.segment "COLDINIT"
dos64_overlay_boot_code_start:
dos64_overlay_cold_bootstrap:
    php
    sei
    cld
    lda dos64_overlay_busy
    jne ov_busy
    lda dos64_overlay_ready
    cmp #OV_READY
    jeq ov_ok                     ; source already belongs to bitmap
    lda dos64_overlay_reu_mib
    cmp #4
    jcc ov_capacity
    cmp #17
    jcs ov_capacity
    lda #0
    sta dos64_overlay_ready
    sta dos64_overlay_current
    inc dos64_overlay_busy
    ldx #OV_HEADER-1
@headers:
    lda OV_SOURCE,x
    cmp dos64_overlay_headers,x
    jne ov_header_failed
    lda OV_SOURCE+OV_SLOT_SIZE,x
    cmp dos64_overlay_headers+OV_HEADER,x
    jne ov_header_failed
    lda OV_INPUT_SOURCE,x
    cmp dos64_overlay_headers+2*OV_HEADER,x
    jne ov_header_failed
    lda OV_PIT_SOURCE,x
    cmp dos64_overlay_headers+3*OV_HEADER,x
    jne ov_header_failed
    lda OV_GFX_SOURCE,x
    cmp dos64_overlay_headers+4*OV_HEADER,x
    jne ov_header_failed
    dex
    bpl @headers
    ldx #0
    jsr ov_dma
    jcs ov_dma_failed
    ldx #8
    jsr ov_dma
    jcs ov_dma_failed
    ldx #16
    jsr ov_dma
    jcs ov_dma_failed
    ldx #24
    jsr ov_dma
    jcs ov_dma_failed
    ldx #32
    jsr ov_dma
    jcs ov_dma_failed
    lda #OV_READY
    sta dos64_overlay_ready
    lda #0
    sta dos64_overlay_busy
    jmp ov_ok
 dos64_overlay_boot_code_end:

.assert __INPUTCODE_SIZE__ <= OV_WINDOW_SIZE, lderror, "input overlay exceeds window"
