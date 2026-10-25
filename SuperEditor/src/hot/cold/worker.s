.setcpu "6502"
EDITOR_BINDINGS=1
.macpack longbranch
.include "editor-api.inc"
.include "hot/api.inc"
.include "document/api.inc"
.include "object/api.inc"
.include "document/math24.inc"
.include "history/api.inc"
; R32 performs cold window loading and flush preparation. No R calls, no
; phase-union storage, no additional state/ZP. C6 stays loaded for hot edits.
.segment "CODE"
 OVL_BINDING
.export entry
entry:
 lda se_overlay_frame
 sta se_hot_command
 cmp #W_LOAD
 jeq load
 jsr valid
 jcs return
 lda se_hot_command
 cmp #W_STEP
 jeq load_step
 lda se_hot_phase
 cmp #2
 bne :+
 lda se_hot_command
 cmp #W_PACKET
 jeq packet
 jmp busy
:
 lda se_hot_phase
 jne busy
 lda se_hot_ready
 jeq state
 lda se_hot_command
 cmp #W_PREPARE
 jeq prepare
 jmp state
okay:
 lda #0
 clc
return:
 rts
pending:
 lda #1
 clc
 rts
state:
 lda #$70
 sec
 rts
busy:
 lda #$71
 sec
 rts
boundary:
 lda #$72
 sec
 rts
context:
 lda #$74
 sec
 rts
.include "hot/validate.s"
.include "hot/cold/load.s"
.include "hot/cold/prepare.s"
.include "render/api.inc"
.include "cache/observer/flush.inc"
