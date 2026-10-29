.ifndef SE_LC_PREFLIGHT_INC
SE_LC_PREFLIGHT_INC=1
; Independent admission component, NOT a PREPARE/RESUME implementation.
; Input: trusted expected resident binding16 at0800. No allocation or lease.
; Output on success: actual FS_FIELDS59 witness at0C40; merged length0C80.
; Scratch0C80..0C8F; object foreground request/validator scratch may change.
; No phase reads/writes, BSS/ZP, source or REU mutation. Nonreentrant.
; Default entry expects both overlay slots idle (direct callable fixture).
; LC_PREFLIGHT_IN_C29=1 expects only its own C busy1 and R busy0 instead.
LC_P_BUILD=$0800
LC_P_IDENTITY=$0C40
LC_P_LENGTH=$0C80
LC_P_TEMP=$0C83
LC_P_END=$0C86
LC_P_TYPE=$0C89
LC_P_BUSY=$D5
LC_P_STATE=$D6
LC_P_BUILD_ERROR=$D8
LC_P_SHAPE=$D9
.endif
