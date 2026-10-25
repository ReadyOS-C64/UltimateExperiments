validate:
    lda F+GR_ROW
    cmp #25
    jcs argument
    lda F+GR_RUNS
    cmp #3
    jcs argument
    lda F+GR_RESET
    cmp #2
    jcs argument
    lda F+GR_RESET
    bne @reset
    lda F+GR_VALID
    cmp #1
    jne argument ;append requires a successfully completed caller frame
@reset:
    lda F+GR_BACKGROUND
    cmp #16
    jcs argument
    lda F+GR_TOP
    cmp #9
    jcs argument
    cmp F+GR_BOTTOM
    jcc @bottom
    jne argument
@bottom:
    lda F+GR_BOTTOM
    cmp #9
    jcs argument
    ldx #GR_LEFT
    jsr horizontal
    jcs return
    ldx #GR_RIGHT
    jsr horizontal
    jcs return
    lda F+GR_LEFT+1
    cmp F+GR_RIGHT+1
    bcc @clip
    jne argument
    lda F+GR_LEFT
    cmp F+GR_RIGHT
    bcc @clip
    jne argument
@clip:
    lda F+GR_RUNS
    asl
    asl
    asl
    asl
    clc
    adc F+GR_RUNS ;2*17=34 maximum
    sta span
    lda #0
    sta span+1
    ldx #GR_RUN_POINTER
    jsr frame_pointer
    jsr phase_span
    jcs return
    ; Font/palette spans must be readable RAM, outside output/shim/frame.
    ldx #GR_FONT
    lda #<$2E8
    ldy #>$2E8
    jsr readable
    jcs return
    ldx #GR_WIDTHS
    lda #128
    ldy #0
    jsr readable
    jcs return
    ldx #GR_NATIVE
    lda #0
    ldy #4
    jsr readable
    jcs return
    ldx #GR_PALETTE
    lda #14
    ldy #0
    jsr readable
    jcs return
    ldy #13
@palette:
    lda (se_gg_pointer),y
    cmp #16
    jcs argument
    dey
    bpl @palette
    lda #0
    sta run
@run:
    lda run
    cmp F+GR_RUNS
    jcs @valid
    jsr descriptor
    ldy #GRR_COUNT
    lda (se_gg_pointer),y
    cmp #129
    jcs argument
    sta count
    iny
    lda (se_gg_pointer),y
    cmp #8
    bcc @origin
    cmp #$F8
    jcc argument
@origin:
    lda #0
    sta span+1
    lda count
    sta span
    lda #GRR_CHARACTERS
    sta work
@array:
    jsr descriptor
    ldy work
    lda (se_gg_pointer),y
    pha
    iny
    lda (se_gg_pointer),y
    sta se_gg_pointer+1
    pla
    sta se_gg_pointer
    jsr phase_span
    jcs return
    inc work
    inc work
    lda work
    cmp #GRR_BOUNDARIES
    bcc @array
    ; Map contains count+1 boundary words, including the no-input case.
    lda count
    clc
    adc #1
    asl
    sta span
    lda #0
    rol
    sta span+1
    jsr descriptor
    ldy #GRR_BOUNDARIES
    lda (se_gg_pointer),y
    pha
    iny
    lda (se_gg_pointer),y
    sta se_gg_pointer+1
    pla
    sta se_gg_pointer
    jsr phase_span
    jcs return
    lda #0
    sta index
@values:
    lda index
    cmp count
    bcs @next
    ldy #GRR_STYLES
    jsr input
    cmp #4
    jcs argument
    ldy #GRR_ROLES
    jsr input
    cmp #14
    jcs argument
    ldy #GRR_FLAGS
    jsr input
    cmp #8
    jcs argument
    inc index
    bne @values
@next:
    inc run
    jmp @run
@valid:
    clc
    rts
horizontal:
    lda F+1,x
    beq @ok
    cmp #1
    jne argument
    lda F,x
    cmp #65
    jcs argument
@ok:
    clc
    rts
.segment "GEOS_ROW_FAST"
frame_pointer:
    lda F,x
    sta se_gg_pointer
    lda F+1,x
    sta se_gg_pointer+1
    rts
.segment "CODE"
; Checked arithmetic, endpoint may be exactly the upper allocation boundary.
endpoint:
    clc
    lda se_gg_pointer
    adc span
    sta ending
    lda se_gg_pointer+1
    adc span+1
    sta ending+1
    jcs argument
    clc
    rts
phase_span:
    jsr endpoint
    jcs return
    lda se_gg_pointer+1
    cmp #$8D
    jcc argument
    cmp #$92
    jcs argument
    lda ending+1
    cmp #$91
    bcc @ok
    jne argument
    lda ending
    cmp #$81
    jcs argument
@ok:
    clc
    rts
readable:
    sta span
    sty span+1
    jsr frame_pointer
    jsr endpoint
    jcs return
    ; Explicit native fallback may be supplied in the existing charset RAM.
    ; Caller must restore/validate it; bitmap styles may alias this region.
    cpx #GR_NATIVE
    bne @ordinary
    lda se_gg_pointer+1
    cmp #$48
    bcc @ordinary
    cmp #$50
    bcs @ordinary
    lda ending+1
    cmp #$50
    bcc @ok
    jne argument
    lda ending
    jne argument
    beq @ok
@ordinary:
    lda se_gg_pointer+1
    cmp #4
    jcc argument
    cmp #$40
    bcc @low
    cmp #$80
    jcc argument
    cmp #$C0
    jcs argument
    lda ending+1
    cmp #$C0
    bcc @frame
    jne argument
    lda ending
    jne argument
    beq @frame
@low:
    lda ending+1
    cmp #$40
    bcc @ok
    jne argument
    lda ending
    jne argument
@ok:
    clc
    rts
@frame:
    ; [start,end) must not overlap the compiled caller frame.
    lda ending+1
    cmp #>F
    bcc @ok
    bne @after
    lda ending
    cmp #<F
    bcc @ok
    beq @ok
@after:
    lda se_gg_pointer+1
    cmp #>(F+GR_SIZE)
    jcc argument
    bne @ok
    lda se_gg_pointer
    cmp #<(F+GR_SIZE)
    jcc argument
    bcs @ok
