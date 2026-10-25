.setcpu "6502"
.macpack longbranch
.include "document/api.inc"
.include "document/splice.inc"
.include "document/math24.inc"
.include "document/frames/local.inc"
.ifndef ENGINE_STATE_ONLY
.segment "CODE"
; A1=whole old root reused, A0=walk normally. Never reads leaf data. Only
; canonical graphs admitted by the checked producer/replay may use this path.
doc_local_try:
    lda walk_record
    jne @walk
    lda walk_root
    cmp se_doc_root_count
    jcs @walk
    sta local_root
    asl
    asl
    asl
    tay
    lda se_doc_roots+1,y
    jeq @corrupt
    cmp #65
    jcs @corrupt
    .repeat 3,N
        lda se_doc_roots+2+N,y
        sta local_end+N
    .endrepeat
    lda local_end
    ora local_end+1
    ora local_end+2
    jeq @corrupt
    ADD24 tx_old_pos,local_end,local_end
    jcs @corrupt
    CMP24 local_end,se_doc_length
    bcc @range
    jne @corrupt
@range:
    CMP24 local_end,tx_position
    bcc @reuse
    beq @reuse
    lda tx_inserted
    beq @walk
    CMP24 tx_old_pos,tx_end
    bcc @walk
@reuse:
    ldx local_root
    jsr doc_emit_reuse_root
    bcs @return
    COPY24 local_end,tx_old_pos
    COPY24 local_end,walk_total
    inc walk_root
    inc se_doc_reused_roots
    lda #1
    clc
    rts
@walk:
    lda #0
    clc
@return:
    rts
@corrupt:
    lda #$42
    sec
    rts

.endif
