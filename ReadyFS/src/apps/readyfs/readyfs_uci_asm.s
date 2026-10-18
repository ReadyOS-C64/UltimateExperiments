;
; ReadyFS UCI register accessors. readyfs_uci.c exclusively owns the proven
; asynchronous PUSH/ABORT waits, queue drains, DATA_ACC, and quiet IDLE.
;

        .export _readyfs_uci_asm_write_cmd
        .export _readyfs_uci_asm_set_base
        .export _readyfs_uci_asm_id
        .export _readyfs_uci_asm_status
        .export _readyfs_uci_asm_read_data
        .export _readyfs_uci_asm_read_stat
        .export _readyfs_uci_asm_push_cmd
        .export _readyfs_uci_asm_accept_data
        .export _readyfs_uci_asm_accept_more_transition
        .export _readyfs_uci_asm_abort
        .export _readyfs_uci_asm_clear_error
        .export _readyfs_uci_asm_softiec_bus

CPU_PORT = $0001

_readyfs_uci_asm_set_base:
        sta uci_base_lo
        stx uci_base_hi
        sta uci_status+1
        sta uci_push+1
        sta uci_accept+1
        sta uci_accept_more_write+1
        sta uci_accept_more_read+1
        sta uci_abort+1
        sta uci_clear_error+1
        stx uci_status+2
        stx uci_push+2
        stx uci_accept+2
        stx uci_accept_more_write+2
        stx uci_accept_more_read+2
        stx uci_abort+2
        stx uci_clear_error+2

        lda uci_base_lo
        sec
        sbc #$01
        sta uci_softiec+1
        lda uci_base_hi
        sbc #$00
        sta uci_softiec+2

        lda uci_base_lo
        clc
        adc #$01
        sta uci_write_cmd+1
        sta uci_id+1
        lda uci_base_hi
        adc #$00
        sta uci_write_cmd+2
        sta uci_id+2

        lda uci_base_lo
        clc
        adc #$02
        sta uci_data+1
        lda uci_base_hi
        adc #$00
        sta uci_data+2

        lda uci_base_lo
        clc
        adc #$03
        sta uci_stat+1
        lda uci_base_hi
        adc #$00
        sta uci_stat+2
        rts

.macro UCI_MAP_IO
        php
        sei
        lda CPU_PORT
        pha
        and #$F8
        ora #$07
        sta CPU_PORT
.endmacro

.macro UCI_RESTORE_IO
        pla
        sta CPU_PORT
        plp
.endmacro

_readyfs_uci_asm_write_cmd:
        sta uci_value
        UCI_MAP_IO
        lda uci_value
uci_write_cmd:
        sta $DF1D
        UCI_RESTORE_IO
        lda uci_value
        rts

_readyfs_uci_asm_id:
        UCI_MAP_IO
uci_id:
        lda $DF1D
        tax
        UCI_RESTORE_IO
        txa
        rts

_readyfs_uci_asm_status:
        UCI_MAP_IO
uci_status:
        lda $DF1C
        tax
        UCI_RESTORE_IO
        txa
        rts

_readyfs_uci_asm_read_data:
        UCI_MAP_IO
uci_data:
        lda $DF1E
        tax
        UCI_RESTORE_IO
        txa
        rts

_readyfs_uci_asm_read_stat:
        UCI_MAP_IO
uci_stat:
        lda $DF1F
        tax
        UCI_RESTORE_IO
        txa
        rts

_readyfs_uci_asm_push_cmd:
        UCI_MAP_IO
        lda #$01
uci_push:
        sta $DF1C
        UCI_RESTORE_IO
        rts

_readyfs_uci_asm_accept_data:
        UCI_MAP_IO
        lda #$02
uci_accept:
        sta $DF1C
        UCI_RESTORE_IO
        rts

; __fastcall__ old_state in A. DATA_ACC is asynchronous, and at 64 MHz the
; MORE -> BUSY -> next-data transition can fit inside ordinary C call overhead.
; Keep the accept write and transition observation adjacent. The 4096-sample
; bound is only a failure/capture bound; the C transport owns all recovery.
_readyfs_uci_asm_accept_more_transition:
        sta accept_old_state
        UCI_MAP_IO
        lda #$02
uci_accept_more_write:
        sta $DF1C
        ldx #$10
        ldy #$00
accept_more_wait_transition:
uci_accept_more_read:
        lda $DF1C
        and #$30
        cmp accept_old_state
        bne accept_more_transition_seen
        dey
        bne accept_more_wait_transition
        dex
        bne accept_more_wait_transition
        lda #$00
        sta accept_result
        beq accept_more_transition_done
accept_more_transition_seen:
        lda #$01
        sta accept_result
accept_more_transition_done:
        UCI_RESTORE_IO
        lda accept_result
        rts

_readyfs_uci_asm_abort:
        UCI_MAP_IO
        lda #$04
uci_abort:
        sta $DF1C
        UCI_RESTORE_IO
        rts

_readyfs_uci_asm_clear_error:
        UCI_MAP_IO
        lda #$08
uci_clear_error:
        sta $DF1C
        UCI_RESTORE_IO
        rts

_readyfs_uci_asm_softiec_bus:
        UCI_MAP_IO
uci_softiec:
        lda $DF1B
        tax
        UCI_RESTORE_IO
        txa
        rts

uci_base_lo: .byte 0
uci_base_hi: .byte 0
uci_value:   .byte 0
accept_old_state: .byte 0
accept_result:    .byte 0
