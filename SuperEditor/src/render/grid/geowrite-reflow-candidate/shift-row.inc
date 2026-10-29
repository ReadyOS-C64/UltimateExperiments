; Private body-row pixel carry primitive. Caller owns foreground + frame.
; Inputs: width60/80,row0..21,col0..width-1,dir0insert/1delete,
; normalized8 high-bit glyph scanlines. Output: old last physical cell's8
; normalized scanlines. Delete input is nextwrappedrow first glyph (0 atCR/EOF).
; Caret-free bitmap and same-role attributes are caller preconditions.
.ifndef LPF
LPF=$8D00
.endif
LP_WIDTH=0
LP_ROW=1
LP_COL=2
LP_DIR=3
LP_INK=4 ;8
LP_CARRY=12 ;8
LP_FRAME_SIZE=64
LP_TEMP=$8000 ;40 byte gathered scanline; invalidates merged-source cache
