; Included only in C7. Candidate8800..883F borrows diagnostics scratch while
; settings menu8 is active and owner0; no persistent/BSS/ZP allocation.
; Every64B candidate is validated BEFORE anyCB80 byte is published. IRQ handles
; input queue only, so this main-thread copy is one logical publication.
SC=$8800
.segment "CODE"
settings_open:
    lda #1
    sta se_e_ui
    lda #8
    sta se_e_menu
    lda #0
    sta se_e_item
    clc
    rts
settings_key:
    lda se_f_owner
    jne settings_reject
    lda se_e_key
    cmp #13
    jeq close
    cmp #$11
    beq @next
    cmp #$91
    beq @previous
    cmp #$31
    bcc @action
    cmp #$39
    bcs @action
    sec
    sbc #$31
    sta se_e_item
    clc
    rts
@next:
    inc se_e_item
    lda se_e_item
    and #7
    sta se_e_item
    clc
    rts
@previous:
    dec se_e_item
    lda se_e_item
    and #7
    sta se_e_item
    clc
    rts
@action:
    jsr fold_key
    cmp #'r'
    jeq settings_reset
    cmp #'h'
    jeq settings_presentation_cycle
    cmp #'s'
    beq @copy
    cmp #'f'
    beq @copy
    cmp #'c'
    beq @copy
    cmp #'g'
    beq @copy
    cmp #'b'
    beq @copy
    cmp #'i'
    beq @copy
    cmp #'u'
    bne @noop
@copy:
    pha
    ldx #SES_SIZE-1
@byte:
    lda se_editor_settings,x
    sta SC,x
    dex
    bpl @byte
    jsr settings_validate
    bcs @invalid
    ldx se_e_item
    txa
    and #7
    tax
    lda settings_offsets,x
    tax
    pla
    cmp #'f'
    jeq settings_font
    cmp #'s'
    jeq settings_size
    cmp #'c'
    jeq settings_ink
    cmp #'g'
    jeq settings_paper
    ldy #SES_BOLD
    cmp #'b'
    jeq settings_style
    ldy #SES_ITALIC
    cmp #'i'
    jeq settings_style
    ldy #SES_UNDERLINE
    jne settings_style
@invalid:
    pla
    jmp settings_reject
@noop:
    clc
    rts
settings_font:
    lda #0 ;next different origin/family, first supported size
    jeq settings_cycle
settings_size:
    lda #1 ;next supported size in current origin/family
settings_cycle:
    sta se_v_col
    stx se_v_menu_row
    ldy #0
@find:
    lda SC+SES_ORIGIN,x
    cmp settings_catalog,y
    bne @find_next
    lda SC+SES_FAMILY,x
    cmp settings_catalog+1,y
    bne @find_next
    lda SC+SES_FAMILY+1,x
    cmp settings_catalog+2,y
    bne @find_next
    lda SC+SES_POINT_SIZE,x
    cmp settings_catalog+3,y
    beq @found
@find_next:
    tya
    clc
    adc #5
    tay
    cpy #settings_catalog_end-settings_catalog
    bcc @find
    jmp settings_reject ;validated candidate must have a catalog face
@found:
    sty se_v_menu_count ;bounded wrap termination, no persistent pointer
@next:
    tya
    clc
    adc #5
    cmp #settings_catalog_end-settings_catalog
    bcc :+
    lda #0
:
    tay
    cpy se_v_menu_count
    beq @accept ;only one eligible face/size: preserve it
    ldx se_v_menu_row
    lda SC+SES_ORIGIN,x
    cmp settings_catalog,y
    bne @different
    lda SC+SES_FAMILY,x
    cmp settings_catalog+1,y
    bne @different
    lda SC+SES_FAMILY+1,x
    cmp settings_catalog+2,y
    bne @different
    lda se_v_col
    beq @next ;font cycling skips all remaining sizes of current family
    bne @eligible
@different:
    lda se_v_col
    bne @next ;size cycling stays in the exact current family/namespace
@eligible:
    cpx #SES_CODE
    bne @accept
    lda settings_catalog+4,y
    beq @next ;CODE can use only genuinely equal measured advances
@accept:
    ldx se_v_menu_row
    lda settings_catalog,y
    sta SC+SES_ORIGIN,x
    lda settings_catalog+1,y
    sta SC+SES_FAMILY,x
    lda settings_catalog+2,y
    sta SC+SES_FAMILY+1,x
    lda settings_catalog+3,y
    sta SC+SES_POINT_SIZE,x
    jmp settings_publish
