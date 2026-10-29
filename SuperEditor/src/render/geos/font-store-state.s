.setcpu "6502"
.include "render/geos/font-store.inc"
.export se_gf_state
.segment "FONT_STORE_STATE"
se_gf_state: .res GF_STATE_SIZE
.assert se_gf_state=$CBC0,lderror,"font store descriptor moved"
