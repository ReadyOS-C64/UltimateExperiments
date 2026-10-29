; Private one-CR-page COW publication + root/CR lexical resolver.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "cache/lexical-link-probe/api.inc"
.include "fold/source.inc"
.import se_f_owner,se_overlay_frame,se_overlay_call,se_render_caps
.import se_snapshot_busy,se_crc_init,se_crc_byte,se_crc_value
.import bca_owner,bca_guard,bca_validate,bca_transfer,bca_crc_root,bca_root_check
.import bca_open_step,se_bc_arena_open,se_bc_page_begin,bca_page_step,se_bc_arena_read
.import bca_pending,bca_done,bca_bad,bca_stale,bca_corrupt
.export entry
.macro CP source,target,n
 .if n=1
 lda source
 sta target
 .else
 ldy #n-1
:
 lda source,y
 sta target,y
 dey
 bpl :-
 .endif
.endmacro
.macro EQ source,target,n
 .if n=1
 lda source
 cmp target
 jne bca_stale
 .else
 ldy #n-1
:
 lda source,y
 cmp target,y
 jne bca_stale
 dey
 bpl :-
 .endif
.endmacro
.macro LIVE source,offset,n
 EQ source,LX_READER+27+offset,n
.endmacro
.segment "CODE"
 OVL_BINDING
entry:
 jsr bca_owner
 bcs link_return
 lda se_overlay_frame
 cmp #2
 jeq cancel
 lda se_render_caps
 cmp #3
 bne miss
 lda se_overlay_frame
 jeq begin
 cmp #3
 jeq resolve
 cmp #1
 jne bca_bad
 lda LL_STATE
 jeq bca_bad
 jsr link_guard
 bcs fail
 jmp step
link_return:rts
miss:lda #2
 clc
 rts
fail:pha
 jsr cancel
 pla
 sec
 rts
.include "cache/lexical-link-probe/guard.inc"
; Root/CR state is separate from the released lexical worker's receipt.
begin:
 lda LP_STATE
 cmp #3
 jne bca_bad
 lda LL_STATE
 ora LX_LIVE
 jne bca_bad
 CP LX_CR+16,LL_TARGET,3
 lda LP_PAGE
 sta LL_LEX
 lda #0
 sta LL_LEX+1
 CP LP_GEN,LL_LEX+2,4
 lda #0
 sta LL_MODE
 jmp start
resolve:
 lda LL_STATE
 ora LX_LIVE
 jne bca_bad
 lda #1
 sta LL_MODE
 CP se_bc_arena,LX_AUTH,13
start:
 ; Authentic held source59 comes from actual producer; resolver capturesfresh.
 CP LX_READER+27,LX_PARSER,59
 lda #0
 ldy #85
@clear:sta LX_READER,y
 dey
 bpl @clear
 jsr reader
 jcs fail
 lda #1
 sta LX_LIVE
 lda LL_MODE
 bne source_matched
 EQ LX_READER+27,LX_PARSER,59
 CP LX_CR,$8200,96
source_matched:
 lda #0
 sta BCA_PHASE
 sta BCA_PROOF
 jsr se_bc_arena_open
 jcs fail
 cmp #1
 jne fail
 lda #1
 sta LL_STATE
 jmp bca_pending
reader:
 pha
 CP LX_READER,se_fs_state,86
 pla
 sta se_overlay_frame
 lda #14
 ldx #0
 jsr se_overlay_call
 php
 pha
 CP se_fs_state,LX_READER,86
 pla
 plp
 rts
cancel:
 lda LX_LIVE
 beq cancel_clear
 CP LX_READER,se_fs_state,86
 jsr se_fs_end
 CP se_fs_state,LX_READER,86
cancel_clear:
 lda #0
 sta LX_LIVE
 sta LL_STATE
 sta BCA_PHASE
 sta BCA_PROOF
 clc
 rts
step:
 lda LL_STATE
 sec
 sbc #1
 cmp #13
 jcs bca_bad
 asl
 tax
 lda step_table,x
 sta LL_JUMP
 lda step_table+1,x
 sta LL_JUMP+1
 jmp (LL_JUMP)
