; Private current-schema flags5 COW rebase; narrow actual single insertion.
; C40 private singleobservedSPLICE bridge, strict firstincrement only.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "cache/edit-rebase-current-probe/api.inc"
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
 jne stale
 jsr release
 lda #0
 clc
 rts
begin:
 lda #0
 sta S_INPUT+3
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
 clc
 adc S_INPUT+3
 cmp #1
 jne miss
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
 lda S_INPUT+3
 sta S_MODE
 CP S_INPUT,S_QUERY,3
 CP se_bc_arena,S_AUTH,13
 lda se_bc_head
 sta S_HEAD
 lda se_bc_tail
 sta S_TAIL
 ldx S_MODE
 bne @empty
 clc
 adc #1
 cmp #3
 bcc :+
 lda #0
:cmp S_HEAD
 jne miss
 jmp @topology
@empty:cmp S_HEAD
 jne miss
@topology:lda S_TAIL
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
 lda S_MODE
 bne @source
 jsr event_check
 jcs @return
@source:
 lda #0
 jsr reader
 jcs @return
 lda #1
 sta S_LIVE
 lda se_bc_flags
 ora #BC_ACTIVE
 and #($FF-BC_PAGE_PROOF)
 sta se_bc_flags
 lda S_MODE
 beq @build
 lda #6
 jsr helper
 jcs failed
 lda #6
 bne @state
@build:lda #0
 jsr helper
 jcs failed
 lda #1
@state:sta S_STATE
 jmp pending
@return:rts
event_check:
 lda S_EVENT
 cmp #$A5
 jne corrupt
 lda S_EVENT+1
 cmp #1
 jne stale
 lda S_EVENT+2
 ora S_EVENT+3
 ora S_EVENT+19
 ora S_EVENT+20
 ora S_EVENT+21
 ora S_EVENT+23
 ora S_EVENT+24
 ora S_EVENT+31
 jne stale
 lda S_EVENT+22
 cmp #1
 jne stale
 EQ S_EVENT+4,S_AUTH+5,4
 EQ S_EVENT+25,S_EVENT+27,2
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
 clc
 rts
guard:
 lda se_render_caps
 cmp #1
 beq @caps
 cmp #3
 jne stale
@caps:
 EQ S_AUTH,se_bc_arena,13
 lda se_bc_count
 clc
 adc S_MODE
 cmp #1
 jne stale
 lda se_bc_flags
 and #(BC_ARMED|BC_LOST|BC_MUTATING|BC_ACTIVE)
 cmp #(BC_ARMED|BC_ACTIVE)
 jne stale
 lda se_bc_head
 cmp S_HEAD
 jne stale
 lda se_bc_tail
 cmp S_TAIL
 jne stale
 lda S_MODE
 bne @source
 ldy S_SLOT
 ldx #0
@event:lda se_bc_ring,y
 cmp S_EVENT,x
 jne stale
 iny
 inx
 cpx #32
 bcc @event
@source:lda #1
 jmp reader
step:
 lda S_ABI
 cmp #S_PROOF
 jne stale
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
 lda #1
 jsr helper
 jcs failed
 cmp #0
 jne pending
 CP BC_IO,S_ROOT,128
 jsr root_check
 jcs failed
 lda S_ROOT+104
 sta BCA_PAGE
 lda #1
 sta BCA_KIND
 sta BCA_GENERATION
 lda #0
 sta BCA_GENERATION+1
 lda #2
 jsr helper
 jcs failed
 lda #2
 sta S_STATE
 jmp pending
