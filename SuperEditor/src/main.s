.setcpu "6502"
.include "platform.inc"

.export se_entry, se_idle, se_diagnostics, se_status, se_mode, se_reu_banks
.export se_last_key, se_key_sequence, se_probe_original
.export se_probe_bank, se_probe_byte, se_probe_saved, se_ink_reverse
.export se_last_modifiers, se_last_matrix
.exportzp text_ptr, screen_ptr
.import __BSS_RUN__, __BSS_SIZE__
.import se_display_init, se_petscii_screen, se_print, se_hex_byte, se_reu_probe
.import se_input_init, se_input_get
.ifdef DISPLAY_PROBE
    .import p_screen, p_key
.endif
.ifdef MEMORY_PROBE
    .import se_memory_probe, se_memory_result
.endif

.ifdef HISTORY_PROBE
    .import se_history_probe, se_h_probe_result, se_h_probe_screen
.endif

.ifdef OVERLAY_PROBE
    .import se_overlay_probe, se_overlay_result
.endif

.ifdef OBJECT_PROBE
    .import se_object_probe, se_object_result
.endif

.ifdef DOCUMENT_PROBE
    .import se_doc_probe, se_doc_result, se_doc_probe_screen
.endif

.ifdef SPLICE_PROBE
    .import se_splice_probe, se_splice_result, se_splice_probe_screen
.endif

.ifdef RANGE_PROBE
    .import se_range_probe, se_range_screen
.endif

.ifdef LOCAL_PROBE
    .import se_local_probe, se_local_screen
.endif

.ifdef CLIPBOARD_PROBE
    .import se_clip_probe, se_clip_result, se_clip_probe_screen
.endif

.segment "LOADADDR"
    .word $0801
.segment "BOOT"
    .word boot_end
    .word 10
    .byte $9E
    .byte $34,$30,$39,$36,0 ; SYS 4096, independent of string character map
boot_end:
    .word 0

.segment "ZEROPAGE"
text_ptr:   .res 2
screen_ptr: .res 2
temp_ptr:   .res 2

.segment "BSS"
; Versioned, read-only observer ABI. SEDG, schema, status, mode, REU bank count,
; last PETSCII key, consumed-key sequence. Never inject edits into this block.
se_diagnostics:   .res 4
se_schema:        .res 1
se_status:        .res 1 ; 0 initializing, 1 ready, 2 REU required
se_mode:          .res 1 ; 0 text40, 1 text60, 2 text80, 3 hires
se_reu_banks:     .res 2 ; 256 banks is represented as $0100
se_last_key:      .res 1
se_key_sequence:  .res 2
se_saved_ddr:     .res 1
se_saved_port:    .res 1
se_probe_bank:    .res 1
se_probe_byte:    .res 1
se_probe_saved:   .res 1
se_probe_original: .res 256
se_ink_reverse:   .res 1
se_last_modifiers: .res 1
se_last_matrix: .res 1

.assert se_diagnostics = $C000, lderror, "diagnostic ABI moved"
.assert __BSS_RUN__ + __BSS_SIZE__ <= SHIM_FIRST, lderror, "BSS reaches ReadyOS shim"

.segment "ENTRY"
se_entry:
    sei
    cld
    lda $00
    pha
    lda $01
    pha
    lda $00
    ora #7
    sta $00
    lda $01
    and #$F8
    ora #6 ; RAM under BASIC; KERNAL and I/O visible
    sta $01
    jsr se_clear_state
    pla
    sta se_saved_port
    pla
    sta se_saved_ddr
    ldx #3
@signature:
    lda signature,x
    sta se_diagnostics,x
    dex
    bpl @signature
    lda #1
    sta se_schema
    ; Disable ROM charset toggle and cursor blink, retaining normal key scan.
    lda #$80
    sta $0291
    lda #1
    sta $CC
    jsr se_display_init
    jsr se_reu_probe
    lda se_reu_banks
    ora se_reu_banks+1
    beq @no_reu
    lda #1
    bne @status
@no_reu:
    lda #2
@status:
    sta se_status
    jsr se_input_init
.ifdef LOCAL_PROBE
    jsr se_local_probe
.endif
.ifdef RANGE_PROBE
    jsr se_range_probe
.endif
.ifdef CLIPBOARD_PROBE
    jsr se_clip_probe
.endif
.ifdef SPLICE_PROBE
    jsr se_splice_probe
.endif
.ifdef DOCUMENT_PROBE
    jsr se_doc_probe
.endif
.ifdef OBJECT_PROBE
    jsr se_object_probe
.endif
.ifdef MEMORY_PROBE
    jsr se_memory_probe
.endif
.ifdef HISTORY_PROBE
    cli
    jsr se_history_probe
.endif
.ifdef OVERLAY_PROBE
    cli
    jsr se_overlay_probe
.endif
.ifdef DISPLAY_PROBE
    jsr p_screen
.else
    jsr se_boot_screen
