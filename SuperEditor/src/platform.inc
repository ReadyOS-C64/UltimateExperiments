; Native PETSCII strings are written readably in assembly source.
; In the mixed-case set: unshifted letters = PETSCII $41-$5A (lowercase),
; shifted letters = $C1-$DA (uppercase). Screen codes are a separate mapping.
.repeat 26, I
    .charmap $41+I, $C1+I
    .charmap $61+I, $41+I
.endrepeat
.include "tui/theme.inc"

K_GETIN = $FFE4
VIC_SCREEN = $4000
VIC_CHARSET = $4800
VIC_BITMAP = $6000
SHIM_FIRST = $C600
SHIM_LAST = $C9FF

.macro PRINT_AT label, row, column
    lda #<label
    sta text_ptr
    lda #>label
    sta text_ptr+1
    lda #<(VIC_SCREEN+40*row+column)
    sta screen_ptr
    lda #>(VIC_SCREEN+40*row+column)
    sta screen_ptr+1
    jsr se_print
.endmacro
