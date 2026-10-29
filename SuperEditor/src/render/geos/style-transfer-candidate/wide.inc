; Explicit trusted glyph-plane/geometry primitive, not a style/source authority.
GT_FRAME=$8A80
GT_BASE=$8400 ;9x40 caret-free packedscanlines
GT_TEMP=$8580 ;40bytes
GT_OP=0
GT_FLAGS=1 ;must0 reserved
GT_TOP=2
GT_ADVANCE=3 ;1..11
GT_X=4
GT_OLD_WIDTH=6
GT_CARET_WIDTH=8 ;1..11
GT_ATTRIBUTE=9
GT_GLYPH=10 ;18bytes (nine16-bit MSB rows), inkinsideadvance
GT_VALID=28
GT_PRIVATE=29
GT_SIZE=105
