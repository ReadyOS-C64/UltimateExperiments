; Private C41: actual typed-root selector + feature3 classification.
; Baseline flags1 is handed to the byte-unchanged C35 via root REQUEST/OP.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "cache/splice-query-probe/api.inc"
.include "fold/source.inc"
.import se_overlay_frame,se_overlay_call,se_f_owner,se_render_caps
.import se_crc_init,se_crc_byte,se_crc_value
.export entry
.segment "CODE"
OVL_BINDING
entry:
 lda se_f_owner
 cmp #4
 jne busy
 lda se_overlay_frame
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
pending:
 lda #SQ_ID
 sta $9135
 lda #1
 sta $9136
 clc
 rts
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
 sta SQ_FRAME+GSEM_ACTIVE
 rts
failed:
 pha
 jsr release
 pla
 sta S_ERROR
 sta SQ_FRAME+GSEM_ERROR
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
 lda se_render_caps
 cmp #1
 beq :+
 cmp #3
 jne miss
:lda SQ_FRAME+GSEM_ACTIVE
 jne busy
 lda se_bc_flags
 and #(BC_ARMED|BC_LOST|BC_MUTATING|BC_ACTIVE)
 cmp #BC_ARMED
 jne miss
 lda se_bc_count
 ora se_doc_read_locks
 jne miss
 lda se_bc_head
 cmp #3
 jcs miss
 cmp se_bc_tail
 jne miss
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
 sta SQ_FRAME+GSEM_CP_VALID
 sta SQ_FRAME+GSEM_READS
 sta SQ_FRAME+GSEM_READS+1
 sta SQ_FRAME+GSEM_READS+2
 lda #2
 sta SQ_FRAME+GSEM_ERROR
 lda #S_PROOF
 sta S_ABI
 lda #1
 sta S_MODE
 CP SQ_FRAME+GSEM_QUERY,S_QUERY,3
 CP se_bc_arena,S_AUTH,13
 lda se_bc_head
 sta S_HEAD
 sta S_TAIL
 lda #0
 jsr reader
 jcs failed
 lda #1
 sta S_LIVE
 sta SQ_FRAME+GSEM_ACTIVE
 lda se_bc_flags
 ora #BC_ACTIVE
 and #($FF-BC_PAGE_PROOF)
 sta se_bc_flags
 lda #0
 jsr helper
 jcs failed
 lda #SQ_SELECT
 sta S_STATE
 jmp pending
guard:
 lda se_render_caps
 cmp #1
 beq @caps
 cmp #3
 jne stale
@caps:
 EQ S_AUTH,se_bc_arena,13
 lda se_bc_count
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
 lda #1
 jmp reader
step:
 lda S_ABI
 cmp #S_PROOF
 jne stale
 lda S_STATE
 cmp #SQ_SELECT
 beq @valid
 cmp #SQ_MAPPED
 jne failed_stale
@valid:
 jsr guard
 jcs failed
 lda S_STATE
 cmp #SQ_SELECT
 beq select_step
 lda #7
 jsr helper
 jcs failed
 cmp #0
 jne pending
 jsr query_final
 jcs failed
 jsr release
 jmp publish
select_step:
 lda #1
 jsr helper
 jcs failed
 cmp #0
 jne pending
 lda BC_IO+31
 cmp #1
 beq legacy
 cmp #S_FEATURE
 jne failed_corrupt
 lda #6
 jsr helper
 jcs failed
 lda #SQ_MAPPED
 sta S_STATE
 jmp pending
legacy:
 ; Fresh baseline C35 owns its original complete source/root/page checks.
 ; End our source lease before another C-slot image can be loaded by root.
 jsr release
 lda #SQ_LEGACY
 sta $9135
 lda #0
 sta $9136
 lda #1
 clc
 rts
failed_stale:lda #$C1
 jmp failed