.ifdef HISTORY_PROBE
    jsr se_h_probe_screen
.endif
.ifdef LOCAL_PROBE
    jsr se_local_screen
.endif
.ifdef RANGE_PROBE
    jsr se_range_screen
.endif
.ifdef CLIPBOARD_PROBE
    jsr se_clip_probe_screen
.endif
.ifdef SPLICE_PROBE
    jsr se_splice_probe_screen
.endif
.ifdef DOCUMENT_PROBE
    jsr se_doc_probe_screen
.endif
.endif
    cli
se_idle:
    jsr se_input_get
    beq se_idle
    sta se_last_key
    stx se_last_modifiers
    sty se_last_matrix
    inc se_key_sequence
    bne :+
    inc se_key_sequence+1
:
.ifdef DISPLAY_PROBE
    lda se_last_key
    jsr p_key
.else
    jsr se_show_key
.endif
    jmp se_idle

.segment "CODE"
se_clear_state:
    lda #<__BSS_RUN__
    sta temp_ptr
    lda #>__BSS_RUN__
    sta temp_ptr+1
    ldx #>__BSS_SIZE__
    ldy #0
    lda #0
    cpx #0
    beq @tail
@page:
    sta (temp_ptr),y
    iny
    bne @page
    inc temp_ptr+1
    dex
    bne @page
@tail:
    ldx #<__BSS_SIZE__
    beq @done
@byte:
    sta (temp_ptr),y
    iny
    dex
    bne @byte
@done:
    rts

.include "boot_ui.s"

.segment "RODATA"
signature: .byte $53,$45,$44,$47
boot_title: .asciiz " SuperEditor  /  standalone C64 editor "
boot_subtitle:
.ifdef HISTORY_PROBE
    .asciiz "Bounded undo / checked REU commands"
.elseif .defined(RANGE_PROBE)
    .asciiz "Immutable range capture / undo base"
.elseif .defined(LOCAL_PROBE)
    .asciiz "Local COW / immutable-reference probe"
.elseif .defined(CLIPBOARD_PROBE)
    .asciiz "Private clipboard + reference replay"
.elseif .defined(SPLICE_PROBE)
    .asciiz "Atomic piece insert/delete/replace"
.elseif .defined(DOCUMENT_PROBE)
    .asciiz "Paged document reader / REU source"
.elseif .defined(OBJECT_PROBE)
    .asciiz "Paged REU object integrity probe"
.elseif .defined(OVERLAY_PROBE)
    .asciiz "Checked disk / REU overlay probe"
.elseif .defined(MEMORY_PROBE)
    .asciiz "Checked REU allocation / DMA probe"
.else
    .asciiz "PETSCII + SuperMark / assembly / REU"
.endif
boot_version:
.ifdef HISTORY_PROBE
    .asciiz "Groups/checkpoint/undo/redo/cancel"
.elseif .defined(RANGE_PROBE)
    .asciiz "20-byte selection / crossing metadata"
.elseif .defined(LOCAL_PROBE)
    .asciiz "144 pieces / 2 shared roots per edit"
.elseif .defined(CLIPBOARD_PROBE)
    .asciiz "Copy/cancel/paste / undo+redo replay"
.elseif .defined(SPLICE_PROBE)
    .asciiz "M2 edits beyond 64 KiB / COW leaves"
.elseif .defined(DOCUMENT_PROBE)
    .asciiz "M2 69632-byte document import/read"
.elseif .defined(OBJECT_PROBE)
    .asciiz "M2 69632-byte noncontiguous object"
.elseif .defined(OVERLAY_PROBE)
    .asciiz "M2 two-slot overlay development probe"
.elseif .defined(MEMORY_PROBE)
    .asciiz "M2 memory service development probe"
.else
    .asciiz "M0 development build 0001"
.endif
boot_ram: .asciiz "ReadyOS $C600-$C9FF stays free"
boot_reu: .asciiz "REU detected: "
boot_ready: .asciiz "Boot and keyboard probe ready."
boot_failed: .asciiz "REU required - no document was opened."
boot_pending:
.ifdef HISTORY_PROBE
    .asciiz ""
.elseif .defined(LOCAL_PROBE)
    .asciiz ""
.elseif .defined(CLIPBOARD_PROBE)
    .asciiz "Clipboard/replay result: "
.elseif .defined(SPLICE_PROBE)
    .asciiz "Atomic edit result: "
.elseif .defined(DOCUMENT_PROBE)
    .asciiz "Document reader result: "
.elseif .defined(OBJECT_PROBE)
    .asciiz "Object probe result: "
.elseif .defined(OVERLAY_PROBE)
    .asciiz "Overlay probe result: "
.elseif .defined(MEMORY_PROBE)
    .asciiz "Memory probe result: "
.else
    .asciiz "Editor features are being implemented."
.endif
boot_key: .asciiz "Last native key:"
boot_footer: .asciiz " D81 / VICE warp + traps / 40 columns "
