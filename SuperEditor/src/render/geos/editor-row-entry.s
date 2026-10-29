; Sealed editor R21 physical GEOS strip leaf. Caller owns all source/layout
; lifetime guards; this renderer is lease-neutral and never touches source.
.setcpu "6502"
.include "editor-api.inc"
.import se_f_owner
.importzp text_ptr,screen_ptr
.import se_geos_row
.import se_geos_packed,se_geos_widths
.export entry
.exportzp se_gg_context,se_gg_pointer
; Existing foreground pointer loans; no resident ZP/state allocation.
se_gg_context=text_ptr
se_gg_pointer=screen_ptr
.segment "CODE"
    OVL_BINDING
entry:
    lda se_f_owner
    cmp #4
    bne busy ;before operation/argument/frame access, including ADMIT
    lda se_overlay_frame
    beq row
    cmp #1 ;ADMIT/NOP validates owner only, no VIC/frame writes
    beq ready
    lda #$90
    sec
    rts
row:
    ldx se_overlay_frame+1
    ldy se_overlay_frame+2
    jmp se_geos_row
ready:
    lda #0
    clc
    rts
busy:
    lda #$B2
    sec
    rts
.assert entry=$A010,lderror,"GEOS row entry must follow16-byte resident binding"
.assert se_geos_packed=$ABF3,lderror,"GEOS page font pointer must match R21"
.assert se_geos_widths=$AEDB,lderror,"GEOS page widths pointer must match R21"
