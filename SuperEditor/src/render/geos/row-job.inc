; Paired C22/R21 paint-only phase loans; no additional runtime allocation.
.ifndef RJ
RJ=$9040
.endif
RJ_COUNT=0
RJ_TOP=1 ;logical absoluteY16..191, nine rows clipped at192
RJ_X=2 ;signed-15..-1 or unsigned16-bit; offright consumes0
RJ_LEFT=4
RJ_RIGHT=6
RJ_CLIP_TOP=8 ;absolute16..192
RJ_CLIP_BOTTOM=9
RJ_MODE=10 ;0resetboth,1append samebands,2advanceoneband/carry oldH1
RJ_BACKGROUND=11
RJ_VALID=16
RJ_DONE=17
RJ_NEXT_X=18
RJ_LAST_BAND=20
RJ_PRIVATE=32
RJ_CHARS=$4400
RJ_STYLES=$44A2
RJ_ROLES=$4544
RJ_FLAGS=$45E6
RJ_MAP=$4688 ;162words, ends47CCexclusive
RJ_PALETTE=$47D0 ;14bytes, readonly
.ifndef RJ_H0
RJ_H0=$88E2
.endif
.ifndef RJ_H1
RJ_H1=$8D00 ;560B second-band votes, ends8F30exclusive
.endif
