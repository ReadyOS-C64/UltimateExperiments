.ifndef SE_FOLD_TRANSFORM_API
SE_FOLD_TRANSFORM_API=1
.include "fold/api.inc"
FT_INVALID=1
FT_CONTAINING=4
FT_SHIFTED=8
; Dense HINT output only: ALWAYS fresh-parse and identity/ancestry match before
; transferring COLLAPSED. Never publish this map directly. SF_LINES is carried
; only as stale metadata and MUST NOT participate in edited retention identity.
; Opener-intersecting or end-crossing deletions drop that record+descendants.
; Insertion at SUMMARY shifts whole record; at HIDDEN is body; at END outside.
; Body edits adjust END, including potential closing-line changes: fresh parse
; must validate closure/identity. SAVED/caret/motion always clear in hints.
; BEGIN/STEP A1 pending/A0 complete/Cclear, A error/Cset; CANCEL A0/Cclear.
; STEP <=one32B read+one32B write; VALID only at full completion. On error or
; cancellation partial output is disposable, objects remain caller-owned.
; Every BEGIN authenticates distinct type46 objects/capacity and rejects any
; physical-bank overlap. Every STEP rechecks immutable input fields, full typed
; tokens/extents/provider epoch. Canonical edit provenance/source lease is the
; caller's responsibility; this helper neither reads nor writes source bytes.
; BEGIN_LOG additionally takes LOG_POINTER (8000..87FF) and LOG_COUNT1..112.
; Packed events9B are position24/delete24/insert24 in sequential canonical
; coordinates. Entire pointer+count span must fit8000..87FF. Caller guarantees
; those host bytes immutable through the job; descriptor/mode bound everySTEP.
; Admission validates one event/STEP before any candidate write. Then one
; source record is read, each edit applies in its own STEP, final record writes
; once. PHASE1 validateLog/2readRecord/3applyEvent, LOG_EVENT is zero-based.
; POSITION/DELETE/INSERT become internal event scratch in log mode. NEW_LENGTH
; is final only after validation/completion. No intermediate REU objects.
; Private caller-owned phase suffix. No storage or ZP is allocated. The caller
; must exclusively own this entire frame and both objects for the whole job.
.ifndef FT_FRAME
FT_FRAME=$8FE4
.endif
se_ft_input=FT_FRAME
se_ft_output=FT_FRAME+5
se_ft_count=FT_FRAME+10
se_ft_length=FT_FRAME+12
se_ft_position=FT_FRAME+15
se_ft_delete=FT_FRAME+18
se_ft_insert=FT_FRAME+21
FT_INPUT_SIZE=24
se_ft_busy=FT_FRAME+24
se_ft_error=FT_FRAME+25
se_ft_valid=FT_FRAME+26
se_ft_index=FT_FRAME+27
se_ft_written=FT_FRAME+29
se_ft_dropped=FT_FRAME+31
se_ft_changed=FT_FRAME+33
se_ft_new_length=FT_FRAME+34
se_ft_delete_end=FT_FRAME+37
se_ft_epoch=FT_FRAME+40
se_ft_bound=FT_FRAME+42
se_ft_record=FT_FRAME+66
se_ft_parents=FT_FRAME+98
se_ft_old_indices=FT_FRAME+130
se_ft_ends=FT_FRAME+162
se_ft_hidden=FT_FRAME+210
se_ft_last=FT_FRAME+258
se_ft_previous_depth=FT_FRAME+261
se_ft_disposition=FT_FRAME+262
se_ft_temp=FT_FRAME+263
se_ft_in_banks=FT_FRAME+266
se_ft_out_banks=FT_FRAME+267
se_ft_outer=FT_FRAME+268
se_ft_inner=FT_FRAME+269
se_ft_physical=FT_FRAME+270
se_ft_current_parent=FT_FRAME+271
se_ft_in_logical=FT_FRAME+273
se_ft_out_logical=FT_FRAME+289
se_ft_in_physical=FT_FRAME+305
se_ft_out_physical=FT_FRAME+321
se_ft_map_counts=FT_FRAME+337
se_ft_log_pointer=FT_FRAME+339
se_ft_log_count=FT_FRAME+341
se_ft_log_mode=FT_FRAME+342
se_ft_phase=FT_FRAME+343
se_ft_log_bound=FT_FRAME+344
se_ft_log_cursor=FT_FRAME+348
se_ft_log_event=FT_FRAME+350
se_ft_log_byte=FT_FRAME+351
se_ft_work_length=FT_FRAME+352
se_ft_final_length=FT_FRAME+355
se_ft_frame_end=FT_FRAME+358
FT_FRAME_SIZE=358
FT_VALIDATE_LOG=1
FT_READ=2
FT_APPLY=3
.assert FT_FRAME_SIZE<=412,error,"transform phase suffix exceeds917F"
.assert se_ft_frame_end<=$9180,error,"transform overlaps next phase"
.ifndef SE_FOLD_TRANSFORM_IMPLEMENTATION
.import se_ft_begin,se_ft_begin_log,se_ft_step,se_ft_cancel
.endif
.endif
