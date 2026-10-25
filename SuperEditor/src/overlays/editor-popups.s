; R22 stateless ReadyOS popup micro module. Operation0 draws current menu/help/
; diagnostics from resident UI state; it receives no pointers into caller C7.
; UI draw includes and box40 remain unchanged. FILE owner1 has its own AUX popup.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "platform.inc"
.include "editor/api.inc"
.include "render/geos/settings.inc"
.segment "CODE"
    OVL_BINDING
.export entry
entry:
    lda se_e_menu
    cmp #8
    jeq settings_popup
    jmp se_ui_draw
.include "overlays/editor-ui-draw.s"
.include "diagnostics/ui.s"

.include "overlays/editor-settings-draw.s"
