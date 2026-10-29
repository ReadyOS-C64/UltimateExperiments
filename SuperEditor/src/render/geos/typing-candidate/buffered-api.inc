.ifndef SE_TYPING_CANDIDATE
SE_TYPING_CANDIDATE=1
; Private plain-row primitive. Explicit trusted caret-free source and glyph.
GT_FRAME=$8B40
GT_BASE=$8400               ;9*40 packed bytes, scanlines left-to-right
GT_TEMP=$8580               ;40-byte scanline staging
GT_OP=0                    ;0 insert,1 delete
GT_FLAGS=1                 ;must0: no wrap/pan/selection/fold/inline/style
GT_TOP=2                   ;16..183, all nine scanlines visible
GT_ADVANCE=3               ;1..8
GT_X=4                     ;word0..320
GT_OLD_WIDTH=6             ;word0..320, actual plain row pixel width
GT_CARET_WIDTH=8           ;1..8, caret at x+advance(insert) orx(delete)
GT_ATTRIBUTE=9             ;required whole two-strip attribute value
GT_GLYPH=10                ;nine MSB-aligned bytes, no bits beyondadvance
GT_VALID=19                ;1 onlyafter complete output
GT_PRIVATE=20
GT_SIZE=96
.global se_typing_patch
.endif
