; Private mapped INLINE worker. No new global capability/proof flags.
.include "cache/splice-query-probe/api.inc"
I_REF=S+64
I_COUNT=S+68
I_NEXT=S+71
I_SLOTS=S+75
I_INDEX=S+76
I_RETURN=S+77 ;20 SOURCE,21 normal producer
I_PHASE=S+78
I_STYLE=S+79
I_BUDGET=S+80
I_REL=S+81
I_POS=S+84
I_FROM=S+87
I_TO=S+90
.assert I_TO+3<=S+94,error,"private inline control/unused parser boundary"
IS=$8880
IR=IS+161
IH=IR+161
IP=IH+21

I_READ_PROOF=64 ;private scoped revocation bit reserved by root, never BCQP
