; Automatic C-slot semantic-to-arena pump. Admission has already opened an EMPTY arena.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "cache/semantic/api.inc"
.include "cache/arena/writer.inc"
.import se_f_owner,se_overlay_call,se_bsc_owned_release
JOB=BC_FRAME+82
.segment "BSC_CODE"
 OVL_BINDING
.export entry
entry:
 lda se_f_owner
 cmp #4
 bne busy
 lda se_overlay_frame
 beq begin
 cmp #1
 beq step
 cmp #2
 jeq cancel
argument:
 lda #BSC_BAD
 sec
 rts
busy:lda #BSC_BUSY
 sec
error_return:rts
miss:
 clc
 rts
begin:
 jsr se_bsc_begin
 bcs error_return
 cmp #2
 beq miss
 lda #4
 jmp arena_pending
step:
 lda se_bc_flags
 and #BC_ACTIVE
 beq argument ;closed STEP must preserve a previously completed baseline
 lda BCA_PHASE
 bne @active
 lda #BSC_BAD
 bne failed ;closed/corrupt STEP cancels own lease and returns explicit error
@active:
 cmp #BW_IDLE
 bne writer_step
 lda JOB
 bne ack
 lda BSC_F+BCF_READY
 bne append
 lda BSC_F+BCF_STATE
 beq final
 jsr se_bsc_step
 jmp checked_pending
append:
 lda #1
 sta JOB
 lda #5
 jsr arena
 bcs failed
 cmp #BC_STREAM
 beq stream
 bcc pending
ack:
 jsr se_bsc_ack
 bcs failed
 lda #0
 sta JOB
 beq pending
final:
 lda #6
 jmp arena_pending
writer_step:
 lda #1
 jsr arena
 bcs failed
 lda se_bc_flags
 and #BC_ARMED
 lsr
 bcc pending
done:
 clc
 rts
arena_pending:
 jsr arena
checked_pending:
 bcs failed
pending:
 lda #1
 clc
 rts
failed:
 pha
 jsr owned_cancel
 pla
 sec
 rts
arena:
 sta se_overlay_frame
 lda #33
 ldx #0
 jmp se_overlay_call
cancel:
 lda se_bc_flags
 and #BC_ACTIVE
 beq done
owned_cancel:
 jsr se_bsc_owned_release
 lda #(BC_LOST|BC_REBUILD_TRIED)
 sta se_bc_flags
 lda #0
 sta BCA_PHASE
 sta BCA_PROOF
 clc
 rts
stream:
 jsr owned_cancel ;writer STREAM has already cleared BC_ACTIVE
 lda #BC_STREAM
 clc
 rts
