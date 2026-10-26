; Private current-schema materialization. Old reachable pages are read-only.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "cache/edit-rebase-integration/api.inc"
.import se_f_owner,se_overlay_frame
.import bca_guard,bca_transfer,bca_open_step,se_bc_arena_open,se_bc_page_begin,bca_page_step,se_bc_arena_read,bca_crc_root,bca_root_check
.import se_crc_init,se_crc_byte,se_crc_value
.export entry
.segment "CODE"
OVL_BINDING
entry:
 lda se_f_owner
 cmp #4
 jne busy
 lda se_overlay_frame
 beq open
 cmp #1
 beq step
 cmp #2
 beq page
 cmp #3
 beq read
 cmp #4
 jeq publish_begin
 cmp #5
 jeq publish_step
 cmp #6
 beq check_root
 jmp ebr_stale
busy:lda #$B2
 sec
 rts
check_root:
 jsr bca_guard
 bcc @ok
 rts
@ok:jmp bca_root_check
ebr_stale:lda #$C1
 sec
 rts
open:jmp se_bc_arena_open
step:
 lda BCA_PHASE
 cmp #7
 bcs :+
 jmp bca_open_step
:jmp bca_page_step
page:jmp se_bc_page_begin
read:jmp se_bc_arena_read
transfer:
 pha
 jsr bca_guard
 bcs @bad
 pla
 jmp bca_transfer
@bad:pla
 jmp ebr_stale
raw_read:lda #1
 jmp transfer
raw_write:lda #0
 jmp transfer
pending:lda #1
 clc
 rts
done:lda #0
 clc
 rts
page_offset:
 pha
 asl
 asl
 asl
 asl
 sta BCA_OFFSET+1
 pla
 lsr
 lsr
 lsr
 lsr
 sta BCA_OFFSET+2
 lda #0
 sta BCA_OFFSET
 rts
dir_offset:
 asl
 asl
 asl
 sta BCA_OFFSET
 lda #1
 sta BCA_OFFSET+1
 lda #0
 sta BCA_OFFSET+2
 lda #8
 sta BCA_LENGTH
 rts
record_offset:
 jsr page_offset
 lda #64
 sta BCA_OFFSET
 ldx E_INDEX
 beq @done
@add:clc
 lda BCA_OFFSET
 adc #96
 sta BCA_OFFSET
 bcc :+
 inc BCA_OFFSET+1
:dex
 bne @add
@done:lda #96
 sta BCA_LENGTH
 rts
record_crc:
 jsr se_crc_init
 ldy #1
@byte:cpy #74
 bne :+
 ldy #76
:lda BC_IO,y
 jsr se_crc_byte
 iny
 cpy #96
 bne @byte
 rts
fold_crc:
 ; Running payload CRC over the current actual bounded transfer.
 ldy #0
@byte:lda BC_IO,y
 jsr se_crc_byte
 iny
 cpy BCA_LENGTH
 bne @byte
 rts
advance:
 inc E_PHASE
 jmp pending
publish_begin:
 jsr bca_guard
 jcs return
 lda S_ROOT+31
 cmp #5
 jne ebr_stale
 lda S_MODE
 bne @proof_done
 EQ S_OLD+28,S_NEW+28,12
 EQ S_NEW+12,S_AUTH+5,4
 EQ S_NEW+59,S_AUTH+5,4
@proof_done:
 lda #0
 ldx #78
@clear:sta E,x
 dex
 bpl @clear
 lda #1
 sta E_PREFLIGHT
 lda S_ROOT+104
 sta E_OLD_CR
 cmp #14
 bne @pair14
 lda #12
 bne @pair
@pair14:lda #14
@pair:sta S_NEW_CR
 clc
 adc #1
 sta S_NEW_LEX
 lda S_NEW_CR
 ldx #1
 jsr reusable_directory
 jcs return
 lda S_NEW_LEX
 ldx #3
 jsr reusable_directory
 jcs return
 lda E_OLD_CR
 jsr page_offset
 lda #64
 sta BCA_LENGTH
 jsr raw_read
 jcs return
 jsr no_chain
 jcs return
 ldx #63
@header:lda BC_IO,x
 sta E_OLD_HEADER,x
 sta S_HEADER,x
 dex
 bpl @header
 CP S_PAGE_CRC,E_EXPECT,2
 lda #$FF
 sta E_NEW_CRC
 sta E_NEW_CRC+1
 sta E_OLD_CRC
 sta E_OLD_CRC+1
 lda #1
 sta E_PHASE
 jmp pending
