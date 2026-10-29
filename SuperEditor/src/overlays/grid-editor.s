.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "platform.inc"
.include "editor/api.inc"
.include "document/api.inc"
.include "document/math24.inc"
.include "hot/api.inc"
.include "render/api.inc"
.include "layout/api.inc"
.include "block/api.inc"
.include "style/api.inc"
.include "render/narrow/grid.inc"
.include "render/grid/api.inc"
.include "render/grid/cache.inc"
NR_SIZE=68
NR_MODE=0
NR_ROW=1
NR_COUNT=2
NR_BACKGROUND=4
NR_BITMAP=5
NR_ATTRIBUTES=7
NR_FONT=9
NR_CHARACTERS=11
NR_ROLES=13
NR_FLAGS=15
NR_PALETTE=17
NR_SELECTED=2
NR_CARET=4
NR_INVERSE=1
BC_ROW=0
BC_COLUMN=1
BC_SCREEN=2
BC_FOREGROUND=3
BC_BACKGROUND=4
BC_FONT=5
BC_BITMAP=7
BC_ATTRIBUTES=9
.import tui_editor_chrome40,grid_mode
.ifndef EDITOR_OVERLAY
.import se_f_owner
.endif
.segment "CODE"
    OVL_BINDING
.export entry
entry:
    lda se_overlay_frame
    cmp #GRID_SOURCE
    jeq grid_source
    cmp #GRID_FINALIZE
    jeq grid_finalize
    cmp #GRID_MODE
    jeq grid_mode
    cmp #GRID_CHROME
    beq grid_chrome
    lda #$70
    sec
    rts
; Reuse the same linked micromodule for source grids and GEOS, including FILE
; owner1. No caller workspace/phase descriptor is read or initialized here.
grid_chrome:
    lda se_f_owner
    cmp #2
    bcs @busy
    jsr tui_editor_chrome40
    lda #0
    clc
    rts
@busy:
    lda #$B2
    sec
    rts
.include "render/grid/preflight.s"
.include "render/grid/source.s"
.include "render/grid/finalize.s"
SE_STYLE_CONTEXT_ONLY=1
.include "overlays/render-style.s"
