.setcpu "6502"
.ifndef DOS64_FILE_DIAGNOSTICS
DOS64_FILE_DIAGNOSTICS=0
.endif
.if DOS64_FILE_DIAGNOSTICS
.export _sf_name,_sf_op,_sf_code,_sf_leaf,_sf_transport
.segment "HIGHBSS"
_sf_name:.res 10
_sf_op:.res 1
_sf_code:.res 1
_sf_leaf:.res 1
_sf_transport:.res 1
.endif
