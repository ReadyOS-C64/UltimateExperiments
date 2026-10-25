; Included once at the end of C10 BLOCK, after its common API/math includes.
; BEGIN/STEP are private to this image: invoking the public resident trampoline
; from C10 would attempt forbidden same-slot nesting. All error cleanup remains
; resident and callable after an asset failure or cancellation.
CLIP_COPY_CODE=1
.export se_clip_overlay_copy_begin,se_clip_overlay_copy_step
.define se_clip_copy_begin se_clip_overlay_copy_begin
.define se_clip_copy_step se_clip_overlay_copy_step
.include "clipboard/copy.s"
.undefine se_clip_copy_begin
.undefine se_clip_copy_step
