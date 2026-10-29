; Private current-schema materialization. Old reachable pages are read-only.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "cache/edit-rebase-current-probe/api.inc"
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
 jmp stale
busy:lda #$B2
 sec
 rts
stale:lda #$C1
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
 jmp stale
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
 jne stale
 lda S_ROOT+30
 jne stale
 EQ S_OLD+28,S_NEW+28,12
 EQ S_NEW+12,S_AUTH+5,4
 EQ S_NEW+59,S_AUTH+5,4
 lda #0
 ldx #78
@clear:sta E,x
 dex
 bpl @clear
 lda S_ROOT+104
 sta E_OLD_CR
 lda #NEW_CR_PAGE
 jsr dir_offset
 jsr raw_read
 jcs return
 ldx #7
@empty1:lda BC_IO,x
 jne stale
 dex
 bpl @empty1
 lda #NEW_LEX_PAGE
 jsr dir_offset
 jsr raw_read
 jcs return
 ldx #7
@empty2:lda BC_IO,x
 jne stale
 dex
 bpl @empty2
 lda E_OLD_CR
 jsr page_offset
 lda #64
 sta BCA_LENGTH
 jsr raw_read
 jcs return
 CP BC_IO,S_HEADER,64
 CP BC_IO+39,E_EXPECT,2
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
 jmp stale
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
 jne stale
 EQ BC_IO+12,S_ROOT+22,4
 EQ BC_IO+59,S_ROOT+22,4
 jsr record_crc
 EQ se_crc_value,BC_IO+74,2
 ; No retained geometry/reference stream is implicitly transformed.
 ldx #3
@runs:lda BC_IO+54,x
 cmp #$FF
 jne stale
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
 jne stale
 lda BC_IO+3
 cmp #5
 jne stale
 lda BC_IO+48
 ora BC_IO+50
 ora BC_IO+53
 jne stale
 lda BC_IO+49
 cmp #1
 jne stale
 lda BC_IO+47
 jeq stale
 cmp #14
 jcs stale
 sta E_OLD_LEX
 CP BC_IO+51,E_LEX_COUNT,2
 clc
 .repeat 3,I
 lda BC_IO+16+I
 adc BC_IO+22+I
 sta E_LEX_BODY+I
 .endrepeat
 jcs stale
 clc
 .repeat 3,I
 lda BC_IO+16+I
 adc BC_IO+19+I
 sta E_LEX_END+I
 .endrepeat
 jcs stale
 ; Initial proof only: edit strictly AFTER this unchanged lexical BODY.
 C24 S_EVENT+16,E_LEX_END
 jcc stale
 jeq stale
 lda #NEW_LEX_PAGE
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
 lda #NEW_CR_PAGE
 jsr record_offset
 jsr raw_write
 jcs return
 inc E_INDEX
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
 jne stale
 lda #NEW_CR_PAGE
 sta E_NEW_PAGE
 lda #1
 sta E_KIND
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
 CP BC_IO,S_HEADER,64
 CP BC_IO+21,E_LEX_USED,2
 CP BC_IO+39,E_EXPECT,2
 CP BC_IO+21,E_LEFT,2
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
 lda E_LEFT
 ora E_LEFT+1
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
 ldx E_LEFT+1
 bne :+
 cmp E_LEFT
 bcc :+
 lda E_LEFT
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
 lda #NEW_LEX_PAGE
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
 clc
 lda E_CURSOR
 adc BCA_LENGTH
 sta E_CURSOR
 bcc :+
 inc E_CURSOR+1
:sec
 lda E_LEFT
 sbc BCA_LENGTH
 sta E_LEFT
 lda E_LEFT+1
 sbc #0
 sta E_LEFT+1
 jmp pending
@finished:jmp advance
descriptor:
 lda BC_IO
 cmp #'L'
 jne stale
 lda BC_IO+1
 cmp #'X'
 jne stale
 lda BC_IO+2
 cmp #'C'
 jne stale
 lda BC_IO+3
 cmp #'1'
 jne stale
 lda BC_IO+4
 and BC_IO+5
 cmp #1
 jne stale
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
 lda #NEW_LEX_PAGE
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
 lda #NEW_CR_PAGE
 sta E_NEW_PAGE
 lda #1
 bne directory
directory_lex:
 lda #NEW_LEX_PAGE
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
 CP se_crc_value,BC_IO+4,2
 lda E_NEW_PAGE
 jsr dir_offset
 jsr raw_write
 jcs return
 jmp advance
journal:
 CP S_EVENT,BC_IO,32
 lda #0
 sta BC_IO
 sta BCA_OFFSET
 sta BCA_OFFSET+2
 lda #9
 sta BCA_OFFSET+1
 lda #32
 sta BCA_LENGTH
 jsr raw_write
 jcs return
 jmp advance
journal_valid:
 lda #0
 sta BCA_OFFSET
 sta BCA_OFFSET+2
 lda #9
 sta BCA_OFFSET+1
 lda #1
 sta BCA_LENGTH
 lda #$A5
 sta BC_IO
 jsr raw_write
 jcs return
 jmp advance
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
 lda #NEW_CR_PAGE
 ldx #1
 jsr verify_page
 jcs return
 EQ BCA_EXPECT,E_CR_EXPECT,2
 lda #NEW_LEX_PAGE
 ldx #3
 jsr verify_page
 jcs return
 EQ BCA_EXPECT,E_LEX_EXPECT,2
 CP S_ROOT,BC_IO,128
 CP S_READER+27,BC_IO+32,59
 CP S_READER+10,BC_IO+91,3
 CP S_AUTH+5,BC_IO+22,4
 lda #1
 sta BC_IO+30
 lda #NEW_CR_PAGE
 sta BC_IO+104
 sta BC_IO+108
 ldx #0
@seq:inc BC_IO+18,x
 bne @ready
 inx
 cpx #4
 bcc @seq
 jmp stale
@ready:jsr bca_crc_root
 CP se_crc_value,BC_IO+119,2
 jsr bca_root_check
 jcs return
 CP BC_IO,S_DRAFT,128
 lda #0
 sta BC_IO+5
 lda S_DEST
 sta BCA_OFFSET
 lda #0
 sta BCA_OFFSET+1
 sta BCA_OFFSET+2
 lda #128
 sta BCA_LENGTH
 jsr raw_write
 jcs return
 jmp root_valid
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
root_valid:
 EQ S_DRAFT+32,S_READER+27,59
 lda S_DEST
 clc
 adc #5
 sta BCA_OFFSET
 lda #0
 sta BCA_OFFSET+1
 sta BCA_OFFSET+2
 lda #1
 sta BC_IO
 sta BCA_LENGTH
 jsr raw_write
 jcs return
 lda S_HEAD
 sta se_bc_tail
 lda #0
 sta se_bc_count
 sta E_PHASE
 jmp done
