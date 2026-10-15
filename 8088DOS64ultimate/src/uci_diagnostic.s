; PRIVATE native-only first-error record. Publish A5 last; fresh ENTRY resets.
.setcpu "6502"
.import dos64_uci_state_start,dos64_uci_state_end,dos64_uci_command,dos64_uci_error
.export dos64_uci_trace_reset,dos64_uci_trace_first
.export dos64_uci_trace_start,dos64_uci_trace_end,dos64_uci_trace_valid
.export dos64_uci_trace_state,dos64_uci_trace_command
.export dos64_uci_trace_first_id,dos64_uci_trace_last_id
.segment "DEVICESTATE"
dos64_uci_trace_start:
.res 4
.res 1
dos64_uci_trace_valid:.res 1
dos64_uci_trace_state:.res 42
dos64_uci_trace_command:.res 128
dos64_uci_trace_first_id:.res 1
dos64_uci_trace_end:
dos64_uci_trace_last_id:.res 1
.segment "HDBIOS"
dos64_uci_trace_reset:
 lda #0
 sta dos64_uci_trace_valid
 sta dos64_uci_trace_first_id
 sta dos64_uci_trace_last_id
 rts
dos64_uci_trace_first:
 lda dos64_uci_trace_valid
 cmp #$a5
 beq done
 ldx #41
copy_state:
 lda dos64_uci_state_start,x
 sta dos64_uci_trace_state,x
 dex
 bpl copy_state
 ldx #127
copy_command:
 lda dos64_uci_command,x
 sta dos64_uci_trace_command,x
 dex
 bpl copy_command
 ; INPUT rejects before an ID read. Store zero with error1 meaning unobserved.
 lda dos64_uci_error
 cmp #1
 beq no_identifier
 lda dos64_uci_trace_last_id
 jmp store_identifier
no_identifier:
 lda #0
store_identifier:
 sta dos64_uci_trace_first_id
 ldx #4
copy_magic:
 lda magic,x
 sta dos64_uci_trace_start,x
 dex
 bpl copy_magic
 lda #$a5
 sta dos64_uci_trace_valid
 done:rts
magic:.byte "UCF2",2
.assert dos64_uci_state_end-dos64_uci_state_start=42,lderror,"Trace state ABI changed"
