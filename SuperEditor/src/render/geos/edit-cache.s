; R28: certify one pending edit, preserve/rebase derived page, atomic publication.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/geos/edit-cache.inc"
.include "render/geos/edit-certificate.inc"
.include "render/geos/semantic.inc"
.include "document/math24.inc"
.import se_f_owner,se_mode,se_e_ui,se_e_draw_sequence,se_r_presentation
.import se_l_mode,se_l_pan,se_sel_mark,se_ef_valid,se_ef_generation
.import se_gc_handle,se_gc_epoch,se_gc_width,se_reu_epoch,se_reu_map
.import se_doc_meta,se_doc_generation,se_doc_epoch,se_doc_busy
.import se_r_revision,se_v_length,se_v_top,se_v_pos,se_view_init,se_view_peek,se_view_advance,se_view_retreat
.import se_hot_caret,se_hot_pending,se_hot_phase,se_hot_ready,se_hot_command,se_hot_delete
.import se_object_id,se_object_validate
.import se_petscii_screen
.importzp screen_ptr
.export entry
.segment "CODE"
 OVL_BINDING
entry:
 lda se_f_owner
 cmp #4
 jne busy
 lda se_overlay_frame
 beq admit
 cmp #2
 jeq rebase
 cmp #3
 jeq cancel
 lda #$90
 sec
 rts
busy:
 lda #$B2
 sec
 rts
pending:
 lda #1
 clc
 rts
miss:
	 ldx GEX_PHASE
 lda #0
 sta GEX_PHASE
 sta GEC_VALID
 sta GCC_VALID
	 cpx #1
	 beq @rebase_refuse
 lda #2
 clc
 rts
@rebase_refuse:
	 sec
	 rts
fault:
 pha
 lda #0
 sta GEX_PHASE
 sta GEC_VALID
 sta GCC_VALID
 pla
 sec
 rts
admit:
 lda #0
 sta GEX_PHASE
 lda GEC_VALID
 cmp #1
 jne miss
 lda se_mode
 cmp #3
 jne miss
 lda se_e_ui
 ora se_r_presentation
 ora se_l_mode
 ora se_l_pan
 ora se_l_pan+1
 ora se_l_pan+2
 ora se_sel_mark
 ora se_ef_valid
 ora se_doc_busy
 ora $912C
 ora $912D
 jne miss
 lda se_hot_ready
 cmp #1
 jne miss
 lda se_hot_pending
 cmp #1
 jne miss
 lda se_hot_phase
 jne miss
 lda GEC_OP
 cmp #2
 jcs miss
 sta GEX_OP
 cmp se_hot_delete
 jne miss
 lda GEX_OP ;the equality CMP above setsZ forboth validoperations
 bne @delete
 lda se_hot_command
 cmp #3
 jne miss
 lda GEC_OLD
 jne miss
 lda GEC_NEW
 jsr printable
 jcs miss
 jmp @operation
@delete:
 lda se_hot_command
 cmp #4
 beq :+
 cmp #5
 jne miss
: lda GEC_NEW
 jne miss
 lda GEC_OLD
 jsr printable
 jcs miss
@operation:
 jsr capability
 jcs fault
 jsr source
 jcs fault
 ; Four-byte revision increment must notwrap, evenifalllowwords repeat.
 clc
 .repeat 4,I
 lda GEC_REVISION+I
 .if I=0
 adc #1
 .else
 adc #0
 .endif
 sta GEX_BUFFER+I
 .endrepeat
 jcs miss
 ldx #3
@revision:
 lda GEX_BUFFER,x
 cmp se_r_revision,x
 jne miss
 lda GEC_REVISION,x
 cmp GCC_KEY+17,x
 jne miss
 dex
 bpl @revision
 ldx #2
