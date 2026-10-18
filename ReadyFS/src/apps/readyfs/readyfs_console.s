; Standalone conio output. Capture every completed physical row before moving
; the cursor, and scroll safely at the bottom instead of writing beyond $07E7.
; The REU DMA uses no cc65 runtime zero page and remains resident across swaps.
        .include "c64.inc"
        .export _cputc, _cputcxy, cputdirect, putchar, newline, plot
        .export _readyfs_console_recording, _readyfs_console_head
        .export _readyfs_console_used, _readyfs_reu_console_bank_value
        .export _readyfs_console_scroll
        .import gotoxy, PLOT

        .export _readyfs_long_options
        .segment "RODATA"
_readyfs_long_options:
        .byte "--recursive",0,"--dry-run",0,"--exclude",0,"--force",0
        .byte "--include",0,"--line",0,"--name",0,"--native-pattern",0
        .byte "--type",0,"--yes",0,"--apply",0,"--continue",0
        .byte "--label",0,"--id",0,"--disposable",0,"--no-verify",0
        .segment "DATA"
_readyfs_console_recording: .byte 0
_readyfs_reu_console_bank_value: .byte $FF
_readyfs_console_head: .word 0
_readyfs_console_used: .word 0
console_offset: .word 0

        .segment "CODE"
_cputcxy:
        pha
        jsr gotoxy
        pla
_cputc:
        cmp #$9E                ; PETSCII yellow: completed work / summaries
        bne @red
        lda #7
        bne @color
@red:   cmp #$1C
        bne @white
        lda #2
        bne @color
@white: cmp #$05
        bne @character
        lda #1
@color: sta CHARCOLOR
        rts
@character:
        cmp #10
        bne @notcr
        lda #0
        sta CURS_X
        jmp plot
@notcr: cmp #13
        bne @print
        jsr newline             ; stash original colors before restoring white
        lda CHARCOLOR
        cmp #2
        beq @normal
        cmp #7
        bne @done
@normal: lda #1
        sta CHARCOLOR
@done:  rts
@print:
        cmp #32
        bcc cputdirect
        bmi @high
        cmp #$60
        bcc @low
        and #$DF
        bne cputdirect
@low:  and #$3F
        jmp cputdirect
@high: and #$7F
        cmp #$7E
        bne @shifted
        lda #$5E
        bne cputdirect
@shifted: ora #$40
cputdirect:
        jsr putchar
        iny
        cpy #40
        bne @position
        jsr newline
        ldy #0
@position:
        sty CURS_X
        rts
putchar:
        ora RVS
        ldy CURS_X
        sta (SCREEN_PTR),y
        lda CHARCOLOR
        sta (CRAM_PTR),y
        rts
newline:
        jsr console_stash_row
        lda CURS_Y
        cmp #24
        bcc @advance
        jsr _readyfs_console_scroll
        jmp plot
@advance:
        inc CURS_Y
plot:
        ldy CURS_X
        ldx CURS_Y
        clc
        jmp PLOT

console_stash_row:
        lda _readyfs_console_recording
        bne @enabled
        rts
@enabled:
        lda _readyfs_reu_console_bank_value
        cmp #$FF
        bne @bank
        rts
@bank:
        sta $DF06
        lda console_offset
        sta $DF04
        lda console_offset+1
        sta $DF05
        lda SCREEN_PTR
        sta $DF02
        lda SCREEN_PTR+1
        sta $DF03
        lda #40
        sta $DF07
        lda #0
        sta $DF08
        sta $DF09
        sta $DF0A
        lda #$90
        sta $DF01
        lda CRAM_PTR
        sta $DF02
        lda CRAM_PTR+1
        sta $DF03
        lda #40
        sta $DF07
        lda #$90
        sta $DF01
        clc
        lda console_offset
        adc #80
        sta console_offset
        lda console_offset+1
        adc #0
        sta console_offset+1
        cmp #$FA
        bne @count
        lda #0
        sta console_offset
        sta console_offset+1
@count:
        inc _readyfs_console_head
        bne @head
        inc _readyfs_console_head+1
@head:
        lda _readyfs_console_head+1
        cmp #3
        bne @used
        lda _readyfs_console_head
        cmp #$20
        bne @used
        lda #0
        sta _readyfs_console_head
        sta _readyfs_console_head+1
@used:
        lda _readyfs_console_used+1
        cmp #3
        bne @increase
        lda _readyfs_console_used
        cmp #$20
        beq @done
@increase:
        inc _readyfs_console_used
        bne @done
        inc _readyfs_console_used+1
@done: rts

; Move 24 screen/color rows and clear row 24. Does not append transcript rows:
; they were captured at emission, so editor layout cannot duplicate output.
_readyfs_console_scroll:
        ldx #0
@pages:
        lda $0428,x
        sta $0400,x
        lda $D828,x
        sta $D800,x
        inx
        bne @pages
@page1:
        lda $0528,x
        sta $0500,x
        lda $D928,x
        sta $D900,x
        inx
        bne @page1
@page2:
        lda $0628,x
        sta $0600,x
        lda $DA28,x
        sta $DA00,x
        inx
        bne @page2
@tail:
        lda $0728,x
        sta $0700,x
        lda $DB28,x
        sta $DB00,x
        inx
        cpx #192
        bne @tail
        ldx #39
@clear:
        lda #32
        sta $07C0,x
        lda CHARCOLOR
        sta $DBC0,x
        dex
        bpl @clear
        rts
