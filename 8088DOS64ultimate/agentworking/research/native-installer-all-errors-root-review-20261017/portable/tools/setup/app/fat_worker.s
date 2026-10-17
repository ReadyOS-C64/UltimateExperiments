.setcpu "6502"
.ifndef DOS64_ALL_FILE_DIAGNOSTICS
DOS64_ALL_FILE_DIAGNOSTICS=0
.endif
.macpack longbranch
.include "coordinator_internal.inc"
.importzp sreg,ptr1
.import pusheax,pushax,pusha
.import _rc_retained,_so_fat_ticket,_so_capacity
.import _nc_begin,_nc_end,_nc_service,_nc_error,_nc_prepared,_nc_closed_quiet
.if DOS64_ALL_FILE_DIAGNOSTICS
.import _nc_transport_error,_fd_transport
.endif
.import _ns_capacity,_ns_io_owner,_ns_cancel,_ns_io_error
.import _fp_selection,_fp_prepare_c,_fp_prepare_b,_fp_prepare_a
.import _nf_plan,_nf_import_dos,_nf_consumed,_nf_inactive,_nf_error
.import _nf_store_write,_nf_store_read,_nf_sector
.import _si_request,_si_result,_si_now,_si_begin,_si_poll,_si_cancel,_si_state,_si_error,_si_closed_quiet,_si_rearm
.import _si_cleanup_begin,_si_cleanup_poll,_si_cleanup_state,_si_cleanup_error,_ps_clock_poll
.import _bc_slot,_bc_clear_error
.import _ps_ticks,_bc_config,_br_request,_sq_page,_sq_read,_sq_bytes,_sq_error
.export _fw_run,_fw_internal,fw_worker_start,fw_worker_end
.ifndef DOS64_ALL_FILE_DIAGNOSTICS
DOS64_ALL_FILE_DIAGNOSTICS=0
.endif
.if DOS64_ALL_FILE_DIAGNOSTICS
.import _fd_set_path,_fd_code,_fd_op,_fd_leaf
.importzp _fd_origin
.endif
.segment "BSS"
_fw_internal: .res 14
.assert *-_fw_internal=14,error,"FW internal ABI14"
STATE=_fw_internal
ERROR=_fw_internal+1
LEAF=_fw_internal+2
CLEAN=_fw_internal+3
FLAGS=_fw_internal+4
DERIVED=_fw_internal+5
TICKET=_fw_internal+6
GUARD=_fw_internal+8
TEXT=_fw_internal+11
SLASH=_fw_internal+12
OPENED=_fw_internal+13
.segment "FAT_CODE"
fw_worker_start:
selection_reason:
 sta LEAF
 lda #6
 jmp first
_fw_run:
 jsr admit
 cmp #1
 jne reject
 lda #<$2710
 sta _si_request+5
 lda #>$2710
 sta _si_request+6
 ldy #127
@home:
 lda _rc_retained,y
 sta _si_request+7,y
 dey
 bpl @home
 lda FLAGS
 and #2
 beq @fresh
 jsr existing_open
 cmp #1
 jne nc_fail
@fresh:
 lda FLAGS
 .if DOS64_ALL_FILE_DIAGNOSTICS
 jsr fd_prepare_c
 .else
 jsr _fp_prepare_c
 .endif
 tax ; C ABI promises A result, not NZ after software-stack cleanup.
 jne nf_fail
 lda FLAGS
 and #2
 beq @plan
 ; Explicit logical merge: preserve preexisting convenience names; reject
 ; archival DOS/DISK1..3 collisions, never silently replace imported files.
 jsr _nf_import_dos
 tax ; C ABI promises A result, not NZ after software-stack cleanup.
 jne nf_fail
@plan:
 .if DOS64_ALL_FILE_DIAGNOSTICS
 jsr fd_plan_c
 .else
 jsr _nf_plan
 .endif
 tax ; C ABI promises A result, not NZ after software-stack cleanup.
 jne nf_fail
 lda #0
 jsr writer
 jeq reject
 lda FLAGS
 and #2
 beq @closed
 lda #3
 sta _br_request
 jsr _nc_prepared
 cmp #1
 jne nc_fail
