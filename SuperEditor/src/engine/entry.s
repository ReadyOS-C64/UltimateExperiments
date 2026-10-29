.setcpu "6502"
.macpack longbranch
.include "engine-api.inc"
.include "engine/api.inc"
.include "document/api.inc"
.segment "CODE"
    OVL_BINDING
entry:
    lda se_overlay_frame
    cmp #ENGINE_BEGIN
    jeq se_doc_splice_begin
    cmp #ENGINE_LOCAL_BEGIN
    jeq se_doc_splice_local_begin
    cmp #ENGINE_FEED
    jeq se_doc_splice_feed
    cmp #ENGINE_STEP
    jeq se_doc_splice_step
    cmp #ENGINE_REFS_BEGIN
    jeq se_doc_splice_refs_begin
    cmp #ENGINE_LOCAL_REFS_BEGIN
    jeq se_doc_splice_local_refs_begin
    lda #$79
    sec
    rts
