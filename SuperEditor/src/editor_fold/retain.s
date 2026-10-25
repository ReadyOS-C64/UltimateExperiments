; C19-only ordered journal -> transformed hints staging. Never publish hints.
.setcpu "6502"
.macpack longbranch
EF_CONTROLLER_IMPLEMENTATION=1
.include "editor_fold/controller.inc"
.include "editor_fold/journal.inc"
.include "fold/editor-leaves/api.inc"
.include "fold/transform.inc"
.import se_ef_journal_call,se_ef_transform_call
.import se_reu_epoch
.import ec_size_object,ec_publish
.export ec_retention_prepare,ec_transform_step,ec_retire_hint,ec_retire_old
EC_TRANSFORM=4
.segment "CODE"
; Before KEY_CAPTURE: journal guard authenticates the old published graph/key
; and current visible witness. A0 unavailable -> parse expanded; A1 transformed
; hint job pending; A2 zero-event certified same visible bytes -> reuse map.
; Attempted journal/transform/provider failures are genuine errors, never a
; partly transformed fallback. Resident emergency owns hint bit0 cleanup.
ec_retention_prepare:
    lda se_ej_status
    cmp #EJ_ARMED
    beq @read
    cmp #EJ_DIRTY
    jne @none
@read:
    ; OPEN/provider replacement is a different graph, not a failed edit chain.
    ; Disarm the stale journal and build normally; never apply old events to a
    ; new document. Same-graph READLOG/provider faults still return genuine Cset.
    ldx #14
@graph:
    lda se_doc_meta,x ;meta/original/append are the contiguous15-byte graph ABI
    cmp se_ef_key,x
    jne @discard
    dex
    bpl @graph
    ldx #1
@epochs:
    lda se_reu_epoch,x
    cmp se_ef_key+EF_KEY_REU_EPOCH,x
    jne @discard
    lda se_doc_epoch,x
    cmp se_ef_key+EF_KEY_DOC_EPOCH,x
    jne @discard
    dex
    bpl @epochs
    SF_COPY se_ef_token,se_ft_input,5
    SF_COPY se_ef_count,se_ft_count,2
    SF_COPY se_ef_key+EF_KEY_LENGTH,se_ft_length,3
    lda #EJ_READLOG
    jsr se_ef_journal_call
    bcs @return
    lda se_ej_count
    beq @same_visible
    sta se_ft_log_count
    lda #0
    sta se_ft_log_pointer
    lda #$80
    sta se_ft_log_pointer+1
    ; Hint capacity equals the old map capacity; no intermediate REU object
    ; per edit. Capture hint ownership immediately after CREATE, before RESIZE.
    ldx se_ec_banks
    lda #SF_OBJECT_TYPE
    jsr se_object_create
    bcs @return
    SF_COPY se_object_id,se_fb_old_token,5
    SF_COPY se_object_id,se_ft_output,5
    lda se_ec_reuse
    ora #1
    sta se_ec_reuse
    jsr ec_size_object
    bcs @return
    jsr se_ef_key_capture
    bcs @return
    lda #3 ;R20 BEGIN_LOG; host8000 immutable until transform finishes
    jsr se_ef_transform_call
    bcs @return
    lda #EC_TRANSFORM
    sta se_ec_phase
    lda #1
    clc
    rts
@same_visible:
    ; A known hot flush may advance committed generation without changing
    ; visible bytes/revision. Zero witnessed edits need no fresh parse.
    jsr se_ef_key_capture
    bcs @return
    jsr ec_publish
    lda #2
    clc
    rts
@none:
    lda #0
    clc
@return:
    rts
@discard:
    lda #EJ_FAILED
    sta se_ej_status
    lda #0
    clc
    rts

; A1 pending / A0 hint complete, Cset error. KEY_MATCH was checked by C19 before
; every slice. Certification is tied to the captured NEW canonical key; the
; builder still freshly parses closure/ranges and owns ancestry/line counts.
ec_transform_step:
    lda #1
    jsr se_ef_transform_call
    bcs @return
    cmp #0
    bne @pending
    lda se_ft_valid
    cmp #1
    bne @bad
    ldx #2
@length:
    lda se_ft_new_length,x
    cmp se_ef_key+EF_KEY_LENGTH,x
    bne @bad
    dex
    bpl @length
    SF_COPY se_ft_written,se_fb_old_count,2
    SF_COPY se_ef_key+EF_KEY_ORIGINAL,se_fb_old_source,5
    SF_COPY se_ef_key+EF_KEY_REVISION,se_fb_old_epoch,4
    SF_COPY se_ef_key+EF_KEY_LENGTH,se_fb_old_length,3
    lda #2
    sta se_fb_old_valid
    lda #0
    clc
    rts
@pending:
    lda #1
    clc
@return:
    rts
@bad:
    lda #SF_BAD
    sec
    rts

; Retire a disposable hint only after successful fresh parsing. Full token/type
; guards and published-map exclusion also protect cleanup on malformed frames.
ec_retire_hint:
    lda se_ec_reuse
    and #1
    beq @done
    ldx #4
@published:
    lda se_fb_old_token,x
    cmp se_ef_token,x
    bne @release
    dex
    bpl @published
    lda #SF_BAD
    sec
    rts
@release:
    SF_COPY se_fb_old_token,se_object_id,5
    jsr se_object_validate
    bcs @return
    lda object_owner,x
    cmp #SF_OBJECT_TYPE
    bne @bad
    jsr se_object_release
    bcs @return
    lda se_ec_reuse
    and #$FE
    sta se_ec_reuse
@done:
    lda #0
    clc
@return:
    rts
@bad:
    lda #SF_BAD
    sec
    rts

; Old published allocation survives the whole transform/fresh-parse process.
; Invalid/foreign descriptors are forgotten without freeing someone else's
; object. No fallible step follows a successful retirement before publication.
ec_retire_old:
    lda se_ef_token+3
    ora se_ef_token+4
    beq @done
    ldx #4
@candidate:
    lda se_ef_token,x
    cmp se_ec_candidate,x
    bne @validate
    dex
    bpl @candidate
    lda #SF_BAD
    sec
    rts
@validate:
    SF_COPY se_ef_token,se_object_id,5
    jsr se_object_validate
    bcs @done
    lda object_owner,x
    cmp #SF_OBJECT_TYPE
    bne @done
    jmp se_object_release
@done:
    lda #0
    clc
    rts
