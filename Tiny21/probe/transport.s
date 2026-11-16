.setcpu "6502"
.macpack longbranch
.include "transport.inc"
.import clock_start, clock_read, clock_delta, clock_rate, clock_now, clock_since
.import clock_is_pal, clock_elapsed, turbo_start, turbo_restore, turbo_readback, turbo_sample
.import reu_transfer
.importzp reu_addr, reu_ram, reu_size, reu_direction, reu_banks
.export probe_main

TURBO = $d031
TILE = $8000
DEST_HI = >TILE
GEO_WIN = $de00
GEO_PAGE = $dffe
GEO_BANK = $dfff
FAR = $002000
PAGES = 16
BYTES = PAGES * 256
REPEATS = 8
RESULT = $ca00
SCREEN = $0400
COLOR = $d800
source = $f0
dest = $f2

.segment "PROBEBSS"
speed: .res 1
lane: .res 1
result_index: .res 1
sweeps: .res 1
blocks: .res 2
page: .res 1

.segment "PROBE"
.macro CONST16 address, value
    lda #<(value)
    sta address
    lda #>(value)
    sta address+1
.endmacro

.macro COPY4 source_addr, dest_addr
    .repeat 4, I
        lda source_addr+I
        sta dest_addr+I
    .endrepeat
.endmacro

probe_main:
    jsr screen_init
    lda #0
    ldx #63
clear:
    sta RESULT,x
    dex
    bpl clear
    lda #'T'
    sta RESULT
    lda #'6'
    sta RESULT+1
    lda #'4'
    sta RESULT+2
    lda #'D'
    sta RESULT+3
    lda #<RUN_NONCE
    sta RESULT+60
    lda #>RUN_NONCE
    sta RESULT+61
    lda #TRANSPORT_GEO
    sta RESULT+5
    lda #REPEATS
    sta RESULT+6
.if TRANSPORT_GEO
    lda #2
.else
    lda #4
.endif
    sta RESULT+7
    jsr clock_start
    COPY4 clock_rate, RESULT+8
    jsr turbo_start
    jcs init_failure
    COPY4 turbo_sample, RESULT+12
    lda turbo_readback
    sta RESULT+62
    jsr seed
    jcs seed_failure

    lda #0
    sta speed
    sta result_index
next_speed:
    ldx speed
    lda speed_controls,x
    sta TURBO
    lda TURBO
    and #$8f
    cmp speed_controls,x
    jne speed_failure
    jsr validate_speed
    jcs speed_failure
    lda #0
    sta lane
next_lane:
    jsr poison
    jsr clock_read
    jcs timing_failure
    COPY4 clock_now, clock_since
    lda #REPEATS
    sta sweeps
next_sweep:
    jsr copy_lane
    jcs copy_failure
    dec sweeps
    bne next_sweep
    jsr clock_read
    jcs timing_failure
    jsr clock_delta
    ldx result_index
    .repeat 4, I
        lda clock_elapsed+I
        sta RESULT+16+I,x
    .endrepeat
    txa
    clc
    adc #4
    sta result_index
    jsr verify
    jcs mismatch
    inc lane
    lda lane
    cmp RESULT+7
    bcc next_lane
    inc speed
    lda speed
    cmp #2
    jcc next_speed
    jsr draw_success
    lda #5
    sta $d020
    lda #3
    sta RESULT+4
    jmp finish

init_failure:
    lda #$81
    bne error
seed_failure:
    lda #$82
    bne error
speed_failure:
    lda #$83
    bne error
timing_failure:
    lda #$84
    bne error
copy_failure:
    lda #$85
    bne error
mismatch:
    lda #$86
error:
    sta RESULT+4
    lda speed
    sta RESULT+48
    lda lane
    sta RESULT+49
    lda #2
    sta $d020
    jsr draw_failure
finish:
    jsr turbo_restore
park:
    jmp park

; Same 329,217-cycle loop used by turbo_start. Tests here validate the
; mode after switching each leg, before any transfer measurement.
validate_speed:
    jsr clock_read
    bcs speed_invalid
    COPY4 clock_now, clock_since
    ldy #0
