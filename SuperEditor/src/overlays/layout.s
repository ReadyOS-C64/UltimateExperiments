.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "layout/api.inc"
.include "editor/api.inc"
.include "document/api.inc"
.include "document/math24.inc"
.include "hot/api.inc"
.include "nav/api.inc"
.include "render/api.inc"
.include "diagnostics/api.inc"
.segment "CODE"
    OVL_BINDING
entry:
    lda se_overlay_frame
    cmp #D_STEP
    jeq se_diag_step
    cmp #D_BEGIN
    bne :+
    lda #0
    sta se_diag_buffer
    lda #$88
    sta se_diag_buffer+1
    COPY24 se_hot_caret,se_diag_cursor
    jmp se_diag_begin
:
    cmp #L_BEGIN
    jeq begin
    cmp #L_STEP
    jne state
    lda se_v_nav_busy
    and se_n_owned
    jeq state
    jsr width
    jcs return
    cmp se_n_view_columns
    jne changed
    jsr se_view_init
    jcs return
    ldx #9
@context:
    lda se_doc_original,x
    cmp se_l_original,x
    jne changed
    dex
    bpl @context
    ldx #1
@generation:
    lda se_doc_generation,x
    cmp se_l_generation,x
    jne changed
    dex
    bpl @generation
    ldx #3
@revision:
    lda se_r_revision,x
    cmp se_l_revision,x
    jne changed
    dex
    bpl @revision
    jsr layout_fold_resume
    jcs return
    cmp #1
    jeq pending_return
    cmp #2
    beq @fold_boundary
    lda #128
    sta se_n_budget
    COPY24 se_l_scan,se_v_pos
    jmp scan
@fold_boundary:
    lda #128
    sta se_n_budget
    COPY24 se_l_scan,se_v_pos
    jmp boundary_ready
scan:
    CMP24 se_v_pos,se_hot_caret
    bne :+
    lda #1
    sta se_l_seen
:
    CMP24 se_v_pos,se_v_length
    jcs eof
    jsr se_view_peek
    jcs return
    pha
    jsr se_view_advance
    pla
    cmp #13
    beq boundary
    lda se_l_mode
    bne budget
    inc se_l_col
    lda se_l_col
    cmp se_n_view_columns
    bne budget
boundary:
    jsr layout_fold_boundary
    jcs return
    cmp #1
    jeq pending_return
boundary_ready:
    lda se_l_rows
    cmp #EDITOR_BODY_ROWS
    bcc append
    lda se_l_seen
    jne finished
    ; Keep the last22 real row starts andmatchingpaintends/foldmarkers.
    jsr layout_fold_shift
    ldx #0
@shift:
    lda se_v_rows+3,x
    sta se_v_rows,x
    inx
    cpx #EDITOR_LAST_ROW_OFFSET
    bcc @shift
    ldx #EDITOR_LAST_ROW_OFFSET
    jmp store_row
append:
    asl
    clc
    adc se_l_rows
    tax
    inc se_l_rows
store_row:
    ldy #0
@anchor:
    lda se_v_pos,y
    sta se_v_rows,x
    inx
    iny
    cpy #3
    bcc @anchor
    lda #0
    sta se_l_col
budget:
    dec se_n_budget
    jne scan
    COPY24 se_v_pos,se_l_scan
    lda #1
    clc
return:
    rts
pending_return:
    lda #1
    clc
    rts
eof:
    jsr layout_fold_eof
    lda se_l_seen
    jeq corrupt
    ; Empty remainder rows share EOF, including the blank row after a CR.
    lda se_l_rows
    cmp #EDITOR_BODY_ROWS
    beq finished
@pad:
    asl
    clc
    adc se_l_rows
    tax
    ldy #0
@byte:
    lda se_v_pos,y
    sta se_v_rows,x
    inx
    iny
    cpy #3
    bcc @byte
    inc se_l_rows
    lda se_l_rows
    cmp #EDITOR_BODY_ROWS
    bcc @pad
finished:
    COPY24 se_v_pos,se_v_bottom
    COPY24 se_v_rows,se_v_top
    COPY24 se_v_top,se_l_top
    COPY24 se_hot_caret,se_l_caret
    jsr se_navigation_cancel
    lda #1
    sta se_l_valid
    lda #0
    clc
    rts
begin:
    lda se_v_nav_busy
    ora se_n_owned
    jne busy
    jsr width
    jcs return
    sta se_n_view_columns
    jsr se_view_init
    jcs return
    CMP24 se_v_top,se_hot_caret
    bcc @bounds
    beq @bounds
    lda #0
    sta se_v_top
    sta se_v_top+1
    sta se_v_top+2
    jmp @bounds
@bounds:
    CMP24 se_hot_caret,se_v_length
    bcc @acquire
    jne corrupt
@acquire:
    jsr se_doc_read_acquire
    jcs return
    lda #1
    sta se_n_owned
    sta se_v_nav_busy
    sta se_l_rows
    sta se_l_active
    lda #0
    sta se_n_reveal
    sta se_l_valid
    sta se_r_valid
    sta se_l_col
    sta se_l_seen
    ldx #9
@tokens:
    lda se_doc_original,x
    sta se_l_original,x
    dex
    bpl @tokens
    ldx #1
@generation:
    lda se_doc_generation,x
    sta se_l_generation,x
    dex
    bpl @generation
    ldx #3
@revision:
    lda se_r_revision,x
    sta se_l_revision,x
    dex
    bpl @revision
    COPY24 se_v_top,se_l_scan
    COPY24 se_v_top,se_l_top
    COPY24 se_v_top,se_v_rows
    jsr layout_fold_init
    jcs return
    lda #1
    clc
    rts
changed:
    lda #$74
    sec
    rts
corrupt:
    lda #$7B
    sec
    rts
busy:
    lda #$7A
    sec
    rts
state:
    lda #$70
    sec
    rts

; No writes or lease acquisition until dimensions have been validated.
width:
    lda se_v_columns
    beq @legacy
    cmp #40
    beq @valid
    cmp #60
    beq @valid
    cmp #80
    bne @bad
@valid:
    clc
    rts
@legacy:
    lda #40
    clc
    rts
@bad:
    jmp corrupt

.include "overlays/layout-fold.s"
