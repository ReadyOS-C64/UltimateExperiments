; Private current-schema flags5 COW rebase; narrow actual single insertion.
; C41 private repeatable narrow SPLICE/REKEY bridge; optional refusals resume C21.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "cache/edit-rebase-integration/api.inc"
.include "fold/source.inc"
.include "supermark/api.inc"
.import se_overlay_frame,se_overlay_call,se_f_owner,se_render_caps
.import se_crc_init,se_crc_byte,se_crc_value
.import se_sm_init,se_sm_at_line,se_sm_feed,se_sm_pos,se_sm_ready,se_sm_kind,se_sm_start,se_sm_end,se_sm_body,se_sm_fence,se_sm_language,se_sm_regions,sm_region_overflow
.export entry
.segment "CODE"
OVL_BINDING
entry:
 lda se_f_owner
 cmp #4
 jne busy
 lda se_overlay_frame
 beq admit
 jmp dispatch
admit:
 pha
 lda se_render_caps
 cmp #1
 beq @ok
 cmp #3
 beq @ok
 pla
 jmp miss
@ok:pla
dispatch:
 cmp #0
 jeq begin
 cmp #1
 jeq step
 cmp #2
 jeq cancel
 lda #$C0
 sec
 rts
busy:lda #$B2
 sec
 rts
ebr_stale:lda #$C1
 sec
 rts
corrupt:lda #$C2
 sec
 rts
miss:
 lda #21
 ldx #1
 jmp request
refuse:
 jsr release
 jmp miss
pending:
 lda #41
 ldx #1
request:
 sta $9135
 stx $9136
 lda #1
 clc
 rts
; R34 andR14 are sequential completed calls, neverR/R orC/Cnested.
helper:
 sta se_overlay_frame
 lda #34
 ldx #0
 jmp se_overlay_call
reader:
 pha
 CP S_READER,se_fs_state,86
 pla
 sta se_overlay_frame
 lda #14
 ldx #0
 jsr se_overlay_call
 php
 pha
 CP se_fs_state,S_READER,86
 pla
 plp
 rts
release:
 lda S_LIVE
 beq release_clear
 CP S_READER,se_fs_state,86
 jsr se_fs_end
release_clear:lda se_bc_flags
 and #($FF-BC_ACTIVE-BC_PAGE_PROOF)
 sta se_bc_flags
 lda #0
 sta S_LIVE
 sta S_STATE
 rts
failed:
 pha
 jsr release
 pla
 sta S_ERROR
 sec
 rts
cancel:
 lda S_ABI
 cmp #S_PROOF
 jne ebr_stale
 jsr release
 lda #0
 clc
 rts
begin:
begin_caps:
 lda se_render_caps
 cmp #1
 beq :+
 cmp #3
 jne miss
:lda se_bc_flags
 and #(BC_ARMED|BC_LOST|BC_MUTATING|BC_ACTIVE)
 cmp #BC_ARMED
 jne miss
 lda se_bc_count
 jeq miss
 cmp #3
 jcs miss
 lda se_doc_read_locks
 jne miss
 lda se_bc_head
 cmp #3
 jcs miss
 lda se_bc_tail
 cmp #3
 jcs miss
 lda #0
 tax
@clear:sta S,x
 sta S+256,x
 dex
 bne @clear
 ldx #63
@tail:sta S+512,x
 dex
 bpl @tail
 lda #S_PROOF
 sta S_ABI
 lda se_bc_count
 sta S_COUNT
 CP se_bc_arena,S_AUTH,13
 lda se_bc_head
 sta S_HEAD
 lda se_bc_tail
 sta S_TAIL
 clc
 adc S_COUNT
 cmp #3
 bcc @index
 sbc #3
@index:cmp S_HEAD
 jne miss
lda S_TAIL
 .repeat 5
 asl
 .endrepeat
 sta S_SLOT
 tay
 ldx #0
@event:lda se_bc_ring,y
 sta S_EVENT,x
 iny
 inx
 cpx #32
 bcc @event
 lda S_EVENT+1
 sec
 sbc #1
 cmp #2
 jcs @return_stale
 sta S_MODE
 lda S_COUNT
 cmp #2
 bne @check_event
 lda S_MODE
 bne @return_stale
 lda S_TAIL
 clc
 adc #1
 cmp #3
 bcc @next
 lda #0
@next:
 .repeat 5
 asl
 .endrepeat
 tay
 ldx #0
@second:lda se_bc_ring,y
 sta S_REKEY,x
 iny
 inx
 cpx #32
 bcc @second
 jsr rekey_check
 bcs @return
@check_event:jsr event_check
 jcs @return
 cmp #2
 jeq miss

 lda #0
 jsr reader
 jcs @return
 lda #1
 sta S_LIVE
 lda se_bc_flags
 ora #BC_ACTIVE
 and #($FF-BC_PAGE_PROOF)
 sta se_bc_flags
 lda #0
 jsr helper
 jcs failed
 lda #1
@state:sta S_STATE
 jmp pending
@return:rts
@return_stale:jmp ebr_stale
event_check:
 lda S_EVENT
 cmp #$A5
 jne corrupt
 lda S_EVENT+2
 ora S_EVENT+3
 ora S_EVENT+31
 jne ebr_stale
 EQ S_EVENT+4,S_AUTH+5,4
@crc_begin:
 jsr se_crc_init
 ldy #1
@crc:lda S_EVENT,y
 jsr se_crc_byte
 iny
 cpy #29
 bcc @crc
 lda S_EVENT+31
 jsr se_crc_byte
 EQ se_crc_value,S_EVENT+29,2
 lda S_MODE
 bne @rekey
 lda S_EVENT+19
 ora S_EVENT+20
 ora S_EVENT+21
 ora S_EVENT+23
 ora S_EVENT+24
 jne unsupported
 lda S_EVENT+22
 cmp #1
 jne unsupported
 ldx #1
@gen:lda S_EVENT+25,x
 cmp S_EVENT+27,x
 jne unsupported
 dex
 bpl @gen
 jmp @supported
@rekey:
 EQ S_EVENT+8,S_EVENT+12,4
@supported:lda #0
 clc
 rts
unsupported:lda #2
 clc
 rts
rekey_check:
 lda S_REKEY
 cmp #$A5
 jne corrupt
 lda S_REKEY+1
 cmp #2
 jne ebr_stale
 lda S_REKEY+2
 ora S_REKEY+3
 ora S_REKEY+31
 jne ebr_stale
 EQ S_REKEY+4,S_AUTH+5,4
 jsr se_crc_init
 ldy #1
@crc:lda S_REKEY,y
 jsr se_crc_byte
 iny
 cpy #29
 bcc @crc
 lda S_REKEY+31
 jsr se_crc_byte
 EQ se_crc_value,S_REKEY+29,2
 clc
 rts
guard:
 lda se_render_caps
 cmp #1
 beq @caps
 cmp #3
 jne ebr_stale
@caps:
 EQ S_AUTH,se_bc_arena,13
 lda se_bc_count
 cmp S_COUNT
 jne ebr_stale
 lda se_bc_flags
 and #(BC_ARMED|BC_LOST|BC_MUTATING|BC_ACTIVE)
 cmp #(BC_ARMED|BC_ACTIVE)
 jne ebr_stale
 lda se_bc_head
 cmp S_HEAD
 jne ebr_stale
 lda se_bc_tail
 cmp S_TAIL
 jne ebr_stale
 ldy S_SLOT
 ldx #0
@event:lda se_bc_ring,y
 cmp S_EVENT,x
 jne ebr_stale
 iny
 inx
 cpx #32
 bcc @event
 lda S_COUNT
 cmp #2
 bne @source
 lda S_TAIL
 clc
 adc #1
 cmp #3
 bcc @next
 lda #0
@next:
 .repeat 5
 asl
 .endrepeat
 tay
 ldx #0
@second:lda se_bc_ring,y
 cmp S_REKEY,x
 jne ebr_stale
 iny
 inx
 cpx #32
 bcc @second
@source:lda #1
 jmp reader
step:
 lda S_ABI
 cmp #S_PROOF
 jne ebr_stale
 lda S_STATE
 jeq failed_stale
 jsr guard
 jcs failed
 lda S_STATE
 cmp #1
 jeq root_step
 cmp #2
 jeq page_step
 cmp #3
 jeq locate
 cmp #4
 jeq parse
 cmp #5
 jeq publish
 jmp failed_stale
root_step:
 lda #4
 sta S_BATCH
@again:
 lda #1
 jsr helper
 jcs failed
 cmp #0
 beq @complete
 dec S_BATCH
 bne @again
 jmp pending