@length:
 lda GEC_LENGTH,x
 cmp GCC_KEY+21,x
 jne miss
 sta GEX_OLD_LENGTH,x
 lda se_v_length,x
 sta GEX_NEW_LENGTH,x
 lda GEC_LENGTH,x
 sta GEX_TEMP,x
 dex
 bpl @length
 jsr delta
 jcs miss
 CMP24 GEX_TEMP,GEX_NEW_LENGTH
 jne miss
 COPY24 GEC_POSITION,GEX_TEMP
 lda GEX_OP
 bne @caret
 inc GEX_TEMP
 bne @caret
 inc GEX_TEMP+1
 bne @caret
 inc GEX_TEMP+2
@caret:
 CMP24 GEX_TEMP,se_hot_caret
 jne miss
 ldx #14
@graph:
 lda se_doc_meta,x
 cmp GCC_KEY,x
 jne miss
 dex
 bpl @graph
 ldx #1
@epochs:
 lda se_doc_generation,x
 cmp GCC_KEY+15,x
 jne miss
 lda se_doc_epoch,x
 cmp GEC_DOC_EPOCH,x
 jne miss
 cmp GCC_KEY+26,x
 jne miss
 lda se_reu_epoch,x
 cmp GEC_REU_EPOCH,x
 jne miss
 cmp GCC_KEY+24,x
 jne miss
 lda se_e_draw_sequence,x
 cmp GEC_SEQUENCE,x
 jne miss
 cmp GCC_SEQUENCE,x
 jne miss
 dex
 bpl @epochs
 ; Readthe oldpage without bypassing owner/physicalbinding/epoch checks.
 lda #0
 sta GP_IO_OFFSET
 sta GP_IO_OFFSET+1
 lda #<GEX_HEADER
 sta GP_IO_POINTER
 lda #>GEX_HEADER
 sta GP_IO_POINTER+1
 lda #64
 sta GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 jsr se_gp_cache_read
 jcs fault
 lda GEX_HEADER+GPH_VALID
 cmp #1
 jne miss
 lda GEX_HEADER+GPH_MAGIC
 cmp #$47
 jne miss
 lda GEX_HEADER+GPH_VERSION
 cmp #GP_CACHE_VERSION
 jne miss
 lda GEX_HEADER+GPH_COUNT
 beq @bad_count
	 cmp #23                    ;1..GP_MAX_LINES; reserved FE shadow is independent
 bcc :+
@bad_count:
 jmp miss
: cmp GCC_COUNT
 jne miss
 sta GEX_PAGE_COUNT
 ldx #36
@oldkey:
 lda GEX_HEADER+4,x
 cmp GCC_KEY,x
 jne miss
 dex
 bpl @oldkey
 ldx #2
@fold:
 lda GEX_HEADER+GPH_FOLD_VALID,x
 cmp GCC_FOLD,x
 jne miss
 dex
 bpl @fold
 lda GEX_HEADER+GPH_FOLD_VALID
 jne miss
 ldx #1
@foldgen:
 lda GEX_HEADER+GPH_FOLD_GENERATION,x
 cmp se_ef_generation,x
 jne miss
 dex
 bpl @foldgen
 ldx #2
@view:
 lda GEX_HEADER+GPH_TOP,x
 cmp se_v_top,x
 jne miss
 lda GEX_HEADER+GPH_PAN,x
 jne miss
 lda GEX_HEADER+GPH_BOTTOM,x
 sta GEX_OLD_BOTTOM,x
 dex
 bpl @view
 lda #0
 sta GEX_ROW
@scan:
 lda GEX_ROW
 cmp GEX_PAGE_COUNT
 jcs miss
 jsr row
 jcs fault
 CMP24 GEC_POSITION,GP_RECORD+GPR_START
 bcc @next
 CMP24 GEC_POSITION,GP_RECORD+GPR_END
 bcc @found
 bne @next
 lda GEX_OP
 jne miss                     ;a delete witness must remain inside CHARS[0..COUNT)
 jmp @found ;complete reason/caret-row proof below disambiguates EOF/CR
@next:
 inc GEX_ROW
 jmp @scan
