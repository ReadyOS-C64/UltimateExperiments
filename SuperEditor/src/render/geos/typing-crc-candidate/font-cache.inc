.ifndef SE_TYPING_FONT_CACHE
SE_TYPING_FONT_CACHE=1
GTF_ID=30                  ;C30 slot1; distinct from R30 typing slot0
GTF_BEGIN=0
GTF_STEP=1
GTF_CANCEL=2
GTF_DATA=$E568              ;128*9 glyphbytes, screen-code indexed
GTF_WIDTHS=$E9E8            ;128 screen-code widths
GTF_META=$EA68              ;32B READY/build/fontwitness
GTF_FRAME=$8B40             ;77-byte actual GGframe
GTF_CONTROL=$8BA0           ;exclusiveowner4, no residentBSS
GTF_PHASE=GTF_CONTROL
GTF_INDEX=GTF_CONTROL+1
GTF_BLOCK=GTF_CONTROL+2
GTF_CRC=GTF_CONTROL+3       ;2 persisted across loader admissions
GTF_BUFFER=$9000            ;256B bounded transfer/readback
.assert GTF_CONTROL+5<=$8C00,error,"fontcontrol outsideprivatephase"
.assert GTF_META+32<=$10000,error,"fontcache exceedsFEtail"
.endif
