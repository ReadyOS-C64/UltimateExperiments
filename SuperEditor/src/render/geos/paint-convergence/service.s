.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "api.inc"
.include "convergence-witness.inc"
.import image_size_lo,image_size_hi,image_crc_lo,image_crc_hi
.assert CV_C21_SIZE=$1000,error,"compact C21 witness requires full4KiB"
.include "render/geos/caret-cache.inc"
.include "render/geos/edit-certificate.inc"
.include "document/math24.inc"
.import se_f_owner,se_mode,se_render_caps,se_r_presentation,se_sel_mark,se_ef_valid
.import se_l_mode,se_l_pan,se_l_manual,se_e_ui,se_e_error,se_h_fault,se_h_phase
.import se_gc_handle,se_gc_epoch,se_reu_epoch,se_reu_map,se_reu_retired
.import se_e_draw_sequence,se_r_revision,se_v_length,se_hot_command,se_hot_caret
.import se_hot_ready,se_hot_pending,se_hot_phase,se_hot_owned,se_hot_delete,se_hot_left,se_hot_right,se_hot_base,se_hot_length
.import se_doc_meta,se_doc_generation,se_doc_epoch,se_v_top
.import se_crc_init,se_crc_byte,se_crc_value,se_bc_flags,se_overlay_binding_digest
.import se_rg_capture_source,se_rg_check_source
.import se_gp_cache_guard,se_gp_cache_read,se_gp_cache_write,se_gp_cache_slot
.importzp text_ptr
.export entry
.segment "CODE"
 OVL_BINDING
entry:
 lda se_f_owner
 cmp #4
 bne busy
 ; Bind the producer protocol to this exact verified C21 image, independent
 ; of a shared resident binding. Old C21/new R63 refuses before phase access.
 lda image_size_hi+CV_C21_INDEX
 eor #>CV_C21_SIZE
 ora image_size_lo+CV_C21_INDEX
 bne argument
 lda image_crc_lo+CV_C21_INDEX
 cmp #<CV_C21_CRC
 bne argument
 lda image_crc_hi+CV_C21_INDEX
 cmp #>CV_C21_CRC
 bne argument
 lda se_overlay_frame
 cmp #5
 jeq bcq_capture_page
 cmp #0
 jeq attempt
 ; R28 owns these same47 bytes on its accepted local path. Its phase selector
 ; cannot be our exact collector marker; never initialize/clobber that job.
 ldx GP_CONTROL+20
 cpx #2
 bne :+
 ldx CV_COLLECT
 cpx #$A6
 jne zero
:cmp #1
 jeq snapshot
 cmp #3
 jeq complete
 cmp #4
 jeq certify
 bne argument
busy:lda #$B2
 sec
 rts
zero:lda #0
 clc
 rts
miss:
 lda #0
 sta CV_ACTIVE
 clc
 rts
argument:lda #$90
 sec
 rts
.include "transaction.s"
BCQ_EDITOR_ACTIVE=1
BCQ_PAGE_REUSE=1
BCQ_PROOF_CAPTURE=1
.include "cache/query/proof.inc"