@found:
 lda GEX_ROW
 cmp GEX_HEADER+GPH_CARET_ROW
 jne miss
 lda GP_RECORD+GPR_TOP
 cmp GCC_Y
 jne miss
 lda GP_RECORD+GPR_HEIGHT
 cmp GCC_HEIGHT
 jne miss
 lda GP_RECORD+GPR_KIND
 jne miss
@geometry:
 lda GP_RECORD+GPR_RASTER_X
 ora GP_RECORD+GPR_RASTER_X+1
 ora GP_RECORD+GPR_COUNT+1
 bne @reason_bad
 lda #9                       ;old raster KIND0 was already proved
 cmp GP_RECORD+GPR_HEIGHT
 bne @reason_bad
 sta GEX_HEIGHT
 lda GP_RECORD+GPR_REASON
 beq @reason_bad
 cmp #7
 bcs @reason_bad
 cmp #2                      ;CR and wraps; EOF has no following-row witness
 beq @reason_bad
 sta GEX_AUX
 lda GP_RECORD+GPR_TOP
 cmp #16
 bcc @reason_bad
 sta GEX_TOP
 clc
 adc GEX_HEIGHT
 bcs @reason_bad
 cmp #193
 bcs @reason_bad
 lda GEX_HEIGHT
 cmp #8
 bne :+
 lda GEX_TOP
 and #7
 bne @reason_bad
: lda GEX_TOP
 lsr
 lsr
 lsr
 sta GEX_FIRST_STRIP
 lda GEX_TOP
 clc
 adc GEX_HEIGHT
 adc #7 ;ceil((Y+height)/8), both additions cannot wrap
 lsr
 lsr
 lsr
 sta GEX_END_STRIP
 lda GP_RECORD+GPR_COUNT
 beq @reason_bad
 cmp #162
 bcs @reason_bad
 sta GEX_BOUNDARIES
 jmp @geometry_ok
@reason_bad:
 jmp miss
@geometry_ok:
 COPY24 GP_RECORD+GPR_START,GEX_OLD_START
 COPY24 GP_RECORD+GPR_END,GEX_OLD_END
 COPY24 GP_RECORD+GPR_NEXT,GEX_OLD_NEXT
 CMP24 GP_RECORD+GPR_FIRST,GEX_OLD_START
 jne miss
 SUB24 GEX_OLD_END,GEX_OLD_START,GEX_TEMP
 lda GEX_TEMP+1
 ora GEX_TEMP+2
 jne miss
 lda GEX_TEMP
 cmp GEX_BOUNDARIES
 jne miss
 CMP24 GEX_OLD_NEXT,GEX_OLD_END
 jcc miss
 CMP24 GEX_OLD_NEXT,GEX_OLD_LENGTH
 bcc @row_shape
 beq @row_shape
 jmp miss
@row_shape:
 lda GEX_AUX
 lsr                          ;only admitted reason below 3 is CR=1
 bne @neighbor
 sec                          ;prove the cached complete-CR shape NEXT=END+1
 ldx #0
@cr_shape:
 lda GEX_OLD_END,x
 adc #0
 eor GEX_OLD_NEXT,x           ;EOR preserves the carry into the next byte
 bne @bad_shape
 inx
 cpx #3
 bne @cr_shape
@neighbor:
 lda GEX_ROW
 beq @first
 sec
 sbc #1
 jsr row
 jcs fault
 CMP24 GP_RECORD+GPR_NEXT,GEX_OLD_START
 bne @bad_shape
 jmp @first_char
@bad_shape:
 jmp miss
@first:
@first_char:
@byte_witness:
 ; Deletionwitness mustmatchthe oldcached literalbyte atthatcanonicalposition.
 lda GEX_OP
 beq @insert_byte
 SUB24 GEC_POSITION,GEX_OLD_START,GEX_TEMP
 lda GEX_ROW
 jsr slot
 jcs fault
 clc
 lda GEX_TEMP
 adc #GPR_CHARS
 ldx #0
 bcc :+
 inx
