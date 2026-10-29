.setcpu "6502"
.macpack longbranch
.include "nav/api.inc"
.include "document/api.inc"
.include "document/math24.inc"
.importzp text_ptr
.segment "CODE"
.ifdef SE_INDEX_DISPATCH
.include "aux/api.inc"
.import se_overlay_call,se_overlay_frame
se_index_changed:
    lda #A_INDEX_CHANGED
    sta se_overlay_frame
    lda #AUX_ID
    ldx #1
    jsr se_overlay_call
    bcc @done
    ; Publication already happened. A missing helper may discard acceleration,
    ; but must never leave stale derived checkpoints trusted by navigation.
    lda #0
    sta se_i_ready
    sta se_n_cache_count
    sta se_n_preferred_valid
@done:
    clc
    rts
.else
; Called once after a known successful editor commit/replay. Preserve the index
; prefix strictly before edit position. This avoids whole-document rebuild on
; each navigation after typing near the end of a large file.
.ifdef SE_INDEX_IN_OVERLAY
.export se_aux_index_changed
se_aux_index_changed:
.else
se_index_changed:
.endif
    lda #0
    sta se_n_preferred_valid
    lda se_i_ready
    jeq done
    lda se_i_count
    jeq reset
    cmp #129
    jcs reset
    ldx #4
@context:
    lda se_i_original,x
    cmp se_doc_original,x
    jne reset
    lda se_i_append,x
    cmp se_doc_append,x
    jne reset
    dex
    bpl @context
    lda se_i_generation
    cmp se_doc_generation
    bne @changed
    lda se_i_generation+1
    cmp se_doc_generation+1
    beq reset ;known publication may alias an old16-bit generation after wrap
@changed:
    lda #0
    sta se_n_cache_count
    inc se_i_generation
    bne :+
    inc se_i_generation+1
:
    lda se_i_generation
    cmp se_doc_generation
    bne reset
    lda se_i_generation+1
    cmp se_doc_generation+1
    bne reset
    CMP24 se_i_scan,se_doc_edit_position
    bcc done ;all scanned bytes precede this edit
@trim:
    lda se_i_count
    sec
    sbc #1
    jsr pointer
    ldy #2
@compare:
    lda (text_ptr),y
    cmp se_doc_edit_position,y
    bcc @restore
    bne @drop
    dey
    bpl @compare
@drop:
    lda se_i_count
    cmp #1
    beq @restore
    dec se_i_count
    bne @trim
@restore:
    ldy #0
    ldx #0
@byte:
    lda (text_ptr),y
    sta se_i_scan,x
    iny
    inx
    cpx #9 ;scan,line,number contiguous resident fields
    bcc @byte
done:
.ifdef SE_INDEX_IN_OVERLAY
    clc ;the old void helper's incidental compare flags are not overlay errors
.endif
    rts
reset:
    lda #0
    sta se_i_ready
    sta se_n_cache_count
.ifdef SE_INDEX_IN_OVERLAY
    clc
.endif
    rts
pointer:
    tax ;retain ordinal while clearing/scaling the16-bit scratch
    sta se_n_temp
    lda #0
    sta se_n_temp+1
    .repeat 3
        asl se_n_temp
        rol se_n_temp+1
    .endrepeat
    clc
    txa
    adc se_n_temp
    sta text_ptr
    lda se_n_temp+1
    adc #>INDEX_FIRST
    sta text_ptr+1
    rts
.endif
