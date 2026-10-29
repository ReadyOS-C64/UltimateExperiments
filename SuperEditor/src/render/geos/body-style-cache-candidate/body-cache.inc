; Private R24 actual-C26 160-cell result cache. No BSS/ZP/asset/bank.
.ifndef BODY_STYLE_CACHE
BODY_STYLE_CACHE=1
BSC_LOOKUP=3
BSC_STORE=4
BSC_COUNT=5
BSC_CANCEL=6
BSC_REU=$FC00              ;512-byte reservation, live record416 only
BSC_BUFFER=$8600           ;416B DOC_LEAF scratch, invalidated before use
BSC_SIZE=416
BSC_VALID=0
BSC_VERSION=1
BSC_MAGIC=2
BSC_COUNT_AT=3
BSC_START=4                ;3B canonical start of actualC26outputwindow
BSC_KEY=7                  ;59B complete R14source identity
BSC_CONTEXT=66             ;10B GSEM START/END/BODY/ROLE
BSC_CAP=76                 ;logicalFE,physicalFE,provider epoch2
BSC_PRODUCER=82            ;actualC26 size2+CRC2, changes revoke cachedresult
BSC_CRC=80                 ;CCITT-FALSE, excludes VALID and these2 bytes
BSC_STYLES=96              ;160 actualC26styles
BSC_ROLES=256              ;160 actualC26roles
BSC_WORK=$45A0             ;8B otherwiseunowned ledger suffix, never continuation
BW_OP=BSC_WORK
BW_INDEX=BSC_WORK+1        ;2B
BW_CRC=BSC_WORK+3          ;2B expected CRC
BW_COUNT=BSC_WORK+5
BW_OFFSET=BSC_WORK+6
BW_ERROR=BSC_WORK+7
.assert BSC_ROLES+160=BSC_SIZE,error,"body style extent"
.assert BSC_REU+BSC_SIZE<=$FE00,error,"body style outside reserved512B"
.assert BSC_BUFFER+BSC_SIZE<=$8800,error,"body cache scratch outside docleaf"
.endif
