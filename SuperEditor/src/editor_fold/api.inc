.ifndef SE_EDITOR_FOLD_API
SE_EDITOR_FOLD_API=1
EF_KEY_SIZE=28
EF_DESCRIPTOR_SIZE=45
EF_PROJECTION_SIZE=69
EF_STATE_SIZE=114
EF_CHANGED=$B7
EF_KEY_META=0
EF_KEY_ORIGINAL=5
EF_KEY_APPEND=10
EF_KEY_GENERATION=15
EF_KEY_REVISION=17
EF_KEY_LENGTH=21
EF_KEY_REU_EPOCH=24
EF_KEY_DOC_EPOCH=26
; Persistent descriptor; no phase-union fields, cursor/gap geometry or ZP.
; KEY_CAPTURE first invalidates map/projection, calls actual view_init and
; validates full3objecttokens, then captures28B. Root alone publishes VALID
; after real builder/validator success. KEY_MATCH checks source identity even
; while VALID0 (in-progress job guard); query consumers MUST also require VALID1.
; Errors invalidate VALID and3projectionbits only, preserve token/count/active
; and all foreign leases. A0/Cclear success; original view/object error or
; EF_CHANGED/Cset. Shared view and object request frames are refreshed/clobbered.
; No alloc/free, source writes, REU DMA or phase inspection. Nonreentrant.
;
; Key excludes gapleft/right/caret: moving the gap changes representation, not
; visible bytes or render revision. Full tokens include generation/provider
; epoch; committed generation, merged length, render revision and two service
; epochs distinguish actual content/lifetime changes under mutation contract.
; Caller must explicitly INVALIDATE on known revision/generation wrap/reset,
; before any alias can be treated as a published map. No edited-fold retention.
;
; MOTION_TICK increments32-bit serial; normal motion preserves map. On wrap,
; INVALIDATE prevents old saved motion0 from restoring an ancient inner caret.
; INVALIDATE does not release allocations or erase published ends/token/count.
.ifndef SE_EDITOR_FOLD_IMPLEMENTATION
.import se_ef_key_capture,se_ef_key_match,se_ef_invalidate,se_ef_motion_tick
.ifndef EDITOR_OVERLAY
.import se_ef_state,se_ef_token,se_ef_count,se_ef_key,se_ef_valid,se_ef_motion
.import se_ef_capacity_banks,se_ef_generation,se_ef_active,se_ef_operation
.import se_ef_paint_ends,se_ef_fold_rows,se_ef_state_end
.endif
.endif
.endif