step_table:
 .word opened,verified,header_read,find,record_read,record_write
 .word seal_header,page_valid,directory,directory_valid,new_verified
 .word root_write,root_valid
opened:
 jsr bca_open_step
 jcs fail
 cmp #1
 jeq bca_pending
 ; The generic OPEN checked format/CRC/current incarnation; source binds here.
 EQ BC_IO+BC_ROOT_SOURCE,LX_READER+27,59
 EQ BC_IO+BC_ROOT_TICKET,LX_AUTH+5,4
 lda BC_IO+94
 and BC_IO+96
 cmp #1
 jne bca_corrupt
 lda BC_IO+95
 ora BC_IO+97
 ora BC_IO+99
 jne bca_corrupt
 lda LL_MODE
 bne @lex_root
 lda BC_IO+98
 jne bca_bad
 lda BC_IO+31
 cmp #1
 jne bca_bad
 jmp @shape
@lex_root:
 lda BC_IO+98
 cmp #LL_LEX_ABI
 bne @unsupported
 lda BC_IO+31
 cmp #LL_ROOT_FLAGS
 beq @shape
@unsupported:jsr cancel
 jmp miss
@shape:
 lda BC_IO+113
 ora BC_IO+114
 jne bca_bad
 lda BC_IO+112
 beq @bad
 cmp #43
 bcs @bad
 sta LL_SLOTS
 lda BC_IO+105
 jne bca_bad
 lda BC_IO+104
 cmp BC_IO+108
 jne bca_bad
 sta LL_OLD
 lda BC_IO+109
 clc
 adc #1
 cmp LL_SLOTS
 jne bca_bad
 EQ BC_IO+106,BC_IO+110,2
 CP BC_IO+106,LL_GENERATION,2
 CP BC_IO,LL_ROOT,128
 lda BCA_SELECTED
 sta LL_SELECTED
 lda LL_OLD
 sta BCA_PAGE
 lda #BC_PAGE_CR
 sta BCA_KIND
 CP LL_GENERATION,BCA_GENERATION,2
 jsr se_bc_page_begin
 jcs fail
 inc LL_STATE
 jmp bca_pending
@bad:jmp bca_bad
verified:
 lda BCA_PHASE
 beq @ready
 jsr bca_page_step
 jcs fail
 jmp bca_pending
@ready:lda #3
 sta LL_STATE
 jmp bca_pending
header_read:
 lda LL_OLD
 jsr page_offset
 lda #64
 sta BCA_LENGTH
 lda #1
 jsr bca_transfer
 jcs fail
 CP BC_IO,LL_HEADER,64
 ; No hidden secondCR page or partial topology is accepted by this profile.
 ldy #7
@nil:lda BC_IO+25,y
 cmp #$FF
 jne bca_bad
 dey
 bpl @nil
 lda BC_IO+24
 jne bca_bad
 lda BC_IO+23
 cmp LL_SLOTS
 jne bca_bad
 lda #0
 sta LL_SLOT
 sta LL_FOUND
 lda LL_MODE
 bne @records
 lda #1
 sta LL_FREE
 lda #4
 sta LL_STATE
 jmp bca_pending
@records:lda #5
 sta LL_STATE
 jmp bca_pending
find:
 lda LL_FREE
 beq @full
 ldx BCA_BANKS
 cpx #16
 beq @available
 txa
 asl
 asl
 asl
 asl
 cmp LL_FREE
 bcc @full
 beq @full
@available:lda LL_FREE
 jsr dir_offset
 lda #8
 sta BCA_LENGTH
 lda #1
 jsr bca_transfer
 jcs fail
 lda #0
 ldy #7
@zero:ora BC_IO,y
 dey
 bpl @zero
 cmp #0
 beq @found
 inc LL_FREE
 jmp bca_pending
@found:jsr se_crc_init
 CP se_crc_value,LL_RUN,2
 lda #5
 sta LL_STATE
 jmp bca_pending
