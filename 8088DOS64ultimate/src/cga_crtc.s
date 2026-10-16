.include "abi.inc"
.macpack longbranch
.import dos64_io_port, dos64_io_value, dos64_io_width
.import dos64_cga_index, dos64_cga_registers, hdb_extension_ready
.import dos64_cga_control, dos64_cga_control_valid
.import dos64_overlay_requested, dos64_overlay_acquire, dos64_overlay_release
.import dos64_cga_status_math
.import io_read_body, io_write_body, io_success, io_unsupported
.export dos64_cga_read_gate, dos64_cga_write_gate
.segment "DEVICESTATE"
cga_port: .res 1
.segment "DEVICECODE"
; Resident gates preserve ordinary PIC/PPI/absent-board callers before the
; extension is installed. CGA calls refuse missing ownership before a jump.
dos64_cga_read_gate:
 php
 sei
 cld
 lda dos64_io_port+1
 cmp #3
 jne io_read_body
 lda hdb_extension_ready
 cmp #$A5
 jne io_unsupported
 jmp cga_read
dos64_cga_write_gate:
 php
 sei
 cld
 lda dos64_io_port+1
 cmp #3
 jne io_write_body
 lda hdb_extension_ready
 cmp #$A5
 jne io_unsupported
 jmp cga_write
.segment "HDBIOS"
; Original IBM CGA decodes3D0..3D7 as four mirrored index/data pairs.
; All port/width validation precedes any register or output descriptor change.
cga_validate:
 lda dos64_io_width
 cmp #2
 bcs @bad
 lda dos64_io_port
 and #$F8
 cmp #$D0
 bne @bad
 lda dos64_io_port
 and #1
 sta cga_port
 clc
 rts
@bad:
 sec
 rts
cga_read:
 lda dos64_io_port
 cmp #$DA
 jeq cga_status_read
 ; Explicit CGA-only XT: no monochrome adapter owns3B4/3B5. Its byte
 ; reads are the same pulled-up unclaimed bus profile as absent game201.
 lda dos64_io_port
 and #$FE
 cmp #$B4
 bne @present
 lda dos64_io_width
 jne io_unsupported
 lda #$FF
 sta dos64_io_value
 jmp io_success
@present:
 jsr cga_validate
 jcs io_unsupported
 ; MC6845 index and R0..R13 are write-only. Their read bus result is not
 ; specified by this model; reject those reads instead of inventing a latch.
 ; A word read necessarily includes a write-only index port, so also refuses.
 lda dos64_io_width
 jne io_unsupported
 lda cga_port
 jeq io_unsupported
 ldx dos64_cga_index
 cpx #14
 jcc io_unsupported
 cpx #18
 jcs io_unsupported
 lda dos64_cga_registers,x
 sta dos64_io_value
 jmp io_success
; Resident HDBIOS return address survives the exclusive FILE arithmetic lease.
; No FILE/UCI state or native clock is touched by the overlaid target.
cga_status_read:
 ; Before nested JSR hides provenance: the original public IO caller must
 ; have no pending return into the exclusive replacement window.
 tsx
 lda $0103,x
 cmp #$C9
 bcc @origin_ok
 cmp #$D0
 jcc io_unsupported
@origin_ok:
 lda dos64_io_width
 jne io_unsupported
 lda #1
 sta dos64_overlay_requested
 jsr dos64_overlay_acquire
 jcs io_unsupported
 jsr dos64_cga_status_math
 bcs @failed
 sta dos64_io_value
 jsr dos64_overlay_release
 jmp io_success
@failed:
 jsr dos64_overlay_release
 jmp io_unsupported
cga_write:
 lda dos64_io_port
 cmp #$D8
 jeq cga_mode_write
 lda dos64_io_port
 and #$FE
 cmp #$B4
 bne @present
 lda dos64_io_width
 jne io_unsupported
 jmp io_success          ; absentMDA byte writes have no latch/device effects
@present:
 jsr cga_validate
 jcs io_unsupported
 lda dos64_io_width
 beq @bytes
 lda dos64_io_port
 and #7
 cmp #7
 jeq io_unsupported       ; second byte would be unimplemented3D8, atomic reject
@bytes:
 ldy #0
@next:
 lda dos64_io_value,y
 jsr cga_write_byte
 cpy dos64_io_width
 beq @done
 iny
 lda cga_port
 eor #1
 sta cga_port
 jmp @next
@done:
 jmp io_success
; IBM CGA write-only six-bit mode latch. This functional renderer supports
; blanking and blink/background intensity within the BIOS-selected geometry.
; Changes to width/graphics/colorburst/high-resolution bits refuse atomically.
cga_mode_write:
 lda dos64_io_width
 jne io_unsupported
 lda dos64_cga_control_valid
 cmp #$A5
 jne io_unsupported
 lda dos64_io_value
 eor dos64_cga_control
 and #$17
 jne io_unsupported
 lda dos64_io_value
 and #$3F
 sta dos64_cga_control
 jmp io_success
cga_write_byte:
 ldx cga_port
 bne @data
 and #$1F
 sta dos64_cga_index
 rts
@data:
 ldx dos64_cga_index
 cpx #16
 bcs @ignored            ; light-pen latches readonly; reserved selections no latch
 and cga_masks,x
 sta dos64_cga_registers,x
@ignored:
 rts
; Original MC6845 implemented bit widths; R14/R15 are the only RW pair.
cga_masks: .byte $FF,$FF,$FF,$0F,$7F,$1F,$7F,$7F,$03,$1F,$7F,$1F,$3F,$FF,$3F,$FF