@closed:
 lda #0
 sta OPENED
 jsr _si_rearm
 cmp #1
 jne input_fail
 lda FLAGS
 .if DOS64_ALL_FILE_DIAGNOSTICS
 jsr fd_prepare_b
 .else
 jsr _fp_prepare_b
 .endif
 tax ; C ABI promises A result, not NZ after software-stack cleanup.
 jne nf_fail
 lda #1
 jsr writer
 jeq reject
 ; C/B slabs are no longer live. Stage actual owned startup text and read it
 ; back before derivingA into200000; no overlaid replacement from this frame.
 lda #0
 sta TEXT
 jsr stage_text
 jeq nf_fail
 inc TEXT
 jsr stage_text
 jeq nf_fail
 lda FLAGS
 jsr pusha
 lda #<AUTO_BYTES
 ldx #>AUTO_BYTES
 jsr pushax
 lda #<CONFIG_BYTES
 ldx #>CONFIG_BYTES
 .if DOS64_ALL_FILE_DIAGNOSTICS
 jsr fd_prepare_a
 .else
 jsr _fp_prepare_a
 .endif
 tax ; C ABI promises A result, not NZ after software-stack cleanup.
 jne nf_fail
 jsr _nc_end
 cmp #1
 jne nc_fail
 jsr _so_fat_ticket
 cmp TICKET
 jne input_fail
 cpx TICKET+1
 jne input_fail
 lda #1
 sta DERIVED
 lda #2
 sta STATE
 lda #1
 ldx #0
 rts
.segment "AUX_CODE"
admit:
 lda STATE
 jne reject
 lda #1
 sta STATE
 lda _rc_retained+RC_VALID
 cmp #1
 jne input_fail
 lda _rc_retained+RC_SOURCE_MASK
 cmp #31
 jne input_fail
 jsr _so_fat_ticket
 sta TICKET
 stx TICKET+1
 ora TICKET+1
 jeq input_fail
 jsr _nc_begin
 cmp #1
 jne nc_fail
 jsr _fp_selection
 cmp #$80
 jcc input_fail
 cmp #$84
 jcs input_fail
 sta FLAGS
 and #3
 cmp _rc_retained+RC_FLAGS
 jne input_fail
 ; One private capacity source. Inputs cannot substitute config/public facts.
 lda #$a5
 sta _si_request
 sta _bc_config
 lda #1
 sta _bc_config+1
 ldy #3
@capacity:
 lda _ns_capacity,y
 sta _si_request+1,y
 sta _bc_config+2,y
 dey
 bpl @capacity
 lda #1
 rts
input_fail:
 jsr _sq_error
 jne selection_reason
 lda #1
 bne first
nf_fail:
 jsr _nc_error
 bne nc_reason
 lda _nf_error
 sta LEAF
 lda #2
 bne first
nc_fail:
 jsr _nc_error
 bne nc_reason
 jsr _sq_error
 jne selection_reason
nc_reason:
 sta LEAF
 lda #3
first:
 ldx ERROR
 bne failed
.if DOS64_ALL_FILE_DIAGNOSTICS
 jsr fd_fw_first
.else
 sta ERROR
.endif
failed:
 jsr _si_cleanup_begin
 cmp #1
 bne @source
@drain:
 jsr _ps_clock_poll
 lda _ps_ticks
 sta _si_now
 lda _ps_ticks+1
 sta _si_now+1
 jsr _si_cleanup_poll
 jsr _si_cleanup_state
 cmp #1
 beq @drain
@source:
 lda OPENED
 beq @quiet
 jsr _nc_closed_quiet
 cmp #1
 beq @quiet
 lda #3
 sta _br_request
 jsr _nc_prepared
@quiet:
 jsr _si_cleanup_error
 sta CLEAN
 jsr _si_closed_quiet
 bne :+
 lda CLEAN
 ora #$80
 sta CLEAN
:
 lda #3
 sta STATE
reject:
 lda #0
 tax
 rts
; Parse existing path from verified capsule BEFORE opening source0. Read may
; only run while closedquiet; no capsule manager call after source OPEN.
existing_open:
 ; Fresh readonly lifecycle after completed SO asset loading. Authentic FAT
 ; admission proved BOTHclosed/quiet; clear only the selected closed context's
 ; past handled EOF, before any new OPEN/current-worker firstcause.
 lda #0
 sta _bc_slot
 jsr _bc_clear_error
 tax
 beq reject
 lda #1
 sta _sq_page
 jsr _sq_read
 cmp #192
 jne reject
 cpx #0
 jne reject
 lda _sq_bytes
 clc
 adc #32
 sta ptr1
 lda _sq_bytes+1
 adc #0
 sta ptr1+1
 ldy #0
 sty SLASH
