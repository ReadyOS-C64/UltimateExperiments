; Overlay-12 REU spool leaf.  ReadyFsTapeCall is packed by cc65; keep these
; offsets synchronized with readyfs_tape.h.  ptr1/ptr2 are cc65 temporary
; runtime pointers, not the software-stack pointer, and no nested call occurs.

        .importzp ptr1, ptr2, ptr3
        .import _readyfs_reu_console_bank_value
        .export _readyfs_tape_spool_dispatch
        .export _readyfs_tape_open_name_dispatch

TC_OPERATION = 0
TC_DATA      = 5
TC_LENGTH    = 7
TC_SPOOL     = 9
TC_RESULT    = 11
TC_TEXT      = 15
TC_OUTPUT    = 19
TC_VALUE     = 25
TC_VALUE2    = 26

SP_BYTES_LO  = 0
SP_BYTES_HI  = 2
SP_REPLAY_LO = 3
SP_REPLAY_HI = 5

OP_INIT  = 10
OP_STORE = 11
OP_FETCH = 12

REU_COMMAND = $DF01
REU_C64_LO  = $DF02
REU_C64_HI  = $DF03
REU_REU_LO  = $DF04
REU_REU_HI  = $DF05
REU_BANK    = $DF06
REU_LEN_LO  = $DF07
REU_LEN_HI  = $DF08

.macro jeq target
        bne :+
        jmp target
:
.endmacro
.macro jne target
        beq :+
        jmp target
:
.endmacro
.macro jcc target
        bcs :+
        jmp target
:
.endmacro
.macro jcs target
        bcc :+
        jmp target
:
.endmacro

        .segment "OVERLAY12"

_readyfs_tape_open_name_dispatch:
        sta ptr1
        stx ptr1+1
        ldy #TC_TEXT
        lda (ptr1),y
        sta ptr2
        iny
        lda (ptr1),y
        sta ptr2+1
        ldy #TC_OUTPUT
        lda (ptr1),y
        sta ptr3
        iny
        lda (ptr1),y
        sta ptr3+1
        ldy #$00
open_copy:
        lda (ptr2),y
        sta (ptr3),y
        beq open_suffix
        iny
        bne open_copy
open_suffix:
        lda #','
        sta (ptr3),y
        iny
        sty open_len
        ldy #TC_VALUE
        lda (ptr1),y
        and #$03
        tax
        ldy open_len
        lda open_letters,x
        sta (ptr3),y
        iny
        lda #','
        sta (ptr3),y
        iny
        sty open_len
        ldy #TC_VALUE2
        lda (ptr1),y
        ldy open_len
        sta (ptr3),y
        iny
        lda #$00
        sta (ptr3),y
        lda #$01
        ldx #$00
        rts
open_letters:
        .byte 's', 'p', 'u', 'l'
open_len:
        .byte 0

_readyfs_tape_spool_dispatch:
        sta ptr1
        stx ptr1+1
        ldy #TC_SPOOL
        lda (ptr1),y
        sta ptr2
        iny
        lda (ptr1),y
        sta ptr2+1
        lda ptr2
        ora ptr2+1
        jeq fail
        ldy #TC_OPERATION
        lda (ptr1),y
        cmp #OP_INIT
        beq initialize
        cmp #OP_STORE
        beq store
        cmp #OP_FETCH
        jeq fetch
        jmp fail

initialize:
        lda #$00
        ldy #$05
init_loop:
        sta (ptr2),y
        dey
        bpl init_loop
        ldy #TC_LENGTH
        sta (ptr1),y
        iny
        sta (ptr1),y
        jmp succeed

validate_data:
        ldy #TC_DATA
        lda (ptr1),y
        iny
        ora (ptr1),y
        beq invalid_data
        ldy #TC_LENGTH
        lda (ptr1),y
        iny
        ora (ptr1),y
        beq invalid_data
        sec
        rts
invalid_data:
        clc
        rts

store:
        jsr validate_data
        jcc fail
        ldy #SP_BYTES_HI
        lda (ptr2),y
        clc
        adc #$01
        jcs fail
        cmp _readyfs_reu_console_bank_value
        jcs fail
        sta spool_bank
        ; If this chunk crosses a 64K boundary, the automatically incremented
        ; REU bank must still remain below all four reserved high banks. An exact end at the
        ; boundary does not touch the following bank.
        ldy #SP_BYTES_LO
        lda (ptr2),y
        ldy #TC_LENGTH
        clc
        adc (ptr1),y
        sta spool_rem
        ldy #SP_BYTES_LO+1
        lda (ptr2),y
        ldy #TC_LENGTH+1
        adc (ptr1),y
        bcc store_dma
        ora spool_rem
        beq store_dma
        lda spool_bank
        clc
        adc #$01
        cmp _readyfs_reu_console_bank_value
        jcs fail
