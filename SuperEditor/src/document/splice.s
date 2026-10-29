.setcpu "6502"
.macpack longbranch
.include "document/api.inc"
.include "object/api.inc"
.include "document/splice.inc"
.include "document/math24.inc"
.include "document/frames/splice.inc"
.ifndef ENGINE_STATE_ONLY
.segment "CODE"
; Full24-bit splice request. No root, generation or committed size mutation.
; A1/Cclear starts transaction; A0/Cclear is a checked zero/zero no-op.
se_doc_splice_begin:
    jsr doc_splice_admit
    bcc :+
    rts
:
    lda #0
    sta tx_local_mode
    jmp byte_begin
; Local entry accepts an already validated canonical graph. Reuses complete
; unaffected roots; the full entry remains the integrity scan/repack path.
se_doc_splice_local_begin:
    jsr doc_splice_admit
    bcc :+
    rts
:
    lda #1
    sta tx_local_mode
byte_begin:
    lda #0
    sta tx_ref_mode
    sta doc_refs_active
    jmp doc_splice_begin_checked
; Shared guard must run BEFORE changing a currently active transaction's mode.
doc_splice_admit:
    jsr se_doc_validate
    bcs @return
    lda se_doc_busy
    ora se_doc_read_locks
    beq @ok
    lda #$41
    sec
@return:
    rts
@ok:
    clc
    rts
doc_splice_begin_checked:
    CMP24 se_doc_edit_position,se_doc_length
    bcc @position
    jne @range
@position:
    ADD24 se_doc_edit_position,se_doc_edit_delete,tx_end
    jcs @range
    CMP24 tx_end,se_doc_length
    bcc @delete
    jne @range
@delete:
    SUB24 se_doc_length,se_doc_edit_delete,tx_new_length
    ADD24 tx_new_length,se_doc_edit_insert,tx_new_length
    jcs @range
    DOC_TOKEN se_doc_original
    jsr se_object_validate
    jcs @return
    lda tx_new_length+2
    cmp object_banks,x
    bcc @capacity
    jne @range
    lda tx_new_length
    ora tx_new_length+1
    jne @range
@capacity:
    DOC_TOKEN se_doc_append
    jsr se_object_validate
    jcs @return
    lda object_size_lo,x
    sta tx_append_start
    lda object_size_mid,x
    sta tx_append_start+1
    lda object_size_hi,x
    sta tx_append_start+2
    lda tx_ref_mode
    beq @byte_append
    COPY24 tx_append_start,tx_append_end
    jmp @append
@byte_append:
    ADD24 tx_append_start,se_doc_edit_insert,tx_append_end
    jcs @range
    lda tx_append_end+2
    cmp object_banks,x
    bcc @append
    jne @range
    lda tx_append_end
    ora tx_append_end+1
    jne @range
@append:
    DOC_TOKEN se_doc_meta
    jsr se_object_validate
    jcs @return
    lda se_doc_edit_insert
    ora se_doc_edit_insert+1
    ora se_doc_edit_insert+2
    ora se_doc_edit_delete
    ora se_doc_edit_delete+1
    ora se_doc_edit_delete+2
    beq @no_op
    jsr doc_emit_reset
    jcs @return
    COPY24 se_doc_edit_position,tx_position
    COPY24 se_doc_edit_insert,tx_insert
    COPY24 se_doc_edit_insert,tx_left
    lda tx_ref_mode
    beq :+
    lda #0
    sta tx_left
    sta tx_left+1
    sta tx_left+2
:
    COPY24 tx_append_start,tx_write
    lda #0
    sta se_doc_reused_roots
    sta tx_inserted
    sta tx_old_pos
    sta tx_old_pos+1
    sta tx_old_pos+2
    jsr se_doc_walk_reset
    lda #1
    sta se_doc_busy
    clc
    rts
@no_op:
    lda #0
    clc
@return:
    rts
@range:
    lda #$32
    sec
    rts
@busy:
    lda #$41
    sec
    rts

; Feed up to1024 bytes from doc read-request buffer8000-83FF. The request is
; unchanged. Only private uncommitted append space is written; retry/cancel safe.
se_doc_splice_feed:
    lda tx_ref_mode
    jne @phase
    lda se_doc_busy
    cmp #1
    jne @phase
    jsr se_doc_validate
    jcs @return
    lda se_doc_count
    sta feed_amount
    lda se_doc_count+1
    sta feed_amount+1
    ora feed_amount
    jeq @argument
    lda #0
    sta feed_amount+2
    CMP24 tx_left,feed_amount
    jcc @range
    lda se_doc_c64+1
    cmp #$80
    jcc @host
    clc
    lda se_doc_c64
    adc se_doc_count
    sta feed_end
    lda se_doc_c64+1
    adc se_doc_count+1
    jcs @host
    cmp #$84
    bcc @write
    jne @host
    lda feed_end
    jne @host
@write:
    DOC_TOKEN se_doc_append
    COPY24 tx_write,se_object_offset
    ldx #1
@request:
    lda se_doc_count,x
    sta se_object_length,x
    lda se_doc_c64,x
    sta se_object_c64,x
    dex
    bpl @request
    lda #0
    jsr se_object_copy
    bcs @return
    ADD24 tx_write,feed_amount,tx_write
    SUB24 tx_left,feed_amount,tx_left
    lda #0
    clc
@return:
    rts
@phase:
    lda #$41
    sec
    rts
@argument:
    lda #$36
    sec
    rts
@range:
    lda #$32
    sec
    rts
@host:
    lda #$33
    sec
    rts
.ifndef ENGINE_CODE
se_doc_splice_cancel:
    lda #0
    sta se_doc_busy
    sta doc_refs_active
    clc
    rts

.endif
.endif
