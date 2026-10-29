.setcpu "6502"
.macpack longbranch
.include "document/api.inc"
.include "object/api.inc"
.include "document/splice.inc"
.include "document/math24.inc"
.include "document/frames/splice_build.inc"
.ifndef ENGINE_STATE_ONLY
.segment "CODE"
; A1/Cclear pending, A0/Cclear committed, Anonzero/Cset error and rolled back.
; Incomplete feed returns45 without aborting, permitting more feed/cancel.
; At most8 old pieces/call. All durable mutation is at the final resident point.
se_doc_splice_step:
    lda se_doc_busy
    cmp #1
    beq @phase
    cmp #2
    jne @state
@phase:
    jsr se_doc_validate
    jcs @abort
    lda tx_left
    ora tx_left+1
    ora tx_left+2
    jne @incomplete
    lda #2
    sta se_doc_busy
    lda #8
    sta build_budget
    lda doc_refs_active
    beq @next
    jsr doc_refs_step
    jcs @abort
    cmp #1
    jeq @pending
    lda ref_resume
    cmp #2
    jeq @flush
    lda #1
    sta build_budget ; resumed old suffix is the only old piece this call
    jmp @suffix
@next:
    lda tx_local_mode
    beq @walk
    jsr doc_local_try
    jcs @abort
    cmp #1
    jeq @yield_root
@walk:
    jsr se_doc_walk_next
    bcc @piece
    cmp #0
    jeq @finish
    jmp @abort
@piece:
    ADD24 tx_old_pos,se_doc_walk_piece+6,tx_piece_end
    jcs @corrupt
    ; Prefix strictly before insertion position; untouched whole pieces pass.
    CMP24 tx_old_pos,tx_position
    bcs @insert
    CMP24 tx_piece_end,tx_position
    bcs @prefix_split
    COPY24 se_doc_walk_piece+6,fragment_length
    jmp @prefix
@prefix_split:
    SUB24 tx_position,tx_old_pos,fragment_length
@prefix:
    jsr copy_piece
    COPY24 fragment_length,se_doc_emit+6
    jsr doc_emit_piece
    jcs @abort
@insert:
    lda tx_inserted
    bne @suffix
    CMP24 tx_piece_end,tx_position
    bcc @suffix
    lda #1
    sta ref_resume
    jsr emit_insert
    jcs @abort
    cmp #1
    jeq @pending
@suffix:
    CMP24 tx_piece_end,tx_end
    jcc @advance
    jeq @advance
    CMP24 tx_old_pos,tx_end
    bcs @whole_suffix
    SUB24 tx_end,tx_old_pos,fragment_delta
    SUB24 tx_piece_end,tx_end,fragment_length
    jmp @fragment
@whole_suffix:
    lda #0
    sta fragment_delta
    sta fragment_delta+1
    sta fragment_delta+2
    COPY24 se_doc_walk_piece+6,fragment_length
@fragment:
    jsr copy_piece
    ADD24 se_doc_walk_piece+3,fragment_delta,se_doc_emit+3
    jcs @corrupt
    COPY24 fragment_length,se_doc_emit+6
    jsr doc_emit_piece
    jcs @abort
@advance:
    COPY24 tx_piece_end,tx_old_pos
@yield_root:
    dec build_budget
    jne @next
    jmp @pending
@finish:
    lda tx_inserted
    bne @flush
    lda #2
    sta ref_resume
    jsr emit_insert ; empty document or insertion at EOF
    jcs @abort
    cmp #1
    jeq @pending
@flush:
    jsr doc_emit_finish
    jcs @abort
    CMP24 emit_total,tx_new_length
    jne @corrupt
    ; All new leaves validated/stashed. Resize append then publish roots with
    ; no intervening fallible operation. IRQ/NMI never observe/edit these fields.
    DOC_TOKEN se_doc_append
    COPY24 tx_append_end,se_object_offset
    jsr se_object_resize
    jcs @abort
.ifdef ENGINE_CODE
.endif
    ldx #0
@publish:
    lda se_doc_next_roots,x
    sta se_doc_roots,x
    inx
    bne @publish
    COPY24 tx_new_length,se_doc_length
    lda emit_root_count
    sta se_doc_root_count
    inc se_doc_generation
    bne :+
    inc se_doc_generation+1
:
    jsr se_doc_invalidate
.ifdef ENGINE_CODE
.endif
    lda #0
    sta se_doc_busy
    clc
    rts
@pending:
    lda #1
    clc
    rts
@corrupt:
    lda #$42
@abort:
    cmp #$43
    bne @cancel
    ldx tx_local_mode
    beq @cancel
    ; Extra local boundaries can exceed32 roots even if a packed graph fits.
    ; Restart from private staged data; old roots/append remain unpublished.
    jsr doc_emit_reset
    bcs @cancel
    jsr se_doc_walk_reset
    jsr doc_refs_rewind
    lda #0
    sta tx_local_mode
    sta se_doc_reused_roots
    sta tx_old_pos
    sta tx_old_pos+1
    sta tx_old_pos+2
    sta tx_inserted
    jmp @pending
@cancel:
    pha
    jsr se_doc_splice_cancel
    pla
    sec
    rts
@incomplete:
    lda #$45
    sec
    rts
@state:
    lda #$40
    sec
    rts
copy_piece:
    ldx #15
@copy:
    lda se_doc_walk_piece,x
    sta se_doc_emit,x
    dex
    bpl @copy
    rts
emit_insert:
    lda tx_ref_mode
    beq @byte
    jmp doc_refs_start
@byte:
    lda #1
    sta tx_inserted
    ldx #15
    lda #0
@clear:
    sta se_doc_emit,x
    dex
    bpl @clear
    lda se_doc_append
    sta se_doc_emit
    lda se_doc_append+1
    sta se_doc_emit+1
    lda se_doc_append+2
    sta se_doc_emit+2
    COPY24 tx_append_start,se_doc_emit+3
    COPY24 tx_insert,se_doc_emit+6
    jsr doc_emit_piece
    bcs @return
    lda #0
    clc
@return:
    rts

.endif

.ifdef ENGINE_CODE
.include "render/api.inc"
.include "hot/api.inc"
.include "history/api.inc"
.endif