@complete:
 CP BC_IO,S_ROOT,128
 ; A checked BASE-only root is legitimate but outside this lexical profile.
 ; Decline at this caller level so release/request returns to the dispatcher,
 ; not to the root_check JSR continuation. All FLAGS5/error checks remain.
 lda S_ROOT+31
 cmp #1
 jeq refuse
 jsr root_check
 jcs failed
 ; All root capability/schema guards passed; a full bounded journal is an
 ; applicability limit, not stale source. Decline at the outer dispatcher.
 lda S_ROOT+30
 clc
 adc S_COUNT
 cmp #49
 jcs refuse
 lda #7
 sta S_STATE
 lda #7
 ldx #11
 jmp request
root_check:
 lda S_ROOT+31
 cmp #5
 jne ebr_stale
 lda S_ROOT+32+30
 cmp #2
 jcs ebr_stale
 lda S_ROOT+32+31
 ora S_ROOT+32+32
 ora S_ROOT+32+33
 jne ebr_stale
 ; OneactualCRpage only, no baselinepage15 dependency; narrowcapacityrefusal.
 lda S_ROOT+104
 jeq ebr_stale
 cmp #16
 jcs ebr_stale
 cmp S_ROOT+108
 jne ebr_stale
 lda S_ROOT+105
 ora S_ROOT+107
 ora S_ROOT+111
 ora S_ROOT+113
 ora S_ROOT+114
 jne ebr_stale
 lda S_ROOT+106
 cmp #1
 jne ebr_stale
 lda S_ROOT+110
 cmp #1
 jne ebr_stale
 lda S_ROOT+112
 jeq @bad
 cmp #43
 jcs @bad
 sta S_N
 sec
 sbc #1
 cmp S_ROOT+109
 jne ebr_stale
 lda S_ROOT+94
 cmp #1
 jne ebr_stale
 lda S_ROOT+96
 cmp #1
 jne ebr_stale
 lda S_ROOT+100
 cmp #1
 jne ebr_stale
 lda S_ROOT+98
 cmp #1
 jne ebr_stale
 lda S_ROOT+102
 cmp #1
 jne ebr_stale
 lda S_ROOT+95
 ora S_ROOT+97
 ora S_ROOT+99
 ora S_ROOT+101
 ora S_ROOT+103
 jne ebr_stale
 lda S_ROOT+115
 and S_ROOT+116
 and S_ROOT+117
 and S_ROOT+118
 cmp #$FF
 jne ebr_stale
 clc
 rts
@bad:jmp ebr_stale
page_step:
 lda #4
 sta S_BATCH
@again:
 lda #1
 jsr helper
 jcs failed
 cmp #0
 beq @complete
 dec S_BATCH
 bne @again
 jmp pending
@complete:
 ; used bytes equal N*96, not an arbitrary truncatedvalidpage.
 lda #0
 sta S_TEMP
 sta S_TEMP+1
 ldx S_N
@sum:clc
 lda S_TEMP
 adc #96
 sta S_TEMP
 bcc :+
 inc S_TEMP+1
:dex
 bne @sum
 EQ S_TEMP,BCA_USED,2
 CP BCA_EXPECT,S_PAGE_CRC,2
 lda #3
 sta S_STATE
 jmp pending
record_read:
 ; page1+64+INDEX*96, covered by actualdirectory/header/fullpayloadCRC.
 lda #64
 sta BCA_OFFSET
 lda S_ROOT+104
 asl
 asl
 asl
 asl
 sta BCA_OFFSET+1
 lda #0
 sta BCA_OFFSET+2
 ldx S_INDEX
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
 lda #3
 jmp helper
record_check:
 CP BC_IO,S_CR,96
 lda S_CR
 cmp #1
 jne corrupt
 lda S_CR+1
 cmp #1
 jne corrupt
 lda S_CR+58
 cmp #1
 jne corrupt
 lda S_CR+63
 cmp #1
 jne corrupt
 lda S_CR+65
 cmp #1
 jne corrupt
 lda S_CR+67
 cmp #1
 jne corrupt
 lda S_CR+64
 ora S_CR+66
 ora S_CR+68
 ora S_CR+92
 ora S_CR+93
 ora S_CR+94
 ora S_CR+95
 jne corrupt
 EQ S_CR+12,S_ROOT+22,4
 EQ S_CR+59,S_ROOT+22,4
 lda S_CR+40
 and S_CR+41
 and S_CR+42
 and S_CR+43
 cmp #$FF
 jne unsupported
 lda S_CR+44
 ora S_CR+45
 ora S_CR+46
 jne unsupported
 EQ S_CR+16,S_EXPECT,3
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
 lda S_CR+2
 and #16
 beq @range
 inc S_LEX_COUNT
 lda S_LEX_COUNT
 cmp #2
 jcs unsupported
