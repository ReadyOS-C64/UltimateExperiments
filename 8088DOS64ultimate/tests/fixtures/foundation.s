.include "abi.inc"
.import dos64_cpu_reset, dos64_mailbox
.export fixture_pass, fixture_fail, fixture_runaway
.export fixture_unbalanced, fixture_bad_write, fixture_return
.export fixture_timed
.export fixture_unimplemented_reu

.ifdef DOS64_UNIT_COLD
.segment "UNITTAIL"
.else
.segment "TESTCODE"
.endif
fixture_pass:
    jsr dos64_cpu_reset
    lda #STATUS_PASS
    sta dos64_mailbox+MB_STATUS
    rts
fixture_fail:
    lda #STATUS_FAIL
    sta dos64_mailbox+MB_STATUS
    rts
fixture_runaway:
    jmp fixture_runaway
fixture_unbalanced:
    pla
    jmp fixture_return
fixture_bad_write:
    lda #$42
    sta $4000
    rts
fixture_timed:
    lda #7
    rts
fixture_unimplemented_reu:
    lda $DF00
    rts
; Stopped by the host before executing. Normal RTS must restore SP=$FF here.
.segment "TESTCODE"
fixture_return:
    nop

.ifdef DOS64_UNIT_COLD
.import __UNITCOLD_RUN__, __UNITCOLD_SIZE__
.assert __UNITCOLD_RUN__ >= $7401, lderror, "unit cold helpers overlap snapshot output/guard"
.assert __UNITCOLD_RUN__+__UNITCOLD_SIZE__ <= $8000, lderror, "unit cold helpers exceed disposable window"
.endif