settings_ink:
    inc SC+SES_FOREGROUND,x
    lda SC+SES_FOREGROUND,x
    and #15
    sta SC+SES_FOREGROUND,x
    jmp settings_publish
settings_paper:
    inc SC+SES_BACKGROUND,x
    lda SC+SES_BACKGROUND,x
    and #15
    sta SC+SES_BACKGROUND,x
    jmp settings_publish
settings_style:
    tya
    eor SC+SES_STYLES,x
    sta SC+SES_STYLES,x
    jmp settings_publish
settings_reset:
    ldx #SES_SIZE-1
@copy:
    lda settings_defaults,x
    sta SC,x
    dex
    bpl @copy
    jsr settings_validate
    jcs settings_reject
    lda #SE_PRESENTATION_DEFAULT
    jsr settings_presentation
settings_publish:
    jsr settings_validate
    jcs settings_reject
    ldx #SES_SIZE-1
@copy:
    lda SC,x
    sta se_editor_settings,x
    dex
    bpl @copy
    lda #0
    sta se_l_valid
    sta se_r_valid
    sta se_st_valid
    sta se_st_request
    sta se_gc_valid
    lda #1
    sta se_e_redraw
    clc
    rts
; No FILE/build/GEOS phase may be interpreted here. Public input already
; cancels owner2 via se_style_input before entering C7; direct foreign calls
; refuse without touching any phase/certificate bytes.
settings_presentation_cycle:
    lda se_render_caps
    beq @markdown
    cmp #1
    beq @full
    lda #0
    beq settings_presentation
@markdown:
    lda #1
    bne settings_presentation
@full:
    lda #3
settings_presentation:
    ldx se_f_owner
    jne settings_reject
    cmp #2
    beq settings_reject
    cmp #4
    bcs settings_reject
    pha
    jsr se_style_input
    lda #0
    sta se_l_valid
    sta se_r_valid
    sta se_st_valid
    sta se_st_request
    sta se_st_cp_valid
    sta se_ef_fold_rows
    sta se_ef_fold_rows+1
    sta se_ef_fold_rows+2
    sta se_gc_width
    sta se_gc_valid
    sta se_gc_valid+1
    sta se_gc_valid+2
    sta GCC_VALID
    sta GEC_VALID
    sta GTC_VALID
    pla
    sta se_render_caps ;all old derived authorities revoked before publication
    lda #1
    sta se_l_need_wrap
    sta se_e_redraw
    clc
    rts
settings_reject:
    lda #$7C
    sta se_e_error
    clc ;optional settings errors never reject/mutate canonical source
    rts
settings_validate:
    ldx #SES_HEADER_SIZE-1
@header:
    lda SC,x
    cmp settings_defaults,x
    bne @bad
    dex
    bpl @header
    ldx #SES_HEADER_SIZE
@profile:
    lda SC+SES_FOREGROUND,x
    cmp #16
    bcs @bad
    lda SC+SES_BACKGROUND,x
    cmp #16
    bcs @bad
    lda SC+SES_STYLES,x
    and #$F8
    bne @bad
    ldy #0
@face:
    lda SC+SES_ORIGIN,x
    cmp settings_catalog,y
    bne @next
    lda SC+SES_FAMILY,x
    cmp settings_catalog+1,y
    bne @next
    lda SC+SES_FAMILY+1,x
    cmp settings_catalog+2,y
    bne @next
    lda SC+SES_POINT_SIZE,x
    cmp settings_catalog+3,y
    bne @next
    cpx #SES_CODE
    bne @advance
    lda settings_catalog+4,y ;generated from128 equal measured advances
    beq @bad
    bne @advance
@next:
    tya
    clc
    adc #5
    tay
    cpy #settings_catalog_end-settings_catalog
    bcc @face
@bad:
    sec
    rts
@advance:
    txa
    clc
    adc #SES_PROFILE_SIZE
    tax
    cpx #SES_SIZE
    bcc @profile
    clc
    rts
.segment "RODATA"
settings_offsets: .byte SES_BODY,SES_HEADING1,SES_HEADING2,SES_HEADING3,SES_HEADING4,SES_HEADING5,SES_HEADING6,SES_CODE
settings_defaults: .incbin "build/editor-settings/editor-defaults.bin"
settings_defaults_end:
settings_catalog: .incbin "build/editor-settings/editor-font-catalog.bin"
settings_catalog_end:
.assert settings_defaults_end-settings_defaults=SES_SIZE,error,"settings defaults size"
.assert (settings_catalog_end-settings_catalog) .mod 5=0,error,"settings catalog record shape"
.assert settings_catalog_end-settings_catalog<=255,error,"settings catalog bounded scan"
