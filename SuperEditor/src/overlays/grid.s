.setcpu "6502"
.include "editor-api.inc"
.include "render/narrow/grid.inc"
.import se_narrow_row,se_bitmap_cell8,se_native_font8
.exportzp se_nr_context,se_nr_pointer,se_bc_context,se_bc_pointer
.export se_petscii_screen
; Foreground pointer loans: no new resident ZP allocation.
se_nr_context=text_ptr
se_bc_context=text_ptr
se_nr_pointer=screen_ptr
se_bc_pointer=screen_ptr
.ifdef GRID60
.import se_narrow_font5
.assert se_narrow_font5=GRID_FONT,lderror,"60-column font must beA800"
.else
.import se_narrow_font4
.assert se_narrow_font4=GRID_FONT,lderror,"80-column font must beA800"
.endif
.assert se_native_font8=GRID_NATIVE_FONT,lderror,"native UI font must beAC00"
.segment "CODE"
    OVL_BINDING
.export entry
entry:
    ldx se_overlay_frame+1
    ldy se_overlay_frame+2
    lda se_overlay_frame
    beq row
    cmp #GRID_CELL8
    beq cell
    cmp #GRID_ADMIT
    beq admitted
    lda #$90
    sec
    rts
row:
    jmp se_narrow_row
cell:
    jmp se_bitmap_cell8
admitted:
    lda #0
    clc
    rts
.assert *-entry=33,error,"grid entry must retain fixed49B including binding"
.assert entry=$A010,lderror,"grid leaf entry must follow16-byte binding"
