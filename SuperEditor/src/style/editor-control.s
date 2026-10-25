.setcpu "6502"
.macpack longbranch
.include "style/api.inc"
.include "editor/api.inc"
.include "document/api.inc"
.include "render/api.inc"
.include "layout/api.inc"
.include "nav/api.inc"
.include "editor_file/api.inc"
.import se_reu_epoch,se_style_release
.import se_mode
.import __STYLE_STATE_RUN__,__STYLE_STATE_SIZE__
.import __SM_STATE_RUN__,__SM_STATE_SIZE__
.import __FOLD_SOURCE_STATE_RUN__,__FOLD_SOURCE_STATE_SIZE__
.export se_style_auto
.segment "STYLE_CODE"
.assert __STYLE_STATE_SIZE__ > 256, lderror, "style clear requires one full page"
.assert __STYLE_STATE_SIZE__ < 512, lderror, "style clear tail exceeds one page"
.assert __SM_STATE_SIZE__ > 0 .and __SM_STATE_SIZE__ < 256, lderror, "parser clear requires one partial page"
; Root calls only while idle, before the next service it checks input again.
se_style_auto:
    lda se_f_owner
    beq claim
    cmp #2
    jne deferred
    jmp key
claim:
    lda se_v_nav_busy
    ora se_n_owned
    jne deferred
    lda #0
    sta se_i_ready
    sta se_i_count
    sta se_n_cache_count
    ldx #<__STYLE_STATE_SIZE__
@state:
    dex
    sta __STYLE_STATE_RUN__+$100,x
    cpx #0
    bne @state
    ; Controller is >256 bytes: clear its prefix and remaining tail explicitly.
    ldx #0
@page:
    sta __STYLE_STATE_RUN__,x
    inx
    bne @page
    ldx #<__SM_STATE_SIZE__
@parser:
    dex
    sta __SM_STATE_RUN__,x
    cpx #0
    bne @parser
    ldx #<__FOLD_SOURCE_STATE_SIZE__
@reader:
    dex
    sta __FOLD_SOURCE_STATE_RUN__,x
    cpx #0
    bne @reader
    lda #2
    sta se_f_owner
key:
    ldx #14
@tokens:
    lda se_doc_meta,x
    sta se_st_key,x
    dex
    bpl @tokens
    ldx #1
@generation:
    lda se_doc_generation,x
    sta se_st_key+15,x
    lda se_reu_epoch,x
    sta se_st_key+ST_KEY_EPOCH,x
    dex
    bpl @generation
    ldx #3
@revision:
    lda se_r_revision,x
    sta se_st_key+17,x
    dex
    bpl @revision
    ldx #2
@position:
    lda se_v_length,x
    sta se_st_key+ST_KEY_LENGTH,x
    lda se_v_top,x
    sta se_st_key+ST_KEY_TOP,x
    lda se_l_pan,x
    sta se_st_key+ST_KEY_PAN,x
    lda se_v_bottom,x
    sta se_st_rows+66,x
    dex
    bpl @position
    lda se_mode
    asl
    ora se_l_mode
    sta se_st_key+ST_KEY_MODE
    ldx #65
@rows:
    lda se_v_rows,x
    sta se_st_rows,x
    dex
    bpl @rows
    lda se_st_busy
    beq start
    jsr se_style_step
    jmp result
start:
    jsr se_style_begin
result:
    bcs failed
    cmp #0
    jne deferred
    ; Completed plan is already published. Release the phase, preserve colors.
    lda #0
    sta se_f_owner
    sta se_st_request
    lda #1
    sta se_e_redraw
    clc
    rts
failed:
    jsr se_style_release
    ldx #STYLE_KEY_BYTES-1
@failure_key:
    lda se_st_key,x
    sta se_st_descriptor,x
    dex
    bpl @failure_key
    lda #$80
    sta se_st_request
    clc ; derived failure retains plain source editing
    rts
deferred:
    lda #2
    clc
    rts
