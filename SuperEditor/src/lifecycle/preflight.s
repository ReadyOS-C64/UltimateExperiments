.setcpu "6502"
.macpack longbranch
.include "lifecycle/preflight.inc"
.include "document/api.inc"
.include "document/math24.inc"
.include "hot/api.inc"
.include "object/api.inc"
.include "editor/api.inc"
.import se_status,se_mode,se_r_presentation,se_l_mode,se_l_manual,se_v_columns
.import se_overlay_busy,se_overlay_binding_digest
.import se_f_owner,se_l_active,se_n_owned,se_s_active,se_s_owned
.import se_diag_active,se_diag_owned,se_ef_active,se_reu_retired
.import se_input_head,se_input_tail,se_input_nmi_pending
.import se_h_phase,se_h_owned_lease,se_h_owned_capture,se_h_owned_splice
.import se_b_phase,se_b_history_owned,se_b_clip_owned,se_clip_busy
.import se_clip_copy_frame_has_object,se_clip_copy_frame_has_lease
.import se_h_validate,se_clip_validate,se_reu_epoch
.import se_r_revision
.import se_gf_state
.export se_lc_preflight

.macro snapshot source,dest,n
 ldx #n-1
:
 lda source,x
 sta LC_P_IDENTITY+dest,x
 dex
 bpl :-
.endmacro
.macro object source,kind
 DOC_TOKEN source
 jsr se_object_validate
 jcs done
 lda object_owner,x
 cmp #kind
 jne shape_error
.endmacro
.segment "CODE"
se_lc_preflight:
 ; Read-only cheap gate FIRST. A File/style/fold/GEOS owner is opaque.
 lda se_e_job
 ora se_e_draw_busy
 ora se_e_redraw
 ora se_f_owner
 ora se_v_nav_busy
 ora se_n_owned
 ora se_l_active
 ora se_s_active
 ora se_s_owned
 ora se_diag_active
 ora se_diag_owned
 ora se_ef_active
 ora se_doc_busy
 ora se_doc_read_locks
 ora se_snapshot_busy
 ora se_hot_phase
 ora se_hot_owned
 ora se_h_phase
 ora se_h_owned_lease
 ora se_h_owned_capture
 ora se_h_owned_splice
 ora se_b_phase
 ora se_b_history_owned
 ora se_b_clip_owned
 ora se_clip_busy
 ora se_clip_copy_frame_has_object
 ora se_clip_copy_frame_has_lease
 ora se_input_nmi_pending
 ora $C6
 ora $98
 ora se_overlay_busy
 ora se_gf_state+5
 ora se_gf_state+8
 jne busy
 lda se_overlay_busy+1
.ifdef LC_PREFLIGHT_IN_C29
 cmp #1
 jne busy
.else
 jne busy
.endif
 ldx se_input_head
 cpx #64
 jcs state_error
 cpx se_input_tail
 jne busy
 lda se_status
 cmp #1
 jne state_error
 lda se_reu_retired
 jne state_error
 lda se_gf_state
 cmp #$A5
 jne state_error
 lda se_e_ui
 beq @source
 cmp #4
 jne busy
 lda se_mode
 cmp #3
 jne state_error
 lda se_r_presentation
 cmp #1
 jne state_error
 beq @mode
@source:
 lda se_r_presentation
 jne state_error
@mode:
 ldx se_mode
 cpx #4
 jcs state_error
 lda widths,x
 cmp se_v_columns
 jne state_error
 lda se_l_mode
 cmp #2
 jcs state_error
 lda se_l_manual
 cmp #2
 jcs state_error
 ldx #15
@binding:
 lda LC_P_BUILD,x
 cmp se_overlay_binding_digest,x
 jne build_error
 dex
 bpl @binding
 jsr se_doc_validate
 jcs done
 object se_doc_meta,3
 object se_doc_original,4
 object se_doc_append,4
 jsr se_h_validate
 jcs done
 jsr se_clip_validate
 jcs done
 ; Match all hot lifetime fields missing from the fast view_init guard.
 lda se_hot_ready
 cmp #1
 jne shape_error
 lda se_hot_pending
 cmp #2
 jcs shape_error
 ldx #4