test_speed_outer:
    ldx #0
test_speed_inner:
    dex
test_speed_branch:
    bne test_speed_inner
    dey
    bne test_speed_outer
.assert >test_speed_inner = >(test_speed_branch+2), lderror, "transport calibration crosses page"
    jsr clock_read
    bcs speed_invalid
    jsr clock_delta
    lda speed
    asl
    asl
    tax
    .repeat 4, I
        lda clock_elapsed+I
        sta RESULT+50+I,x
    .endrepeat
    lda speed
    bne check_fast
    lda clock_elapsed+3
    bne speed_invalid
    lda clock_elapsed+2
    cmp #4
    bcc speed_invalid
    cmp #7
    bcs speed_invalid
    clc
    rts
check_fast:
    lda clock_elapsed+3
    ora clock_elapsed+2
    bne speed_invalid
    lda clock_elapsed+1
    cmp #18
    bcc speed_invalid
    cmp #23
    bcs speed_invalid
    clc
    rts
speed_invalid:
    sec
    rts

seed:
.if TRANSPORT_GEO
    ; The runner resets the cartridge mapping first. Still qualify the
    ; aperture itself before the seed sweep in case loader handoff is
    ; asynchronous. Probe only the first byte of our owned sample page.
    lda #$80
    sta TURBO
    ldx #0
    ldy #0
geo_ready:
    lda #0
    sta GEO_BANK
    lda #32
    sta GEO_PAGE
    lda #$5a
    sta GEO_WIN
    cmp GEO_WIN
    bne geo_yield
    lda #$a5
    sta GEO_WIN
    cmp GEO_WIN
    beq geo_seed_ready
geo_yield:
    inx
    bne geo_ready
    iny
    cpy #8
    bne geo_ready
    lda GEO_WIN
    sta RESULT+59
    sec
    rts
geo_seed_ready:
    CONST16 source, sample
    lda #0
    sta GEO_BANK
    sta page
seed_page:
    lda page
    clc
    adc #32
    sta GEO_PAGE
    ldy #0
seed_geo:
    lda (source),y
    sta GEO_WIN,y
    cmp GEO_WIN,y
    bne invalid_seed
    iny
    bne seed_geo
    inc source+1
    inc page
    lda page
    cmp #PAGES
    bne seed_page
    clc
    rts
invalid_seed:
    sta RESULT+58
    lda GEO_WIN,y
    sta RESULT+59
    lda page
    sta RESULT+62
    sty RESULT+63
    sec
    rts
.else
    jsr copy_internal
    lda #32
    sta reu_banks
    jsr reu_start
    lda #0
    sta reu_direction
    CONST16 reu_size, BYTES
    jmp reu_transfer
.endif

reu_start:
    CONST16 reu_addr, FAR
    lda #^FAR
    sta reu_addr+2
    CONST16 reu_ram, TILE
    lda #1
    sta reu_direction
    rts

copy_lane:
    lda lane
    beq expansion_default
.if TRANSPORT_GEO
    jmp copy_internal
.else
    cmp #3
    beq copy_internal
    cmp #2
    beq single_bytes
    jsr reu_start
    lda #PAGES
    sta blocks
small_chunks:
    CONST16 reu_size, 256
    jsr reu_transfer
    bcs copy_exit
    dec blocks
    bne small_chunks
copy_exit:
    rts

single_bytes:
    jsr reu_start
    ; Both address cursors advance in the production REU driver.
    CONST16 blocks, BYTES
one_byte:
    CONST16 reu_size, 1
    jsr reu_transfer
    bcs copy_exit
    lda blocks
    bne decrement
    dec blocks+1
decrement:
    dec blocks
    lda blocks
    ora blocks+1
    bne one_byte
    clc
    rts
.endif

expansion_default:
.if TRANSPORT_GEO
    lda #0
    sta GEO_BANK
    sta page
    lda #DEST_HI
    sta geo_store+2
read_page:
    lda page
    clc
    adc #32
    sta GEO_PAGE
    ldy #0
