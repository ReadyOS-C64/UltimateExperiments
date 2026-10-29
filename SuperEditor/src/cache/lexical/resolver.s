; Private one-CR-page COW publication + root/CR lexical resolver.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "cache/lexical/link.inc"
.include "fold/source.inc"
.include "render/geos/semantic.inc"
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
 jeq bca_bad
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
link_guard:

 lda LX_LIVE
 cmp #1
 jne bca_stale
 lda LX_READER+7
 and LX_READER+8
 cmp #1
 jne bca_stale
 lda se_doc_read_locks
 jeq bca_stale
 EQ LX_AUTH,se_bc_arena,13
 lda se_bc_flags
 and #(BC_ARMED|BC_LOST|BC_MUTATING|BC_ACTIVE)
 cmp #(BC_ARMED|BC_ACTIVE)
 jne bca_stale
 lda se_bc_count
 jne bca_stale
 FS_FIELDS LIVE
 lda se_doc_busy
 ora se_h_phase
 ora se_b_phase
 ora se_clip_busy
 ora se_snapshot_busy
 jne bca_stale
 jsr se_doc_validate
 jcs link_return
 CP se_doc_meta,se_object_id,5
 jsr se_object_validate
 jcs link_return
 CP se_doc_original,se_object_id,5
 jsr se_object_validate
 jcs link_return
 CP se_doc_append,se_object_id,5
 jsr se_object_validate
 jcs link_return
 jmp bca_guard
; Root/CR state is separate from the released lexical worker's receipt.
resolve:
 lda LL_STATE
 jne bca_bad
 lda LX_LIVE
 cmp #1
 jne bca_bad
 lda #1
 sta LL_MODE
 CP se_bc_arena,LX_AUTH,13
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
cancel:
 lda LX_LIVE
 beq cancel_clear
 CP LX_READER,se_fs_state,86
 jsr se_fs_end
 CP se_fs_state,LX_READER,86
cancel_clear:
 lda se_bc_flags
 and #($FF-BC_ACTIVE)
 sta se_bc_flags
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
 cmp #5
 jcs bca_bad
 asl
 tax
 lda step_table,x
 sta LL_JUMP
 lda step_table+1,x
 sta LL_JUMP+1
 jmp (LL_JUMP)
step_table:
 .word opened,verified,header_read,bca_bad,record_read
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
 lda BC_IO+31
 cmp #1
 beq @base
 cmp #LL_ROOT_FLAGS
 bne @unsupported
 lda BC_IO+98
 cmp #LL_LEX_ABI
 beq @shape
@unsupported:jsr cancel
 jmp miss
@base:lda BC_IO+98
 jne bca_corrupt
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
 lda #5
 sta LL_STATE
 jmp bca_pending
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
 jmp resolved_record
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
resolved_record:
 ; This narrow resolver searches START exactly, not a forged hostpage ref.
 ldy #2
@query:lda BC_IO+16,y
 cmp LL_QUERY,y
 jne @next
 dey
 bpl @query
 lda BC_IO+3
 cmp #5
 jne bca_corrupt
 lda BC_IO+69
 cmp $9096+1+GSEM_LANG
 jne bca_corrupt
 ldx #3
 ldy #22
 jsr source_sum
 ldx #6
 ldy #19
 jsr source_sum
 EQ LX_BODY,$9096+1+GSEM_BODY,3
 EQ LX_END,$9096+1+GSEM_END,3
 lda BC_IO+2
 and #LL_LEX_COMPLETE
 jeq receipt
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

receipt:
 lda LL_ROOT+31
 cmp #1
 jne @miss_root
 ldy #3
@nil:lda BC_IO+47,y
 cmp #$FF
 jne bca_corrupt
 dey
 bpl @nil
 lda BC_IO+51
 ora BC_IO+52
 ora BC_IO+53
 jne bca_corrupt
 CP BC_IO,LX_PACKET,96
 jsr cancel
 CP LX_AUTH,LX+94,13
 CP LX_READER+27,LX+32,59
 lda #0
 sta LX_STATE
 sta LX_READY
 lda #4
 clc
 rts
@miss_root:jsr cancel
 jmp miss
