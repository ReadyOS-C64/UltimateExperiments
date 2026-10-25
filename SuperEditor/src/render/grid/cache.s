.setcpu "6502"
GRID_CACHE_IMPLEMENTATION=1
.include "render/grid/cache.inc"
.include "render/grid/api.inc"
.ifdef EDITOR_OVERLAY
.include "editor-api.inc"
.else
.import se_gc_handle,se_gc_epoch,se_gc_width,se_gc_valid,se_gc_previous_ui,se_gc_current_ui
.import se_reu_alloc,se_reu_copy,se_reu_epoch,se_reu_retired
.import se_reu_map,se_reu_logical_owner,se_reu_physical_owner
.import se_reu_c64,se_reu_offset,se_reu_length,se_reu_logical
.endif
.export se_grid_cache_begin,se_grid_cache_row,se_grid_cache_commit
.export se_grid_cache_finish,se_grid_cache_invalidate
.segment "CODE"
se_grid_cache_begin:
    cmp #60
    beq @valid
    cmp #80
    bne cache_bad
@valid:
    pha
    txa
    pha
    jsr cache_owned
    bcc @width
    ; Provider retired/zero epochs cannot authorize a new derived allocation.
    lda se_reu_epoch
    ora se_reu_epoch+1
    beq @width
    lda se_reu_retired
    bne @width
    lda #GRID_CACHE_OWNER
    jsr se_reu_alloc
    bcs @width
    sta se_gc_handle
    lda se_reu_epoch
    sta se_gc_epoch
    lda se_reu_epoch+1
    sta se_gc_epoch+1
@width:
    pla
    tax
    ora se_gc_previous_ui
    ora se_gc_current_ui
    beq :+
    jsr se_grid_cache_invalidate
:
    stx se_gc_current_ui
    pla
    cmp se_gc_width
    beq :+
    sta se_gc_width
    jsr se_grid_cache_invalidate
:
    jmp cache_zero

se_grid_cache_invalidate:
    lda #0
    sta se_gc_valid
    sta se_gc_valid+1
    sta se_gc_valid+2
    rts

se_grid_cache_finish:
    lda se_gc_current_ui
    sta se_gc_previous_ui
cache_zero:
    lda #0
    clc
    rts
cache_bad:
    lda #$7B
    sec
    rts

; Never trust a handle across provider reset/rebind. Physical-bank selection is
; exclusively through checked logical DMA; this check does not program hardware.
cache_owned:
    lda se_reu_epoch
    ora se_reu_epoch+1
    beq @lost
    lda se_reu_retired
    bne @lost
    lda se_gc_epoch
    cmp se_reu_epoch
    bne @lost
    lda se_gc_epoch+1
    cmp se_reu_epoch+1
    bne @lost
    ldx se_gc_handle
    beq @lost
    lda se_reu_logical_owner,x
    cmp #GRID_CACHE_OWNER
    bne @lost
    ldy se_reu_map,x
    beq @lost
    lda se_reu_physical_owner,y
    cmp #GRID_CACHE_OWNER
    bne @lost
    clc
    rts
@lost:
    jsr se_grid_cache_invalidate
    sta se_gc_handle ; A0 from invalidate, no freeing possibly foreign banks
    sec
    rts

cache_index:
    cmp #2
    bcc cache_bad
    cmp #24
    bcs cache_bad
    sec
    sbc #2
    clc
    rts

; A logical row0..21 -> X valid-byte index, Y bit. No persistent scratch.
cache_bit:
    pha
    and #7
    tay
    lda cache_masks,y
    tay
    pla
    lsr
    lsr
    lsr
    tax
    rts

se_grid_cache_row:
    jsr cache_index
    bcs @return
    pha
    jsr cache_owned
    bcs cache_dirty
    pla
    pha
    jsr cache_bit
    tya
    and se_gc_valid,x
    beq cache_dirty
    pla
    pha
    jsr cache_request
    lda #1
    jsr se_reu_copy
    bcs cache_dirty
    ldx #0
@compare:
    lda G_CHARS,x
    cmp GRID_CACHE_TEMP,x
    bne cache_dirty
    inx
    cpx #GRID_CACHE_PACKET
    bne @compare
    pla
    jmp cache_zero
@return:
    rts
cache_dirty:
    pla
cache_clear_bit:
    jsr cache_bit
    tya
    eor #$FF
    and se_gc_valid,x
    sta se_gc_valid,x
    lda #1
    clc
    rts

se_grid_cache_commit:
    jsr cache_index
    bcs @return
    pha
    jsr cache_owned
    bcs @ignore
    pla
    pha
    jsr cache_request
    lda #<G_CHARS
    sta se_reu_c64
    lda #>G_CHARS
    sta se_reu_c64+1
    lda #0
    jsr se_reu_copy
    bcs @ignore
    pla
    jsr cache_bit
    tya
    ora se_gc_valid,x
    sta se_gc_valid,x
    jmp cache_zero
@ignore:
    ; A failed stash must not leave an older input valid for a partial paint.
    pla
    jsr cache_clear_bit
    jmp cache_zero
@return:
    rts

; A row0..21 -> request exact240 bytes, offset=row*240. Bounded <=21adds.
; Fetch buffer is exactly240 bytes; COMMIT overrides only the host pointer.
cache_request:
    tax
    lda #0
    sta se_reu_offset
    sta se_reu_offset+1
    sta se_reu_length+1
    cpx #0
    beq @ready
@offset:
    lda se_reu_offset
    clc
    adc #GRID_CACHE_PACKET
    sta se_reu_offset
    bcc :+
    inc se_reu_offset+1
:
    dex
    bne @offset
@ready:
    lda #GRID_CACHE_PACKET
    sta se_reu_length
    lda #<GRID_CACHE_TEMP
    sta se_reu_c64
    lda #>GRID_CACHE_TEMP
    sta se_reu_c64+1
    lda se_gc_handle
    sta se_reu_logical
    rts
.segment "RODATA"
cache_masks: .byte 1,2,4,8,16,32,64,128
