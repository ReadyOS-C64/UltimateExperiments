.setcpu "6502"
.import dos64_overlay_ready, dos64_overlay_busy, dos64_bios_ready, dos64_import_state
.export dos64_cold_release, dos64_cold_open
.segment "NATIVESTATE"
; Loaded initialized control byte; bitmap ownership is irreversible until a
; fresh PRG load. Never infer lifetime from bytes in overwritten cold RAM.
dos64_cold_open: .byte $a5
.segment "CODE"
; A/X/Y clobbered; preserve P except C. Caller owns RAM+I/O.
dos64_cold_release:
 php
 sei
 lda dos64_cold_open
 beq @done
 cmp #$a5
 bne @fail
 lda dos64_import_state
 cmp #1
 beq @fail
 lda dos64_overlay_busy
 bne @fail
 lda dos64_overlay_ready
 cmp #$a5
 bne @fail
 lda dos64_bios_ready
 cmp #$a5
 bne @fail
 lda #0
 sta dos64_cold_open
@done:
 plp
 clc
 rts
@fail:
 plp
 sec
 rts

.import dos64_import_cold_init, dos64_import_cold_start, dos64_import_cold_poll
.export dos64_import_init, dos64_import_start, dos64_import_poll, dos64_cold_error
.segment "NATIVESTATE"
dos64_cold_error: .byte 0
.segment "CODE"
.macro COLD_GATE name, target
name:
 php
 sei
 pha
 lda dos64_cold_open
 cmp #$a5
 bne @fail
 pla
 plp
 jmp target
@fail:
 lda #1
 sta dos64_cold_error
 pla
 plp
 sec
 rts
.endmacro
COLD_GATE dos64_import_init, dos64_import_cold_init
COLD_GATE dos64_import_start, dos64_import_cold_start
COLD_GATE dos64_import_poll, dos64_import_cold_poll
