.include "abi.inc"
.import dos64_cpu_reset, dos64_mailbox
.export fixture_pass, fixture_fail, fixture_runaway
.export fixture_unbalanced, fixture_bad_write, fixture_return
.export fixture_timed
.export fixture_unimplemented_reu

.segment "TESTCODE"
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
fixture_return:
    nop
