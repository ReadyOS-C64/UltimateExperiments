; Bounded vertical transport component, not an editor publication API.
; Caller must supply source/geometry authority before invoking this primitive.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.import se_f_owner,se_mode,se_render_caps,se_sel_mark
.import se_gc_handle,se_gc_epoch,se_reu_map,se_gc_valid
.import se_reu_epoch,se_reu_retired,se_reu_logical_owner,se_reu_physical_owner
.import se_reu_logical,se_reu_offset,se_reu_c64,se_reu_length,se_reu_copy
.export se_rg_prepare,se_rg_apply,se_rg_check_owner
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
se_rg_prepare:
 jsr check_owner
 jcs return
 lda #0
 sta READY
 lda VERSION
 cmp #1
 bne bad
 lda FIRST
 cmp #23
 bcs bad
 lda COUNT
 cmp #23
 bcs bad
 lda DIRECTION
 cmp #1
 beq :+
 cmp #$FF
 bne bad
: clc
 adc FIRST
 cmp #23
 bcs bad
 clc
 adc COUNT
 cmp #23
 bcs bad
 lda FIRST
 clc
 adc COUNT
 cmp #23
 bcs bad
 lda se_gc_handle
 sta HANDLE
 tax
 lda se_reu_map,x
 sta MAP
 lda se_gc_epoch
 sta EPOCH
 lda se_gc_epoch+1
 sta EPOCH+1
 lda FIRST
 clc
 adc #2
 jsr multiply
 lda LENGTH
 sta SRC
 lda LENGTH+1
 clc
 adc #$60
 sta SRC+1
 lda DIRECTION
 cmp #1
 bne @up
 clc
 lda SRC
 adc #$40
 sta DST
 lda SRC+1
 adc #1
 bne @high
@up:
 sec
 lda SRC
 sbc #$40
 sta DST
 lda SRC+1
 sbc #1
@high:
 sta DST+1
 lda COUNT
 jsr multiply
 lda #$A5
 sta READY
 jmp zero
return:
 rts
; A*320, no address/bank assumptions. Result bounded by admitted row count.
multiply:
 sta WORK
 sta LENGTH
 lda #0
 sta LENGTH+1
 ldx #6
@bit:
 asl LENGTH
 rol LENGTH+1
 dex
 bne @bit
 clc
 lda LENGTH+1
 adc WORK
 sta LENGTH+1
 rts
se_rg_apply:
 jsr check_owner
 jcs return
 lda READY
 cmp #$A5
 jne bad
 lda se_gc_handle
 cmp HANDLE
 jne bad
 tax
 lda se_reu_map,x
 cmp MAP
 jne bad
 lda se_gc_epoch
 cmp EPOCH
 jne bad
 lda se_gc_epoch+1
 cmp EPOCH+1
 jne bad
 ; Derive bounds again and require the stored plan to match exactly. No
 ; caller-provided raw CPU address or byte length is ever sent to DMA.
 ldx #5
@saved:
 lda SRC,x
 sta G+19,x
 dex
 bpl @saved
 jsr se_rg_prepare
 jcs return
 ldx #5
@same:
 lda SRC,x
 cmp G+19,x
 jne bad
 dex
 bpl @same
 lda #0
 sta READY
 lda COUNT
 jeq zero
 ; Future caller must restore valid bits only after complete cache publication.
 lda #0
 sta se_gc_valid
 sta se_gc_valid+1
 sta se_gc_valid+2
 lda #$20
 sta OFFSET
 jsr move
 jcs return
 ldx #9
 jsr attributes
 ldx #11
 jsr attributes
 ldx #13
 jsr divide
 lda #$3C
 sta OFFSET
 jmp move
attributes:
 sec
 lda G+1,x
 sbc #$60
 sta G+1,x
 jsr divide
 clc
 lda G+1,x
 adc #$40
 sta G+1,x
 rts
divide:
 ldy #3
@bit:
 lsr G+1,x
 ror G,x
 dey
 bne @bit
 rts
move:
 jsr request
 lda SRC
 sta se_reu_c64
 lda SRC+1
 sta se_reu_c64+1
 lda #0
 jsr se_reu_copy
 jcs return
 jsr request
 lda DST
 sta se_reu_c64
 lda DST+1
 sta se_reu_c64+1
 lda #1
 jmp se_reu_copy
request:
 lda HANDLE
 sta se_reu_logical
 lda #0
 sta se_reu_offset
 lda OFFSET
 sta se_reu_offset+1
 lda LENGTH
 sta se_reu_length
 lda LENGTH+1
 sta se_reu_length+1
 rts

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
