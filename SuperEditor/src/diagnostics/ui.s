; Included in C7. Buffer8800 is exclusively borrowed until this popup closes.
; R1 paints from8000/8400/hot; it cannot reuse this COW output scratch.
.include "diagnostics/api.inc"
.segment "CODE"
diag_popup:
    lda #1
    sta tui_box_x
    lda #3
    sta tui_box_y
    lda #38
    sta tui_box_w
    lda #20
    sta tui_box_h
    jsr tui_box40
    PRINT_AT diag_title,4,3
    PRINT_AT diag_length,6,3
    PRINT_AT diag_cursor,7,3
    PRINT_AT diag_hash,8,3
    PRINT_AT diag_pending,10,3
    PRINT_AT diag_epoch,11,3
    PRINT_AT diag_owners,12,3
    PRINT_AT diag_overlay,14,3
    PRINT_AT diag_map,17,3
    PRINT_AT diag_physical,18,3
    PRINT_AT diag_types1,19,3
    PRINT_AT diag_types2,20,3
    PRINT_AT diag_close,21,3
    ldx #16
    lda #TUI_TITLE
@title:
    sta $D800+4*40+3,x
    dex
    bpl @title
    ldx #30
    lda #TUI_STATUS
@hint:
    sta $D800+21*40+3,x
    dex
    bpl @hint
    lda #0
    sta se_v_menu_index
@field:
    ldx se_v_menu_index
    ldy diag_fields,x
    lda $8800,y
    jsr se_hex_byte
    pha ;low screen-code hex digit
    txa
    pha ;high digit
    ldx se_v_menu_index
    lda diag_fields+1,x
    sta se_v_menu_row
    lda diag_fields+2,x
    sta se_v_col
    lda #TUI_HIGHLIGHT
    sta tui_color
    pla
    ldx se_v_col
    ldy se_v_menu_row
    jsr tui_putc40
    pla
    ldx se_v_col
    inx
    ldy se_v_menu_row
    jsr tui_putc40
    lda se_v_menu_index
    clc
    adc #3
    sta se_v_menu_index
    cmp #diag_fields_end-diag_fields
    bcc @field
    lda #0
    clc
    rts
.segment "RODATA"
diag_title: .asciiz "Diagnostics ABI $"
diag_length: .asciiz "Length $        Gen $"
diag_cursor: .asciiz "Cursor $        CRC $"
diag_hash: .asciiz "CRC16/CCITT-FALSE  Type $"
diag_pending: .asciiz "Pending $    Dirty $"
diag_epoch: .asciiz "Epoch $        Banks $"
diag_owners: .asciiz "Allocated $     Free $"
diag_overlay: .asciiz "Overlay loads / hits / calls"
diag_map: .asciiz "Map $        Logical $"
diag_physical: .asciiz "Physical $"
diag_types1: .asciiz "Owners: 0 free 1 control 2 assets"
diag_types2: .asciiz "3 meta 4 source; epoch-borrowed"
diag_close: .asciiz "F1/F6/F7 or STOP closes"
; descriptor offset,row,column; display multibyte values most significant first.
diag_fields:
 .byte DS_ABI,4,20
 .byte DS_LENGTH+2,6,11,DS_LENGTH+1,6,13,DS_LENGTH,6,15
 .byte DS_GENERATION+1,6,24,DS_GENERATION,6,26
 .byte DS_CURSOR+2,7,11,DS_CURSOR+1,7,13,DS_CURSOR,7,15
 .byte DS_CRC+1,7,24,DS_CRC,7,26
 .byte DS_HASH_TYPE,8,28
 .byte DS_PENDING,10,12,DS_DIRTY,10,23
 .byte DS_EPOCH+1,11,10,DS_EPOCH,11,12
 .byte DS_BANKS+1,11,25,DS_BANKS,11,27
 .byte DS_ALLOCATED+1,12,14,DS_ALLOCATED,12,16
 .byte DS_FREE+1,12,25,DS_FREE,12,27
 .byte DS_LOADS+1,15,4,DS_LOADS,15,6
 .byte DS_HITS+1,15,14,DS_HITS,15,16
 .byte DS_CALLS+1,15,24,DS_CALLS,15,26
 .byte DS_MAP+1,17,8,DS_MAP,17,10
 .byte DS_LOGICAL_OWNERS+1,17,25,DS_LOGICAL_OWNERS,17,27
 .byte DS_PHYSICAL_OWNERS+1,18,13,DS_PHYSICAL_OWNERS,18,15
diag_fields_end:
