.setcpu "6502"
.include "style/api.inc"
; Suffix only; root links after existing VIEWSTATE and clears all256 on boot.
.segment "VIEWSTATE"
se_st_cache_generation:.res 2
se_st_cache_valid:.res 1