read_geo:
    ; Unroll eight visible I/O loads/stores per iteration.
    .repeat 7
        lda GEO_WIN,y
        ; The high bytes of these stores are patched once per page.
        sta TILE,y
        iny
    .endrepeat
    lda GEO_WIN,y
geo_store:
    sta TILE,y
    iny
    bne read_geo
    inc page
    lda page
    cmp #PAGES
    beq geo_done
    lda geo_store+2
    clc
    adc #1
    sta geo_store+2
    .repeat 7, I
        sta read_geo+5+I*7
    .endrepeat
    jmp read_page
geo_done:
    ; Restore the eight store operands before the next sweep.
    lda #DEST_HI
    sta geo_store+2
    .repeat 7, I
        sta read_geo+5+I*7
    .endrepeat
    clc
    rts
.else
    jsr reu_start
    CONST16 reu_size, BYTES
    jmp reu_transfer
.endif

; Same data and destination, already resident in C64 RAM. This is a
; separately labeled CPU reference, not a standard-REU direct read.
copy_internal:
    ldy #0
internal_loop:
    .repeat PAGES, I
        lda sample+I*256,y
        sta TILE+I*256,y
    .endrepeat
    iny
    bne internal_loop
    clc
    rts

poison:
    ldy #0
poison_loop:
    .repeat PAGES, I
        lda sample+I*256,y
        eor #$ff
        sta TILE+I*256,y
    .endrepeat
    iny
    beq poison_done
    jmp poison_loop
poison_done:
    rts

verify:
    CONST16 source, sample
    CONST16 dest, TILE
    ldx #PAGES
verify_page:
    ldy #0
verify_byte:
    lda (source),y
    cmp (dest),y
    bne verify_fail
    iny
    bne verify_byte
    inc source+1
    inc dest+1
    dex
    bne verify_page
    clc
    rts
verify_fail:
    sta RESULT+58
    lda (dest),y
    sta RESULT+59
    sty RESULT+63
    txa
    sta RESULT+62
    sec
    rts

screen_init:
    lda $dd02
    ora #3
    sta $dd02
    lda $dd00
    ora #3
    sta $dd00
    lda #$1b
    sta $d011
    lda #$08
    sta $d016
    lda #$16
    sta $d018
    lda #0
    sta $d015
    sta $d01a
    lda #3
    sta $d020
    lda #11
    sta $d021
    ldx #0
fill:
    lda #' '
    .repeat 4, I
        sta SCREEN+256*I,x
    .endrepeat
    lda #1
    .repeat 4, I
        sta COLOR+256*I,x
    .endrepeat
    inx
    bne fill
    ldx #11
video_marker:
    lda #$a0
    sta SCREEN+1,x
    lda marker_colors,x
    sta COLOR+1,x
    dex
    bpl video_marker
    ldx #title_end-title-1
title_copy:
    lda title,x
    sta SCREEN+41,x
    lda #3
    sta COLOR+41,x
    dex
    bpl title_copy
    rts

draw_success:
    ldx #summary_end-summary-1
summary_copy:
    lda summary,x
    sta SCREEN+161,x
    dex
    bpl summary_copy
    rts

draw_failure:
    lda #$50
    sta SCREEN+161
    lda #$52
    sta SCREEN+162
    lda #$4f
    sta SCREEN+163
    lda #$42
    sta SCREEN+164
    lda #$45
    sta SCREEN+165
    lda RESULT+4
    and #15
    ora #'0'
    sta SCREEN+167
    rts

speed_controls: .byte $80,$8f
marker_colors: .byte RUN_MARKER
title:
    ; ASCII uppercase equals screen code on the lowercase character set.
.if TRANSPORT_GEO
    .byte "C64U TRANSPORT / GEORAM"
.else
    .byte "C64U TRANSPORT / REU DMA"
.endif
title_end:
summary: .byte "COMPLETE / ALL BYTES VERIFIED"
summary_end:

.align 256
sample: .incbin "sample.bin"
.assert *-sample = BYTES, error, "wrong sample size"
