.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/geos/source-line.inc"
.ifdef SE_EDITOR_GEOS_INLINE
.include "render/geos/semantic.inc"
.include "render/geos/inline.inc"
.include "render/geos/editor.inc"
.include "render/geos/source-certificate.inc"
.import se_st_request,se_st_cp_valid
INLINE_CONT=GSEM_FRAME+$A7
; Reserve a full24bit sparse glyph-source ledger. A rendered boundary can
; bridge arbitrarily long hidden source, so a16bit delta is insufficient.
INLINE_SOURCES=$4400
INLINE_SOURCE_CAPACITY=162
INLINE_LINE=INLINE_SOURCES+INLINE_SOURCE_CAPACITY*3
INLINE_CORE_SIZE=GL_GLYPH+14 ;GG_INPUT_SIZE; measure outputs are not live across calls
INLINE_MAP=INLINE_LINE+INLINE_CORE_SIZE
INLINE_MAP_SIZE=INLINE_SOURCE_CAPACITY*2
INLINE_FS=INLINE_MAP+INLINE_MAP_SIZE
INLINE_IDENTITY_SIZE=59
INLINE_PACKET=INLINE_FS+INLINE_IDENTITY_SIZE
.assert INLINE_PACKET+32<=$4800,error,"GEOS inline continuation exceeds inactive style plan"
.endif
.import se_f_owner,se_fs_end,se_fs_state,se_fs_state_size
.import se_geos_packed,se_geos_widths
.ifndef SE_EDITOR_GEOS_INLINE
.import se_geos_bands_begin,se_geos_bands_step,se_geos_bands_hit_y
.endif
.export se_gb_frame
se_gb_frame=GEOS_LINE_FRAME
.importzp text_ptr,screen_ptr
.export entry,se_geos_source_line,se_gs_active,se_gs_context_valid,se_gs_saved_source
.exportzp se_gg_context,se_gg_pointer
se_gg_context=text_ptr
se_gg_pointer=screen_ptr
se_gs_active=GS_ACTIVE
se_gs_context_valid=GS_CONTEXT_VALID
se_gs_saved_source=GS_FS
.assert se_fs_state=$8EE0,lderror,"GEOS reader overlap moved"
.assert se_fs_state_size=GS_CONTEXT_SIZE,lderror,"GEOS reader context changed"
L=GEOS_LINE_FRAME
.segment "GEOS_SOURCE"
    OVL_BINDING
entry:
se_geos_source_line:
    lda se_f_owner
    cmp #GS_OWNER
    jne busy
    lda se_overlay_frame
.ifdef SE_EDITOR_GEOS_INLINE
    cmp #SC_CONSUME
    jeq certificate
.endif
    cmp #GS_BEGIN
    jeq begin
    cmp #GS_STEP
    jeq step
    cmp #GS_CANCEL
    jeq cancel
    cmp #GS_HIT
    bne bands
    ldx #<L
    ldy #>L
    jmp se_geos_line_hit
bands:
.ifdef SE_EDITOR_GEOS_INLINE
    jmp argument ;editor mixed-height geometry is scheduled by C21
.else
    cmp #GS_BANDS_BEGIN
    jcc argument
    cmp #GS_BANDS_HIT+1
    jcs argument
    tax
    lda GS_ACTIVE
    ora GS_CONTEXT_VALID
    jne busy
    cpx #GS_BANDS_BEGIN
    beq :+
    cpx #GS_BANDS_STEP
    beq :++
    jmp se_geos_bands_hit_y
:   jmp se_geos_bands_begin
:   jmp se_geos_bands_step
.endif
begin:
    lda GS_ACTIVE
    ora GS_CONTEXT_VALID
    jne busy
    lda L+GL_ENCODING
    cmp #2
    jcs argument ;invalid encoding owns no source lease
    sta GS_ENCODING
    lda #0
    sta GS_ERROR
    sta GS_READS
.ifdef SE_EDITOR_GEOS_INLINE
    sta INLINE_CONT
    sta SC_VALID
    sta SW_VALID
.endif
    lda GS_ENCODING
    beq :+
    lda #8 ;fixed native-code cell advance, no measure/raster access
:
    ldx #31
@styles:
    sta GS_STYLES,x
    dex
    bpl @styles
    jsr save_overlap
    lda #0
    ldx #GS_CONTEXT_SIZE-1
@clear:
    sta se_fs_state,x
    dex
    bpl @clear
    lda #0
    jsr reader_invoke
    jcs return
    lda #1
    sta GS_ACTIVE
    sta GS_CONTEXT_VALID
    lda #<se_geos_packed
    sta L+GL_FONT
    lda #>se_geos_packed
    sta L+GL_FONT+1
    lda #<se_geos_widths
    sta L+GL_WIDTHS
    lda #>se_geos_widths
    sta L+GL_WIDTHS+1
    lda #0
    sta L+GL_NATIVE
    sta L+GL_NATIVE+1
    lda #<GS_PACKET
    sta L+GL_PACKET
    lda #>GS_PACKET
    sta L+GL_PACKET+1
    lda #<GS_STYLES
    sta L+GL_STYLES
    sta L+GL_ADVANCES
    lda #>GS_STYLES
    sta L+GL_STYLES+1
    sta L+GL_ADVANCES+1
    ldx #<L
    ldy #>L
    jsr se_geos_line_begin
    jcs fail
    jmp pending
