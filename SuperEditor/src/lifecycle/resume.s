.setcpu "6502"
.macpack longbranch
.include "lifecycle/resume.inc"
.import se_overlay_busy,se_overlay_active,se_overlay_frame,se_overlay_call
.ifdef EDITOR_MANAGED_CODE
.import se_overlay_unverify
.endif
.import se_input_head,se_input_tail,se_input_nmi_pending,se_input_irq_ticks,se_input_backpressure
.import se_doc_invalidate,se_v_cache_count,se_i_ready,se_v_nav_busy
.import se_l_valid,se_l_active,se_l_need_wrap,se_r_valid,se_r_damage_valid
.import se_st_valid,se_st_request,se_st_cp_valid,se_gc_valid,se_gf_state
.import se_ef_fold_rows
.import se_e_job,se_e_draw_busy,se_e_redraw,se_f_owner,se_status,se_e_error,se_idle
.import se_display_init,se_mode
.export se_lc_resume_entry,se_lc_warm_hardware,se_lc_driver_entry
.segment "RESUME"
se_lc_resume_entry:
 sei
 cld
 ldx #$FF
 txs
 lda $00
 ora #7
 sta $00
 lda $01
 and #$F8
 ora #6
 sta $01
 lda #0
 sta LC_PHASE
 sta se_overlay_busy
 sta se_overlay_busy+1
 sta se_overlay_active
 sta se_overlay_active+1
 sta se_input_head
 sta se_input_tail
 sta se_input_nmi_pending
 sta se_input_irq_ticks
 sta se_input_irq_ticks+1
 sta se_input_backpressure
 sta $C6
 sta se_v_cache_count
 sta se_v_cache_count+1
 sta se_i_ready
 sta se_v_nav_busy
 sta se_l_valid
 sta se_l_active
 sta se_r_valid
 sta se_r_damage_valid
 sta se_st_valid
 sta se_st_request
 sta se_st_cp_valid
 sta se_gc_valid
 sta se_gc_valid+1
 sta se_gc_valid+2
 sta se_gf_state+21
 sta se_ef_fold_rows
 sta se_ef_fold_rows+1
 sta se_ef_fold_rows+2
 sta $CF00 ;GFQ_ACTIVE is disposable; never inspect an old phase
 sta $CF90 ;GCC_VALID cannot survive a hardware/matrix reset
 sta $CFE8 ;C6edit certificate is derived, never a warm continuation
 sta $CC00 ;preview worker phase, not preview history
 sta se_e_job
 sta se_e_draw_busy
 sta se_f_owner
.ifdef EDITOR_MANAGED_CODE
 jsr se_overlay_unverify ;disarm restored catalog before any execution
.endif
 jsr se_doc_invalidate
 lda #1
 sta se_l_need_wrap
 sta se_overlay_frame
 ; C29HARDWARE does not reset top/pan/preferred/mode/presentation/folds.
 lda #LC_HARDWARE
 sta se_overlay_frame
 lda #LC_CONTROLLER_ID
 ldx #1
 jsr se_overlay_call
 bcc @ready
 sta se_e_error ;restored canonical state remains available for retry
@ready:
 lda #1
 sta se_e_redraw
 sta se_status
 cli
 jmp se_idle
.assert se_lc_resume_entry=LC_RESUME,lderror,"fresh prelude mustrun0A00"
.assert *<=LC_DRIVER,lderror,"fresh prelude overlaps0AE0callable driver"
.res LC_DRIVER-LC_RESUME-(*-se_lc_resume_entry),0
se_lc_driver_entry:
 sta se_overlay_frame
 lda #LC_CONTROLLER_ID
 ldx #1
 jmp se_overlay_call
.assert se_lc_driver_entry=LC_DRIVER,lderror,"callable driver mustrun0AE0"
.assert *<=LC_RESUME_END,lderror,"fresh prelude/driver exceeds0A00page"
.segment "CODE"
se_lc_warm_hardware:
 jsr se_display_init
 lda se_mode
 beq @ready
 cmp #4
 bcs @bad
 cmp #3
 beq @geos
 cmp #1
 beq @sixty
 lda #16
 bne @grid
@sixty:lda #17
@grid:
 pha
 lda #2 ;GRID_ADMIT no writes
 sta se_overlay_frame
 pla
 ldx #0
 jsr se_overlay_call
 bcs @done
 jmp @bitmap
@geos:
 lda #4
 sta se_f_owner
 lda #1 ;R21 ADMIT owneronly
 sta se_overlay_frame
 lda #21
 ldx #0
 jsr se_overlay_call
 php
 pha
 lda #0
 sta se_f_owner
 pla
 plp
 bcs @done
@bitmap:
 lda #$3B
 sta $D011
 lda #8
 sta $D016
 sta $D018
 lda #0
 sta $D015
@ready:
 lda #0
 clc
@done:rts
@bad:
 lda #LC_E_STATE
 sec
 rts
; Link this object last among C29code/data objects. The fixed CONTROL memory
; region independently rejects any overflow even if future objects are added.
.segment "RODATA"
.assert *<=LC_RESUME_TEMPLATE,lderror,"C29code+RODATA overlaps freshB800template"
