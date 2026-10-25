; Initial semantic baseline writer. Completed output only, never inferred hits.
.setcpu "6502"
.macpack longbranch
.include "cache/arena/writer.inc"
.include "cache/semantic/api.inc"
.include "object/api.inc"
.import se_f_owner,se_reu_epoch,se_doc_epoch,se_doc_generation,se_doc_validate
.import se_doc_meta,se_doc_original,se_doc_append,se_doc_length,se_doc_root_count
.import se_r_revision,se_hot_ready,se_hot_pending,se_hot_phase,se_hot_owned,se_hot_fault
.import se_hot_epoch,se_hot_generation,se_hot_original,se_hot_append,se_hot_base
.import se_hot_old_length,se_hot_length,se_hot_left,se_hot_right,se_doc_read_locks
.import se_crc_init,se_crc_byte,se_crc_value
.import bca_owner,bca_guard,bca_validate,bca_transfer,bca_crc_root,bca_root_check,bca_pending,bca_done,bca_bad,bca_stale,bca_corrupt
.export se_bc_write_begin,se_bc_write_append,se_bc_write_final,se_bc_write_step,se_bc_write_cancel
.macro EQ source,target,n
 ldy #n-1
:
 lda source,y
 cmp target,y
 jne bca_stale
 dey
 bpl :-
.endmacro
.macro CP source,target,n
 ldy #n-1
:
 lda source,y
 sta target,y
 dey
 bpl :-
.endmacro
.macro LIVE source,off,n
 EQ source,BSC_READER+27+off,n
.endmacro
.segment "CODE"
; Caller has just completed an actual R14 guard. Still compare all59 source
; identity bytes to live fields at EVERY boundary; no guessed revision witness.
bw_guard:
 jsr bca_guard
 jcs @return
 EQ BSC_AUTH,BSC_F+BCF_ARENA,13
 EQ BSC_AUTH,BCA_BOUND,13
 lda BSC_F+BCF_ABI
 cmp #1
 jne bca_bad
 lda BSC_F+BCF_CAPS
 jeq @bad
 cmp #1
 beq :+
 cmp #3
 jne @bad
:
 lda se_bc_flags
 and #BC_ARMED
 jne bca_bad
 LIVE se_reu_epoch,0,2
 LIVE se_doc_epoch,2,2
 LIVE se_doc_generation,4,2
 LIVE se_doc_meta,6,5
 LIVE se_doc_original,11,5
 LIVE se_doc_append,16,5
 LIVE se_doc_length,21,3
 LIVE se_doc_root_count,24,1
 LIVE se_r_revision,25,4
 LIVE se_hot_ready,29,1
 LIVE se_hot_pending,30,1
 LIVE se_hot_phase,31,1
 LIVE se_hot_owned,32,1
 LIVE se_hot_fault,33,1
 LIVE se_hot_epoch,34,2
 LIVE se_hot_generation,36,2
 LIVE se_hot_original,38,5
 LIVE se_hot_append,43,5
 LIVE se_hot_base,48,3
 LIVE se_hot_old_length,51,2
 LIVE se_hot_length,53,2
 LIVE se_hot_left,55,2
 LIVE se_hot_right,57,2
 EQ BSC_LENGTH,BSC_READER+10,3
 ; Provider graph may change without a source-byte revision (fault injection,
 ; provider failure). Authenticate all three live source capabilities too.
 jsr se_doc_validate
 jcs @return
 CP se_doc_meta,se_object_id,5
 jsr se_object_validate
 jcs @return
 CP se_doc_original,se_object_id,5
 jsr se_object_validate
 jcs @return
 CP se_doc_append,se_object_id,5
 jsr se_object_validate
 jcs @return
 ; Restore arena request capability after the source checks, no DMA yet.
 jmp bca_validate
