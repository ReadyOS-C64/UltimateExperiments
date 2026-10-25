.ifndef SE_SAVE_API
SE_SAVE_API=1
; State is also the next operation to perform. Each operation returns to resident
; dispatch; no pointers into overlays or open IEC selection survive a step.
SV_IDLE=0
SV_CREATE=1
SV_WRITE=2
SV_CLOSE=3
SV_OPEN_VERIFY=4
SV_COMPARE=5
SV_CLOSE_VERIFY=6
SV_BACKUP=7
SV_PROMOTE=8
SV_CHECK_TARGET=9
SV_DELETE_BACKUP=10
SV_DONE=11
SV_ABORT_CLOSE=12
SV_DELETE_TEMP=13
SV_ROLLBACK=14
SV_RECOVERY=15
; Caller must distinguish a definite refusal from a lost command acknowledgement.
SV_CANCEL=0
SV_OK=1
SV_FAILED=2
SV_MATCH=3
SV_MISMATCH=4
SV_UNCERTAIN=5
.global se_sv_begin,se_sv_step,se_sv_phase,se_sv_had_target,se_sv_error
.endif
