.ifndef SE_BITMAP_CELL8_API
SE_BITMAP_CELL8_API=1
; X/Y -> immutable caller-owned11-byte input frame. Foreground-only,
; nonreentrant; loans two EXISTING pointer pairs, allocates no ZP/BSS.
; Both pairs are clobbered. The context pair ends pointing at source glyph.
.importzp se_bc_context,se_bc_pointer
.global se_bitmap_cell8
BC_ROW=0                 ;physical row0..24
BC_COLUMN=1              ;physical8px column0..39
BC_SCREEN=2              ;raw screen code;bit7 inverts128-glyph native font
BC_FOREGROUND=3          ;0..15
BC_BACKGROUND=4          ;0..15
BC_FONT=5                ;1KiB aligned in A000..BC00;1024 readable bytes
BC_BITMAP=7              ;must be6000: actual-mode VIC bitmap
BC_ATTRIBUTES=9          ;must be4000: actual-mode VIC screen/attribute matrix
BC_SIZE=11
BC_ARGUMENT=$90
; Caller owns frame/font/output storage, keeps frame/font disjoint from output,
; and supplies readable font RAM with I/O/ROM banking already appropriate.
; Success A0/Cclear; invalid fields A90/Cset before frame/output writes.
; Writes exactly8 bitmap bytes and1 attribute; no KERNAL/REU/VIC calls.
.endif