publish_step:
 jsr bca_guard
 jcs return
 lda E_PHASE
 cmp #1
 jeq copy_record
 cmp #2
 jeq write_record
 cmp #3
 jeq finish_cr
 cmp #4
 jeq lex_page_begin
 cmp #5
 jeq lex_page_step
 cmp #6
 jeq copy_lex
 cmp #7
 jeq finish_lex
 cmp #8
 jeq directory_cr
 cmp #9
 jeq directory_lex
 cmp #10
 jeq journal
 cmp #11
 jeq journal_valid
 cmp #12
 jeq root_draft
 jmp ebr_stale
return:rts
copy_record:
 lda E_OLD_CR
 jsr record_offset
 jsr raw_read
 jcs return
 CP E_OLD_CRC,se_crc_value,2
 jsr fold_crc
 CP se_crc_value,E_OLD_CRC,2
 lda BC_IO
 and BC_IO+1
 cmp #1
 jne ebr_stale
 EQ BC_IO+12,S_ROOT+22,4
 EQ BC_IO+59,S_ROOT+22,4
 ldx #40
@refs:lda BC_IO,x
 cmp S_NEW_CR
 jeq ebr_stale
 cmp S_NEW_LEX
 jeq ebr_stale
 txa
 clc
 adc #7
 tax
 cpx #61
 bcc @refs
 jsr record_crc
 EQ se_crc_value,BC_IO+74,2
 ; No retained geometry/reference stream is implicitly transformed.
 ldx #3
@runs:lda BC_IO+54,x
 cmp #$FF
 jne ebr_stale
 dex
 bpl @runs
 lda E_INDEX
 cmp S_INDEX
 bne @unchanged
 EQ BC_IO,S_OLD,96
 CP S_NEW,BC_IO,96
 jmp @ticket
@unchanged:
 bcc @ticket
 INC24 BC_IO+16
@ticket:
 CP S_AUTH+5,BC_IO+12,4
 CP S_AUTH+5,BC_IO+59,4
 lda BC_IO+2
 and #$10
 jeq @plain
 inc E_FOUND
 lda E_FOUND
 cmp #1
 jne ebr_stale
 lda BC_IO+3
 cmp #5
 jne ebr_stale
 lda BC_IO+48
 ora BC_IO+50
 ora BC_IO+53
 jne ebr_stale
 lda BC_IO+49
 cmp #1
 jne ebr_stale
 lda BC_IO+47
 jeq ebr_stale
 cmp #16
 jcs ebr_stale
 sta E_OLD_LEX
 CP BC_IO+51,E_LEX_COUNT,2
 clc
 .repeat 3,I
 lda BC_IO+16+I
 adc BC_IO+22+I
 sta E_LEX_BODY+I
 .endrepeat
 jcs ebr_stale
 clc
 .repeat 3,I
 lda BC_IO+16+I
 adc BC_IO+19+I
 sta E_LEX_END+I
 .endrepeat
 jcs ebr_stale
 ; Initial proof only: edit strictly AFTER this unchanged lexical BODY.
 C24 S_EVENT+16,E_LEX_END
 jcc ebr_stale
 jeq ebr_stale
 lda S_NEW_LEX
 sta BC_IO+47
@plain:
 jsr record_crc
 CP se_crc_value,BC_IO+74,2
 CP BC_IO,S_CR,96
 jmp advance
write_record:
 CP S_CR,BC_IO,96
 CP E_NEW_CRC,se_crc_value,2
 lda #96
 sta BCA_LENGTH
 jsr fold_crc
 CP se_crc_value,E_NEW_CRC,2
 lda S_NEW_CR
 jsr record_offset
 lda E_PREFLIGHT
 bne :+
 jsr raw_write
 jcs return
:inc E_INDEX
 lda E_INDEX
 cmp S_N
 beq @done
 lda #1
 sta E_PHASE
 jmp pending
@done:jmp advance
finish_cr:
 EQ E_OLD_CRC,E_EXPECT,2
 lda E_FOUND
 cmp #1
 jne ebr_stale
 lda S_NEW_CR
 sta E_NEW_PAGE
 lda #1
 sta E_KIND
 lda E_PREFLIGHT
 jne advance
 CP S_HEADER+21,E_USED,2
 jsr write_header
 jcs return
 CP E_NEW_CRC,E_CR_EXPECT,2
 jmp advance
lex_page_begin:
 lda E_OLD_LEX
 sta BCA_PAGE
 lda #3
 sta BCA_KIND
 lda #1
 sta BCA_GENERATION
 lda #0
 sta BCA_GENERATION+1
 sta BCA_PHASE
 sta BCA_PROOF
 jsr se_bc_page_begin
 jcs return
 jmp advance
