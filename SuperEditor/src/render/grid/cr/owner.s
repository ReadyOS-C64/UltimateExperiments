; Bounded CR transport owner check; not an editor publication API.
; Caller must supply source/geometry authority before invoking this primitive.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.import se_f_owner,se_mode,se_render_caps,se_sel_mark
.import se_gc_handle,se_gc_epoch,se_reu_map,se_gc_valid
.import se_reu_epoch,se_reu_retired,se_reu_logical_owner,se_reu_physical_owner
.import se_reu_logical,se_reu_offset,se_reu_c64,se_reu_length,se_reu_copy
.export se_rg_check_owner
se_rg_check_owner=check_owner
G=$8D80
VERSION=G
DIRECTION=G+1
FIRST=G+2
COUNT=G+3
READY=G+4
HANDLE=G+5
MAP=G+6
EPOCH=G+7
SRC=G+9
DST=G+11
LENGTH=G+13
WORK=G+15
OFFSET=G+16
.segment "CODE"
busy:
 lda #$B2
 sec
 rts
bad:
 lda #$90
 sec
 rts
zero:
 lda #0
 clc
 rts
check_owner:
 lda se_f_owner
 cmp #4
 bne busy
 lda se_mode
 cmp #1
 beq :+
 cmp #2
 bne bad
: lda se_render_caps
 ora se_sel_mark
 bne bad
 jmp owned
owned:
 lda se_reu_retired
 bne stale
 lda se_gc_epoch
 cmp se_reu_epoch
 bne stale
 lda se_gc_epoch+1
 cmp se_reu_epoch+1
 bne stale
 lda se_reu_epoch
 ora se_reu_epoch+1
 beq stale
 ldx se_gc_handle
 beq stale
 lda se_reu_logical_owner,x
 cmp #$FE
 bne stale
 ldy se_reu_map,x
 beq stale
 lda se_reu_physical_owner,y
 cmp #$FE
 bne stale
 clc
 rts
stale:
 lda #$18
 sec
 rts
