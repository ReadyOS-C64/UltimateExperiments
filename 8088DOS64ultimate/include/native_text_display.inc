.ifndef DOS64_NATIVE_TEXT_DISPLAY_INC
DOS64_NATIVE_TEXT_DISPLAY_INC = 1
; Setup/restore own VIC bitmap state and CIA2 bank pins; no CIA timer access.
; Saved fields: ready, D011 low7, D016, D018, D015, D020, D021, PRA, DDRA.
ND_READY=0
ND_D011=1
ND_D016=2
ND_D018=3
ND_D015=4
ND_D020=5
ND_D021=6
ND_PRA=7
ND_DDRA=8
ND_SIZE=9
.endif