@return:rts
@bad:jmp bca_bad
; R33 BEGIN after OPEN and actual BSC_BEGIN; no outstanding output packet.
se_bc_write_begin:
 jsr bca_owner
 jcs @return
 lda BCA_PHASE
 jne bca_bad
 lda BSC_F+BCF_READY
 jne bca_bad
 jsr bw_guard
 jcs @return
 lda BSC_READER+7
 and BSC_READER+8
 cmp #1
 jne bca_bad
 lda se_doc_read_locks
 jeq bca_stale
 lda se_bc_flags
 and #BC_LOST
 beq :+
 lda BSC_F+BCF_BUDGET
 and #BW_REBUILD
 jeq bca_stale
:
 lda BCA_SELECTED
 sta BCA_OFFSET
 lda #0
 sta BCA_OFFSET+1
 sta BCA_OFFSET+2
 lda #128
 sta BCA_LENGTH
 lda #1
 jsr bca_transfer
 jcs @return
 jsr bca_root_check
 jcs @return
 CP BC_IO+BC_ROOT_SEQUENCE,BCA_SEQUENCE,4
 lda BC_IO+BC_ROOT_FLAGS
 ora BC_IO+BC_ROOT_RECORDS
 ora BC_IO+BC_ROOT_RECORDS+1
 ora BC_IO+BC_ROOT_RECORDS+2
 jne bca_bad
 lda #0
 sta BW_CP
 sta BW_CS
 sta BW_IP
 sta BW_IS
 sta BW_RECORDS
 sta BW_RECORDS+1
 sta BW_RECORDS+2
 sta BW_EVENTS
 sta BW_EVENTS+1
 sta BW_EVENTS+2
 sta BW_USED_C
 sta BW_USED_C+1
 sta BW_USED_I
 sta BW_USED_I+1
 lda #$FF
 ldy #7
@refs:sta BW_FIRST,y
 dey
 bpl @refs
 ldy #3
@inline:sta BW_INLINE,y
 sta BW_CRC_C,y
 dey
 bpl @inline
 lda #1
 sta BW_FREE
 ; No stale orphan directory may authorize a page after an aborted baseline.
 lda #0
 sta BCA_CURSOR
 sta BCA_CURSOR+2
 lda #1
 sta BCA_CURSOR+1
 lda #BW_DIRECTORY
 sta BCA_PHASE
 lda se_bc_flags
 ora #BC_ACTIVE
 sta se_bc_flags
 jmp bca_pending
@return:rts
; APPEND accepts the producer's pending packet, which is not ACKed until done.
; IO118..127 is exclusive temporary storage beyond the source-exchange extent.
se_bc_write_append:
 jsr bca_owner
 jcs @return
 lda BCA_PHASE
 cmp #BW_IDLE
 jne bca_bad
 jsr bw_guard
 jcs @return
 lda BSC_F+BCF_READY
 cmp #1
 beq @cr
 cmp #2
 jne bca_bad
 sta BW_PENDING
 CP BC_IO,BC_IO+118,10
 jsr inline_crc
 CP se_crc_value,BW_STAGE,2
 jmp append_packet
@cr:
 sta BW_PENDING
 jmp append_packet
@return:rts
append_packet:
 lda BW_PENDING
 cmp #1
 beq @cr
 lda BW_IS
 cmp #255
 jeq @seal_i
 lda BW_IP
 bne @inline
 jsr allocate
 jcs stream_required
 sta BW_IP
@inline:
 jsr inline_crc
 EQ se_crc_value,BW_STAGE,2
 CP BC_IO+118,BC_IO,10
 lda #10
 ldx #1
 jmp @write
@seal_i:lda #2
 jmp @seal
@cr:
 lda BW_CS
 cmp #42
 jeq @seal_c
 lda BW_CP
 bne @record
 jsr allocate
 jcs stream_required
 sta BW_CP
