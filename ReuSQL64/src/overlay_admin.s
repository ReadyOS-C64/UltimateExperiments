        .export _rsql_overlay_load_admin

        .segment "ENGINE"

; Load the fixed administration cache without using the cc65 software stack.
; This is safe when called by an overlay-return trampoline: all executing code
; remains resident while DMA replaces $7C00-$BFFF.
_rsql_overlay_load_admin:
        lda $0001
        pha
        ora #$06
        and #$FE
        sta $0001
        lda #$00
        sta $DF02
        sta $DF04
        sta $DF06
        sta $DF07
        sta $DF09
        sta $DF0A
        lda #$7C
        sta $DF03
        lda #$22
        sta $DF05
        lda #$44
        sta $DF08
        lda #$91
        sta $DF01
        pla
        sta $0001
        lda #$00
        tax
        rts
