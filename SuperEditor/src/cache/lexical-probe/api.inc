; PRIVATE lexical-page vertical slice. No editor/root lexical completeness claim.
.ifndef CACHE_LEXICAL_PROBE
CACHE_LEXICAL_PROBE=1
.include "cache/api.inc"
LX=BC_FRAME
LX_STATE=LX+1
LX_ERROR=LX+2
LX_LIVE=LX+3
LX_READY=LX+4                 ;1 span7 atIO,2 FINISH barrier; ACK releases2
LX_CAPS=LX+5
LX_LANGUAGE=LX+6
LX_BODY=LX+21
LX_END=LX+24
LX_INDEX=LX+27
LX_USED=LX+28
LX_FINISHED=LX+29
LX_BUDGET=LX+30
LX_TEMP=LX+31                 ;24bit
LX_FEEDS=LX+41                ;24bit accepted bytes
LX_EVENTS=LX+44               ;16bit (single-page capacity is bounded below)
LX_READS=LX+47                ;24bit actual32-byte reads
LX_AUTH=LX+66                 ;live arena5/ticket4/incarnation4
LX_PARSER=LX+94               ;actual60B se_sl
LX_PARK=LX+154                ;13B BEGIN transition parking, dead afterinit
LX_READER=LX+173              ;actual86B countedR14 sourcecontext
LX_PACKET=LX+259              ;32B sourcepacket
LX_CR=LX+291                  ;actualC35-produced96B record
LX_OUTPUT=BC_IO
LX_ROLES=$8200                ;caller-owned128B provisional consumer output
LX_READER_LIVE=1
LX_BAD=$90
LX_CHANGED=$B1
LX_BUSY=$B2
LEX_DESC_BYTES=96
LEX_SPAN_BYTES=7
LEX_SPAN_LIMIT=562            ;96+562*7=4030 <=4032
.endif
