; Functional original CGA beam/status for the canonical IBM BIOS raster.
; Read-only observation of already-published exact PIT time; no CIA sampling,
; IRQ/PIT mutation, invented read-count progress or timing-policy shortcut.
.include "abi.inc"
.macpack longbranch
.import dos64_cga_control, dos64_cga_control_valid, dos64_cga_registers
.import dos64_pit_ready, dos64_pit_error, dos64_pit_poll_error, dos64_pit_phase, dos64_pit_total, dos64_pit_fraction
.import v_crtc_defaults
.export dos64_cga_status_math
.segment "DEVICESTATE"
cga_time: .res 6
cga_rem: .res 2
.segment "FILECODE"
; Internal only, owned FILE lease, installed HDBIOS and RAM+I/O. A=status on
; C clear; C set if time/timing profile unsupported. Native/guest clocks and
; hardware latches remain untouched. Public port gate owns native P/descriptor.
dos64_cga_status_math:
 lda dos64_cga_control_valid
 cmp #$A5
 jne @bad
 lda dos64_pit_ready
 cmp #1
 jne @bad
 lda dos64_pit_error
 jne @bad
 lda dos64_pit_poll_error
 beq @clock_ok
 cmp #4                  ; existing SAMPLE uncertainty keeps last publication
 jne @bad
@clock_ok:
 ; The PIT publication contract requires a normalized rational remainder.
 lda dos64_pit_fraction+2
 cmp #$06
 bcc @fraction_ok
 jne @bad
 lda dos64_pit_fraction+1
 cmp #$E3
 bcc @fraction_ok
 jne @bad
 lda dos64_pit_fraction
 cmp #$F4
 jcs @bad
@fraction_ok:
 ; Canonical timing only. Arbitrary CRTC programming is still latched, but
 ; status refuses unsupported raster geometries rather than fabricating one.
 ldy #32
 lda dos64_cga_control
 and #2
 bne @timing
 ldy #0
 lda dos64_cga_control
 and #1
 beq @timing
 ldy #16
@timing:
 ldx #0
@register:
 lda v_crtc_defaults,y
 cmp dos64_cga_registers,x
 jne @bad
 iny
 inx
 cpx #10
 bne @register
 ; XT oscillator=12*PIT. Every canonical mode is76PITticks per line,
 ;262lines per frame,200active, VSYNC224..239. Frame=19912PITticks.
 ; Preserve all48whole PIT bits so neither timer phase nor total wrap aliases.
 ldx #3
@time:
 lda dos64_pit_total,x
 sta cga_time+2,x
 dex
 bpl @time
 lda dos64_pit_phase
 sta cga_time
 lda dos64_pit_phase+1
 sta cga_time+1
 lda #0
 sta cga_rem
 sta cga_rem+1
 ldx #48
@frame_bit:
 asl cga_time
 rol cga_time+1
 rol cga_time+2
 rol cga_time+3
 rol cga_time+4
 rol cga_time+5
 rol cga_rem
 rol cga_rem+1
 sec
 lda cga_rem
 sbc #<$4DC8
 tay
 lda cga_rem+1
 sbc #>$4DC8
 bcc @frame_next
 sty cga_rem
 sta cga_rem+1
@frame_next:
 dex
 bne @frame_bit
 ldy #4                 ; no lightpen trigger; disconnected switch is off
 ; VSYNC interval [224*76,240*76). Width16lines is fixed by originalMC6845.
 sec
 lda cga_rem
 sbc #<$4280
 tax
 lda cga_rem+1
 sbc #>$4280
 bcc @not_sync
 cmp #4
 bcc @sync
 bne @not_sync
 cpx #$C0
 bcs @not_sync
@sync:
 ldy #12
@not_sync:
 sec
 lda cga_rem
 sbc #<$3B60             ;200active lines
 lda cga_rem+1
 sbc #>$3B60
 bcs @blank
 ; Remainder modulo76PITticks:16-bit input, remainder fits one byte.
 lda #0
 ldx #16
@line_bit:
 asl cga_rem
 rol cga_rem+1
 rol a
 cmp #76
 bcc @line_next
 sbc #76
@line_next:
 dex
 bne @line_bit
 cmp #53
 bcc @status
 bne @blank
 ; Horizontal display ends at640/master =53+1/3PITticks. The exact
 ; PIT rational fraction (denominator451572) resolves the fractional seam.
 lda dos64_pit_fraction+2
 cmp #$02
 bcc @status
 bne @blank
 lda dos64_pit_fraction+1
 cmp #$4B
 bcc @status
 bne @blank
 lda dos64_pit_fraction
 cmp #$FC
 bcc @status
@blank:
 iny                    ; bit0 means safe regen access (inverse active display)
@status:
 tya
 clc
 rts
@bad:
 sec
 rts
