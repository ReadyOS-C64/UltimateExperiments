.include "abi.inc"
.export dos64_guest, dos64_mailbox, dos64_cpu_reset
.export dos64_guest_end, dos64_mailbox_end

.segment "BSS"
dos64_guest: .res G_SIZE
dos64_guest_end:
dos64_mailbox: .res MB_SIZE
dos64_mailbox_end:

.segment "CODE"
; Original 8088 reset state. General registers are initialized deterministically
; by this emulator; their power-on hardware values are not promised.
; In: none. Out: guest state. Clobbers: A, X, N/Z/C. Preserves: Y, $01, D/I.
dos64_cpu_reset:
    lda #0
    ldx #G_SIZE-1
@clear:
    sta dos64_guest,x
    dex
    bpl @clear
    lda #$FF
    sta dos64_guest+G_CS
    sta dos64_guest+G_CS+1
    lda #$02
    sta dos64_guest+G_FLAGS
    lda #$F0
    sta dos64_guest+G_FLAGS+1
    rts
