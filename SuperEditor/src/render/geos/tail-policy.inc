; Pure virtual-tail/selection policy shared by C22 and the R25 probe.
; Caller authenticates owner4 and binds S/R/source/lo/hi/want/flags/char/role.
.include "document/math24.inc"
tail_selection:
 ldx #2
@source:
 lda R+GPR_END,x
 sta source,x
 dex
 bpl @source
 lda #0
 sta flags
 sta role
 lda #32
 sta char
 ; No normalized offscreen tail may acquire paint flags or a folded plus.
 lda R+GPR_TAIL_VALID
 beq done
 lda R+GPR_FLAGS
 bpl selection
 lda #1
 sta flags
 lda #43
 sta char
 lda #2
 sta role
selection:
 lda want
 beq done
 lda R+GPR_REASON
 cmp #1
 bne done
 CMP24 source,hi
 bcs done
 lda R+GPR_FLAGS
 bmi folded
 CMP24 source,lo
 bcc done
 bcs selected
folded:
 CMP24 lo,R+GPR_NEXT
 bcs done
selected:
 lda flags
 ora #2
 sta flags
done:
 lda #0
 clc
 rts
selection_bounds:
 lda S+$4E
 beq done_bounds
 ldx #2
@compare:
 lda S+$6C,x
 cmp S+$45,x
 bcc @anchor_first
 bne @caret_first
 dex
 bpl @compare
@caret_first:
 ldx #2
@copy_end:
 lda S+$6C,x
 sta hi,x
 dex
 bpl @copy_end
 jmp done_bounds
@anchor_first:
 ldx #2
@copy_start:
 lda S+$6C,x
 sta lo,x
 dex
 bpl @copy_start
done_bounds:
 lda #0
 clc
 rts