@path:
 lda (ptr1),y
 sta _br_request+14,y
 cmp #'/'
 bne :+
 sty SLASH
:
 iny
 cpy #128
 bne @path
 ldy #0
@root:
 cpy SLASH
 beq @endroot
 lda _br_request+14,y
 sta _bc_config+6,y
 iny
 bne @root
@endroot:
 lda #0
 sta _bc_config+6,y
 lda #2
 sta _br_request
 lda #1
 sta _br_request+1
 .if DOS64_ALL_FILE_DIAGNOSTICS
 jsr fd_existing_open
 .else
 jsr _nc_prepared
 .endif
 cmp #1
 jne reject
 inc OPENED
 lda #7
 sta _br_request
 jmp _nc_prepared
; A=0C/1B. SI state() refreshes observations from PRIVATE ledger before
; immediate trusted masked copy; caller cannot inject facts between calls.
.if DOS64_ALL_FILE_DIAGNOSTICS
writer:
 jsr fd_output_path
 cmp #1
 jne reject
 jmp fd_writer_continue
fd_output_path:
.else
writer:
.endif
 sta TEXT
 ldy #0
@outroot:
 lda _rc_retained,y
 sta _si_request+135,y
 beq @leaf
 iny
 cpy #122 ; root plus /C.IMG and NUL must fit the canonical128B path.
 bcc @outroot
 jmp input_fail
@leaf:
 lda #'/'
 sta _si_request+135,y
 iny
 ldx TEXT
 lda leaves,x
 sta _si_request+135,y
 iny
 ldx #0
@suffix:
 lda suffix,x
 sta _si_request+135,y
 iny
 inx
 cpx #5
 bne @suffix
.if DOS64_ALL_FILE_DIAGNOSTICS
 lda #1
 rts
fd_writer_continue:
.endif
 jsr _nc_service
 cmp #1
 jne nc_fail
 lda _ps_ticks
 sta _si_now
 lda _ps_ticks+1
 sta _si_now+1
 jsr _si_begin
 cmp #1
 jne si_fail
@poll:
 jsr _si_poll
 jsr _si_error
 jne si_fail
 jsr _si_state
 cmp #3
 jeq si_fail
 cmp #2
 beq @complete
 jsr _nc_service
 cmp #1
 beq @time
 jsr _si_cancel
@time:
 lda _ps_ticks
 sta _si_now
 lda _ps_ticks+1
 sta _si_now+1
 inc GUARD
 bne @poll
 inc GUARD+1
 bne @poll
 inc GUARD+2
 bne @poll
 jsr _si_cancel
 lda #4
 jmp first
@complete:
 jsr _nf_consumed
 cmp #1
 jne input_fail
 jsr _si_state
 cmp #2
 jne si_fail
 ; Fresh private-backed counts must match the actual profile geometry.
 ldx #3
@counts:
 lda _si_result+4,x
 cmp _si_result+8,x
 jne input_fail
 lda TEXT
 bne @bsize
 lda FLAGS
 and #1
 tay
 lda c_size0,x
 cpy #0
 beq @size
 lda c_size1,x
 jmp @size
@bsize:
 lda b_size,x
@size:
 cmp _si_result+4,x
 jne input_fail
 dex
 bpl @counts
 lda TEXT
 asl a
 asl a
 asl a
 tay
 ldx #0
@receipt:
 lda _si_result+4,x
 sta _rc_retained+RC_OUTPUT,y
 lda _si_result+12,x
 sta _rc_retained+RC_OUTPUT+4,y
 iny
 inx
 cpx #4
 bne @receipt
 lda TEXT
 tax
 lda masks,x
 ora _rc_retained+RC_OUTPUT_MASK
 sta _rc_retained+RC_OUTPUT_MASK
 lda #1
 rts
si_fail:
 jsr _nc_error
 jne nc_reason
 lda _si_result+1
 sta LEAF
 lda #5
 jmp first
