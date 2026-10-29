; R25 pure virtual CR/fold-summary policy. No source/layout/cache calls.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/geos/editor.inc"
.include "render/geos/page-paint.inc"
S=GPP_STATE
R=S+$20
source=S+$42
lo=S+$48
hi=S+$4B
want=S+$9E
flags=S+$9F
char=S+$5D
role=S+$5E
.segment "CODE"
 OVL_BINDING
.export entry
entry:
 lda se_f_owner
 cmp #4
 jne busy
 lda se_overlay_frame
 jne selection_bounds
.include "render/geos/tail-policy.inc"
busy:
 lda #$B2
 sec
 rts