@record:
 CP BSC_CR,BC_IO,96
 lda BC_IO
 cmp #1
 jne bca_bad
 lda BC_IO+1
 cmp #1
 jne bca_bad
 EQ BC_IO+12,BCA_TICKET,4
 EQ BC_IO+44,BW_EVENTS,3
 ; Producer validated spans/event grammar; verify its complete record CRC.
 jsr record_crc
 lda se_crc_value
 cmp BC_IO+74
 jne bca_corrupt
 lda se_crc_value+1
 cmp BC_IO+75
 jne bca_corrupt

 CP BW_INLINE,BC_IO+40,4
 lda #$FF
 ldy #7
@adjacent:sta BC_IO+76,y
 dey
 bpl @adjacent
 jsr record_crc
 CP se_crc_value,BC_IO+74,2
 lda #96
 ldx #0
@write:
 sta BCA_LENGTH
 stx BW_KIND
 jsr stream_offset
 ldx BW_KIND
 ; CRC words/used words are indexed by kind*2 below.
 txa
 asl
 tax
 lda BW_CRC_C,x
 sta se_crc_value
 lda BW_CRC_C+1,x
 sta se_crc_value+1
 ldy #0
@crc:lda BC_IO,y
 jsr se_crc_byte
 iny
 cpy BCA_LENGTH
 bne @crc
 lda #0
 jsr bca_transfer
 jcs @return
 ldx BW_KIND
 txa
 asl
 tax
 lda se_crc_value
 sta BW_CRC_C,x
 lda se_crc_value+1
 sta BW_CRC_C+1,x
 clc
 lda BW_USED_C,x
 adc BCA_LENGTH
 sta BW_USED_C,x
 bcc :+
 inc BW_USED_C+1,x
:
 lda BW_PENDING
 cmp #1
 beq @record_done
 lda BW_EVENTS
 ora BW_EVENTS+1
 ora BW_EVENTS+2
 bne :+
 lda BW_IP
 sta BW_INLINE
 lda BW_IS
 sta BW_INLINE+1
 lda #1
 sta BW_INLINE+2
 lda #0
 sta BW_INLINE+3
:
 inc BW_IS
 inc BW_EVENTS
 bne @appended
 inc BW_EVENTS+1
 bne @appended
 inc BW_EVENTS+2
 bne @appended
 jmp bca_bad
@record_done:
 lda BW_CP
 sta BW_LAST
 lda BW_CS
 sta BW_LAST+1
 lda #1
 sta BW_LAST+2
 lda #0
 sta BW_LAST+3
 lda BW_RECORDS
 ora BW_RECORDS+1
 ora BW_RECORDS+2
 bne @has_first
 CP BW_LAST,BW_FIRST,4
@has_first:
 inc BW_CS
 inc BW_RECORDS
 bne :+
 inc BW_RECORDS+1
 bne :+
 inc BW_RECORDS+2
:
 lda #0
 sta BW_EVENTS
 sta BW_EVENTS+1
 sta BW_EVENTS+2
 lda #$FF
 ldy #3
@clear_inline:sta BW_INLINE,y
 dey
 bpl @clear_inline
@appended:
 lda #BW_IDLE
 sta BCA_PHASE
 jmp bca_done
@seal_c:lda #1
@seal:
 sta BW_KIND
 jsr allocate
 jcs stream_required
 sta BW_NEXT
 jmp start_seal
@return:rts
; A new cachepage, not a physical bank. Never retain a truncated baseline.
allocate:
 lda BW_FREE
 cmp #15
 bcc @ok
 lda #BC_STREAM
 sec
 rts
@ok:inc BW_FREE
 clc
 rts
; KIND1CR/2INLINE; offset current page+64+used, X destroyed.
stream_offset:
 ldx BW_KIND
 cpx #0
 beq @cr
 lda BW_IP
 bne @page
@cr:lda BW_CP
@page:jsr page_offset
 ldx BW_KIND
 txa
 asl
 tax
 clc
 lda BW_USED_C,x
 adc #64
 sta BCA_OFFSET
 lda BW_USED_C+1,x
 adc BCA_OFFSET+1
 sta BCA_OFFSET+1
 rts