: jsr field
 lda #<GEX_BUFFER
 sta GP_IO_POINTER
 lda #>GEX_BUFFER
 sta GP_IO_POINTER+1
 lda #1
 sta GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 jsr se_gp_cache_read
 jcs fault
 lda GEX_BUFFER
 cmp GEC_OLD
 jne miss
 jmp @stage
@insert_byte:
 COPY24 GEC_POSITION,se_v_pos
 jsr se_view_peek
 jcs fault
 cmp GEC_NEW
 jne miss
@stage:
 ; Retain the checked old-header witness.
 lda #<GEX_OLD_HEADER
 sta GP_IO_OFFSET
 lda #>GEX_OLD_HEADER
 sta GP_IO_OFFSET+1
 lda #<GEX_HEADER
 sta GP_IO_POINTER
 lda #>GEX_HEADER
 sta GP_IO_POINTER+1
 lda #64
 sta GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 jsr se_gp_cache_write
 jcs fault
 ; Refreshcurrentcheckedsource BEFOREconstructingthenewheader.
 jsr source
 jcs fault
 ldx #63
@header:
 lda GEX_HEADER,x
 sta GP_HEADER,x
 dex
 bpl @header
 ldx #14
@new_graph:
 lda se_doc_meta,x
 sta GP_HEADER+4,x
 dex
 bpl @new_graph
 ldx #1
@new_epoch:
 lda se_doc_generation,x
 sta GP_HEADER+GPH_KEY+15,x
 lda se_reu_epoch,x
 sta GP_HEADER+GPH_KEY+24,x
 lda se_doc_epoch,x
 sta GP_HEADER+GPH_KEY+26,x
 dex
 bpl @new_epoch
 ldx #3
@new_revision:
 lda se_r_revision,x
 sta GP_HEADER+GPH_KEY+17,x
 dex
 bpl @new_revision
 ldx #2
@new_length:
 lda se_v_length,x
 sta GP_HEADER+GPH_KEY+21,x
 dex
 bpl @new_length
 lda #0
 sta GP_HEADER+GPH_VALID
 sta GP_HEADER+GPH_SEEN
 sta GP_HEADER+GPH_CARET_VISIBLE
 sta GEC_VALID
 sta GCC_VALID
 lda #$FF
 sta GP_HEADER+GPH_CARET_ROW
 jsr header_write
 jcs fault
 lda #1
 sta GEX_PHASE
 jmp pending
; C21 proves row convergence and enters one synchronous suffix rebase.
rebase:
	 lda GEX_PHASE
	 cmp #1
	 jne miss
 jsr current
 jcs fault
	 jsr syntax_proof
	 jcs fault
	 lda GEX_AUX
	 lsr
	 bne @proof_done
	 ; FAST=4 is an uninterrupted C21 handoff. The executable write watch
	 ; proves this live dirty prefix is unchanged from publication to entry.
	 lda GP_RECORD+GPR_REASON
	 cmp #1
	 jne miss
	 ; GSEM START is the complete logical-event start, while cached START is
	 ; this visual segment. Equality excludes a final CR segment after any
	 ; soft wrap, including viewport row zero with START>0.
	 CMP24 GSEM_FRAME+GSEM_START,GEX_OLD_START
	 jne miss
@proof_done:
 lda GEX_PAGE_COUNT
 sta GP_HEADER+GPH_COUNT
 COPY24 GEX_OLD_BOTTOM,GEX_TEMP
 jsr delta
 jcs miss
 COPY24 GEX_TEMP,GP_HEADER+GPH_BOTTOM
@loop:
 lda GEX_SCAN_ROW
 cmp GEX_PAGE_COUNT
 jcs commit
 lda GEX_SCAN_ROW
 jsr row
 jcs fault
 lda GP_RECORD+GPR_COUNT+1
 jne miss
 lda GP_RECORD+GPR_COUNT
 cmp #162
 jcs miss
 lda #<GP_RECORD
 sta screen_ptr
 lda #>GP_RECORD
 sta screen_ptr+1
 ldx #4
