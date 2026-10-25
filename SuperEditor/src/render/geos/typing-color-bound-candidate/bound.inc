; Private read-only conditional admission proof, NOT an installed C6/R30 guard.
; Caller authenticates full source/GCC/GTC context immediately before calling.
; All row/palette data is fetched through checked typedFE transport here.
TCB_FRAME=$8A00
TCB_ROW=0
TCB_TOP=1
TCB_FIRST=2 ;affected tile columns inclusive
TCB_LAST=3
TCB_ATTR=4 ;expected white foreground1/background6
TCB_SIZE=24
TCB_BASE=$8400 ;360 post-edit BASE-INK bytes,9 scanlines*40, no inverse/caret
TCB_VOTES=$8580 ;80 scratch votes, two physical8px tilebands
TCB_HEADER=$90CA ;exact authenticated header copy already used by C32
TCB_ROLEBUF=$8200 ;161 checkedrole bytes; no source/packet/frame overlap
