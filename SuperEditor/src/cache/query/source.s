.setcpu "6502"
.macpack longbranch
.include "cache/query/api.inc"
.include "fold/source.inc"
.import se_f_owner,se_overlay_frame,se_overlay_call
.import bca_guard
.include "cache/arena/api.inc"
.ifndef BCQ_SELECTOR_OWNS_OWNER
.export bq_owner
.endif
.export bq_authority,bq_source,bq_end,bq_pending,bq_bad,bq_changed,bq_corrupt,bq_fail,bq_done
.segment "CODE"
.ifndef BCQ_SELECTOR_OWNS_OWNER
bq_owner:
 lda se_f_owner
 cmp #4
 beq @ok
 lda #$B2
 sec
 rts
@ok:clc
 rts
.endif
bq_authority:
 lda se_bc_flags
 and #BC_ARMED|BC_LOST|BC_MUTATING|BC_ACTIVE
.ifdef BCQ_EDITOR_ACTIVE
 ldx BQ_LIVE
 beq :+
 eor #BC_ACTIVE
:
.endif
 cmp #BC_ARMED
 jne bq_changed
 lda se_bc_count
 jne bq_changed
 ldy #12
@tuple:lda BQ_AUTH,y
 cmp se_bc_arena,y
 jne bq_changed
 dey
 bpl @tuple
 jmp bca_guard
; A0realBEGIN/A1realGUARD. IO may be overwritten, caller must drainREADY first.
bq_source:
 pha
 ldy #85
@to:lda BQ_READER,y
 sta se_fs_state,y
 dey
 bpl @to
 pla
 sta se_overlay_frame
 lda #14
 ldx #0
 jsr se_overlay_call
 php
 pha
 ldy #85
@from:lda se_fs_state,y
 sta BQ_READER,y
 dey
 bpl @from
 pla
 plp
 rts
bq_end:
 lda BQ_STATE
 beq @clear
 lda #0
 sta BCA_PHASE
 sta BCA_PROOF
 lda BQ_LIVE
 beq @clear
.ifdef BCQ_EDITOR_ACTIVE
 lda se_bc_flags
 and #$FF-BC_ACTIVE
 sta se_bc_flags
.endif
 ldy #85
@to:lda BQ_READER,y
 sta se_fs_state,y
 dey
 bpl @to
 jsr se_fs_end
 lda #0
 sta BQ_READER+7
 sta BQ_READER+8
@clear:lda #0
 sta BQ_LIVE
 sta BQ_STATE
 sta BQ_READY
 rts
bq_bad:lda #$C0
 bne bq_fail
bq_changed:lda #$C1
 bne bq_fail
bq_corrupt:lda #$C2
bq_fail:
 pha
 jsr bq_end
 pla
 sta BQ_ERROR
 sec
 rts
bq_pending:lda #1
 clc
 rts
bq_done:jsr bq_end
 lda #0
 clc
 rts

.ifdef BCQ_CLASSIFY
.export bq_baseline_miss
bq_baseline_miss:
 jsr bq_end
 lda #2
 clc
 rts
.endif
