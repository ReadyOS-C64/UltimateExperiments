.setcpu "6502"
.export st_lex_phase
.segment "STYLE_STATE"
st_lex_phase:.res 1 ;0C14 owns line,1init,2scan/drain,3paint
