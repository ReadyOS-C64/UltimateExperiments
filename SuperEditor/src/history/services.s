.setcpu "6502"
.macpack longbranch
.include "history/api.inc"
.include "document/api.inc"
.include "object/api.inc"
.segment "CODE"
se_h_validate:
    jsr se_h_context
    bcs @return
    lda se_h_fault
    beq @ok
    lda #$65
    sec
@return:
    rts
@ok:
    clc
    rts
se_h_context:
    jsr se_doc_validate
    bcs @return
    lda se_h_ready
    cmp #1
    bne @state
    lda se_doc_generation
    cmp se_h_generation
    bne @changed
    lda se_doc_generation+1
    cmp se_h_generation+1
    bne @changed
    ldx #4
@context:
    lda se_h_original,x
    cmp se_doc_original,x
    bne @changed
    lda se_h_append,x
    cmp se_doc_append,x
    bne @changed
    dex
    bpl @context
    lda se_h_end+1
    cmp #$B0
    bcc @cursor
    bne @corrupt
    lda se_h_end
    bne @corrupt
@cursor:
    lda se_h_cursor+1
    cmp se_h_end+1
    bcc @journal
    bne @corrupt
    lda se_h_cursor
    cmp se_h_end
    bcc @journal
    bne @corrupt
@journal:
    DOC_TOKEN se_h_token
    jsr se_object_validate
    bcs @return
    lda object_owner,x
    cmp #6
    bne @corrupt
    lda object_size_lo,x
    ora object_size_mid,x
    bne @corrupt
    lda object_size_hi,x
    cmp #1
    bne @corrupt
    lda #0
    clc
@return:
    rts
@changed:
    lda #$64
    sec
    rts
@state:
    lda #$60
    sec
    rts
@corrupt:
    lda #$62
    sec
    rts

; A0 stash/A1 fetch, private position/count, fixed transient8000 packet.
se_h_io:
    pha
    DOC_TOKEN se_h_token
    ldx #2
@position:
    lda se_h_io_pos,x
    sta se_object_offset,x
    dex
    bpl @position
    lda se_h_io_count
    sta se_object_length
    lda se_h_io_count+1
    sta se_object_length+1
    lda #0
    sta se_object_c64
    lda #$80
    sta se_object_c64+1
    pla
    jmp se_object_copy

se_h_dirty_update:
    ldx #3
@compare:
    lda se_h_current,x
    cmp se_h_saved,x
    bne @dirty
    dex
    bpl @compare
    lda #0
    sta se_h_dirty
    rts
@dirty:
    lda #1
    sta se_h_dirty
    rts

se_h_cancel:
    lda se_h_phase
    beq @idle
    lda se_h_applied
    bne @committed
    lda #0
    jmp se_h_abort
@idle:
    lda #0
    clc
    rts
@committed:
    lda #$61
    sec
    rts
; A error,0 explicit cancellation. Own only the epoch's capture/lease/splice.
; Applied-edit status remains visible after a post-publication storage fault.
se_h_abort:
    sta se_h_error
    lda se_h_original+3
    cmp se_doc_epoch
    bne @forget
    lda se_h_original+4
    cmp se_doc_epoch+1
    bne @forget
    lda se_h_owned_capture
    beq @splice
    jsr se_range_cancel
@splice:
    lda se_h_owned_splice
    beq @lease
    jsr se_doc_splice_cancel
@lease:
    lda se_h_owned_lease
    beq @forget
    jsr se_doc_read_release
@forget:
    lda #0
    sta se_h_owned_capture
    sta se_h_owned_splice
    sta se_h_owned_lease
    sta se_h_phase
    lda se_h_applied
    beq @result
    lda se_h_error
    sta se_h_fault
@result:
    lda se_h_error
    beq @cancel
    sec
    rts
@cancel:
    clc
    rts
