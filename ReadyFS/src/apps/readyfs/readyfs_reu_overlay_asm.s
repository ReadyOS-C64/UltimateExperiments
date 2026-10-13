        .importzp sp
        .import pushax, incsp6
        .import _readyfs_reu_history_bank_value
        .import _readyfs_reu_overlay_bank_value
        .import _readyfs_reu_batch_bank_value
        .import _readyfs_reu_console_bank_value
        .export _readyfs_reu_console_fetch
        .export _readyfs_reu_overlay_store
        .export _readyfs_reu_overlay_fetch
        .export _readyfs_reu_session_store
        .export _readyfs_reu_session_fetch
        .export _readyfs_reu_batch_store
        .export _readyfs_reu_batch_fetch

        .segment "CODE"

; Flat cc65 boundaries for overlay cache DMA. The last argument is in A/X;
; offset and data are already on the software stack. Program one REU transfer
; directly and remove exactly six argument bytes, avoiding the proven nested
; five-argument C repacking failure in both slot stores and later fetches.
_readyfs_reu_console_fetch:
        jsr pushax
        ldx _readyfs_reu_console_bank_value
        lda #$91
        bne rf_dma_start

_readyfs_reu_overlay_store:
        jsr pushax
        ldx _readyfs_reu_overlay_bank_value
        lda #$90
        bne rf_dma_start

_readyfs_reu_overlay_fetch:
        jsr pushax
        ldx _readyfs_reu_overlay_bank_value
        lda #$91
        bne rf_dma_start

_readyfs_reu_batch_store:
        jsr pushax
        ldx _readyfs_reu_batch_bank_value
        lda #$90
        bne rf_dma_start

_readyfs_reu_batch_fetch:
        jsr pushax
        ldx _readyfs_reu_batch_bank_value
        lda #$91
rf_dma_start:
        pha
        cpx #$00
        beq rf_dma_fail
        ldy #$02
        lda (sp),y
        iny
        ora (sp),y
        beq rf_dma_fail
        ldy #$00
        lda (sp),y
        iny
        ora (sp),y
        beq rf_dma_fail

        ldy #$02
        lda (sp),y
        sta $DF02
        iny
        lda (sp),y
        sta $DF03
        iny
        lda (sp),y
        sta $DF04
        iny
        lda (sp),y
        sta $DF05
        stx $DF06
        ldy #$00
        lda (sp),y
        sta $DF07
        iny
        lda (sp),y
        sta $DF08
        pla
        sta $DF01
        lda #$01
        ldx #$00
        jmp incsp6

rf_dma_fail:
        pla
        lda #$00
        tax
        jmp incsp6

; Flat session-bank DMA uses the same manually decoded six-byte boundary as
; overlay DMA. The caller supplies a session-relative offset; add $2000 while
; programming the REU address. C callers have already bounded every transfer
; to the $DFF0-byte session allocation.
_readyfs_reu_session_store:
        jsr pushax
        lda #$90
        bne rf_session_start

_readyfs_reu_session_fetch:
        jsr pushax
        lda #$91
rf_session_start:
        pha
        lda _readyfs_reu_history_bank_value
        beq rf_session_fail
        ldy #$02
        lda (sp),y
        iny
        ora (sp),y
        beq rf_session_fail
        ldy #$00
        lda (sp),y
        iny
        ora (sp),y
        beq rf_session_fail

        ldy #$02
        lda (sp),y
        sta $DF02
        iny
        lda (sp),y
        sta $DF03
        ldy #$04
        lda (sp),y
        sta $DF04
        iny
        lda (sp),y
        clc
        adc #$20
        bcs rf_session_fail
        sta $DF05
        lda _readyfs_reu_history_bank_value
        sta $DF06
        ldy #$00
        lda (sp),y
        sta $DF07
        iny
        lda (sp),y
        sta $DF08
        pla
        sta $DF01
        lda #$01
        ldx #$00
        jmp incsp6

rf_session_fail:
        pla
        lda #$00
        tax
        jmp incsp6
