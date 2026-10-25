.setcpu "6502"
.macpack longbranch
.include "document/api.inc"
.include "object/api.inc"
.segment "DOCSTATE"
init_banks: .res 1
init_count: .res 1
init_error: .res 1
.segment "CODE"
; A data banks1..16. Metadata1 + originalN + appendN, published together.
; Caller has initialized provider/object services. Refuses same-epoch reinit.
se_doc_init:
    sta init_banks
    cmp #1
    jcc @argument
    cmp #17
    jcs @argument
    jsr object_service_valid
    jcs @return
    lda se_doc_epoch
    cmp se_object_epoch
    bne @start
    lda se_doc_epoch+1
    cmp se_object_epoch+1
    jeq @state
@start:
    lda #0
    sta init_count
    sta se_doc_ready
    lda #3
    ldx #1
    jsr se_object_create
    jcs @failed
    ldy #4
@meta:
    lda se_object_id,y
    sta se_doc_meta,y
    dey
    bpl @meta
    inc init_count
    lda #0
    sta se_object_offset
    sta se_object_offset+1
    lda #1
    sta se_object_offset+2
    jsr se_object_resize ; private metadata bank; only initialized root refs read
    bcs @failed
    lda #4
    ldx init_banks
    jsr se_object_create
    bcs @failed
    ldy #4
@original:
    lda se_object_id,y
    sta se_doc_original,y
    dey
    bpl @original
    inc init_count
    lda #4
    ldx init_banks
    jsr se_object_create
    bcs @failed
    ldy #4
@append:
    lda se_object_id,y
    sta se_doc_append,y
    dey
    bpl @append
    lda #0
    ldx #0
@roots:
    sta se_doc_roots,x
    sta se_doc_next_roots,x
    inx
    bne @roots
    sta se_doc_root_count
    sta se_doc_busy
    sta se_doc_read_locks
    sta se_snapshot_busy
    sta se_doc_length
    sta se_doc_length+1
    sta se_doc_length+2
    sta se_doc_generation+1
    lda #1
    sta se_doc_generation
    lda se_object_epoch
    sta se_doc_epoch
    lda se_object_epoch+1
    sta se_doc_epoch+1
    jsr se_doc_invalidate
    lda #1
    sta se_doc_ready
    lda #0
    clc
@return:
    rts
@failed:
    sta init_error
    lda init_count
    cmp #2
    bcc @release_meta
    DOC_TOKEN se_doc_original
    jsr se_object_release
@release_meta:
    lda init_count
    beq @done
    DOC_TOKEN se_doc_meta
    jsr se_object_release
@done:
    lda init_error
    sec
    rts
@state:
    lda #$40
    sec
    rts
@argument:
    lda #$36
    sec
    rts