page_offset:
 pha
 lsr
 lsr
 lsr
 lsr
 sta BCA_OFFSET+2
 pla
 asl
 asl
 asl
 asl
 sta BCA_OFFSET+1
 lda #0
 sta BCA_OFFSET
 rts
record_crc:
 jsr se_crc_init
 ldy #1
@byte:cpy #74
 bne :+
 ldy #76
:
 lda BC_IO,y
 jsr se_crc_byte
 iny
 cpy #96
 bne @byte
 rts
; FINAL only after the actual producer has completely drained and released.
se_bc_write_final:
 jsr bca_owner
 jcs @return
 lda BCA_PHASE
 cmp #BW_IDLE
 jne bca_bad
 jsr bw_guard
 jcs @return
 lda BSC_F+BCF_STATE
 ora BSC_F+BCF_READY
 ora BSC_F+BCF_FLAGS
 ora BW_EVENTS
 ora BW_EVENTS+1
 ora BW_EVENTS+2
 jne bca_bad
 lda BW_RECORDS
 ora BW_RECORDS+1
 ora BW_RECORDS+2
 jeq bca_bad
 lda BSC_AT_EOF
 cmp #1
 jne bca_bad
 EQ BSC_CURSOR,BSC_LENGTH,3
 EQ BSC_LINES,BW_RECORDS,3
 lda BSC_READER+7
 ora BSC_READER+8
 jne bca_bad
 lda #0
 sta BW_PENDING
 sta BW_NEXT
 lda BW_CP
 beq @inline
 lda #1
 bne @seal
@inline:lda BW_IP
 jeq build_root
 lda #2
@seal:sta BW_KIND
 jmp start_seal
@return:rts
; Build an INVALID page header from authoritative private stream state.
start_seal:
 lda BW_KIND
 cmp #1
 beq @cr
 lda BW_IP
 bne @page
@cr:lda BW_CP
@page:sta BW_PAGE
 lda #0
 ldy #63
@zero:sta BC_IO,y
 dey
 bpl @zero
 lda #$42
 sta BC_IO
 lda #$50
 sta BC_IO+1
 lda #1
 sta BC_IO+2
 sta BC_IO+6
 lda BW_PAGE
 sta BC_IO+4
 lda BW_KIND
 sta BC_IO+5
 CP BCA_INC,BC_IO+8,4
 CP BCA_BOUND,BC_IO+12,5
 CP BCA_TICKET,BC_IO+17,4
 CP BCA_TICKET,BC_IO+33,4
 lda #$FF
 ldy #7
@nil:sta BC_IO+25,y
 dey
 bpl @nil
 lda BW_NEXT
 beq :+
 sta BC_IO+29
 lda #0
 sta BC_IO+30
 sta BC_IO+32
 lda #1
 sta BC_IO+31
:
 lda BW_KIND
 sec
 sbc #1
 tax
 cpx #0
 beq @cslots
 lda BW_IS
 bne @slots
@cslots:lda BW_CS
@slots:sta BC_IO+23
 txa
 asl
 tax
 lda BW_USED_C,x
 sta BC_IO+21
 lda BW_USED_C+1,x
 sta BC_IO+22
 lda BW_CRC_C,x
 sta BC_IO+39
 lda BW_CRC_C+1,x
 sta BC_IO+40
 jsr se_crc_init
 ldy #0
@crc:cpy #3
 beq @skip
 cpy #37
 beq @skip
 cpy #38
 beq @skip
 lda BC_IO,y
 jsr se_crc_byte
@skip:iny
 cpy #64
 bne @crc
 CP se_crc_value,BC_IO+37,2
 lda #BW_HEADER
 sta BCA_PHASE
 jmp bca_pending
build_root:
 lda #0
 ldy #127
