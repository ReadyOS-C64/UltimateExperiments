; Sequential semantic batch, no editor/display dependency. Caller owns owner4.
.ifndef SE_CACHE_SEMANTIC_API
SE_CACHE_SEMANTIC_API=1
.include "cache/api.inc"
BSC_ABI=1
BSC_REBUILD=$80             ;BCF_BUDGET bit7, fresh unarmed rebuild only
BSC_RECORD=1
BSC_INLINE=2
BSC_BLOCK=1
BSC_BODY=2
BSC_FINISH=3
BSC_NEXT=4
BSC_EOF=5
BSC_BAD=$90
BSC_CHANGED=$B1
BSC_BUSY=$B2
BSC_F=BC_FRAME
BSC_PARSER=BC_FRAME+BCF_PARSER
BSC_READER=BC_FRAME+BCF_READER
BSC_PACKET=BC_FRAME+BCF_PACKET
BSC_CR=BC_FRAME+BCF_CR
BSC_CURSOR=BC_FRAME+21       ;absolute24, block scan or inline BODY scan
BSC_INDEX=BC_FRAME+24
BSC_USED=BC_FRAME+25
BSC_NEXT_SOURCE=BC_FRAME+26  ;absolute24 next real logical line
BSC_CARRY=BC_FRAME+29        ;incoming fence/lang/regions/overflow24
BSC_END=BC_FRAME+35          ;absolute24 current END excludingCR
BSC_TEMP=BC_FRAME+38         ;24bit arithmetic
BSC_BLOCK_FEEDS=BC_FRAME+41  ;actual accepted sourcebytes,24bit counters
BSC_INLINE_FEEDS=BC_FRAME+44
BSC_READS=BC_FRAME+47
BSC_LINES=BC_FRAME+50
BSC_EVENTS=BC_FRAME+53
BSC_BODY_SCANS=BC_FRAME+56
BSC_TERMINAL=BC_FRAME+59     ;unterminated real event / EOF sentinel
BSC_AT_EOF=BC_FRAME+60
BSC_AUTH=BC_FRAME+66         ;immutable arena5/incarnation4/ticket4
BSC_LENGTH=BC_FRAME+79      ;actual frozen merged source length24
BSC_READER_LIVE=1
.global se_bsc_begin,se_bsc_step,se_bsc_ack,se_bsc_cancel
.endif
