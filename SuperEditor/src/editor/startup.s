.setcpu "6502"
.macpack longbranch
.include "platform.inc"
.include "editor/api.inc"
.include "document/api.inc"
.include "object/api.inc"
.include "history/api.inc"
.include "hot/api.inc"
.include "render/geos/settings.inc"
.include "render/presentation.inc"
.include "../../build/editor-settings/presentation-defaults.inc"
.export se_presentation_default
se_presentation_default=SE_PRESENTATION_DEFAULT
.import se_overlay_call,se_overlay_frame
.import se_clip_init
.import se_reu_provider_init,se_overlay_init,se_overlay_read,se_overlay_import,se_reu_banks,se_print
.importzp text_ptr,screen_ptr
.export se_editor_startup,se_editor_import
.segment "COLD"
se_editor_startup:
    jsr se_reu_provider_init
    bcc :+
    cmp #0
    jne failed
    lda #$78 ;missing REU must not look like a zero error code
    jmp failed
:
    jsr se_object_init
    jcs failed
    jsr se_clip_init
    jcs failed
    jsr se_overlay_init
    jcs failed
.ifdef EDITOR_MANAGED_CODE
    sta $CF90 ;overlay_init success returnsA0
    sta $CFE8
.endif

    lda #SE_PRESENTATION_DEFAULT
    sta se_render_caps
    ; Session settings initialize from host build defaults, never a disk config.
    ldx #SES_SIZE-1
@settings:
    lda session_defaults,x
    sta se_editor_settings,x
    dex
    bpl @settings
    lda #1
    ldx se_reu_banks+1
    beq :+
    lda #16
:
    jsr se_doc_init
    jcs failed
    ; A small native source is the initial unsaved tutorial until file UI lands.
    ldx #0
@sample:
    lda sample,x
    sta $8000,x
.ifdef EDITOR_MANAGED_CODE
    inx
    bne @sample
    ; X is already zero after the first page completes.
@sample_tail:
    lda sample+$100,x
    sta $8100,x
    inx
    cpx #<(sample_end-sample)
    bcc @sample_tail
.else
    lda sample+$100,x
    sta $8100,x
    inx
    bne @sample
.endif
    DOC_TOKEN se_doc_original
    lda #0
    sta se_object_offset
    sta se_object_offset+1
    sta se_object_offset+2
    sta se_object_c64
    lda #$80
    sta se_object_c64+1
    lda #<(sample_end-sample)
    sta se_object_length
    sta se_doc_source_length
    lda #>(sample_end-sample)
    sta se_object_length+1
    sta se_doc_source_length+1
    lda #0
    sta se_doc_source_length+2
    jsr se_object_copy
    jcs failed
    jsr se_doc_adopt_original
    jcs failed
    ldx #0
@asset:
    txa
    pha
    ; A still holds the original index saved above. Each filename has one
    ; low address byte and one packed high-nibble/length byte. All names live
    ; below $1000, and COLD_FILE checks both limits at assembly/link time.
    asl a
    tax
    lda file_catalog,x
    sta text_ptr
    lda file_catalog+1,x
    tay
    lsr a
    lsr a
    lsr a
    lsr a
    sta text_ptr+1
    tya
    and #$0F
    ldx text_ptr
    ldy text_ptr+1
    jsr se_editor_import
    sta se_e_error
    pla
    tax
    bcs asset_failed
    inx
    cpx #COLD_FILE_COUNT
    bcc @asset
    jsr se_editor_fonts_import
    bcs failed
    jsr se_history_cold
    bcs failed
    lda #H_INIT
    jsr se_history_call
    bcs failed
    jsr se_hot_cold
    bcs failed
    lda #1
    sta se_hot_group
    lda #W_LOAD
    jsr se_hot_call
    bcs failed
    lda #1
    sta se_e_job
    clc
    rts
.export se_editor_fonts_import
se_editor_fonts_import:
    lda #0
    ldx #63
@clear:
    sta se_gf_state,x
    dex
    bpl @clear
    sta se_overlay_frame
    lda #8
    sta se_overlay_frame+1
@call:
    lda #28
    ldx #1
    jsr se_overlay_call
    bcs @return
    cmp #1
    bne @return
    sta se_overlay_frame
    jmp @call
@return:
    rts
se_editor_import:
    jsr se_overlay_read
    bcs @return
    jmp se_overlay_import
@return:
    rts
asset_failed:
    lda se_e_error
failed:
    pha
    PRINT_AT failure_title,10,2
    PRINT_AT failure_hint,12,2
    pla
    sec
    rts