@range:
 clc
 .repeat 3,I
 lda S_CR+16+I
 adc S_CR+19+I
 sta S_END+I
 .endrepeat
 jcs corrupt
 clc
 .repeat 3,I
 lda S_CR+16+I
 adc S_CR+25+I
 sta S_NEXT+I
 .endrepeat
 jcs corrupt
 lda #0
 clc
 rts
locate:
 lda #4
 sta S_BATCH
@again:
 jsr record_read
 jcs failed
 jsr record_check
 jcs failed
 cmp #2
 jeq refuse
 lda S_MODE
 beq @position_ok
 lda S_CR+2
 and #16
 beq @position_ok
 ; R34's retained absolute LEX proof is intentionally after-code even for
 ; representation-only replay. Reject unsupported placement before writes.
 C24 S_EVENT+16,S_END
 jcc refuse
 jeq refuse
@position_ok:
 lda S_MARK
 bne @advance
 lda S_CR+3
 cmp #5
 bne @compare
 sec
 .repeat 3,I
 lda S_CR+19+I
 sbc S_CR+22+I
 sta S_TEMP+I
 .endrepeat
 jcc refuse
 lda S_TEMP+2
 bne @long
 lda S_TEMP+1
 cmp #16
 bcc @compare
@long:lda #1
 sta S_LONG
@compare:
 lda S_MODE
 bne @advance
 C24 S_EVENT+16,S_END
 jcc @inside
 jeq @inside
@advance:
 CP S_NEXT,S_EXPECT,3
 inc S_INDEX
 lda S_INDEX
 cmp S_N
 bcc @continue
 lda S_LONG
 jeq refuse
 lda S_MODE
 beq @dirty
 lda #$FF
 sta S_INDEX
 jmp publish_ready
@dirty:
 lda S_MARK
 jeq refuse
 lda S_DIRTY
 sta S_INDEX
 CP S_DIRTY_END,S_END,3
 CP S_DIRTY_NEXT,S_NEXT,3
 jsr se_sm_init
 CP S_OLD+16,se_sm_pos,3
 jsr se_sm_at_line
 lda S_OLD+28
 sta se_sm_fence
 lda S_OLD+29
 sta se_sm_language
 lda S_OLD+30
 sta se_sm_regions
 CP S_OLD+31,sm_region_overflow,3
 CP S_OLD+16,S_CURSOR,3
 lda #4
 sta S_STATE
@pending:jmp pending
@continue:
 dec S_BATCH
 jne @again
 jmp pending
@inside:
 C24 S_EVENT+16,S_CR+16
 jcc refuse
 jeq refuse
 ; DirtytrueCRplainline with complete emptyINLINE certificate.
 lda S_CR+2
 cmp #5
 jne refuse
 lda S_CR+3
 cmp #0
 jne refuse
 lda S_CR+22
 ora S_CR+23
 ora S_CR+24
 ora S_CR+44
 ora S_CR+45
 ora S_CR+46
 ora S_CR+69
 ora S_CR+70
 ora S_CR+71
 jne refuse
 lda S_CR+40
 and S_CR+41
 and S_CR+42
 and S_CR+43
 cmp #$FF
 jne refuse
 ; Position strictlyinterior, includingnotactualCRatEND.
 C24 S_EVENT+16,S_END
 jcs refuse
 CP S_CR,S_OLD,96
 CP S_END,S_DIRTY_END,3
 CP S_NEXT,S_DIRTY_NEXT,3
 lda S_INDEX
 sta S_DIRTY
 lda #1
 sta S_MARK
 jmp @advance
failed_stale:lda #$C1
 jmp failed
parse:
 CP S_CURSOR,S_READER,3
 lda #32
 sta S_READER+3
 lda #<S_PACKET
 sta S_READER+4
 lda #>S_PACKET
 sta S_READER+5
 lda #2
 jsr reader
 jcs failed
 lda S_READER+6
 jeq failed_stale
 sta S_USED
 lda #0
 sta S_AT
@feed:
 ldx S_AT
 lda S_PACKET,x
 jsr allowed_byte
 jcs refuse
 ldx S_AT
 lda S_PACKET,x
 jsr se_sm_feed
 INC24 S_CURSOR
 INC24 S_FEEDS
 inc S_AT
 lda se_sm_ready
 jne convergence_dispatch
 lda S_AT
 cmp S_USED
 bcc @feed
 jmp pending