@prefix:
 jsr shift
 jcs miss
 jsr advance3
 dex
 bne @prefix
 lda GEX_SCAN_ROW
 jsr slot
 jcs fault
 lda #<GP_RECORD
 sta GP_IO_POINTER
 lda #>GP_RECORD
 sta GP_IO_POINTER+1
 lda #32
 sta GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 jsr se_gp_cache_write
 jcs fault
 ; Old-key logical certificates safely miss; rows need no rekey transaction.
 ; ABI3 consumers derive affinities from FIRST; no absolute arrays to shift.
 inc GEX_SCAN_ROW
 jmp @loop
commit:
 lda #1
 sta GP_HEADER+GPH_VALID
 jsr header_write
 jcs fault
 lda #0
 sta GEX_PHASE
 sta GEC_VALID
 sta GCC_VALID
 clc
 rts
cancel:
 lda GEX_PHASE
 beq @done
 jsr capability
 bcs @forget
 lda #0
 sta GP_IO_OFFSET
 sta GP_IO_OFFSET+1
 lda #<GP_HEADER
 sta GP_IO_POINTER
 lda #>GP_HEADER
 sta GP_IO_POINTER+1
 lda #64
 sta GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 jsr se_gp_cache_read
 bcs @forget
 lda #0
 sta GP_HEADER+GPH_VALID
 jsr header_write
@forget:
 lda #0
 sta GEX_PHASE
 sta GEC_VALID
 sta GCC_VALID
@done:
 lda #0
 clc
 rts
; Helpers have noallocation/free/source mutation andnooverlay calls.
printable:
 cmp #$30
 bcc @bad
 cmp #$3A
 bcc @yes
 cmp #$41
 bcc @bad
 cmp #$5B
 bcc @yes
 cmp #$C1
 bcc @bad
 cmp #$DB
 bcs @bad
@yes:
 clc
 rts
@bad:
 sec
 rts
count_delta:
 .byte 1,$FF
capability:
 lda se_gc_width
 cmp #$FF
 bne @bad
 lda se_gc_handle
 beq @bad
 cmp GCC_HANDLE
 bne @bad
 tax
 lda se_reu_map,x
 cmp GCC_PHYSICAL
 bne @bad
 ldx #1
@epoch:
 lda se_gc_epoch,x
 cmp GCC_EPOCH,x
 bne @bad
 cmp se_reu_epoch,x
 bne @bad
 dex
 bpl @epoch
 lda #0
 clc
 rts
@bad:
 lda #$18
 sec
 rts
source:
 jsr se_view_init
 bcs @return
 .repeat 3,T
 ldx #4
: lda se_doc_meta+T*5,x
 sta se_object_id,x
 dex
 bpl :-
 jsr se_object_validate
 bcs @return
 .endrepeat
@return:
 rts
current:
 lda $912C
 ora $912D
 bne @busy
 jsr capability
 bcs @return
 jmp se_gp_cache_guard
@busy:
 lda #$B2
 sec
@return:
 rts
slot:
 jsr se_gp_cache_slot
 bcs @done
 lda GP_IO_OFFSET
 sta GEX_BASE
 lda GP_IO_OFFSET+1
 sta GEX_BASE+1
@done:
 rts
row:
 jsr slot
 bcs @done
 lda #<GP_RECORD
 sta GP_IO_POINTER
 lda #>GP_RECORD
 sta GP_IO_POINTER+1
 lda #32
 sta GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 jsr se_gp_cache_read
@done:
 rts
field:
 clc
 adc GEX_BASE
 sta GP_IO_OFFSET
 txa
 adc GEX_BASE+1
 sta GP_IO_OFFSET+1
 rts
header_write:
 lda #0
 sta GP_IO_OFFSET
 sta GP_IO_OFFSET+1
 sta GP_IO_LENGTH+1
 lda #<GP_HEADER
 sta GP_IO_POINTER
 lda #>GP_HEADER
 sta GP_IO_POINTER+1
 lda #64
 sta GP_IO_LENGTH
 jmp se_gp_cache_write