failed_corrupt:lda #$C2
 jmp failed
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
metadata_read:
 ; Aoffsetlow,Yoffsethigh,Xlength. CPU targetfixedBC_IO, typedarenaonly.
 sta BCA_OFFSET
 sty BCA_OFFSET+1
 stx BCA_LENGTH
 lda #0
 sta BCA_OFFSET+2
 lda #8
 jmp helper
empty_slot:
 lda #$78
 ldy #1
 ldx #8
 jsr metadata_read
 bcs @return
 ldx #7
@zero:lda BC_IO,x
 jne stale
 dex
 bpl @zero
 clc
@return:rts
query_final:
 lda #0
 ldy #9
 ldx #32
 jsr metadata_read
 jcs @return
 EQ BC_IO,S_MAN+64,32
 CP BC_IO,S_EVENT,32
 jsr event_check
 jcs @return
 EQ S_EVENT+12,S_READER+52,4
 EQ S_DRAFT+32,S_READER+27,25
 EQ S_DRAFT+57,S_EVENT+8,4
 EQ S_DRAFT+36,S_EVENT+25,2
 lda S_DRAFT+62
 jne stale
 EQ S_DRAFT+91,S_DRAFT+53,3
 CP S_DRAFT+91,S_TEMP,3
 INC24 S_TEMP
 EQ S_TEMP,S_READER+10,3
 lda S_READER+57
 cmp #1
 jne stale
 clc
 .repeat 4,I
 lda S_ROOT+26+I
 .if I=0
 adc #1
 .else
 adc #0
 .endif
 sta S_TEMP+I
 .endrepeat
 jcs stale
 EQ S_TEMP,S_AUTH+5,4
 clc
@return:rts

publish:
 lda S_CR+3
 cmp #$FF
 bne @ordinary
 lda #0
 ldx #3
@zero:sta SQ_FRAME+GSEM_KIND,x
 dex
 bpl @zero
 jmp @anchors
@ordinary:
 sta SQ_FRAME+GSEM_KIND
 ldx #2
@fields:lda S_CR+69,x
 sta SQ_FRAME+GSEM_LANG,x
 dex
 bpl @fields
@anchors:
 ldx #2
@coords:lda S_CR+16,x
 sta SQ_FRAME+GSEM_START,x
 lda S_END,x
 sta SQ_FRAME+GSEM_END,x
 dex
 bpl @coords
 ldx #0
 ldy #3
 clc
@body:lda S_CR+16,x
 adc S_CR+22,x
 sta SQ_FRAME+GSEM_BODY,x
 inx
 dey
 bne @body
 lda #0
 sta SQ_FRAME+GSEM_ROLE
 sta SQ_FRAME+GSEM_REVERSE
 sta SQ_FRAME+GSEM_INLINE
 lda #9
 sta SQ_FRAME+GSEM_HEIGHT
 lda SQ_FRAME+GSEM_KIND
 cmp #4
 bcs @not_inline
 lda S_CR+2
 and #4
 beq @has_inline
 lda S_CR+44
 ora S_CR+45
 ora S_CR+46
 bne @has_inline
 lda S_CR+40
 and S_CR+41
 and S_CR+42
 and S_CR+43
 cmp #$FF
 beq @inline_done
@has_inline:inc SQ_FRAME+GSEM_INLINE
@inline_done:lda SQ_FRAME+GSEM_KIND
@not_inline:
 cmp #5
 bne :+
 lda #8
 sta SQ_FRAME+GSEM_HEIGHT
 lda #4
 bne @role
:cmp #2
 bne :+
 inc SQ_FRAME+GSEM_REVERSE
 lda #2
 bne @role
:cmp #3
 bne :+
 lda #1
 bne @role
:cmp #4
 beq @code
 cmp #6
 bne @done
@code:lda #4
@role:sta SQ_FRAME+GSEM_ROLE
@done:lda #0
 sta SQ_FRAME+GSEM_ERROR
 clc
 rts