step:
.ifdef SE_EDITOR_GEOS_INLINE
    lda INLINE_CONT
    jne inline_resume
.endif
    lda GS_ACTIVE
    jeq state
    lda L+GL_ENCODING
    cmp GS_ENCODING
    beq :+
    lda #GL_CHANGED
    jmp fail
:
    lda #1
    jsr reader
    jcs fail
    ldx #2
@offset:
    lda L+GL_SCAN,x
    sta GS_FS,x ;reader offset0..2
    sta L+GL_PACKET_AT,x
    dex
    bpl @offset
    lda #32
    sta GS_FS+3
    lda #<GS_PACKET
    sta GS_FS+4
    lda #>GS_PACKET
    sta GS_FS+5
    lda #2
    jsr reader
    jcs fail
    inc GS_READS
    lda GS_FS+6
    sta L+GL_PACKET_COUNT
.ifdef SE_EDITOR_GEOS_INLINE
    beq @feed_line
    lda GS_ENCODING
    bne @feed_line
    lda GSEM_FRAME+GSEM_KIND
    cmp #4
    bcs @feed_line
    lda GSEM_FRAME+GSEM_INLINE
    beq @feed_line
    jsr window_try
    jcs inline_request
    jsr style_remember
    jmp @feed_line
@feed_line:
    lda L+GL_PACKET_COUNT
feed_line:
.endif
    ldx #<L
    ldy #>L
    cmp #0
    beq @eof
    jsr se_geos_line_step
    jmp @result
@eof:
    jsr se_geos_line_finish
@result:
    bcs fail
    lda L+GL_STATE
    cmp #2
    beq complete
pending:
.ifdef SE_EDITOR_GEOS_INLINE
    lda #20
    sta $9135
    lda #1
    sta $9136
.endif
    lda #GS_PENDING
    clc
return:
    rts
complete:
.ifdef SE_EDITOR_GEOS_INLINE
    lda SC_VALID
    cmp #1
    bne :+
    inc SC_VALID ;complete currentC20 output, consumed only after parentguard
:
.endif
    jsr cleanup
zero:
    lda #0
    clc
    rts
cancel:
.ifdef SE_EDITOR_GEOS_INLINE
    lda #0
    sta SC_VALID
    sta SW_VALID
.endif
    lda GS_CONTEXT_VALID
    beq zero
    jsr cleanup
    jmp zero
fail:
    sta GS_ERROR
    pha
.ifdef SE_EDITOR_GEOS_INLINE
    lda #0
    sta SC_VALID
    sta SW_VALID
.endif
    jsr cleanup
    pla
    sec
    rts
.ifdef SE_EDITOR_GEOS_INLINE
certificate:
    lda GS_ACTIVE
    ora GS_CONTEXT_VALID
    jne busy
    jsr style_certificate
    jcc zero
    lda #GI_ID
    sta $9135
    lda #GI_BEGIN
    ldx GSEM_FRAME+GSEM_COUNT
    cpx #161
    bne :+
    lda #GI_BEGIN_WIDE
:
    sta $9136
    lda #GS_PENDING
    clc
    rts
.endif
argument:
    lda #GL_ARGUMENT
    sec
    rts
state:
    lda #GL_STATE_ERROR
    sec
    rts
busy:
    lda #$B2
    sec
    rts
; All reader calls return with GL restored, including admission/guard faults.
reader:
    pha
    jsr save_overlap
    ldx #GS_CONTEXT_SIZE-1
@restore:
    lda GS_FS,x
    sta se_fs_state,x
    dex
    bpl @restore
    pla
reader_invoke:
    sta se_overlay_frame
    lda #14
    ldx #0
    jsr se_overlay_call
reader_finish:
    php
    pha
    ldx #GS_CONTEXT_SIZE-1
@save:
    lda se_fs_state,x
    sta GS_FS,x
    lda GS_OVERLAP,x
    sta se_fs_state,x
    dex
    bpl @save
    pla
    plp
    rts
save_overlap:
    ldx #GS_CONTEXT_SIZE-1
@copy:
    lda se_fs_state,x
    sta GS_OVERLAP,x
    dex
    bpl @copy
    rts
cleanup:
    lda GS_CONTEXT_VALID
    beq @done
    jsr save_overlap
    ldx #GS_CONTEXT_SIZE-1
@restore:
    lda GS_FS,x
    sta se_fs_state,x
    dex
    bpl @restore
    jsr se_fs_end
    jsr reader_finish
@done:
    lda #0
    sta GS_ACTIVE
    sta GS_CONTEXT_VALID
    rts
.ifdef SE_EDITOR_GEOS_INLINE
.include "render/geos/source-inline.s"
.include "render/geos/source-certificate.s"
.include "render/geos/style-window.s"
.include "render/geos/certificate-consumer.s"
.endif
