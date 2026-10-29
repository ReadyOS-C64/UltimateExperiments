.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "cache/rekey-probe/rekey.inc"
.include "cache/arena/api.inc"
.include "fold/source.inc"
.import se_f_owner,se_render_caps,se_overlay_call,se_overlay_frame
.import se_crc_init,se_crc_byte,se_crc_value
.import se_bc_arena_open,bca_open_step,bca_guard,bca_transfer,bca_crc_root,bca_root_check
.export entry
.macro CP from,to,n
 .local loop
 ldx #n-1
loop:lda from,x
 sta to,x
 dex
 bpl loop
.endmacro
.macro EQ from,to,n
 .local loop
 ldx #n-1
loop:lda from,x
 cmp to,x
 jne stale
 dex
 bpl loop
.endmacro
.macro C24 lhs,rhs
 .local loop,done
 ldx #2
loop:lda lhs,x
 cmp rhs,x
 bne done
 dex
 bpl loop
 lda #0
done:
.endmacro
.segment "CODE"
 OVL_BINDING
entry:
 lda se_f_owner
 cmp #4
 jne busy
 lda se_overlay_frame
 beq begin
 cmp #1
 jeq step
 cmp #2
 jne bad
 lda RK_ABI
 cmp #$52
 jne bad
 jsr release
 lda #0
 clc
 rts
busy:lda #$B2
 sec
 rts
bad:lda #$C0
 sec
 rts
stale:lda #$C1
 sec
 rts
corrupt:lda #$C2
 sec
 rts
miss:lda #2
 clc
 rts
pending:lda #1
 clc
 rts
begin:
 lda se_render_caps
 cmp #1
 beq :+
 cmp #3
 jne miss
:lda se_bc_flags
 and #(BC_ARMED|BC_LOST|BC_MUTATING|BC_ACTIVE)
 cmp #BC_ARMED
 jne miss
 lda se_doc_read_locks
 jne miss
 lda se_bc_count
 cmp #1
 jne miss
 lda se_bc_head
 cmp #3
 jcs miss
 lda se_bc_tail
 cmp #3
 jcs miss
 lda #0
 tax
begin_clear:sta RK,x
 sta RK+256,x
 dex
 bne begin_clear
 ldx #63
begin_tail:sta RK+512,x
 dex
 bpl begin_tail
 lda #$52
 sta RK_ABI
 CP se_bc_arena,RK_AUTH,13
 lda se_bc_head
 sta RK_HEAD
 lda se_bc_tail
 sta RK_TAIL
 clc
 adc #1
 cmp #3
 bcc :+
 lda #0
:cmp RK_HEAD
 jne miss ;malformed ring never acquires a reader or writes REU
 lda #1
 sta RK_COUNT
 lda RK_TAIL
 .repeat 5
 asl
 .endrepeat
 sta RK_SLOT
 tay
 ldx #0
begin_event:lda se_bc_ring,y
 sta RK_EVENT,x
 iny
 inx
 cpx #32
 bcc begin_event
 jsr event_check
 jcs return
 lda se_bc_flags
 ora #BC_ACTIVE
 sta se_bc_flags
 lda #RK_PHASE_OPEN
 sta RK_STATE
 jsr se_bc_arena_open
 jcs failed
 jmp pending
step:
 lda RK_ABI
 cmp #$52
 jne bad
 lda RK_STATE
 jeq bad
 jsr guard
 jcs failed
 lda RK_LIVE
 beq step_dispatch
 lda #1
 jsr source
 jcs failed
step_dispatch:
 lda RK_STATE
 cmp #RK_PHASE_OPEN
 jeq open_step
 cmp #RK_PHASE_SOURCE
 jeq source_begin
 cmp #RK_PHASE_JOURNAL
 jeq journal
 cmp #RK_PHASE_JVALID
 jeq journal_valid
 cmp #RK_PHASE_ROOT
 jeq write_root
 cmp #RK_PHASE_VALID
 jeq commit
 lda #$C0
 jmp failed
return:rts
failed:
 pha
 jsr release
 pla
 sta RK_ERROR
 sec
 rts
guard:
 EQ RK_AUTH,se_bc_arena,13
 lda se_bc_flags
 and #(BC_ARMED|BC_LOST|BC_MUTATING|BC_ACTIVE)
 cmp #(BC_ARMED|BC_ACTIVE)
 jne stale
 lda se_bc_head
 cmp RK_HEAD
 jne stale
 lda se_bc_tail
 cmp RK_TAIL
 jne stale
 lda se_bc_count
 cmp RK_COUNT
 jne stale
 ldy RK_SLOT
 ldx #0
guard_event:lda se_bc_ring,y
 cmp RK_EVENT,x
 jne stale
 iny
 inx
 cpx #32
 bcc guard_event
 jmp bca_guard
