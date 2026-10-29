.setcpu "6502"
.export se_ej_position,se_ej_delete,se_ej_insert,se_ej_count,se_ej_status,se_ej_ticket
.export se_ej_generation,se_ej_length
.segment "VIEWSTATE"
se_ej_position: .res 3
se_ej_delete: .res 3
se_ej_insert: .res 3
se_ej_count: .res 1
se_ej_status: .res 1
se_ej_ticket: .res 4
.assert *-se_ej_position=15,error,"journal VIEW state15"
.segment "BSS"
se_ej_generation: .res 2
se_ej_length: .res 3
