; C7 rare bounded admission. Included into the parent menu CODE object.
; Caller has freshly claimed owner4, with no old source-reader lease.
; A1/Cclear schedules C34; A2/Cclear optional miss. No C-slot child call.
.ifndef SE_CACHE_EDITOR_ADMIT
SE_CACHE_EDITOR_ADMIT=1
.include "cache/semantic/api.inc"
.ifndef BC_REBUILD_TRIED
BC_REBUILD_TRIED=$10
.endif
.include "cache/arena/api.inc"
.include "object/api.inc"
.global se_f_owner,se_render_caps,se_overlay_call,se_overlay_frame
.export se_bc_admit
BCAI_STEPS=BC_FRAME+21
BCAI_SOURCE_ACTIVE=$912C
BCAI_SOURCE_CONTEXT=$912D
BCAI_REQUEST=$9135
BCAI_OPERATION=$9136
.segment "CODE"
se_bc_admit:
 lda se_f_owner
 cmp #4
 jne bcai_miss
 lda se_render_caps
 jeq bcai_miss
 cmp #1
 beq :+
 cmp #3
 jne bcai_miss
:
 pha
 lda se_bc_flags
 and #(BC_ACTIVE|BC_MUTATING)
 beq :+
 pla
 jmp bcai_miss
:
 ; Clear only the explicitly owned replacement frame; old GEOS source flags
 ; are nonauthoritative because admission holds no source lease.
 lda #0
 tax
@pages:
 sta BC_FRAME,x
 sta BC_FRAME+$100,x
 inx
 bne @pages
 ldx #63
@tail:
 sta BC_FRAME+$200,x
 dex
 bpl @tail
 sta BCAI_SOURCE_ACTIVE
 sta BCAI_SOURCE_CONTEXT
 pla
 sta BC_FRAME+BCF_CAPS
 lda #(BC_LOST|BC_REBUILD_TRIED)
 sta se_bc_flags
 ; Full rebuild deliberately releases any previous arena before OPEN.
 ldy #4
 lda #0
@present:
 ora se_bc_arena,y
 dey
 bpl @present
 cmp #0 ;DEY ended at FF; test accumulated token, not its flags
 beq @open
 lda #3
 jsr bcai_call
 bcs bcai_failed
 cmp #0
 bne bcai_failed
@open:
 lda #36
 sta BCAI_STEPS
 lda #0
 jsr bcai_call
 bcs bcai_failed
@result:
 cmp #0
 beq bcai_ready
 cmp #1
 bne bcai_failed
 dec BCAI_STEPS
 beq bcai_failed
 lda #1
 jsr bcai_call
 bcc @result
bcai_failed:
 ; Capture diagnostic only; optional cache failure cannot veto source work.
 sta BC_FRAME+BCF_ERROR
 lda #(BC_LOST|BC_REBUILD_TRIED)
 sta se_bc_flags
 lda BCA_PHASE
 cmp #1
 beq @candidate
 cmp #5
 beq @candidate
 cmp #6
 jne bcai_miss
@candidate:
 ; Never release a token already published by the writer or another path.
 ldy #4
@published:
 lda BCA_BOUND,y
 cmp se_bc_arena,y
 bne @validate
 dey
 bpl @published
 jmp bcai_miss
@validate:
 ldy #4
@capture:
 lda BCA_BOUND,y
 sta se_object_id,y
 dey
 bpl @capture
 jsr se_object_validate
 bcs bcai_miss ;stale/foreign is not permission to free a recycled bank
 lda object_owner,x
 cmp #BC_OBJECT_TYPE
 jne bcai_miss
 jsr se_object_release
 bcc @released
 ; Exact validated owned capability still reachable for explicit TRIM retry.
 ldy #4
@retain:
 lda BCA_BOUND,y
 sta se_bc_arena,y
 dey
 bpl @retain
 jmp bcai_miss
@released:
 lda #0
 sta BCA_PHASE
 sta BCA_PROOF
bcai_miss:
 lda #BC_MISS
 clc
 rts
bcai_ready:
 lda #BSC_ABI
 sta BC_FRAME+BCF_ABI
 lda #BSC_REBUILD
 sta BC_FRAME+BCF_BUDGET
 ldy #4
@arena:
 lda se_bc_arena,y
 sta BC_FRAME+BCF_ARENA,y
 dey
 bpl @arena
 ldy #3
@key:
 lda se_bc_incarnation,y
 sta BC_FRAME+BCF_INCARNATION,y
 lda se_bc_ticket,y
 sta BC_FRAME+BCF_TICKET,y
 dey
 bpl @key
 lda #34
 sta BCAI_REQUEST
 lda #0
 sta BCAI_OPERATION
 lda #BC_PENDING
 clc
 rts
bcai_call:
 sta se_overlay_frame
 lda #33
 ldx #0
 jmp se_overlay_call
.endif