event_check:
 lda RK_EVENT
 cmp #BC_EVENT_VALID
 jne corrupt
 lda RK_EVENT+1
 cmp #BC_EVENT_REKEY
 jne stale
 lda RK_EVENT+2
 ora RK_EVENT+3
 ora RK_EVENT+31
 jne corrupt
 EQ RK_EVENT+4,RK_AUTH+5,4
 EQ RK_EVENT+8,RK_EVENT+12,4
 jsr se_crc_init
 ldy #1
event_check_crc:lda RK_EVENT,y
 jsr se_crc_byte
 iny
 cpy #29
 bcc event_check_crc
 lda RK_EVENT+31
 jsr se_crc_byte
 EQ se_crc_value,RK_EVENT+29,2
 clc
 rts
open_step:
 jsr bca_open_step
 jcs failed
 cmp #0
 jne pending
 CP BC_IO,RK_ROOT,128
 jsr root_admit
 jcs failed
 lda #RK_PHASE_SOURCE
 sta RK_STATE
 jmp pending
root_admit:
 ; This first bridge appends exactly one representation event to a baseline.
 lda RK_ROOT+31
 cmp #1
 jne stale
 lda RK_ROOT+30
 jne stale
 lda RK_ROOT+94
 cmp #1
 jne stale
 lda RK_ROOT+96
 cmp #1
 jne stale
 lda RK_ROOT+100
 cmp #1
 jne stale
 lda RK_ROOT+95
 ora RK_ROOT+97
 ora RK_ROOT+98
 ora RK_ROOT+99
 ora RK_ROOT+101
 ora RK_ROOT+102
 ora RK_ROOT+103
 jne stale
 EQ RK_ROOT+22,RK_AUTH+5,4
 EQ RK_ROOT+26,RK_AUTH+5,4
 lda RK_ROOT+32+30 ;rootSOURCE+pending
 cmp #1
 jne stale
 lda RK_ROOT+32+29
 cmp #1
 jne stale
 lda RK_ROOT+32+31
 ora RK_ROOT+32+32
 ora RK_ROOT+32+33
 jne stale
 clc
 rts
refuse:
 jsr release
 jmp miss
source_begin:
 lda #0
 jsr source
 jcs failed
 lda #1
 sta RK_LIVE
 jsr pair_check
 jcs failed
 lda BCA_SELECTED
 eor #128
 sta RK_DEST
 lda #RK_PHASE_JOURNAL
 sta RK_STATE
 jmp pending
; Fresh current59 is always the actual checked R14 capture. It is never forged
; from old geometry. Old semantic ticket stays unchanged, including every CR.
pair_check:
 EQ RK_ROOT+32,RK_READER+27,4 ;provider/document epochs
 EQ RK_ROOT+38,RK_READER+33,15 ;allthree typed source tokens
 EQ RK_ROOT+57,RK_EVENT+8,4 ;oldvisible revision
 EQ RK_READER+52,RK_EVENT+12,4 ;newvisible revision
 EQ RK_ROOT+36,RK_EVENT+25,2 ;oldgeneration
 EQ RK_READER+31,RK_EVENT+27,2 ;newgeneration
 EQ RK_ROOT+91,RK_READER+10,3 ;actualmerged lengthunchanged
 lda RK_READER+57 ;currentFS pending30
 jne stale
 ; Representation publication is generation+1, or unchanged for zero/zero.
 lda RK_EVENT+19
 ora RK_EVENT+20
 ora RK_EVENT+21
 ora RK_EVENT+22
 ora RK_EVENT+23
 ora RK_EVENT+24
 beq pair_check_zero
 clc
 lda RK_EVENT+25
 adc #1
 sta RK_WORK
 lda RK_EVENT+26
 adc #0
 jcs stale
 sta RK_WORK+1
 EQ RK_WORK,RK_EVENT+27,2
 jmp pair_check_length
pair_check_zero:EQ RK_EVENT+25,RK_EVENT+27,2
pair_check_length:
 ; committedAfter=committedBefore-delete+insert, with full24-bit carry.
 sec
.repeat 3,I
 lda RK_ROOT+53+I
 sbc RK_EVENT+19+I
 sta RK_WORK+I
.endrepeat
 jcc stale
 clc
.repeat 3,I
 lda RK_WORK+I
 adc RK_EVENT+22+I
 sta RK_WORK+I
.endrepeat
 jcs stale
 EQ RK_WORK,RK_READER+48,3
 EQ RK_WORK,RK_ROOT+91,3
 ; The trusted minimal flush tuple must lie inside both frozen hotwindows.
 sec
.repeat 3,I
 lda RK_EVENT+16+I
 sbc RK_ROOT+80+I
 sta RK_WORK+I
