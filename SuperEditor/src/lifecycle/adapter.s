; Standalone callable C29 adapter. No root scheduler/job or new resident state.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "lifecycle/adapter.inc"
.include "lifecycle/preflight.inc"
.import se_lc_preflight,se_lc_warm_hardware
.import se_overlay_frame,se_overlay_call
.import se_reu_alloc,se_reu_epoch,se_reu_retired,se_reu_map
.import se_reu_logical_owner,se_reu_physical_owner
.import se_hot_caret,se_sel_mark,se_sel_anchor
.export entry
.segment "CODE"
 OVL_BINDING
entry:
 lda se_overlay_frame
 beq begin
 cmp #LC_STEP
 jeq step
 cmp #LC_CANCEL
 jeq cancel
 cmp #LC_HARDWARE
 jeq se_lc_warm_hardware
 lda #LC_E_STATE
 sec
 rts
begin:
 lda LC_PHASE
 beq :+
 lda #LC_E_STATE
 sec
 rts
:
 jsr se_lc_preflight
 jcs done
 ; Witness excludes foreground object/overlay/DMA scratch only. No document
 ; flush, source lease, history append, or view/selection motion is performed.
 ldx #58
@identity:lda LC_P_IDENTITY,x
 sta LC_WITNESS,x
 dex
 bpl @identity
 ldx #2
@caret:lda se_hot_caret,x
 sta LC_CARET,x
 lda se_sel_anchor,x
 sta LC_SELECTION+1,x
 dex
 bpl @caret
 lda se_sel_mark
 sta LC_SELECTION
 ; Reuse only an exact current owned capability. Never free a stale/foreign
 ; allocation just because an earlier cold descriptor happened to name it.
 lda LC_EPOCH
 cmp se_reu_epoch
 bne @allocate
 lda LC_EPOCH+1
 cmp se_reu_epoch+1
 bne @allocate
 ldx LC_HANDLE
 beq @allocate
 lda se_reu_logical_owner,x
 cmp #LC_OWNER
 bne @allocate
 ldy se_reu_map,x
 beq @allocate
 lda se_reu_physical_owner,y
 cmp #LC_OWNER
 beq @owned
@allocate:
 lda #LC_OWNER
 jsr se_reu_alloc
 jcs done
 sta LC_HANDLE
 tax
 ldy se_reu_map,x
@owned:
 sty LC_PHYSICAL
 lda se_reu_epoch
 sta LC_EPOCH
 lda se_reu_epoch+1
 sta LC_EPOCH+1
 ldx #0
@prelude:
 lda LC_RESUME_TEMPLATE,x
 sta LC_RESUME,x
 inx
 bne @prelude
 lda #0
 jmp copy
step:
 jsr se_lc_preflight
 jcs abort
 ldx #58
@identity:lda LC_P_IDENTITY,x
 cmp LC_WITNESS,x
 jne changed
 dex
 bpl @identity
 ldx #2
@caret:lda se_hot_caret,x
 cmp LC_CARET,x
 jne changed
 lda se_sel_anchor,x
 cmp LC_SELECTION+1,x
 jne changed
 dex
 bpl @caret
 lda se_sel_mark
 cmp LC_SELECTION
 jne changed
 lda #1
copy:
 sta se_overlay_frame
 lda #LC_COPY_ID
 ldx #0
 jsr se_overlay_call
 bcs abort
 rts
cancel:
 lda #0
 sta LC_PHASE ;header remainsuncommitted afteradmitted BEGIN
 clc
 rts
changed:
 lda #LC_E_CHANGED
abort:
 pha
 lda #0
 sta LC_PHASE
 pla
 sec
done:rts
