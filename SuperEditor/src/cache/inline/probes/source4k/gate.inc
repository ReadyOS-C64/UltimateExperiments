; PRIVATE C26 SOURCE3 admission only. Owner4 was checked by actual entry.
; No phase writes, allocation, source lease or parser entry before handoff.
; FALLBACK5 enters the unchanged legacy source_begin below this gate.
    lda GS_ACTIVE
    ora GS_CONTEXT_VALID
    bne source_legacy
    lda F+167                ; actual C20 saved SOURCE continuation
    cmp #1
    bne source_legacy
    lda F+GSEM_ACTIVE
    bne source_legacy
    lda se_bc_flags
    and #$2F                 ; ARMED/LOST/MUTATING/ACTIVE/PAGE_PROOF
    cmp #$21                 ; actual authority remains C39's responsibility
    bne source_legacy
    lda se_bc_count
    bne source_legacy
    lda F+GSEM_COUNT
    cmp #161
    bcs source_legacy
    lda F+GSEM_ROLE
    cmp #14
    bcs source_legacy
    lda F+GSEM_KIND
    cmp #4
    bcs source_legacy
    lda F+GSEM_INLINE
    beq source_legacy
    ; Proper unsigned24-bit END-BODY, rejecting underflow. Registers only.
    sec
    lda F+GSEM_END
    sbc F+GSEM_BODY
    lda F+GSEM_END+1
    sbc F+GSEM_BODY+1
    tax
    lda F+GSEM_END+2
    sbc F+GSEM_BODY+2
    bcc source_legacy
    bne @long
    cpx #16                  ; 4096 bytes, not a low-byte/16-bit length test
    bcc source_legacy
@long:
    lda #39
    sta $9135
    lda #0
    sta $9136
    lda #1
    clc
    rts