; Signedonebyte delta, with24bit overflow/underflow refusal.
delta:
 lda GEX_OP
 bne @delete
 clc
 lda GEX_TEMP
 adc #1
 sta GEX_TEMP
 lda GEX_TEMP+1
 adc #0
 sta GEX_TEMP+1
 lda GEX_TEMP+2
 adc #0
 sta GEX_TEMP+2
 bcs @bad
 clc
 rts
@delete:
 sec
 lda GEX_TEMP
 sbc #1
 sta GEX_TEMP
 lda GEX_TEMP+1
 sbc #0
 sta GEX_TEMP+1
 lda GEX_TEMP+2
 sbc #0
 sta GEX_TEMP+2
 bcc @bad
 clc
 rts
@bad:
 sec
 rts
shift:
 ldy #2
@load:
 lda (screen_ptr),y
 sta GEX_TEMP,y
 dey
 bpl @load
 CMP24 GEX_TEMP,GEX_OLD_NEXT
 bcc @bad
 CMP24 GEX_TEMP,GEX_OLD_LENGTH
 bcc @delta
 bne @bad
@delta:
 jsr delta
 bcs @bad
 CMP24 GEX_TEMP,GEX_NEW_LENGTH
 bcc @save
 bne @bad
@save:
 ldy #2
@store:
 lda GEX_TEMP,y
 sta (screen_ptr),y
 dey
 bpl @store
 clc
 rts
@bad:
 sec
 rts
advance3:
 clc
 lda screen_ptr
 adc #3
 sta screen_ptr
 bcc :+
 inc screen_ptr+1
: rts

; Complete-event authority for the one-byte alphanumeric lane. The block prefix
; is unchanged (edit is in BODY); same-event exact packet convergence proves
; KIND/LANG/INLINE. Inline output can differ only if the edit splits/joins a
; '*'/'@' run or changes a native-pound escape context. Refuse those cases.
syntax_proof:
 ; Exact transition lane: ordinary prose, beyond an alphanumeric first byte.
 lda GSEM_FRAME+GSEM_KIND
 bne @early_refuse
 CMP24 GEC_POSITION,GSEM_FRAME+GSEM_START
 bcc @early_refuse
 beq @early_refuse
 CMP24 GEC_POSITION,GSEM_FRAME+GSEM_BODY
 bcc @early_refuse
 CMP24 GEC_POSITION,GSEM_FRAME+GSEM_END
 bcc @position
 bne @early_refuse
 lda GEX_OP
 bne @position               ;only deleting the final body byte may land at END
@early_refuse:
 jmp @refuse
@position:
 jsr se_view_init
 bcc :+
 rts
:
 COPY24 GSEM_FRAME+GSEM_START,se_v_pos
 jsr se_view_peek
 bcc :+
 rts
:
 jsr printable
 jcs @refuse
 COPY24 GEC_POSITION,se_v_pos
 CMP24 se_v_pos,GSEM_FRAME+GSEM_BODY
 beq @next
 jsr se_view_retreat
 jsr se_view_peek
 bcc :+
 rts
:
 cmp #'*'
 beq @refuse
 cmp #'@'
 beq @refuse
 cmp #$5C
 beq @refuse
@next:
 COPY24 GEC_POSITION,se_v_pos
 lda GEX_OP
 bne @next_ready
 jsr se_view_advance          ;skip the inserted byte
@next_ready:
 CMP24 se_v_pos,GSEM_FRAME+GSEM_END
 bcs @safe
 jsr se_view_peek
 bcc :+
 rts
:
 cmp #'*'
 beq @late_refuse
 cmp #'@'
 beq @late_refuse
 cmp #$5C
 beq @late_refuse
@safe:
 lda #0
 clc
 rts
@late_refuse:
@refuse:
 lda #0
 sec
 rts
