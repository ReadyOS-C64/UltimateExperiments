.macro COPY24 source, target
    .repeat 3,N
        lda source+N
        sta target+N
    .endrepeat
.endmacro
.macro ADD24 left, right, target
    clc
    .repeat 3,N
        lda left+N
        adc right+N
        sta target+N
    .endrepeat
.endmacro
.macro SUB24 left, right, target
    sec
    .repeat 3,N
        lda left+N
        sbc right+N
        sta target+N
    .endrepeat
.endmacro
; C/Z have the same unsigned meaning as CMP on the entire24-bit operand.
.macro CMP24 left, right
    lda left+2
    cmp right+2
    bne :+
    lda left+1
    cmp right+1
    bne :+
    lda left
    cmp right
:
.endmacro
