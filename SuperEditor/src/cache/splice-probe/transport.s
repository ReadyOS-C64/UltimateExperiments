; Private R34. Typed arena only; NEVER calls R14 or any R-slot image.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "cache/splice-probe/api.inc"
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
 jeq step
 cmp #2
 jeq page
 cmp #3
 jeq read
 cmp #4
 jeq publish_begin
 cmp #5
 jeq publish_step
 cmp #6
 jeq query_begin
 cmp #7
 jeq query_step
 cmp #8
 jeq raw_read
 lda #$C0
 sec
 rts
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
; Restore actualtype53 request after every checkedsource call disturbs it.
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
; Event identity and source equivalence are checked by C40 on every entry.
; These checks independently refuse accidental exposure of a current-ticket CR
; as if all old records had been reparsed.
publish_begin:
 jsr bca_guard
 jcs return
 lda S_ROOT+31
 cmp #1
 jne stale
 lda S_ROOT+30
 jne stale
 lda S_NEW
 cmp #1
 jne stale
 lda S_NEW+3
 cmp #0
 jne stale
 EQ S_OLD+28,S_NEW+28,12
 EQ S_NEW+12,S_AUTH+5,4
 EQ S_NEW+59,S_AUTH+5,4
 ; Assemble explicit base/live mapping; no old CR ticket is written.
 lda #0
 ldx #127
@zero:sta S_MAN,x
 dex
 bpl @zero
 lda #'S'
 sta S_MAN
 lda #'P'
 sta S_MAN+1
 lda #'M'
 sta S_MAN+2
 lda #'1'
 sta S_MAN+3
 lda #1
 sta S_MAN+4
 sta S_MAN+5
 sta S_MAN+35
 lda #128
 sta S_MAN+6
 CP S_ROOT+22,S_MAN+8,4
 CP S_AUTH+5,S_MAN+12,4
 lda #1
 sta S_MAN+16
 sta S_MAN+18
 lda S_INDEX
 sta S_MAN+17
 CP S_OLD+16,S_MAN+20,3
 ; Stored lengths are relative; copy actual checked absolute boundaries.
 CP S_END,S_MAN+23,3
 CP S_NEXT,S_MAN+26,3
 CP S_END,S_MAN+29,3
 INC24 S_MAN+29
 CP S_NEXT,S_MAN+32,3
 INC24 S_MAN+32
 CP S_OLD+28,S_MAN+36,12
 CP S_OLD+74,S_MAN+48,2
 CP S_NEW+74,S_MAN+50,2
 lda #15
 sta S_MAN+52
 lda #1
 sta S_MAN+54
 CP S_ROOT+91,S_MAN+56,3
 CP S_READER+10,S_MAN+59,3
 CP S_EVENT,S_MAN+64,32
 CP S_ROOT+119,S_MAN+96,2
 CP S_ROOT+18,S_MAN+98,4
 lda S_DEST
 eor #128
 sta S_MAN+102
 jsr se_crc_init
 ldy #0
@mcrc:lda S_MAN,y
 jsr se_crc_byte
 iny
 cpy #126
 bcc @mcrc
 CP se_crc_value,S_MAN+126,2
 lda #1
 sta S_PSTATE
 jmp pending
return:rts
publish_step:
 jsr bca_guard
 jcs return
 lda S_PSTATE
 cmp #1
 jeq payload_manifest
 cmp #2
 jeq payload_record
 cmp #3
 jeq page_header
 cmp #4
 jeq directory
 cmp #5
 jeq page_valid
 cmp #6
 jeq directory_valid
 cmp #7
 jeq journal
 cmp #8
 jeq journal_valid
 cmp #9
 jeq root_draft
 cmp #10
 jeq root_valid
 jmp stale
request:
 ; X=length,A=lowoffset,Y=highoffset, bankoffset0; no physical address.
 sta BCA_OFFSET
 sty BCA_OFFSET+1
 stx BCA_LENGTH
 lda #0
 sta BCA_OFFSET+2
 rts
advance:
 inc S_PSTATE
 jmp pending
payload_manifest:
 CP S_MAN,BC_IO,128
 lda #$40
 ldy #$F0
 ldx #128
 jsr request
 jsr raw_write
 jcs return
 jmp advance
payload_record:
 CP S_NEW,BC_IO,96
 lda #$C0
 ldy #$F0
 ldx #96
 jsr request
 jsr raw_write
 jcs return
 jmp advance
page_header:
 lda #0
 ldx #63
@zero:sta S_HEADER,x
 dex
 bpl @zero
 lda #'B'
 sta S_HEADER
 lda #'P'
 sta S_HEADER+1
 lda #1
 sta S_HEADER+2
 sta S_HEADER+6
 sta S_HEADER+23
 lda #15
 sta S_HEADER+4
 lda #6
 sta S_HEADER+5
 CP S_AUTH+9,S_HEADER+8,4
 CP S_AUTH,S_HEADER+12,5
 CP S_AUTH+5,S_HEADER+17,4
 CP S_AUTH+5,S_HEADER+33,4
 lda #224
 sta S_HEADER+21
 lda #$FF
 ldx #7