@zero:sta BC_IO,y
 dey
 bpl @zero
 lda #$42
 sta BC_IO
 lda #$43
 sta BC_IO+1
 lda #$41
 sta BC_IO+2
 lda #$31
 sta BC_IO+3
 lda #1
 sta BC_IO+4
 lda #128
 sta BC_IO+6
 lda #BC_OBJECT_TYPE
 sta BC_IO+13
 CP BCA_BOUND,BC_IO+8,5
 CP BCA_INC,BC_IO+14,4
 CP BCA_TICKET,BC_IO+22,4
 CP BCA_TICKET,BC_IO+26,4
 ; Baseline has no previous journal dependency. Root completeness1 only now.
 lda #1
 sta BC_IO+31
 CP BSC_READER+27,BC_IO+32,59
 CP BSC_LENGTH,BC_IO+91,3
 lda #1
 sta BC_IO+94
 sta BC_IO+96
 sta BC_IO+100
 CP BW_FIRST,BC_IO+104,4
 CP BW_LAST,BC_IO+108,4
 CP BW_RECORDS,BC_IO+112,3
 lda #$FF
 ldy #3
@index:sta BC_IO+115,y
 dey
 bpl @index
 ldx #0
@sequence:inc BCA_SEQUENCE,x
 bne @seq_ok
 inx
 cpx #4
 bne @sequence
 jmp bca_stale
@seq_ok:CP BCA_SEQUENCE,BC_IO+18,4
 jsr bca_crc_root
 CP se_crc_value,BC_IO+119,2
 lda #BW_ROOT
 sta BCA_PHASE
 jmp bca_pending
; Each STEP at most one page/root publication DMA. Caller must not ACK the
; pending parser packet while these private seals are in progress.
se_bc_write_step:
 jsr bca_owner
 jcs @return
 jsr bw_guard
 jcs @return
 lda BCA_PHASE
 cmp #BW_DIRECTORY
 jeq @directory_clear
 cmp #BW_HEADER
 jeq @header
 cmp #BW_PAGE_VALID
 jeq @page_valid
 cmp #BW_DIR_WRITE
 jeq @directory_write
 cmp #BW_DIR_VALID
 jeq @directory_valid
 cmp #BW_RESUME
 jeq append_packet
 cmp #BW_ROOT
 jeq @root
 cmp #BW_ROOT_VALID
 jeq @root_valid
 jmp bca_bad
@directory_clear:
 lda #0
 ldy #127
@zero:sta BC_IO,y
 dey
 bpl @zero
 CP BCA_CURSOR,BCA_OFFSET,3
 lda #128
 sta BCA_LENGTH
 lda #0
 jsr bca_transfer
 jcs @return
 clc
 lda BCA_CURSOR
 adc #128
 sta BCA_CURSOR
 bcc :+
 inc BCA_CURSOR+1
:
 lda BCA_CURSOR+1
 cmp #9
 jne bca_pending
 lda #$FF
 ldy #3
@first_nil:sta BW_FIRST,y
 dey
 bpl @first_nil
 lda #BW_IDLE
 sta BCA_PHASE
 jmp bca_done
@header:
 lda BW_PAGE
 jsr page_offset
 lda #64
 sta BCA_LENGTH
 lda #0
 jsr bca_transfer
 jcs @return
 inc BCA_PHASE
 jmp bca_pending
@page_valid:
 lda BW_PAGE
 jsr page_offset
 lda #3
 sta BCA_OFFSET
 lda #1
 sta BC_IO
 sta BCA_LENGTH
 lda #0
 jsr bca_transfer
 jcs @return
 ; Prepare final entryCRC with state1; write INVALID then state1 last.
 lda #0
 ldy #7
@entry_zero:sta BC_IO,y
 dey
 bpl @entry_zero
 lda #1
 sta BC_IO
 sta BC_IO+3
 lda BW_KIND
 sta BC_IO+2
 jsr se_crc_init
 ldy #0
@crc:cpy #4
 beq @skip
 cpy #5
 beq @skip
 lda BC_IO,y
 jsr se_crc_byte
