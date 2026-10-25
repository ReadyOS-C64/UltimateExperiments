.setcpu "6502"
.macpack longbranch
.include "editor/api.inc"
.include "document/api.inc"
.include "document/math24.inc"
.include "hot/api.inc"
.importzp text_ptr
.export se_view_init,se_view_peek,se_view_advance,se_view_retreat
.segment "CODE"
; Derive visible length and cache bounds. Pending data are never read through
; committed roots. Shared document IO is refreshed on every independent call.
return:
    rts
changed:
    lda #$74
    sec
    rts
state:
    lda #$70
    sec
    rts
se_view_init:
    jsr se_doc_validate
    bcs return
    lda se_hot_ready
    beq state
    ldx #4
@context:
    lda se_hot_original,x
    cmp se_doc_original,x
    bne changed
    lda se_hot_append,x
    cmp se_doc_append,x
    bne changed
    dex
    bpl @context
    lda se_hot_generation
    cmp se_doc_generation
    bne changed
    lda se_hot_generation+1
    cmp se_doc_generation+1
    bne changed
    lda se_hot_length
    sta se_v_span
    lda se_hot_length+1
    sta se_v_span+1
    lda se_hot_old_length
    sta se_v_old_span
    lda se_hot_old_length+1
    sta se_v_old_span+1
    lda #0
    sta se_v_span+2
    sta se_v_old_span+2
    sta se_v_cache_count
    sta se_v_cache_count+1
    SUB24 se_doc_length,se_v_old_span,se_v_length
    ADD24 se_v_length,se_v_span,se_v_length
    ADD24 se_hot_base,se_v_span,se_v_hot_end
    lda #0
    clc
    rts
; Peek one source byte, preserving position. A native byte/Cclear. Caller checks
; visible EOF first.128-byte committed cache is bounded even on long lines.
se_view_peek:
    CMP24 se_v_pos,se_hot_base
    jcc before_gap
    CMP24 se_v_pos,se_v_hot_end
    jcs after_gap
    SUB24 se_v_pos,se_hot_base,se_v_phys
    lda se_v_phys+1
    cmp se_hot_left+1
    bcc gap_prefix
    bne gap_suffix
    lda se_v_phys
    cmp se_hot_left
    bcc gap_prefix
gap_suffix:
    sec
    lda se_v_phys
    sbc se_hot_left
    sta text_ptr
    lda se_v_phys+1
    sbc se_hot_left+1
    sta text_ptr+1
    clc
    lda text_ptr
    adc se_hot_right
    sta text_ptr
    lda text_ptr+1
    adc se_hot_right+1
    jmp gap_high
gap_prefix:
    lda se_v_phys
    sta text_ptr
    lda se_v_phys+1
gap_high:
    clc
    adc #>HOT_FIRST
    sta text_ptr+1
    ldy #0
    lda (text_ptr),y
    clc
    rts
before_gap:
    COPY24 se_v_pos,se_v_phys
    jmp source_byte
after_gap:
    SUB24 se_v_pos,se_v_span,se_v_phys
    ADD24 se_v_phys,se_v_old_span,se_v_phys
source_byte:
    lda se_v_cache_count
    ora se_v_cache_count+1
    beq cache_fill
    CMP24 se_v_phys,se_v_cache_base
    bcc cache_fill
    CMP24 se_v_phys,se_v_cache_end
    bcs cache_fill
    jmp cache_byte
cache_fill:
    COPY24 se_v_phys,se_v_cache_base
    lda se_v_cache_base
    and #$80
    sta se_v_cache_base
    COPY24 se_v_cache_base,se_doc_offset
    SUB24 se_doc_length,se_v_cache_base,se_v_temp
    lda se_v_temp+2
    ora se_v_temp+1
    bne @full
    lda se_v_temp
    cmp #129
    bcc @count
@full:
    lda #128
@count:
    sta se_doc_count
    sta se_v_cache_count
    lda #0
    sta se_doc_count+1
    sta se_v_cache_count+1
    sta se_doc_c64
    sta se_v_temp+1
    sta se_v_temp+2
    lda #$80
    sta se_doc_c64+1
    lda se_doc_count
    sta se_v_temp
    ADD24 se_v_cache_base,se_v_temp,se_v_cache_end
    jsr se_doc_read
    jcs return
cache_byte:
    sec
    lda se_v_phys
    sbc se_v_cache_base
    tay
    lda $8000,y
    clc
    rts
se_view_advance:
    inc se_v_pos
    bne :+
    inc se_v_pos+1
    bne :+
    inc se_v_pos+2
:
    rts
se_view_retreat:
    ; Position only; all callers immediately use peek, which defines A/P.
    lda se_v_pos
    bne @low
    lda se_v_pos+1
    bne @middle
    dec se_v_pos+2
@middle:
    dec se_v_pos+1
@low:
    dec se_v_pos
    rts