store_dma:
        lda #SP_BYTES_LO
        sta spool_state_offset
        lda #$90
        jsr dma
        ldy #SP_BYTES_LO
        lda (ptr2),y
        ldy #TC_LENGTH
        clc
        adc (ptr1),y
        ldy #SP_BYTES_LO
        sta (ptr2),y
        iny
        lda (ptr2),y
        ldy #TC_LENGTH+1
        adc (ptr1),y
        ldy #SP_BYTES_LO+1
        sta (ptr2),y
        jcc succeed
        ldy #SP_BYTES_HI
        lda (ptr2),y
        clc
        adc #$01
        sta (ptr2),y
        jmp succeed

fetch:
        jsr validate_data
        jcc fail
        ; Compare the one-byte 64K bank cursors.
        ldy #SP_REPLAY_HI
        lda (ptr2),y
        ldy #SP_BYTES_HI
        cmp (ptr2),y
        bcc fetch_adjacent
        jne fetch_eof
        lda #$00
        sta spool_state_offset
        beq fetch_remaining
fetch_adjacent:
        ; An adjacent end bank can still leave fewer bytes than requested.
        ; Cap that final chunk even when its end is exactly a 64K boundary.
        ldy #SP_REPLAY_HI
        lda (ptr2),y
        clc
        adc #$01
        ldy #SP_BYTES_HI
        cmp (ptr2),y
        jne fetch_more_banks
        lda #$01
        sta spool_state_offset
fetch_remaining:
        ldy #SP_BYTES_LO
        lda (ptr2),y
        ldy #SP_REPLAY_LO
        sec
        sbc (ptr2),y
        sta spool_rem
        ldy #SP_BYTES_LO+1
        lda (ptr2),y
        ldy #SP_REPLAY_LO+1
        sbc (ptr2),y
        sta spool_rem+1
        bcc fetch_borrowed
        lda spool_state_offset
        jne fetch_more_banks ; adjacent with >=64K remaining
        beq fetch_cap
fetch_borrowed:
        lda spool_state_offset
        jeq fetch_eof        ; same-bank cursor passed EOF
fetch_cap:
        lda spool_rem+1
        ora spool_rem
        beq fetch_eof
        ldy #TC_LENGTH+1
        lda (ptr1),y
        cmp spool_rem+1
        bcc fetch_amount_ready
        bne cap_amount
        dey
        lda (ptr1),y
        cmp spool_rem
        bcc fetch_amount_ready
        beq fetch_amount_ready
cap_amount:
        ldy #TC_LENGTH
        lda spool_rem
        sta (ptr1),y
        iny
        lda spool_rem+1
        sta (ptr1),y
fetch_amount_ready:
fetch_more_banks:
        ldy #SP_REPLAY_HI
        lda (ptr2),y
        clc
        adc #$01
        jcs fail
        cmp _readyfs_reu_console_bank_value
        jcs fail
        sta spool_bank
        lda #SP_REPLAY_LO
        sta spool_state_offset
        lda #$91
        jsr dma
        ldy #SP_REPLAY_LO
        lda (ptr2),y
        ldy #TC_LENGTH
        clc
        adc (ptr1),y
        ldy #SP_REPLAY_LO
        sta (ptr2),y
        iny
        lda (ptr2),y
        ldy #TC_LENGTH+1
        adc (ptr1),y
        ldy #SP_REPLAY_LO+1
        sta (ptr2),y
        bcc succeed
        ldy #SP_REPLAY_HI
        lda (ptr2),y
        clc
        adc #$01
        sta (ptr2),y
        jmp succeed

fetch_eof:
        lda #$00
        ldy #TC_LENGTH
        sta (ptr1),y
        iny
        sta (ptr1),y
        jmp succeed

; A is the REU command. ptr1 is the call, ptr2 is the spool state.
dma:
        pha
        ldy #TC_DATA
        lda (ptr1),y
        sta REU_C64_LO
        iny
        lda (ptr1),y
        sta REU_C64_HI
        ldy spool_state_offset
        lda (ptr2),y
        sta REU_REU_LO
        iny
        lda (ptr2),y
        sta REU_REU_HI
        lda spool_bank
        sta REU_BANK
        ldy #TC_LENGTH
        lda (ptr1),y
        sta REU_LEN_LO
        iny
        lda (ptr1),y
        sta REU_LEN_HI
        pla
        sta REU_COMMAND
        rts

fail:
        lda #$00
        .byte $2C              ; BIT abs consumes the following LDA immediate
succeed:
        lda #$01
finish:
        ldx #$00
        rts

spool_bank:
        .byte 0
spool_state_offset:
        .byte 0
spool_rem:
        .word 0
