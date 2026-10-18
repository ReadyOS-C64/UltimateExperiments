.include "reu.inc"
.include "modal_assets.inc"
.ifndef DOS64_MODAL_MENU
DOS64_MODAL_MENU=0
.endif
.if DOS64_MODAL_MENU
.macpack longbranch
.import dos64_host_input_matrix,dos64_native_diag
.import dos64_cold_open,dos64_cache_limit,dos64_overlay_ready
.import dos64_overlay_busy,dos64_overlay_current
.import dos64_reu_request,dos64_reu_transfer
.import hdb_active,sav_borrowed
.export dos64_modal_pending,dos64_modal_edge,dos64_modal_input
.segment "DEVICESTATE"
dos64_modal_pending: .res 1
dos64_modal_edge: .res 1
.segment "INPUTCODE"
; Called only inside the normal INPUT lease, after a ghost-free CIA scan.
; C=0 normal keys. C=1/A=1 handled/defer (HI_QUEUE, no guest word).
; C=1/A=0 broker loaded: the resident footer may JMP7000 AFTER lease return.
dos64_modal_input:
 lda dos64_modal_pending
 cmp #2
 jeq modal_after_redraw
 cmp #1
 beq modal_request
 lda dos64_modal_edge
 cmp #2
 bne @chord
 ldx #7
@release_fence:
 lda dos64_host_input_matrix,x
 and modal_nonmod_masks,x
 jne modal_handled
 dex
 bpl @release_fence
 jmp modal_released
@chord:
 lda dos64_host_input_matrix+7
 cmp #$a4                       ; Ctrl + Commodore + Run/Stop
 bne modal_released
 ldx #6
@other:
 lda dos64_host_input_matrix,x
 and modal_nonmod_masks,x
 bne modal_released
 dex
 bpl @other
 lda dos64_modal_edge
 bne modal_handled
 lda #1
 sta dos64_modal_edge
 sta dos64_modal_pending
modal_request:
 lda dos64_native_diag
 cmp #5
 beq modal_load
 cmp #4
 jne modal_failed
 lda dos64_native_diag+3
 ora hdb_active
 ora sav_borrowed
 bne modal_handled
 lda #2
 sta dos64_native_diag+3         ; normal coherent PAUSE command
 bne modal_handled
modal_released:
 lda #0
 sta dos64_modal_edge
 clc
 rts
modal_after_redraw:
 lda dos64_native_diag
 cmp #5
 jne modal_failed
 lda dos64_native_diag+3
 bne modal_handled
 lda dos64_native_diag+4
 cmp #$a5
 jne modal_failed
 lda #3
 sta dos64_native_diag+3         ; only after resident full redraw succeeded
 lda #0
 sta dos64_modal_pending
modal_handled:
 lda #1
 sec
 rts
modal_load:
 lda dos64_cold_open
 ora hdb_active
 ora sav_borrowed
 jne modal_failed
 lda dos64_cache_limit
 cmp #32
 jne modal_failed
 lda dos64_overlay_ready
 cmp #$a5
 jne modal_failed
 lda dos64_overlay_busy
 cmp #1
 jne modal_failed
 lda dos64_overlay_current
 cmp #3
 jne modal_failed
 ldx #0
 jsr modal_dma
 bcs modal_failed
 ldx #63
@header:
 lda $c000,x
 cmp modal_expected,x
 jne modal_failed
 dex
 bpl @header
 ldx #8
 jsr modal_dma
 bcs modal_failed
 lda #0
 sta dos64_modal_pending
 sec
 rts
modal_failed:
 lda #0
 sta dos64_modal_pending
 lda #$e1
 sta dos64_native_diag
 lda #9
 sta dos64_native_diag+1
 lda #$20
 sta dos64_native_diag+2
 bne modal_handled
modal_dma:
 ldy #7
@copy:
 lda modal_requests,x
 sta dos64_reu_request,y
 inx
 dey
 bpl @copy
 jmp dos64_reu_transfer
modal_requests:
.macro READ host, far, count
 .byte 1,>count,<count,^far,>far,<far,>host,<host
.endmacro
 READ $c000,MM_HEADER_REU,64
 READ $7000,MM_BROKER_REU,MM_BROKER_BYTES
modal_nonmod_masks:
 .byte $ff,$7f,$ff,$ff,$ff,$ff,$ef,$db
modal_expected:
 MM_EXPECTED_HEADER
.endif
