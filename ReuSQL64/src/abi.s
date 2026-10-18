        .export _rsql_abi_table
        .export _rsql_test_sentinel
        .export _rsql_reu_size_selector
        .export _rsql_overlay_preloaded_mask
        .export _rsql_overlay_diag_slot
        .export _rsql_overlay_diag_low
        .export _rsql_overlay_diag_high
        .export _rsql_overlay_diag_oserror
        .export _rsql_float_text
        .export _rsql_float_a
        .export _rsql_float_b
        .export _rsql_float_out
        .export _rsql_float_destination
        .export _rsql_float_negative
        .export _rsql_float_eval_abi
        .export _rsql_float_add_abi
        .export _rsql_float_div_abi
        .export _rsql_i64_clear
        .export _rsql_i64_increment
        .export _rsql_finish_mutation
        .export _rsql_checkpoint
        .export _rsql_restore
        .export _rsql_checkpoint_control
        .import _rsql_api_version
        .import _rsql_init
        .import _rsql_shutdown
        .import _rsql_exec
        .import _rsql_query_open
        .import _rsql_cursor_next
        .import _rsql_cursor_column
        .import _rsql_value_read
        .import _rsql_query_close
        .import _rsql_last_error
        .import _rsql_not_implemented
        .import _rsql_journal_commit
        .import _rsql_journal_rollback
        .importzp ptr1

        .segment "ABI"

_rsql_abi_table:
        jmp _rsql_api_version
        jmp _rsql_init
        jmp _rsql_shutdown
        jmp _rsql_exec
        jmp _rsql_query_open
        jmp _rsql_cursor_next
        jmp _rsql_cursor_column
        jmp _rsql_value_read
        jmp _rsql_query_close
_rsql_checkpoint:
        jmp _rsql_shutdown           ; quiesce before host/device REU capture
_rsql_restore:
        jmp _rsql_init               ; reopen after host/device REU replacement
        jmp _rsql_last_error

; __fastcall__ pointer arrives in A/X. This phase-neutral helper avoids a
; compiler-generated software-stack frame in every mutation entry.
_rsql_i64_clear:
        sta ptr1
        stx ptr1+1
        ldy #$07
        lda #$00
@clear_i64:
        sta (ptr1),y
        dey
        bpl @clear_i64
        rts

_rsql_i64_increment:
        sta ptr1
        stx ptr1+1
        ldy #$00
@increment_i64:
        lda (ptr1),y
        clc
        adc #$01
        sta (ptr1),y
        bne @increment_done
        iny
        cpy #$08
        bcc @increment_i64
@increment_done:
        rts

; __fastcall__ return code arrives in A. Preserve the mutation error across a
; successful rollback, but let a rollback failure take precedence.
_rsql_finish_mutation:
        cmp #$00
        bne @rollback
        jmp _rsql_journal_commit
@rollback:
        pha
        jsr _rsql_journal_rollback
        beq @original_error
        tax
        pla
        txa
        ldx #$00
        rts
@original_error:
        pla
        ldx #$00
        rts

; BASIC V2 stores numbers as exponent plus signed 31-bit mantissa. These
; helpers execute from $C000 RAM, which stays visible while BASIC/KERNAL ROM is
; banked over the active query sidecar. Input/output buffers also remain here.
.macro FLOAT_ROM_ENTER
        lda #$01
        sta $cfef
        ldx #$00
@save_cc65_zp:
        lda $02,x
        pha
        inx
        cpx #$1a
        bcc @save_cc65_zp
        lda $01
        pha
        ora #$03
        sta $01
.endmacro

.macro FLOAT_ROM_EXIT
        pla
        sta $01
        ldx #$19
@restore_cc65_zp:
        pla
        sta $02,x
        dex
        bpl @restore_cc65_zp
        lda #$00
        sta $cfef
.endmacro

_rsql_float_eval_abi:
        FLOAT_ROM_ENTER
        lda #<_rsql_float_text
        sta $7a
        lda #>_rsql_float_text
        sta $7b
        lda _rsql_float_text
        clc
        jsr $bcf3           ; FIN: text at TXTPTR -> FAC1
        ldx #<_rsql_float_out
        ldy #>_rsql_float_out
        jsr $bbd4           ; MOVMF: FAC1 -> five-byte memory float
        lda _rsql_float_negative
        beq @sign_done
        lda _rsql_float_out
        beq @sign_done
        lda _rsql_float_out+1
        eor #$80
        sta _rsql_float_out+1
@sign_done:
        lda #$00
        sta _rsql_float_negative
        jsr float_store_output
        FLOAT_ROM_EXIT
        rts

_rsql_float_add_abi:
        FLOAT_ROM_ENTER
        lda #<_rsql_float_a
        ldy #>_rsql_float_a
        jsr $bba2           ; MOVFM: A -> FAC1
        lda #<_rsql_float_b
        ldy #>_rsql_float_b
        jsr $b867           ; FADD: FAC1 += B
        ldx #<_rsql_float_out
        ldy #>_rsql_float_out
        jsr $bbd4
        jsr float_store_output
        FLOAT_ROM_EXIT
        rts

_rsql_float_div_abi:
        FLOAT_ROM_ENTER
        lda #<_rsql_float_b
        ldy #>_rsql_float_b
        jsr $bba2           ; FAC1 = denominator
        lda #<_rsql_float_a
        ldy #>_rsql_float_a
        jsr $bb0f           ; FDIV: memory A / FAC1
        ldx #<_rsql_float_out
        ldy #>_rsql_float_out
        jsr $bbd4
        jsr float_store_output
        FLOAT_ROM_EXIT
        rts

float_store_output:
        lda _rsql_float_destination
        sta $fb
        lda _rsql_float_destination+1
        sta $fc
        ldx #$00
        ldy #$00
@copy:
        lda _rsql_float_out,x
        sta ($fb),y
        inx
        iny
        cpx #$05
        bcc @copy
        rts

_rsql_float_text:
        .res 64, $00
_rsql_float_a:
        .res 5, $00
_rsql_float_b:
        .res 5, $00
_rsql_float_out:
        .res 5, $00
_rsql_float_destination:
        .word $0000
_rsql_float_negative:
        .byte $00

        .segment "CONTROL"

_rsql_test_sentinel:
        .byte $00
_rsql_reu_size_selector:
        .byte $05                  ; VICE lane defaults to 16MB; Peddle overrides
_rsql_overlay_preloaded_mask:
        .byte $00                  ; VICE loads device-8 sidecars; Peddle sets $7F
_rsql_overlay_diag_slot:
        .byte $FF
_rsql_overlay_diag_low:
        .byte $FF
_rsql_overlay_diag_high:
        .byte $FF
_rsql_overlay_diag_oserror:
        .byte $FF

        .segment "CONTROLFLAG"

_rsql_checkpoint_control:
        .byte $00