@nil:sta S_HEADER+25,x
 dex
 bpl @nil
 jsr se_crc_init
 ldy #0
@man:lda S_MAN,y
 jsr se_crc_byte
 iny
 cpy #128
 bcc @man
 ldy #0
@cr:lda S_NEW,y
 jsr se_crc_byte
 iny
 cpy #96
 bcc @cr
 CP se_crc_value,S_HEADER+39,2
 jsr se_crc_init
 ldy #0
@hcrc:cpy #3
 beq @skip
 cpy #37
 beq @skip
 cpy #38
 beq @skip
 lda S_HEADER,y
 jsr se_crc_byte
@skip:iny
 cpy #64
 bcc @hcrc
 CP se_crc_value,S_HEADER+37,2
 CP S_HEADER,BC_IO,64
 lda #0
 ldy #$F0
 ldx #64
 jsr request
 jsr raw_write
 jcs return
 jmp advance
directory:
 lda #0
 ldx #7
@zero:sta BC_IO,x
 dex
 bpl @zero
 lda #1
 sta BC_IO
 sta BC_IO+3
 lda #6
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
 bcc @crc
 CP se_crc_value,BC_IO+4,2
 lda #0
 sta BC_IO+3
 lda #$78
 ldy #1
 ldx #8
 jsr request
 jsr raw_write
 jcs return
 jmp advance
page_valid:
 lda #3
 ldy #$F0
 bne valid
directory_valid:
 lda #$7B
 ldy #1
valid:
 ldx #1
 jsr request
 lda #1
 sta BC_IO
 jsr raw_write
 jcs return
 jmp advance
journal:
 CP S_EVENT,BC_IO,32
 lda #0
 sta BC_IO
 ldy #9
 ldx #32
 jsr request
 jsr raw_write
 jcs return
 jmp advance
journal_valid:
 lda #$A5
 sta BC_IO
 lda #0
 ldy #9
 ldx #1
 jsr request
 jsr raw_write
 jcs return
 jmp advance
root_draft:
 CP S_ROOT,BC_IO,128
 CP S_READER+27,BC_IO+32,59
 CP S_READER+10,BC_IO+91,3
 CP S_AUTH+5,BC_IO+22,4
 lda #1
 sta BC_IO+30
 lda #S_FEATURE
 sta BC_IO+31
 lda #15
 sta BC_IO+115
 lda #0
 sta BC_IO+116
 sta BC_IO+118
 lda #1
 sta BC_IO+117
 ldx #0
@seq:inc BC_IO+18,x
 bne @ok
 inx
 cpx #4
 bcc @seq
 jmp stale
@ok:jsr bca_crc_root
 CP se_crc_value,BC_IO+119,2
 jsr bca_root_check
 jcs return
 CP BC_IO,S_DRAFT,128
 lda #0
 sta BC_IO+5
 lda S_DEST
 ldy #0
 ldx #128
 jsr request
 jsr raw_write
 jcs return
 jmp advance
root_valid:
 CP S_DRAFT,BC_IO,128
 jsr bca_root_check
 jcs return
 EQ S_DRAFT+32,S_READER+27,59
 lda S_DEST
 clc
 adc #5
 ldy #0
 ldx #1
 jsr request
 lda #1
 sta BC_IO
 jsr raw_write
 jcs return
 lda S_HEAD
 sta se_bc_tail
 lda #0
 sta se_bc_count
 sta S_PSTATE
 clc
 rts
; Read-only mappedquery. BaseCR tickets remainbase; dirtyCR ticket islive.
; S_ORIGIN distinguishesderived coordinate output, never reticketsstoredCRs.
query_begin:
 lda #1
 sta S_PSTATE
 jmp se_bc_arena_open
query_step:
 jsr bca_guard
 jcs return
 lda S_PSTATE
 cmp #1
 jeq qroot
 cmp #2
 jeq qpage
 cmp #3
 jeq qmanifest
 cmp #4
 jeq qnew
 cmp #5
 jeq qold
 cmp #6
 jeq qbase
 cmp #7
 jeq qrecord
 jmp stale
qroot:
 jsr bca_open_step
 jcs return
 cmp #0
 jne pending
 CP BC_IO,S_ROOT,128
 lda S_ROOT+31
 cmp #S_FEATURE
 jne stale
 lda S_ROOT+30
 cmp #1
 jne stale
 EQ S_ROOT+22,S_AUTH+5,4
 EQ S_ROOT+32,S_READER+27,59
 EQ S_ROOT+91,S_READER+10,3
 lda S_ROOT+115
 cmp #15
 jne stale
 lda S_ROOT+116
 ora S_ROOT+118
 jne stale
 lda S_ROOT+117
 cmp #1
 jne stale
 lda S_ROOT+112
 jeq stale
 cmp #43
 jcs stale
 sta S_N
 lda S_ROOT+113
 ora S_ROOT+114
 jne stale
 lda #15
 sta BCA_PAGE
 lda #6
 sta BCA_KIND
 lda #1
 sta BCA_GENERATION
 lda #0
 sta BCA_GENERATION+1
 jsr se_bc_page_begin
 jcs return
 inc S_PSTATE
 jmp pending
