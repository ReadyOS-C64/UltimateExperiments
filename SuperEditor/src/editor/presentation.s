.setcpu "6502"
.include "render/presentation.inc"
.import se_ef_valid
.segment "BSS"
.export se_render_caps
se_render_caps: .res 1
.segment "CODE"
.export se_ef_visible
; Published fold choices remain stored while Plain presents expanded source.
; Preserves C/X/Y like LDA absolute; A/N/Z describe effective projection state.
se_ef_visible:
    lda se_render_caps
    beq @raw
    lda se_ef_valid
@raw:
    rts
