.ifndef SE_SUPERMARK_API
SE_SUPERMARK_API = 1
SM_ABI_VERSION=1
; Pure semantic API: no VIC, REU, document mutation, KERNAL, or overlay calls.
SM_PROSE=0
SM_BLANK=1
SM_HEADING=2
SM_LIST=3
SM_CODE_OPEN=4
SM_CODE_LINE=5
SM_CODE_CLOSE=6
SM_REGION_OPEN=7
SM_REGION_CLOSE=8
SM_TEXT=0
SM_BASIC=1
SM_ASM=2
SM_NORMAL=0
SM_EMPHASIS=1
SM_STRONG=2
SM_INLINE_CODE=4
SM_KEYWORD=7
SM_NUMBER=8
SM_STRING=9
SM_COMMENT=10
SM_DIRECTIVE=11
SM_LABEL=12
SM_OPERATOR=13
SM_PAIR=1
SM_ESCAPE=2
.endif
.macro SM_INC24 value
    inc value
    bne :+
    inc value+1
    bne :+
    inc value+2
:
.endmacro
.macro SM_COPY24 source, target
    lda source
    sta target
    lda source+1
    sta target+1
    lda source+2
    sta target+2
.endmacro
.macro SM_ADD8 source, target
    clc
    adc source
    sta target
    lda source+1
    adc #0
    sta target+1
    lda source+2
    adc #0
    sta target+2
.endmacro
