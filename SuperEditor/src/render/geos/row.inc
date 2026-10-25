.ifndef SE_GEOS_ROW_API
SE_GEOS_ROW_API=1
; Compiled caller-owned frame, default within COW suffix. No allocation/BSS/ZP.
.ifndef GEOS_ROW_FRAME
GEOS_ROW_FRAME=$8880
.endif
GR_ROW=0                    ;physical320x8 VIC strip0..24
GR_RUNS=1                   ;0..2 intersecting native source runs
GR_RESET=2                  ;1 clear clip+histogram,0 append to same strip/frame
GR_BACKGROUND=3             ;low nibble0..15
GR_RUN_POINTER=4            ;caller-owned17-byte descriptors in8D00..917F
GR_FONT=6
GR_WIDTHS=8
GR_NATIVE=10
GR_PALETTE=12               ;14 ReadyOS/SuperMark foregrounds0..15
GR_LEFT=14                  ;16-bit screen clip,0..320 inclusive
GR_RIGHT=16                 ;half-open horizontal clip
GR_TOP=18                   ;strip local vertical clip0..8 inclusive
GR_BOTTOM=19
GR_INPUT_SIZE=20
GR_VALID=20                 ;1 complete strip/append,0 error/in progress
GR_GLYPH=21                 ;existing77-byte GG frame, private
GR_HISTOGRAM=98             ;40x14 saturating base-ink weights
GR_PRIVATE=658
GR_SIZE=704
; Descriptor inputs; outputs follow them. Input/map arrays are caller-owned,
; disjoint and fit8D00..917F; maps contain consumed+1 untrimmed16-bit boundaries.
; Horizontal origins-15..-1 use two's complement. Their pixels clip before
; address calculation; advances cross zero modulo65536. Other high unsigned
; origins retain off-right behavior. Returned boundaries/NEXT_X retain the same
; encoding until advances become nonnegative; callers must interpretFFF1..FFFF
; as signed. Positive origins/clip bounds remain unsigned0..320.
GRR_COUNT=0                 ;0..128 source bytes
GRR_Y=1                     ;signed glyph origin−8..7 relative to strip
GRR_X=2                     ;untrimmed16-bit x;FFF1..FFFF encode-15..-1
GRR_CHARACTERS=4
GRR_STYLES=6                ;GG bold1/italic2,0..3
GRR_ROLES=8                 ;14 palette roles,0..13
GRR_FLAGS=10                ;inverse1,selected2,caret4;selected/caret union once
GRR_BOUNDARIES=12
GRR_DONE=14
GRR_NEXT_X=15
GRR_SIZE=17
.global se_geos_row
GR_ARGUMENT=$90
.assert GEOS_ROW_FRAME >= $8880 .and GEOS_ROW_FRAME+GR_SIZE <= $8C00,error,"GEOS row frame outside caller COW suffix"
.endif
