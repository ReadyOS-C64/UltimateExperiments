.setcpu "6502"
.macpack longbranch
.include "cache/arena/api.inc"
.include "object/api.inc"
.import bca_owner,bca_guard,bca_validate,bca_done,bca_bad,bca_open_step
.ifdef BCA_WRITER_PROFILE
.include "cache/arena/writer.inc"
.else
.import bca_page_step
.endif
.export se_bc_arena_step,se_bc_arena_cancel,se_bc_arena_trim
.segment "CODE"
se_bc_arena_step:
 jsr bca_owner
 bcs @done
 lda BCA_PHASE
 jeq bca_done
.ifdef BCA_WRITER_PROFILE
 cmp #10
 bcs @writer
 cmp #7
 jcs bca_bad
 jmp bca_open_step
@writer:jmp se_bc_write_step
.else
 cmp #7
 bcs @page
 jmp bca_open_step
@page:jmp bca_page_step
.endif
@done:rts
se_bc_arena_cancel:
 jsr bca_owner
 bcs @done
 lda BCA_PHASE
.ifdef BCA_WRITER_PROFILE
 cmp #10
 bcc :+
 jmp se_bc_write_cancel
:
.endif
 cmp #1
 beq @candidate
 cmp #5
 beq @candidate
 cmp #6
 bne @clear
@candidate:
 ; Never release a capability now published by another path.
 ldy #4
@same:lda se_bc_arena,y
 cmp BCA_BOUND,y
 bne @release
 dey
 bpl @same
 jmp @clear
@release:
 jsr bca_validate
 bcs @done
 jsr se_object_release
 bcs @done
@clear:lda #0
 sta BCA_PHASE
 sta BCA_PROOF
 jmp bca_done
@done:rts
se_bc_arena_trim:
 jsr bca_owner
 bcs @done
 lda BCA_PHASE
 jne bca_bad
 lda se_bc_flags
 and #BC_MUTATING
 jne bca_bad
 ldy #4
@token:lda se_bc_arena,y
 sta BCA_BOUND,y
 dey
 bpl @token
 jsr bca_validate
 bcs @done
 jsr se_object_release
 bcs @done
 ; All release guards succeeded. Keep monotonically advancing incarnation and
 ; observer ticket; dropping derived cache cannot reset mutation observation.
 lda #0
 ldy #4
@clear:sta se_bc_arena,y
 dey
 bpl @clear
 sta BCA_PROOF
 lda se_bc_flags
 and #($FF-BC_ARMED)
 ora #BC_LOST
 sta se_bc_flags
 jmp bca_done
@done:rts