.endrepeat
 jcc stale
 lda RK_WORK+2
 jne stale
 clc
 lda RK_ROOT+83
 adc RK_ROOT+80
 sta RK_WORK+3
 lda RK_ROOT+84
 adc RK_ROOT+81
 sta RK_WORK+4
 lda RK_ROOT+82
 adc #0
 sta RK_WORK+5
 jcs stale
 clc
.repeat 3,I
 lda RK_EVENT+16+I
 adc RK_EVENT+19+I
 sta RK_WORK+6+I
.endrepeat
 jcs stale
 C24 RK_WORK+6,RK_WORK+3
 jcc pair_check_new_window
 jne stale
pair_check_new_window:
 clc
 lda RK_ROOT+85
 adc RK_ROOT+80
 sta RK_WORK+3
 lda RK_ROOT+86
 adc RK_ROOT+81
 sta RK_WORK+4
 lda RK_ROOT+82
 adc #0
 sta RK_WORK+5
 jcs stale
 clc
.repeat 3,I
 lda RK_EVENT+16+I
 adc RK_EVENT+22+I
 sta RK_WORK+6+I
.endrepeat
 jcs stale
 C24 RK_WORK+6,RK_WORK+3
 jcc pair_check_ok
 jne stale
pair_check_ok:clc
 rts
journal:
 CP RK_EVENT,BC_IO,32
 lda #0
 sta BC_IO
 sta BCA_OFFSET
 sta BCA_OFFSET+2
 lda #9
 sta BCA_OFFSET+1
 lda #32
 sta BCA_LENGTH
 lda #0
 jsr transfer
 jcs failed
 inc RK_STATE
 jmp pending
journal_valid:
 lda #BC_EVENT_VALID
 sta BC_IO
 lda #1
 sta BCA_LENGTH
 lda #0
 sta BCA_OFFSET
 sta BCA_OFFSET+2
 lda #9
 sta BCA_OFFSET+1
 lda #0
 jsr transfer
 jcs failed
 inc RK_STATE
 jmp pending
write_root:
 CP RK_ROOT,BC_IO,128
 CP RK_READER+27,BC_IO+32,59
 lda #1
 sta BC_IO+30
 ldx #0
write_root_seq:inc BC_IO+18,x
 bne write_root_seq_ok
 inx
 cpx #4
 bcc write_root_seq
 jmp failed_stale
write_root_seq_ok:
 jsr bca_crc_root
 CP se_crc_value,BC_IO+119,2
 ; Check the exact candidate withVALID1; store its staged copy withVALID0.
 jsr bca_root_check
 jcs failed
 CP BC_IO,RK_ROOT,128
 lda #0
 sta BC_IO+5
 lda RK_DEST
 sta BCA_OFFSET
 lda #0
 sta BCA_OFFSET+1
 sta BCA_OFFSET+2
 lda #128
 sta BCA_LENGTH
 lda #0
 jsr transfer
 jcs failed
 inc RK_STATE
 jmp pending
failed_stale:
 lda #$C1
 jmp failed
commit:
 ; R14GUARD already ran this STEP. Reconstruct IO after its overlapping frame.
 CP RK_ROOT,BC_IO,128
 jsr bca_root_check
 jcs failed
 jsr current_root_source
 jcs failed
 lda RK_DEST
 clc
 adc #5
 sta BCA_OFFSET
 lda #0
 sta BCA_OFFSET+1
 sta BCA_OFFSET+2
 lda #1
 sta BC_IO
 sta BCA_LENGTH
 lda #0
 jsr transfer
 jcs failed
 ; Durable event + rootVALID are now published. Retire exactly this one event
 ; without yielding; a queued key cannot edit source inside this foreground unit.
 lda RK_HEAD
 sta se_bc_tail
 lda #0
 sta se_bc_count
 jsr release
 lda #0
 clc
 rts
current_root_source:
 EQ RK_ROOT+32,RK_READER+27,59
 clc
 rts
transfer:
 ; R14 validates source objects and may change the global object request token.
 ; Restore and revalidate the captured type53 capability immediately before DMA.
 pha
 jsr bca_guard
 bcs transfer_error
 pla
 jmp bca_transfer
transfer_error:
 pla
 lda #$C1
 sec
 rts
; Context exchange is identical to the established cache job cleanup ABI.
source:
 pha
 CP RK_READER,se_fs_state,86
 pla
 sta se_overlay_frame
 lda #14
 ldx #0
 jsr se_overlay_call
 php
 pha
 CP se_fs_state,RK_READER,86
 pla
 plp
 rts
release:
 lda RK_LIVE
 beq release_clear
 CP RK_READER,se_fs_state,86
 jsr se_fs_end
 lda #0
 sta RK_READER+7
 sta RK_READER+8
release_clear:
 lda se_bc_flags
 and #($FF-BC_ACTIVE-BC_PAGE_PROOF)
 sta se_bc_flags
 lda #0
 sta RK_STATE
 sta RK_LIVE
 rts