qpage:
 jsr bca_page_step
 jcs return
 cmp #0
 jne pending
 lda BCA_USED
 cmp #224
 jne stale
 lda BCA_USED+1
 jne stale
 jmp advance
qmanifest:
 lda #$40
 ldy #$F0
 ldx #128
 jsr request
 jsr se_bc_arena_read
 jcs return
 CP BC_IO,S_MAN,128
 lda S_MAN
 cmp #'S'
 jne stale
 lda S_MAN+1
 cmp #'P'
 jne stale
 lda S_MAN+2
 cmp #'M'
 jne stale
 lda S_MAN+3
 cmp #'1'
 jne stale
 lda S_MAN+4
 cmp #1
 jne stale
 lda S_MAN+5
 cmp #1
 jne stale
 EQ S_MAN+8,S_ROOT+26,4
 EQ S_MAN+12,S_AUTH+5,4
 lda S_MAN+16
 cmp #1
 jne stale
 lda S_MAN+18
 cmp #1
 jne stale
 lda S_MAN+19
 jne stale
 lda S_MAN+17
 cmp S_N
 jcs stale
 jsr se_crc_init
 ldy #0
@crc:lda S_MAN,y
 jsr se_crc_byte
 iny
 cpy #126
 bcc @crc
 EQ se_crc_value,S_MAN+126,2
 jmp advance
qnew:
 lda #$C0
 ldy #$F0
 ldx #96
 jsr request
 jsr se_bc_arena_read
 jcs return
 CP BC_IO,S_NEW,96
 EQ S_NEW+12,S_AUTH+5,4
 EQ S_NEW+59,S_AUTH+5,4
 EQ S_NEW+34,S_MAN+42,6
 EQ S_NEW+74,S_MAN+50,2
 jmp advance
qold:
 lda S_MAN+102
 cmp #0
 beq @read
 cmp #128
 jne stale
@read:ldy #0
 ldx #128
 jsr request
 jsr raw_read
 jcs return
 jsr bca_root_check
 jcs return
 CP BC_IO,S_DRAFT,128
 EQ BC_IO+22,S_MAN+8,4
 EQ BC_IO+18,S_MAN+98,4
 EQ BC_IO+119,S_MAN+96,2
 lda BC_IO+31
 cmp #1
 jne stale
 lda BC_IO+30
 jne stale
 EQ BC_IO+104,S_ROOT+104,11
 lda #1
 sta BCA_PAGE
 sta BCA_KIND
 sta BCA_GENERATION
 lda #0
 sta BCA_GENERATION+1
 jsr se_bc_page_begin
 jcs return
 jmp advance
qbase:
 jsr bca_page_step
 jcs return
 cmp #0
 jne pending
 jmp advance
qrecord:
 lda #64
 sta BCA_OFFSET
 lda #$10
 sta BCA_OFFSET+1
 lda #0
 sta BCA_OFFSET+2
 ldx S_INDEX
 beq @ready
@add:clc
 lda BCA_OFFSET
 adc #96
 sta BCA_OFFSET
 bcc :+
 inc BCA_OFFSET+1
:dex
 bne @add
@ready:lda #96
 sta BCA_LENGTH
 jsr se_bc_arena_read
 jcs return
 CP BC_IO,S_CR,96
 lda S_CR
 cmp #1
 jne stale
 lda S_CR+1
 cmp #1
 jne stale
 EQ S_CR+12,S_ROOT+26,4
 EQ S_CR+59,S_ROOT+26,4
 EQ S_CR+16,S_EXPECT,3
 jsr qcrc
 jcs return
 clc
 .repeat 3,I
 lda S_CR+16+I
 adc S_CR+25+I
 sta S_NEXT+I
 .endrepeat
 jcs stale
 lda #0
 sta S_ORIGIN
 lda S_INDEX
 cmp S_MAN+17
 bcc @mapped
 bne @suffix
 CP S_NEW,S_CR,96
 lda #1
 sta S_ORIGIN
 jmp @mapped
@suffix:INC24 S_CR+16
@mapped:
 clc
 .repeat 3,I
 lda S_CR+16+I
 adc S_CR+19+I
 sta S_END+I
 .endrepeat
 jcs stale
 C24 S_QUERY,S_END
 bcc @found
 beq @found
 CP S_NEXT,S_EXPECT,3
 inc S_INDEX
 lda S_INDEX
 cmp S_N
 jcs stale
 jmp pending
@found:
 ; OutputCRC certifiesderivedlivecoordinates; originalstoredCR notwritten.
 jsr se_crc_init
 ldy #1
@crc:cpy #74
 bne :+
 ldy #76
:lda S_CR,y
 jsr se_crc_byte
 iny
 cpy #96
 bcc @crc
 CP se_crc_value,S_CR+74,2
 lda #0
 clc
 rts
qcrc:
 jsr se_crc_init
 ldy #1
@crc:cpy #74
 bne :+
 ldy #76
:lda S_CR,y
 jsr se_crc_byte
 iny
 cpy #96
 bcc @crc
 EQ se_crc_value,S_CR+74,2
 clc
 rts