@tokens:
 lda se_hot_original,x
 cmp se_doc_original,x
 jne shape_error
 lda se_hot_append,x
 cmp se_doc_append,x
 jne shape_error
 dex
 bpl @tokens
 ldx #1
@epochs:
 lda se_hot_epoch,x
 cmp se_doc_epoch,x
 jne shape_error
 lda se_hot_generation,x
 cmp se_doc_generation,x
 jne shape_error
 dex
 bpl @epochs
 ; Same geometry/arithmetic as source-context SHAPE, in private cold scratch.
 lda se_hot_right+1
 cmp #8
 jcc @ordered
 jne shape_error
 lda se_hot_right
 jne shape_error
@ordered:
 lda se_hot_left+1
 cmp se_hot_right+1
 jcc @length
 jne shape_error
 lda se_hot_left
 cmp se_hot_right
 jcc @length
 jne shape_error
@length:
 sec
 lda #0
 sbc se_hot_right
 sta LC_P_TEMP
 lda #8
 sbc se_hot_right+1
 sta LC_P_TEMP+1
 clc
 lda LC_P_TEMP
 adc se_hot_left
 sta LC_P_TEMP
 lda LC_P_TEMP+1
 adc se_hot_left+1
 cmp se_hot_length+1
 jne shape_error
 lda LC_P_TEMP
 cmp se_hot_length
 jne shape_error
 lda se_hot_old_length
 sta LC_P_TEMP
 lda se_hot_old_length+1
 sta LC_P_TEMP+1
 cmp #8
 jcc @old
 jne shape_error
 lda LC_P_TEMP
 jne shape_error
@old:
 lda #0
 sta LC_P_TEMP+2
 ADD24 se_hot_base,LC_P_TEMP,LC_P_END
 jcs shape_error
 CMP24 LC_P_END,se_doc_length
 jcc @merged
 jne shape_error
@merged:
 SUB24 se_doc_length,LC_P_TEMP,LC_P_LENGTH
 lda se_hot_length
 sta LC_P_TEMP
 lda se_hot_length+1
 sta LC_P_TEMP+1
 ADD24 LC_P_LENGTH,LC_P_TEMP,LC_P_LENGTH
 jcs shape_error
 lda se_hot_left
 sta LC_P_TEMP
 lda se_hot_left+1
 sta LC_P_TEMP+1
 ADD24 se_hot_base,LC_P_TEMP,LC_P_END
 jcs shape_error
 CMP24 LC_P_END,se_hot_caret
 jne shape_error
 ; Publication only after every checked source prerequisite. FS_FIELDS59,
 ; excluding caret/gap movement as a retained-fold key would do, is NOT enough
 ; for lifecycle: here full gap geometry is intentionally part of the witness.
 snapshot se_reu_epoch,0,2
 snapshot se_doc_epoch,2,2
 snapshot se_doc_generation,4,2
 snapshot se_doc_meta,6,5
 snapshot se_doc_original,11,5
 snapshot se_doc_append,16,5
 snapshot se_doc_length,21,3
 snapshot se_doc_root_count,24,1
 snapshot se_r_revision,25,4
 snapshot se_hot_ready,29,1
 snapshot se_hot_pending,30,1
 snapshot se_hot_phase,31,1
 snapshot se_hot_owned,32,1
 snapshot se_hot_fault,33,1
 snapshot se_hot_epoch,34,2
 snapshot se_hot_generation,36,2
 snapshot se_hot_original,38,5
 snapshot se_hot_append,43,5
 snapshot se_hot_base,48,3
 snapshot se_hot_old_length,51,2
 snapshot se_hot_length,53,2
 snapshot se_hot_left,55,2
 snapshot se_hot_right,57,2
 lda #0
 clc
done:rts
busy:lda #LC_P_BUSY
 sec
 rts
state_error:lda #LC_P_STATE
 sec
 rts
build_error:lda #LC_P_BUILD_ERROR
 sec
 rts
shape_error:lda #LC_P_SHAPE
 sec
 rts
.segment "RODATA"
widths:.byte 0,60,80,0