lex_page_step:
 jsr bca_page_step
 jcs return
 cmp #0
 jne pending
 lda E_OLD_LEX
 jsr page_offset
 lda #64
 sta BCA_LENGTH
 jsr raw_read
 jcs return
 jsr no_chain
 jcs return
 CP BC_IO,S_HEADER,64
 CP BC_IO+21,E_LEX_USED,2
 CP BC_IO+39,E_EXPECT,2
 CP BC_IO+21,RX_LEFT,2
 lda #64
 sta E_CURSOR
 lda #0
 sta E_CURSOR+1
 lda #$FF
 sta E_NEW_CRC
 sta E_NEW_CRC+1
 sta E_OLD_CRC
 sta E_OLD_CRC+1
 jmp advance
copy_lex:
 lda RX_LEFT
 ora RX_LEFT+1
 jeq @finished
 lda E_OLD_LEX
 jsr page_offset
 lda E_CURSOR
 sta BCA_OFFSET
 clc
 lda E_CURSOR+1
 adc BCA_OFFSET+1
 sta BCA_OFFSET+1
 lda #128
 ldx RX_LEFT+1
 bne :+
 cmp RX_LEFT
 bcc :+
 lda RX_LEFT
:sta BCA_LENGTH
 jsr raw_read
 jcs return
 CP E_OLD_CRC,se_crc_value,2
 jsr fold_crc
 CP se_crc_value,E_OLD_CRC,2
 lda E_CURSOR+1
 bne @copied
 lda E_CURSOR
 cmp #64
 bne @copied
 jsr descriptor
 jcs return
@copied:
 CP E_NEW_CRC,se_crc_value,2
 jsr fold_crc
 CP se_crc_value,E_NEW_CRC,2
 lda E_PREFLIGHT
 bne @advance
 lda S_NEW_LEX
 asl
 asl
 asl
 asl
 clc
 adc E_CURSOR+1
 sta BCA_OFFSET+1
 lda E_CURSOR
 sta BCA_OFFSET
 lda #0
 sta BCA_OFFSET+2
 jsr raw_write
 jcs return
@advance:
 clc
 lda E_CURSOR
 adc BCA_LENGTH
 sta E_CURSOR
 bcc :+
 inc E_CURSOR+1
:sec
 lda RX_LEFT
 sbc BCA_LENGTH
 sta RX_LEFT
 lda RX_LEFT+1
 sbc #0
 sta RX_LEFT+1
 jmp pending
@finished:jmp advance
descriptor:
 lda BC_IO
 cmp #'L'
 jne ebr_stale
 lda BC_IO+1
 cmp #'X'
 jne ebr_stale
 lda BC_IO+2
 cmp #'C'
 jne ebr_stale
 lda BC_IO+3
 cmp #'1'
 jne ebr_stale
 lda BC_IO+4
 and BC_IO+5
 cmp #1
 jne ebr_stale
 EQ BC_IO+8,E_LEX_BODY,3
 EQ BC_IO+11,E_LEX_END,3
 EQ BC_IO+14,S_AUTH,5
 EQ BC_IO+19,S_ROOT+22,4
 EQ BC_IO+23,S_AUTH+9,4
 EQ BC_IO+27,S_ROOT+32,59
 EQ BC_IO+86,E_LEX_COUNT,2
 CP S_AUTH,BC_IO+14,13
 CP S_READER+27,BC_IO+27,59
 clc
 rts
finish_lex:
 EQ E_OLD_CRC,E_EXPECT,2
 lda E_PREFLIGHT
 beq @write
 lda #0
 sta E_PREFLIGHT
 sta E_INDEX
 sta E_FOUND
 CP E_OLD_HEADER,S_HEADER,64
 CP S_PAGE_CRC,E_EXPECT,2
 lda #$FF
 sta E_NEW_CRC
 sta E_NEW_CRC+1
 sta E_OLD_CRC
 sta E_OLD_CRC+1
 lda #1
 sta E_PHASE
 jmp pending
@write:
 lda S_NEW_LEX
 sta E_NEW_PAGE
 lda #3
 sta E_KIND
 CP E_LEX_USED,E_USED,2
 jsr write_header
 jcs return
 CP E_NEW_CRC,E_LEX_EXPECT,2
 jmp advance