@full:jsr cancel
 lda #3
 clc
 rts
record_offset:
 jsr page_offset
 lda #64
 sta BCA_OFFSET
 ldx LL_SLOT
 beq @done
@slot:clc
 lda BCA_OFFSET
 adc #96
 sta BCA_OFFSET
 bcc :+
 inc BCA_OFFSET+1
:
 dex
 bne @slot
@done:lda #96
 sta BCA_LENGTH
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
record_check:
 jsr record_crc
 EQ se_crc_value,BC_IO+74,2
 rts
record_read:
 lda LL_OLD
 jsr record_offset
 jsr se_bc_arena_read
 jcs fail
 lda BC_IO
 and BC_IO+1
 cmp #1
 jne bca_corrupt
 jsr record_check
 EQ BC_IO+12,LX_AUTH+5,4
 lda LL_MODE
 jne resolved_record
 ; BaselineABI0 has no lexical records; do not replace unknownformats.
 lda BC_IO+2
 and #LL_LEX_COMPLETE
 jne bca_bad
 ldy #3
@nil:lda BC_IO+47,y
 cmp #$FF
 jne bca_bad
 dey
 bpl @nil
 ldy #2
@target:lda BC_IO+16,y
 cmp LL_TARGET,y
 bne @ordinary
 dey
 bpl @target
 lda LL_FOUND
 jne bca_corrupt
 EQ BC_IO,$8200,96
 inc LL_FOUND
 lda BC_IO+2
 ora #LL_LEX_COMPLETE
 sta BC_IO+2
 CP LL_LEX,BC_IO+47,4
 CP LL_COUNT,BC_IO+51,2
 lda #0
 sta BC_IO+53
 jsr record_crc
 CP se_crc_value,BC_IO+74,2
@ordinary:
 lda #6
 sta LL_STATE
 jmp bca_pending
record_write:
 ; Held96B record is rechecked before publishing it to candidate scratch.
 jsr record_check
 lda LL_FREE
 jsr record_offset
 CP LL_RUN,se_crc_value,2
 ldy #0
@byte:lda BC_IO,y
 jsr se_crc_byte
 iny
 cpy #96
 bne @byte
 CP se_crc_value,LL_RUN,2
 lda #0
 jsr bca_transfer
 jcs fail
 inc LL_SLOT
 lda LL_SLOT
 cmp LL_SLOTS
 beq @end
 lda #5
 sta LL_STATE
 jmp bca_pending
@end:dec LL_FOUND
 jne bca_bad
 lda #7
 sta LL_STATE
 jmp bca_pending
seal_header:
 CP LL_HEADER,BC_IO,64
 lda #0
 sta BC_IO+3
 sta BC_IO+7
 lda LL_FREE
 sta BC_IO+4
 lda #1
 sta BC_IO+6
 CP LL_RUN,BC_IO+39,2
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
 lda LL_FREE
 jsr page_offset
 lda #64
 sta BCA_LENGTH
 lda #0
 jsr bca_transfer
 jcs fail
 inc LL_STATE
 jmp bca_pending
page_valid:
 lda LL_FREE
 jsr page_offset
 lda #3
 sta BCA_OFFSET
 lda #1
 sta BC_IO
 sta BCA_LENGTH
 lda #0
 jsr bca_transfer
 jcs fail
 inc LL_STATE
 jmp bca_pending
directory:
 lda #0
 ldy #7
@clear:sta BC_IO,y
 dey
 bpl @clear
 lda #1
 sta BC_IO
 sta BC_IO+3
 lda #BC_PAGE_CR
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
 lda LL_FREE
 jsr dir_offset
 lda #8
 sta BCA_LENGTH
 lda #0
 jsr bca_transfer
 jcs fail
 inc LL_STATE
 jmp bca_pending
directory_valid:
 lda LL_FREE
 jsr dir_offset
 clc
 lda BCA_OFFSET
 adc #3
 sta BCA_OFFSET
 bcc :+
 inc BCA_OFFSET+1
:
 lda #1
 sta BC_IO
 sta BCA_LENGTH
 lda #0
 jsr bca_transfer
 jcs fail
 lda LL_FREE
 sta BCA_PAGE
 lda #BC_PAGE_CR
 sta BCA_KIND
 lda #1
 sta BCA_GENERATION
 lda #0
 sta BCA_GENERATION+1
 jsr se_bc_page_begin
 jcs fail
 inc LL_STATE
 jmp bca_pending
new_verified:
 lda BCA_PHASE
 beq @ready
 jsr bca_page_step
 jcs fail
 jmp bca_pending
@ready:inc LL_STATE
 jmp bca_pending
root_write:
 CP LL_ROOT,BC_IO,128
 jsr bca_root_check
 jcs fail
 lda #0
 sta BC_IO+5
 lda #LL_ROOT_FLAGS
 sta BC_IO+31
 lda #LL_LEX_ABI
 sta BC_IO+98
 sta BC_IO+102
 lda LL_FREE
 sta BC_IO+104
 sta BC_IO+108
 lda #1
 sta BC_IO+106
 sta BC_IO+110
 lda #0
 sta BC_IO+107
 sta BC_IO+111
 ldx #0
@seq:inc BC_IO+18,x
 bne @ok
 inx
 cpx #4
 bne @seq
 jmp bca_stale
@ok:jsr bca_crc_root
 CP se_crc_value,BC_IO+119,2
 jsr root_offset
 lda #128
 sta BCA_LENGTH
 lda #0
 jsr bca_transfer
 jcs fail
 inc LL_STATE
 jmp bca_pending
root_valid:
 jsr root_offset
 clc
 lda BCA_OFFSET
 adc #5
 sta BCA_OFFSET
 lda #1
 sta BC_IO
 sta BCA_LENGTH
 lda #0
 jsr bca_transfer
 jcs fail
 jsr cancel
 jmp bca_done
root_offset:
 lda LL_SELECTED
 eor #128
 sta BCA_OFFSET
 lda #0
 sta BCA_OFFSET+1
 sta BCA_OFFSET+2
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
 ldx #0
 stx BCA_OFFSET+2
 asl
 rol BCA_OFFSET+2
 asl
 rol BCA_OFFSET+2
 asl
 rol BCA_OFFSET+2
 sta BCA_OFFSET
 ldx BCA_OFFSET+2
 inx
 stx BCA_OFFSET+1
 lda #0
 sta BCA_OFFSET+2
 rts
resolved_record:
 ; This narrow resolver searches START exactly, not a forged hostpage ref.
 ldy #2
@query:lda BC_IO+16,y
 cmp LL_QUERY,y
 jne @next
 dey
 bpl @query
 lda BC_IO+2
 and #LL_LEX_COMPLETE
 jeq @miss
 lda BC_IO+3
 cmp #5
 bne @corrupt
 lda BC_IO+53
 bne @corrupt
 CP BC_IO+47,LP_PAGE,1
 lda BC_IO+48
 bne @corrupt
 CP BC_IO+49,LP_GEN,2
 CP BC_IO+51,LP_COUNT,2
 lda BC_IO+69
 sta LX_LANGUAGE
 ldx #3
 ldy #22
 jsr source_sum
 ldx #6
 ldy #19
 jsr source_sum
 lda #3
 sta LP_STATE
 lda #0
 sta LL_STATE
 ; Real R14 lease remains owned for actual releasedR26 consumer.
 jmp bca_done
@next:inc LL_SLOT
 lda LL_SLOT
 cmp LL_SLOTS
 beq @miss
 jmp bca_pending
@miss:jsr cancel
 jmp miss

@corrupt:jmp bca_corrupt
source_sum:
 clc
 lda BC_IO+16
 adc BC_IO,y
 sta LX_BODY-3,x
 lda BC_IO+17
 adc BC_IO+1,y
 sta LX_BODY-2,x
 lda BC_IO+18
 adc BC_IO+2,y
 sta LX_BODY-1,x
 jcs bca_corrupt
 rts
