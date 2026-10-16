.ifndef DOS64_NATIVE_SAVE_INC
DOS64_NATIVE_SAVE_INC=1
; Development command ABI, body first then command publish. SAVE only from
; coherentPAUSED5 with owned new path; pending ACK0, finalA5/E1. During stage7
; only CANCEL9 is accepted; unrelated requests reject without touching UCI.
; Known-closed failure may remainPAUSED/dirty; unknown or infrastructure fault
; enters E1 and RUN3 cannot resume. Standard commands1..4 remain unchanged.
NATIVE_SAVE_COMMAND=7
NATIVE_SAVE_CANCEL=9
NATIVE_SAVE_STAGE=7
.endif