write_header:
 CP S_HEADER,BC_IO,64
 lda E_NEW_PAGE
 sta BC_IO+4
 lda E_KIND
 sta BC_IO+5
 CP S_AUTH+5,BC_IO+17,4
 CP S_AUTH+5,BC_IO+33,4
 CP E_USED,BC_IO+21,2
 CP E_NEW_CRC,BC_IO+39,2
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
 bcc @crc
 CP se_crc_value,BC_IO+37,2
 ; Header was genuinely valid and destination directory is still unpublished.
 lda E_NEW_PAGE
 jsr page_offset
 lda #64
 sta BCA_LENGTH
 jmp raw_write
directory_cr:
 lda S_NEW_CR
 sta E_NEW_PAGE
 lda #1
 bne directory
directory_lex:
 lda S_NEW_LEX
 sta E_NEW_PAGE
 lda #3
directory:
 pha
 lda #0
 ldx #7
@zero:sta BC_IO,x
 dex
 bpl @zero
 pla
 sta BC_IO+2
 lda #1
 sta BC_IO
 sta BC_IO+3
 jsr directory_crc
 CP se_crc_value,BC_IO+4,2
 lda E_NEW_PAGE
 jsr dir_offset
 jsr raw_write
 jcs return
 jmp advance
journal:
 CP S_EVENT,BC_IO,32
 lda E_JOURNAL
 beq @copied
 CP S_REKEY,BC_IO,32
@copied:lda #0
 sta BC_IO
 jsr journal_offset
 lda #32
 sta BCA_LENGTH
 jsr raw_write
 jcs return
 jmp advance
journal_offset:
 clc
 lda S_ROOT+30
 adc E_JOURNAL
 ldx #0
 stx BCA_OFFSET+2
 .repeat 5
 asl
 rol BCA_OFFSET+2
 .endrepeat
 sta BCA_OFFSET
 lda BCA_OFFSET+2
 clc
 adc #9
 sta BCA_OFFSET+1
 lda #0
 sta BCA_OFFSET+2
 rts
journal_valid:
 jsr journal_offset
 lda #1
 sta BCA_LENGTH
 lda #$A5
 sta BC_IO
 jsr raw_write
 jcs return
 inc E_JOURNAL
 lda E_JOURNAL
 cmp S_COUNT
 beq :+
 lda #10
 sta E_PHASE
 jmp pending
:jmp advance
root_draft:
 ; Final bounded critical slice: authenticate both complete COW pages and
 ; private expected CRCs, then publish/retire without yielding. No proof bit.
 ; At worst two4032B payloads are checked here, in <=128B transfers.
 ; The selected baseline must still be byte-identical after all yielded copies.
 lda S_DEST
 eor #128
 sta BCA_OFFSET
 lda #0
 sta BCA_OFFSET+1
 sta BCA_OFFSET+2
 lda #128
 sta BCA_LENGTH
 jsr raw_read
 jcs return
 EQ BC_IO,S_ROOT,128
 lda S_NEW_CR
 ldx #1
 jsr verify_page
 jcs return
 EQ BCA_EXPECT,E_CR_EXPECT,2
 lda S_NEW_LEX
 ldx #3
 jsr verify_page
 jcs return
 EQ BCA_EXPECT,E_LEX_EXPECT,2
 lda #3
 clc
 rts
verify_page:
 sta BCA_PAGE
 stx BCA_KIND
 lda #1
 sta BCA_GENERATION
 lda #0
 sta BCA_GENERATION+1
 sta BCA_PHASE
 sta BCA_PROOF
 jsr se_bc_page_begin
 bcs @done
@step:jsr bca_page_step
 bcs @done
 cmp #1
 beq @step
@done:rts
no_chain:
 lda BC_IO+29
 and BC_IO+30
 and BC_IO+31
 and BC_IO+32
 cmp #$FF
 jne ebr_stale
 clc
 rts
; Reclamation is only for directory kind1/3 with exact generation1; all
; candidates are excluded from the full selected-root reference closure in
; the nonwriting pass before any payload/directory/root write.
reusable_directory:
 stx E_KIND
 jsr dir_offset
 jsr raw_read
 bcs @done
 ldx #7
 lda #0
@empty:ora BC_IO,x
 dex
 bpl @empty
 cmp #0
 beq @ok
 lda BC_IO
 cmp #1
 jne ebr_stale
 lda BC_IO+1
 ora BC_IO+6
 ora BC_IO+7
 jne ebr_stale
 lda BC_IO+2
 cmp E_KIND
 jne ebr_stale
 lda BC_IO+3
 cmp #1
 jne ebr_stale
 jsr directory_crc
 EQ se_crc_value,BC_IO+4,2
@ok:clc
@done:rts
directory_crc:
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
 bcc @crc
 rts