allowed_byte:
 cmp #13
 beq @cr
 cmp #32
 beq @ok
 cmp #33
 beq @ok
 cmp #44
 beq @ok
 cmp #46
 beq @ok
 cmp #59
 beq @ok
 cmp #63
 beq @ok
 cmp #48
 bcc @bad
 cmp #58
 bcc @ok
 cmp #65
 bcc @bad
 cmp #91
 bcc @ok
 cmp #$C1
 bcc @bad
 cmp #$DB
 bcc @ok
@bad:jmp ebr_stale
@cr:
 CP S_END,S_TEMP,3
 INC24 S_TEMP
 C24 S_CURSOR,S_TEMP
 jne ebr_stale
@ok:clc
 rts
convergence_dispatch:
 jsr converge
 jcs refuse
 rts
converge:
 CP S_NEXT,S_TEMP,3
 INC24 S_TEMP
 EQ S_TEMP,se_sm_pos,3
 EQ S_OLD+16,se_sm_start,3
 EQ S_OLD+16,se_sm_body,3
 CP S_END,S_TEMP,3
 INC24 S_TEMP
 EQ S_TEMP,se_sm_end,3
 lda se_sm_kind
 cmp #0
 jne failed_stale
 lda se_sm_fence
 cmp S_OLD+34
 jne failed_stale
 lda se_sm_language
 cmp S_OLD+35
 jne failed_stale
 lda se_sm_regions
 cmp S_OLD+36
 jne failed_stale
 EQ sm_region_overflow,S_OLD+37,3
 CP S_OLD,S_NEW,96
 CP S_AUTH+5,S_NEW+12,4
 CP S_AUTH+5,S_NEW+59,4
 INC24 S_NEW+19
 INC24 S_NEW+25
 jsr se_crc_init
 ldy #1
@crc:cpy #74
 bne :+
 ldy #76
:lda S_NEW,y
 jsr se_crc_byte
 iny
 cpy #96
 bcc @crc
 CP se_crc_value,S_NEW+74,2
publish_ready:
 lda #4
 jsr helper
 jcs failed
 lda #5
 sta S_STATE
 jmp pending
publish:
 ; One source/observer guard belongs to this synchronous foreground call.
 ; Each R34 operation retains its own typed arena guard. Never carry this
 ; quota/proof across a public yield; cap at four existing bounded units.
 lda #4
 sta S_BATCH
@again:
 lda #5
 jsr helper
 jcs failed
 cmp #3
 jeq commit
 dec S_BATCH
 bne @again
 jmp pending

; R34 returned verified A3. The following calls are synchronous, so there is
; no input/source/cache mutation opportunity between that verification,
; FORMAT validation, VALID-last root stash and RAM retirement.
commit:
 CP S_ROOT,BC_IO,128
 CP S_READER+27,BC_IO+32,59
 CP S_READER+10,BC_IO+91,3
 CP S_AUTH+5,BC_IO+22,4
 clc
 lda S_ROOT+30
 adc S_COUNT
 sta BC_IO+30
 lda S_NEW_CR
 sta BC_IO+104
 sta BC_IO+108
 ldx #0
@seq:inc BC_IO+18,x
 bne @ready
 inx
 cpx #4
 bcc @seq
 jmp failed_stale
@ready:jsr se_crc_init
 ldy #0
@crc:cpy #5
 beq @skip
 cpy #119
 beq @skip
 cpy #120
 beq @skip
 lda BC_IO,y
 jsr se_crc_byte
@skip:iny
 cpy #128
 bcc @crc
 CP se_crc_value,BC_IO+119,2
 lda #6
 jsr helper
 jcs failed
 CP BC_IO,S_DRAFT,128
 lda #0
 sta BC_IO+5
 lda S_DEST
 sta se_object_offset
 lda #0
 sta se_object_offset+1
 sta se_object_offset+2
 sta se_object_length+1
 lda #128
 sta se_object_length
 jsr stash
 jcs failed
 lda S_DEST
 clc
 adc #5
 sta se_object_offset
 lda #1
 sta BC_IO
 sta se_object_length
 jsr stash
 jcs failed
 lda S_HEAD
 sta se_bc_tail
 lda #0
 sta se_bc_count
 jsr release
 jmp miss
stash:
 CP S_AUTH,se_object_id,5
 lda #<BC_IO
 sta se_object_c64
 lda #>BC_IO
 sta se_object_c64+1
 lda #0
 jmp se_object_copy
