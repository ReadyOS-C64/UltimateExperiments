.ifndef SE_CACHE_REKEY_PROBE
SE_CACHE_REKEY_PROBE=1
.include "cache/api.inc"
RK=BC_FRAME
RK_ABI=RK
RK_STATE=RK+1
RK_ERROR=RK+2
RK_LIVE=RK+3
RK_AUTH=RK+8 ;live token5/ticket4/incarnation4 order
RK_HEAD=RK+21
RK_TAIL=RK+22
RK_COUNT=RK+23
RK_SLOT=RK+24
RK_DEST=RK+27
RK_ROOT=RK+32 ;128-byte checked root snapshot
RK_WORK=RK+160 ;three24-bit temporaries; dead before writer publication
RK_READER=RK+173 ;86-byte actual R14 context, resident-cancel compatible
RK_EVENT=RK+259 ;32-byte immutable producer-event snapshot
RK_PHASE_OPEN=1
RK_PHASE_SOURCE=2
RK_PHASE_JOURNAL=3
RK_PHASE_JVALID=4
RK_PHASE_ROOT=5
RK_PHASE_VALID=6
.endif