; Actual staging writes followed by exact byte readback; sources at fixed,
; disjoint3DA000/3DC000, exclusively owned for derivedA startup files.
.macro PUSH_REU
 ldx TEXT
 lda text_low,x
 tax
 lda #0
 ldy #$3d
 sty sreg
 ldy #0
 sty sreg+1
 jsr pusheax
.endmacro
stage_text:
 PUSH_REU
 ldx TEXT
 lda text_ptr_lo,x
 pha
 lda text_ptr_hi,x
 tax
 pla
 jsr pushax
 ldx TEXT
 lda text_length,x
 ldx #0
 jsr _nf_store_write
 ldx TEXT
 cmp text_length,x
 bne stage_reject
 PUSH_REU
 lda #<_nf_sector
 ldx #>_nf_sector
 jsr pushax
 ldx TEXT
 lda text_length,x
 ldx #0
 jsr _nf_store_read
 ldx TEXT
 cmp text_length,x
 bne stage_reject
 lda text_ptr_lo,x
 sta ptr1
 lda text_ptr_hi,x
 sta ptr1+1
 ldy #0
@compare:
 lda (ptr1),y
 cmp _nf_sector,y
 bne stage_reject
 iny
 tya
 cmp text_length,x
 bne @compare
 lda #1
 rts
stage_reject:
 lda #0
 rts
fw_worker_end:
.segment "RODATA"
leaves: .byte 'C','B'
.if DOS64_ALL_FILE_DIAGNOSTICS
.byte 'A'
.endif
suffix: .byte ".IMG",0
masks: .byte RC_C_MASK,RC_B_MASK
c_size0: .dword $200000
c_size1: .dword $1400000
b_size: .dword 368640
; LowWORD destinations are A000/C000, not CPU pointers.
text_low: .byte $a0,$c0
text_ptr_lo: .byte <auto_text,<config_text
text_ptr_hi: .byte >auto_text,>config_text
text_length: .byte AUTO_BYTES,CONFIG_BYTES
auto_text: .byte "@ECHO OFF",13,10,"PATH C:\DOS;C:\",13,10,"C:",13,10
AUTO_BYTES=*-auto_text
config_text: .byte "FILES=20",13,10,"BUFFERS=10",13,10
CONFIG_BYTES=*-config_text

; Explicit empty segment gives the qualified copier a zero RO length symbol.
.segment "AUX_RO"

.if DOS64_ALL_FILE_DIAGNOSTICS
.segment "AUX_CODE"
; Composition-only presentation wrappers reuse the real writer's canonical
; output-path builder. No C software-stack arguments or private receipts change.
fd_metadata:
 jsr fd_output_path
 cmp #1
 bne @bad
 lda #<(_si_request+135)
 ldx #>(_si_request+135)
 jsr _fd_set_path
 lda #7
 sta _fd_origin
 lda #0
 rts
@bad:
 lda #1
 rts
fd_prepare_c:
 lda OPENED
 bne @existing
 lda #0
 jsr fd_metadata
 bne @bad
@existing:
 lda FLAGS
 jmp _fp_prepare_c
@bad: rts
fd_plan_c:
 lda #0
 jsr fd_metadata
 bne @bad
 jmp _nf_plan
@bad:rts
fd_existing_open:
 lda #<(_br_request+14)
 ldx #>(_br_request+14)
 jsr _fd_set_path
 lda #1
 sta _fd_origin
 jmp _nc_prepared
fd_prepare_b:
 lda #1
 jsr fd_metadata
 bne @bad
 lda FLAGS
 jmp _fp_prepare_b
@bad: rts
fd_prepare_a:
 pha
 txa
 pha
 lda #2
 jsr fd_metadata
 pla
 tax
 pla
 jmp _fp_prepare_a
.endif

.if DOS64_ALL_FILE_DIAGNOSTICS
.segment "FILE_DIAG"
; Called at the original private FW first-cause STORE, before cleanup can fail.
fd_fw_first:
 sta ERROR
 ldx _fd_code
 bne @done
 sta _fd_code
 jsr fd_fw_detail
 sta _fd_transport
 lda _fd_origin
 sta _fd_op
@done:rts
.endif

.if DOS64_ALL_FILE_DIAGNOSTICS
.segment "CODE"
fd_fw_detail:
 lda LEAF
 sta _fd_leaf
 jmp _nc_transport_error
.endif