.ifdef EDITOR_MANAGED_CODE
.segment "COLD"
.else
.segment "RODATA"
.endif
failure_title: .asciiz "Editor failed."
file39: .byte $4C,$49,$46,$45,$43,$54,$52,$4C ;LIFECTRL
file40: .byte $4C,$49,$46,$45,$43,$4F,$50,$59 ;LIFECOPY
file41: .byte $47,$45,$4F,$53,$44,$45,$4C,$54,$41 ;GEOSDELTA
.segment "COLD"
.ifdef EDITOR_MANAGED_CODE
failure_hint: .asciiz "Disk/REU?"
.else
failure_hint: .asciiz "Check disk and REU."
.endif
file42: .byte $47,$46,$4F,$4E,$54 ;GFONT
file43: .byte $47,$54,$59,$50,$45 ;GTYPE
file44: .byte $43,$4F,$44,$45 ;CODE
file45: .byte $43,$4C,$45,$58 ;CLEX
file47=file15 ;GRID shares the existing GRIDEDIT prefix
file46=file43+1 ;TYPE shares the suffix of GTYPE, saving cold filename bytes
.include "editor/catalog.inc"
file49=file36+4 ;FOLD: R33 current-BODY presentation plan
file59=file26+4 ;ROW: R29 Plain CR geometry, shared GEOSROW suffix
file48: .byte $48,$4F,$54,$43,$4F,$4C,$44 ;HOTCOLD (raw DOS bytes, not text charmap)
file38: .byte $47,$45,$4F,$53,$43,$41,$52,$45,$54
file36: .byte $47,$45,$4F,$53,$46,$4F,$4C,$44
file37: .byte $47,$45,$4F,$53,$54,$41,$49,$4C
file33: .byte $47,$45,$4F,$53,$50,$52,$45,$56,$49,$45,$57
file34: .byte $47,$45,$4F,$53,$46,$4F,$4E,$54,$52,$4F,$57
file35: .byte $47,$45,$4F,$53,$46,$4F,$4E,$54,$49,$4E
file32: .byte $50,$4F,$50,$55,$50,$53 ;POPUPS
file31: .byte $47,$45,$4F,$53,$49,$4E,$4C,$4E
file29: .byte $47,$45,$4F,$53,$53,$45,$4D,$41
file30: .byte $47,$45,$4F,$53,$4C,$45,$58
file28: .byte $47,$45,$4F,$53,$4E,$41,$56
file24: .byte $47,$45,$4F,$53,$4C,$49,$4E,$45
file25: .byte $47,$45,$4F,$53,$50,$41,$47,$45
file26: .byte $47,$45,$4F,$53,$52,$4F,$57
file27: .byte $47,$45,$4F,$53,$50,$41,$49,$4E,$54
file23: .byte $46,$4F,$4C,$44,$58,$46,$4F,$52,$4D ;FOLDXFORM
file21: .byte $46,$4F,$4C,$44,$43,$54,$4C ;FOLDCTL
file22: .byte $52,$41,$4E,$47,$45,$49,$4F ;RANGEIO
file18: .byte $46,$4F,$4C,$44,$50,$41,$52,$53,$45 ;FOLDPARSE
file19: .byte $46,$4F,$4C,$44,$46,$49,$4E,$49,$53,$48 ;FOLDFINISH
file20: .byte $46,$4F,$4C,$44,$43,$4F,$52,$45 ;FOLDCORE
file15: .byte $47,$52,$49,$44,$45,$44,$49,$54 ;GRIDEDIT
file16: .byte $47,$52,$49,$44,$38,$30 ;GRID80
file17: .byte $47,$52,$49,$44,$36,$30 ;GRID60
file14: .byte $4C,$45,$58,$49,$43,$41,$4C ;LEXICAL
file12: .byte $53,$54,$59,$4C,$45,$52 ;STYLER
file13: .byte $56,$49,$45,$57,$53,$4F,$55,$52,$43,$45 ;VIEWSOURCE
file10: .byte $46,$49,$4C,$45,$49,$4F ;FILEIO
file11: .byte $41,$55,$58 ;AUX
file0: .byte $45,$45,$44,$49,$54 ;EEDIT
file1: .byte $45,$50,$4C,$41,$59 ;EPLAY
file2: .byte $57,$49,$4E,$44,$4F,$57 ;WINDOW
file3: .byte $54,$45,$58,$54,$34,$30 ;TEXT40
file4: .byte $4D,$45,$4E,$55,$34,$30 ;MENU40
file5: .byte $45,$4E,$47,$49,$4E,$45 ;ENGINE
file9: .byte $4C,$41,$59,$4F,$55,$54 ;LAYOUT
file8: .byte $42,$4C,$4F,$43,$4B ;BLOCK
file7: .byte $53,$45,$41,$52,$43,$48 ;SEARCH
file6: .byte $4E,$41,$56,$49,$47,$41,$54,$45 ;NAVIGATE
sample:
    .byte "# SuperEditor",13,13
    .byte "A PETSCII notebook.",13
    .byte "Type here. Return starts a new line.",13
    .byte "Both lower and UPPER case stay intact.",13,13
    .byte "**Strong** and *emphasis* use stars.",13
    .byte "- A native list",13
    .byte "1. An ordered item",13,13
    .byte ":::asm",13
    .byte "loop: lda #$00",13
    .byte "      sta $d020",13
    .byte "      rts",13
    .byte ":::",13,13
    .byte "F1 menus   F7 typed commands",13
    .byte "Try syntax plain or syntax full.",13
    .byte "F1 File opens and saves.",13
sample_end:
.ifdef EDITOR_MANAGED_CODE
.assert (sample_end-sample)>256,error,"bounded sample copy requires a second page"
.assert (sample_end-sample)<512,error,"bounded sample copy exceeds two pages"
.else
    .res 512-(sample_end-sample),0
.endif
.assert * <=$0F00,lderror,"cold code overlaps REU probe save bytes"

.segment "SETTINGS_STATE"
.export se_editor_settings,se_editor_settings_end
se_editor_settings: .res SES_SIZE
se_editor_settings_end:
.assert se_editor_settings_end-se_editor_settings=64,error,"session settings extent"
.segment "COLD"
session_defaults:
.incbin "build/editor-settings/editor-defaults.bin"
.assert *-session_defaults=SES_SIZE,error,"invalid generated settings table"

.segment "FONT_STORE_STATE"
.export se_gf_state
se_gf_state: .res 64
.segment "PREVIEW_STATE"
.export se_preview_state,se_preview_state_end
se_preview_state: .res 1024
se_preview_state_end:
