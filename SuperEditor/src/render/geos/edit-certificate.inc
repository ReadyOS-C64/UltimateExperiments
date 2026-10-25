; One exact C6 mutation relative to the last published GEOS source page.
; This is an admission witness, never an aggregate damage-range substitute.
.ifndef SE_GEOS_EDIT_CERTIFICATE
SE_GEOS_EDIT_CERTIFICATE=1
.include "render/geos/caret-cache.inc"
GEC_RECORD=$CFE8
GEC_VALID=GEC_RECORD
GEC_OP=GEC_RECORD+1 ;0 insert,1 delete (BACK has already moved the gap/caret)
GEC_POSITION=GEC_RECORD+2 ;3 canonical bytes
GEC_OLD=GEC_RECORD+5
GEC_NEW=GEC_RECORD+6
GEC_REVISION=GEC_RECORD+7 ;4 before the mutation
GEC_LENGTH=GEC_RECORD+11 ;3 old merged length
GEC_SEQUENCE=GEC_RECORD+14 ;2 last complete page publication
GEC_DOC_EPOCH=GEC_RECORD+16 ;2
GEC_REU_EPOCH=GEC_RECORD+18 ;2
GEC_END=GEC_RECORD+20
.assert GEC_RECORD>=GCC_STATE+88,error,"edit certificate overlaps caret/UI scratch"
.assert GEC_END<=$D000,error,"edit certificate exceeds warm extent"
.endif
