; Checked paint convergence. Descriptor is never a semantic checkpoint.
.include "render/geos/edit-cache.inc"
CV=GEX_STATE
; R28 always clears GEX_PHASE before any admission scratch write. Keeping the
; collector marker there revokes its loan even when R28 rejects before ROW.
CV_COLLECT=CV
CV_ACTIVE=CV+1
.assert CV_COLLECT=GEX_PHASE,error,"collector must follow R28 phase handoff"
CV_ROWS=CV+2
CV_LINE=CV+3
CV_MIN=CV+5
CV_MAX=CV+6
CV_REMAIN=CV+7
CV_OFFSET=CV+9
CV_LENGTH=CV+11
CV_DIFFERENT=CV+13
CV_INDEX=CV+14
CV_EXPECT=CV+15
CV_CERT=$DD68
CV_NEXT=$DE68
CV_PACKET=$D568
CV_DATA=$8600
CV_OTHER=$8400
CV_CHUNK=$8080
CV_SIZE=240
CV_SOURCE=67
CV_CRCS=126
CV_HEADER=170
CV_CRC=238
CV_IDENTITY=$8DA0
.assert CV_PACKET+842<CV_CERT,error,"convergence packet/certificate overlap"
.assert CV_NEXT+256<GEX_TAIL_END,error,"convergence descriptor beyond reservation"
CV_SLOT=CV+17
CV_HEADERCRC=CV+19
CV_HANDLE=CV+22
CV_PHYSICAL=CV+23
CV_EPOCH=CV+24
CV_CAPS=CV+26
CV_CERT_CRC=CV+27

CV_DELTA=CV+29
CV_SCREEN=CV+33
CV_SKIP_FIRST=CV+36
CV_SKIP_END=CV+37
CV_VIC=CV+38
CV_CHECK=CV+40
CV_BITMAP=CV+41
CV_ATTR=CV+43

CV_COUNT=CV+4
CV_FIELD=CV+45

CV_OLD_COUNT=CV+46

CV_BACKUP=CV+27
CV_BUDGET=CV+21
