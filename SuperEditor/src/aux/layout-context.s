.setcpu "6502"
.macpack longbranch
.include "aux/api.inc"
.include "layout/api.inc"
.include "editor/api.inc"
.include "document/api.inc"
.include "document/math24.inc"
.include "hot/api.inc"
.include "render/api.inc"
.segment "CODE"
; Pure no-wrap context comparison. No index access, leases, reads or writes;
; safe while FILESTATE owns the derived sparse-index address range.
se_aux_layout_context:
    CMP24 se_hot_caret,se_v_top
    bcc changed
    CMP24 se_hot_caret,se_v_bottom
    bcc context
    CMP24 se_hot_caret,se_l_caret
    bne changed
context:
    lda se_l_valid
    beq changed
    ldx #9
@tokens:
    lda se_doc_original,x
    cmp se_l_original,x
    bne changed
    dex
    bpl @tokens
    ldx #1
@generation:
    lda se_doc_generation,x
    cmp se_l_generation,x
    bne changed
    dex
    bpl @generation
    ldx #3
@revision:
    lda se_r_revision,x
    cmp se_l_revision,x
    bne changed
    dex
    bpl @revision
    CMP24 se_v_top,se_l_top
    bne changed
    lda #0
    clc
    rts
changed:
    lda #1
    clc
    rts