@skip:iny
 cpy #8
 bne @crc
 CP se_crc_value,BC_IO+4,2
 lda #0
 sta BC_IO+3
 inc BCA_PHASE
 jmp bca_pending
@directory_write:
 jsr directory_offset
 lda #8
 sta BCA_LENGTH
 lda #0
 jsr bca_transfer
 jcs @return
 inc BCA_PHASE
 jmp bca_pending
@directory_valid:
 jsr directory_offset
 lda BCA_OFFSET
 clc
 adc #3
 sta BCA_OFFSET
 lda #1
 sta BC_IO
 sta BCA_LENGTH
 lda #0
 jsr bca_transfer
 jcs @return
 ; Finished old page is now immutable. Newpage begins with fresh CRCFFFF.
 lda BW_KIND
 cmp #1
 beq @new_cr
 lda BW_NEXT
 sta BW_IP
 lda #0
 sta BW_IS
 sta BW_USED_I
 sta BW_USED_I+1
 lda #$FF
 sta BW_CRC_I
 sta BW_CRC_I+1
 jmp @sealed
@new_cr:
 lda BW_NEXT
 sta BW_CP
 lda #0
 sta BW_CS
 sta BW_USED_C
 sta BW_USED_C+1
 lda #$FF
 sta BW_CRC_C
 sta BW_CRC_C+1
@sealed:
 lda BW_PENDING
 beq @final_next
 lda #BW_RESUME
 sta BCA_PHASE
 jmp bca_pending
@final_next:
 lda #BW_IDLE
 sta BCA_PHASE
 jmp se_bc_write_final
@root:
 ; Root was assembled after real EOF. Reject in-memory damage before stash.
 lda #1
 sta BC_IO+5
 jsr bca_root_check
 php
 dec BC_IO+5
 plp
 jcs @return
 lda BCA_SELECTED
 eor #128
 sta BCA_OFFSET
 lda #0
 sta BCA_OFFSET+1
 sta BCA_OFFSET+2
 lda #128
 sta BCA_LENGTH
 lda #0
 jsr bca_transfer
 jcs @return
 inc BCA_PHASE
 jmp bca_pending
@root_valid:
 lda BCA_SELECTED
 eor #128
 clc
 adc #5
 sta BCA_OFFSET
 lda #1
 sta BC_IO
 sta BCA_LENGTH
 lda #0
 jsr bca_transfer
 jcs @return
 ; This verified full baseline represents every event through capturedticket.
 ; Retire the old producer queue only AFTER the REU rootVALID commit and
 ; BEFORE publishing ARMED. Do not reset the monotonic observedticket.
 lda #0
 sta se_bc_head
 sta se_bc_tail
 sta se_bc_count
 lda se_bc_flags
 and #($FF-BC_LOST-BC_ACTIVE)
 ora #BC_ARMED
 sta se_bc_flags
 lda #0
 sta BCA_PHASE
 jmp bca_done
@return:rts
directory_offset:
 lda BW_PAGE
 ldx #0
 stx BCA_OFFSET+2
 asl
 rol BCA_OFFSET+2
 asl
 rol BCA_OFFSET+2
 asl
 rol BCA_OFFSET+2
 sta BCA_OFFSET
 lda BCA_OFFSET+2
 clc
 adc #1
 sta BCA_OFFSET+1
 lda #0
 sta BCA_OFFSET+2
 rts
se_bc_write_cancel:
 jsr bca_owner
 bcs @return
 lda se_bc_flags
 and #($FF-BC_ARMED-BC_ACTIVE)
 ora #BC_LOST
 sta se_bc_flags
 lda #0
 sta BCA_PHASE
 sta BCA_PROOF
 jmp bca_done
@return:rts

stream_required:
 jsr se_bc_write_cancel
 lda #BC_STREAM
 clc
 rts

inline_crc:
 jsr se_crc_init
 ldy #0
@byte:lda BC_IO+118,y
 jsr se_crc_byte
 iny
 cpy #10
 bne @byte
 rts
