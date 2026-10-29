.setcpu "6502"
.macpack longbranch
.include "editor_file/api.inc"
.include "editor/api.inc"
.include "tui/theme.inc"
.import se_f_ui_key,se_f_ui_index,se_f_ui_help
.import se_petscii_screen
.segment "CODE"
; Native16-byte name line; root C7 supplies dialog framing and lists. Carry clear:
; A0 editing,A1 accept(name validation still mandatory),A2 cancel. No disk access.
se_file_ui_key:
    lda se_e_key
    cmp #$8B ;F6 remains inside file modal
    beq @help
    cmp #$03 ;RUN/STOP
    beq @cancel
    cmp #$0D
    beq @accept
    cmp #$86 ;F3 toggles8/9
    beq @device
    cmp #$14
    beq @delete
    cmp #$20
    bcc @editing
    cmp #$7F
    bcc @insert
    cmp #$A0
    bcc @editing
@insert:
    ldx se_f_name_len
    cpx #16
    bcs @editing
    sta se_f_name,x
    inc se_f_name_len
@editing:
    lda #0
    clc
    rts
@help:
    lda se_f_ui_help
    eor #1
    sta se_f_ui_help
    jmp @editing
@device:
    lda se_f_device
    eor #1
    sta se_f_device
    jmp @editing
@delete:
    lda se_f_name_len
    beq @editing
    dec se_f_name_len
    jmp @editing
@accept:
    lda se_f_name_len
    beq @editing
    lda #1
    clc
    rts
@cancel:
    lda #2
    clc
    rts
.ifndef SE_FILE_UI_KEY_ONLY
; One bottom row only; rows0..23 are deliberately untouched. Raw PETSCII byte
; conversion matches screen codes, preserving lower/upper charset behavior.
se_file_ui_draw:
    ldx #39
@clear:
    lda #$20
    sta $43C0,x
    lda #TUI_STATUS
    sta $DBC0,x
    dex
    bpl @clear
    lda se_f_ui_help
    beq @normal
    ldx #0
@help:
    lda help,x
    beq @done
    sta $43C0,x
    inx
    bne @help
@done:
    lda #0
    clc
    rts
@normal:
    ldx #0
@label:
    lda label,x
    beq @name
    sta $43C0,x
    inx
    bne @label
@name:
    ldy #0
@next:
    cpy se_f_name_len
    bcs @drive
    lda se_f_name,y
    jsr se_petscii_screen
    sta $43C6,y
    lda #TUI_TITLE
    sta $DBC6,y
    iny
    bne @next
@drive:
    lda se_f_device
    clc
    adc #$30
    sta $43D9
    lda #0
    clc
    rts
.segment "RODATA"
label: .byte 6,9,12,5,$3A,$20,0 ;FILE:

help: .byte 18,5,20,$3A,7,15,$20,19,20,15,16,$3A,2,1,3,11,$20,6,3,$3A,8,$2F,9,$20,6,6,$3A,8,5,12,16,0
.endif
