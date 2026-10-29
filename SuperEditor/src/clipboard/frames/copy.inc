; Persistent COPY frame: original field order and30-byte OBJECTS footprint.
; Default/CLIP_COPY_CLEANUP_ONLY allocates it. C10 imports exact resident aliases
; from editor-api.inc; no pointer into an executable slot survives a work slice.
.ifdef CLIP_COPY_CODE
copy_token = se_clip_copy_frame_token
copy_has_object = se_clip_copy_frame_has_object
copy_has_lease = se_clip_copy_frame_has_lease
copy_epoch = se_clip_copy_frame_epoch
copy_generation = se_clip_copy_frame_generation
copy_pos = se_clip_copy_frame_pos
copy_left = se_clip_copy_frame_left
copy_written = se_clip_copy_frame_written
copy_size = se_clip_copy_frame_size
copy_end = se_clip_copy_frame_end
copy_chunk = se_clip_copy_frame_chunk
copy_error = se_clip_copy_frame_error
copy_abort = se_clip_copy_abort
copy_cleanup = se_clip_copy_cleanup
.else
.segment "OBJECTS"
copy_token: .res 5
copy_has_object: .res 1
copy_has_lease: .res 1
copy_epoch: .res 2
copy_generation: .res 2
copy_pos: .res 3
copy_left: .res 3
copy_written: .res 3
copy_size: .res 3
copy_end: .res 3
copy_chunk: .res 3
copy_error: .res 1
.ifdef CLIP_COPY_CLEANUP_ONLY
.export se_clip_copy_frame_token, se_clip_copy_frame_has_object
.export se_clip_copy_frame_has_lease, se_clip_copy_frame_epoch
.export se_clip_copy_frame_generation, se_clip_copy_frame_pos
.export se_clip_copy_frame_left, se_clip_copy_frame_written
.export se_clip_copy_frame_size, se_clip_copy_frame_end
.export se_clip_copy_frame_chunk, se_clip_copy_frame_error
se_clip_copy_frame_token = copy_token
se_clip_copy_frame_has_object = copy_has_object
se_clip_copy_frame_has_lease = copy_has_lease
se_clip_copy_frame_epoch = copy_epoch
se_clip_copy_frame_generation = copy_generation
se_clip_copy_frame_pos = copy_pos
se_clip_copy_frame_left = copy_left
se_clip_copy_frame_written = copy_written
se_clip_copy_frame_size = copy_size
se_clip_copy_frame_end = copy_end
se_clip_copy_frame_chunk = copy_chunk
se_clip_copy_frame_error = copy_error
.endif
.endif
