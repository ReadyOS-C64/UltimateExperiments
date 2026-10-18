.include "memory.inc"
.include "render_text.inc"
.macpack longbranch
.import dos64_cache_init, dos64_cache_flush, dos64_mem_write
.import dos64_cache_limit
.importzp dos64_mem_value
.importzp dos64_address
.import dos64_render_text_row, dos64_render_text_request
.import dos64_native_text_setup
.export dos64_native_text_probe, dos64_text_probe_mailbox
.ifndef PROBE_MODE
PROBE_MODE=3
.endif
.if PROBE_MODE < 2
COLS=40
STRIDE=8
.else
COLS=80
STRIDE=16
.endif
.segment "PROBEMAILBOX"
; DTP1, version1, text mode, status(A5 pass/E1 fail), error,
; bitmap/matrix/font sum16 little endian. External verifier also checks SHA256.
dos64_text_probe_mailbox: .res 14
.segment "DEVICESTATE"
np_count: .res 2
np_char: .res 1
np_sum: .res 2
np_index: .res 1
.segment "CODE"
; Destructive, owned fixture: modifies guest BDA and B8000 CGA backing in REU.
; Owns $4000 matrix, $4800 font, $6000 bitmap, guest cache and VIC state.
; A static presentation fixture, not DOS boot. Cursor deliberately hidden.
dos64_native_text_probe:
    php
    sei
    cld
    lda #$2F
    sta $00
    lda #$35
    sta $01
    lda #<np_nmi
    sta $FFFA
    lda #>np_nmi
    sta $FFFB
    ldx #13
    lda #0
@clear: sta dos64_text_probe_mailbox,x
    dex
    bpl @clear
    ldx #5
@header: lda np_header,x
    sta dos64_text_probe_mailbox,x
    dex
    bpl @header
    lda #32
    sta dos64_cache_limit
    jsr dos64_cache_init
    jcs np_fail
    lda #0
    sta dos64_address
    lda #4
    sta dos64_address+1
    lda #0
    sta dos64_address+2
    ; All 256 BDA page bytes start defined; only this owned fixture is changed.
    sta np_char
    sta np_count
    lda #1
    sta np_count+1
    jsr np_fill
    jcs np_fail
    ldx #0
@bda: lda np_offsets,x
    sta dos64_address
    lda #4
    sta dos64_address+1
    lda #0
    sta dos64_address+2
    lda np_values,x
    sta dos64_mem_value
    stx np_index
    jsr dos64_mem_write
    jcs np_fail
    ldx np_index
    inx
    cpx #8
    bne @bda
    lda #0
    sta dos64_address
    lda #$80
    sta dos64_address+1
    lda #$0B
    sta dos64_address+2
    lda #<(COLS*25)
    sta np_count
    lda #>(COLS*25)
    sta np_count+1
@spaces:
    lda #$20
    jsr np_cell
    jcs np_fail
    jsr np_decrement
    bne @spaces
    ; First rows: recognizable marker and DOS-like text, explicitly a fixture.
    lda #<np_lines
    sta np_text+1
    lda #>np_lines
    sta np_text+2
    lda #0
    sta dos64_address
    lda #$80
    sta dos64_address+1
    lda #$0B
    sta dos64_address+2
np_text_loop:
np_text: lda $FFFF
    cmp #$FF
    beq np_glyphs
    jsr np_cell
    jcs np_fail
    inc np_text+1
    bne np_text_loop
    inc np_text+2
    jmp np_text_loop
np_glyphs:
    lda #<(10*COLS*2)
    sta dos64_address
    lda #>($8000+10*COLS*2)
    sta dos64_address+1
    lda #0
    sta np_char
@glyph:
    lda np_char
    jsr np_cell
    jcs np_fail
    inc np_char
    bne @glyph
    jsr dos64_cache_flush
    jcs np_fail
    lda #0
    sta dos64_render_text_request+RT_ROW
    lda #1
    sta dos64_render_text_request+RT_BLINK
@row:
    jsr dos64_render_text_row
    jcs np_fail
    inc dos64_render_text_request+RT_ROW
    lda dos64_render_text_request+RT_ROW
    cmp #25
    bne @row
    ; Complete output checksums are evidence metadata, not acceptance alone.
    lda #0
    sta np_scan+1
    lda #$60
    sta np_scan+2
    lda #<8000
    sta np_count
    lda #>8000
    sta np_count+1
    jsr np_checksum
    lda np_sum
    sta dos64_text_probe_mailbox+8
    lda np_sum+1
    sta dos64_text_probe_mailbox+9
    lda #0
    sta np_scan+1
    lda #$40
    sta np_scan+2
    lda #<1000
    sta np_count
    lda #>1000
    sta np_count+1
    jsr np_checksum
    lda np_sum
    sta dos64_text_probe_mailbox+10
    lda np_sum+1
    sta dos64_text_probe_mailbox+11
    lda #0
    sta np_scan+1
    lda #$48
    sta np_scan+2
    lda #0
    sta np_count
    lda #8
    sta np_count+1
    jsr np_checksum
    lda np_sum
    sta dos64_text_probe_mailbox+12
    lda np_sum+1
    sta dos64_text_probe_mailbox+13
    jsr dos64_native_text_setup
    lda #$A5
    sta dos64_text_probe_mailbox+6
    plp
    clc
    rts
np_fail:
    lda #$E1
    sta dos64_text_probe_mailbox+6
    lda #1
    sta dos64_text_probe_mailbox+7
    plp
    sec
    rts
np_nmi: rti
np_cell:
    sta dos64_mem_value
    jsr dos64_mem_write
    bcs @error
    jsr np_next
    lda #7
    sta dos64_mem_value
    jsr dos64_mem_write
    bcs @error
    jsr np_next
    clc
@error: rts
np_next:
    inc dos64_address
    bne :+
    inc dos64_address+1
:   rts
np_fill:
    lda np_char
    sta dos64_mem_value
    jsr dos64_mem_write
    bcs @exit
    jsr np_next
    jsr np_decrement
    bne np_fill
    clc
@exit: rts
np_decrement:
    lda np_count
    bne :+
    dec np_count+1
:   dec np_count
    lda np_count
    ora np_count+1
    rts
np_checksum:
    lda #0
    sta np_sum
    sta np_sum+1
np_checksum_byte:
np_scan: lda $FFFF
    clc
    adc np_sum
    sta np_sum
    bcc :+
    inc np_sum+1
:   inc np_scan+1
    bne :+
    inc np_scan+2
:   jsr np_decrement
    bne np_checksum_byte
    rts
np_header: .byte "DTP1",1,PROBE_MODE
np_offsets: .byte $49,$4A,$4B,$4C,$4D,$4E,$4F,$62
np_values: .byte PROBE_MODE,COLS,0,0,STRIDE,0,0,0
np_lines:
.byte "DOS64 NATIVE TEXT FIXTURE "
.if COLS=40
.byte "40 COLUMNS"
.else
.byte "80 COLUMNS"
.endif
.res COLS-36,$20
.byte "A>VER"
.res COLS-5,$20
.byte "MS-DOS Version 3.30 (sample text)"
.res COLS-33,$20
.byte "A>DIR"
.res COLS-5,$20
.byte "PRESENTATION ONLY - NO DOS EXECUTION"
.res COLS-36,$20
.byte $DA
.res COLS-2,$C4
.byte $BF
.byte $B3," CP437 GLYPHS BELOW; CURSOR HIDDEN"
.res COLS-36,$20
.byte $B3
.byte $C0
.res COLS-2,$C4
.byte $D9
.byte $FF