root_check:
 lda S_ROOT+31
 cmp #5
 jne stale
 lda S_ROOT+30
 ora S_ROOT+32+30
 ora S_ROOT+32+31
 ora S_ROOT+32+32
 ora S_ROOT+32+33
 jne stale
 ; OneactualCRpage only, no baselinepage15 dependency; narrowcapacityrefusal.
 lda S_ROOT+104
 jeq stale
 cmp #14
 jcs stale
 cmp S_ROOT+108
 jne stale
 lda S_ROOT+105
 ora S_ROOT+107
 ora S_ROOT+111
 ora S_ROOT+113
 ora S_ROOT+114
 jne stale
 lda S_ROOT+106
 cmp #1
 jne stale
 lda S_ROOT+110
 cmp #1
 jne stale
 lda S_ROOT+112
 jeq @bad
 cmp #43
 jcs @bad
 sta S_N
 sec
 sbc #1
 cmp S_ROOT+109
 jne stale
 lda S_ROOT+94
 cmp #1
 jne stale
 lda S_ROOT+96
 cmp #1
 jne stale
 lda S_ROOT+100
 cmp #1
 jne stale
 lda S_ROOT+98
 cmp #1
 jne stale
 lda S_ROOT+102
 cmp #1
 jne stale
 lda S_ROOT+95
 ora S_ROOT+97
 ora S_ROOT+99
 ora S_ROOT+101
 ora S_ROOT+103
 jne stale
 lda S_ROOT+115
 and S_ROOT+116
 and S_ROOT+117
 and S_ROOT+118
 cmp #$FF
 jne stale
 EQ S_ROOT+22,S_ROOT+26,4
 ; semanticTicket=current-1, observedrevision=current-1, generationunchanged.
 sec
 .repeat 4,I
 lda S_AUTH+5+I
 .if I=0
 sbc #1
 .else
 sbc #0
 .endif
 sta S_TEMP+I
 .endrepeat
 jcc stale
 EQ S_TEMP,S_ROOT+22,4
 EQ S_ROOT+32,S_READER+27,25
 EQ S_ROOT+57,S_EVENT+8,4
 EQ S_READER+52,S_EVENT+12,4
 EQ S_EVENT+25,S_READER+31,2
 clc
 .repeat 4,I
 lda S_EVENT+8+I
 .if I=0
 adc #1
 .else
 adc #0
 .endif
 sta S_TEMP+I
 .endrepeat
 jcs stale
 EQ S_TEMP,S_EVENT+12,4
 lda S_READER+57
 cmp #1
 jne stale
 EQ S_ROOT+91,S_ROOT+53,3
 CP S_ROOT+91,S_TEMP,3
 INC24 S_TEMP
 EQ S_TEMP,S_READER+10,3
 lda BCA_SELECTED
 eor #128
 sta S_DEST
 clc
 rts
@bad:jmp stale
page_step:
 lda #1
 jsr helper
 jcs failed
 cmp #0
 jne pending
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
 clc
 rts
locate:
 jsr record_read
 jcs failed
 jsr record_check
 jcs failed
 C24 S_EVENT+16,S_END
 bcc @inside
 beq @inside
 CP S_NEXT,S_EXPECT,3
 inc S_INDEX
 lda S_INDEX
 cmp S_N
 jcs failed_stale
 jmp pending
@inside:
 C24 S_EVENT+16,S_CR+16
 jcc failed_stale
 jeq failed_stale
 ; DirtytrueCRplainline with complete emptyINLINE certificate.
 lda S_CR+2
 cmp #5
 jne failed_stale
 lda S_CR+3
 cmp #0
 jne failed_stale
 lda S_CR+22
 ora S_CR+23
 ora S_CR+24
 ora S_CR+44
 ora S_CR+45
 ora S_CR+46
 ora S_CR+69
 ora S_CR+70
 ora S_CR+71
 jne failed_stale
 lda S_CR+40
 and S_CR+41
 and S_CR+42
 and S_CR+43
 cmp #$FF
 jne failed_stale
 ; Position strictlyinterior, includingnotactualCRatEND.
 C24 S_EVENT+16,S_END
 jcs failed_stale
 CP S_CR,S_OLD,96
 jsr se_sm_init
 CP S_CR+16,se_sm_pos,3
 jsr se_sm_at_line
 lda S_CR+28
 sta se_sm_fence
 lda S_CR+29
 sta se_sm_language
 lda S_CR+30
 sta se_sm_regions
 CP S_CR+31,sm_region_overflow,3
 CP S_CR+16,S_CURSOR,3
 lda #4
 sta S_STATE
 jmp pending
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
 jcs failed
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
@bad:jmp stale
@cr:
 CP S_END,S_TEMP,3
 INC24 S_TEMP
 C24 S_CURSOR,S_TEMP
 jne stale
@ok:clc
 rts
convergence_dispatch:
 jsr converge
 jcs failed
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
 lda #4
 jsr helper
 jcs failed
 lda #5
 sta S_STATE
 jmp pending
publish:
 lda #5
 jsr helper
 jcs failed
 cmp #0
 jne pending
 jsr release
 lda #0
 clc
 rts
