; R28: certify one pending edit, preserve/rebase derived page, atomic publication.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/geos/edit-cache.inc"
.include "render/geos/edit-certificate.inc"
.include "document/math24.inc"
.import se_f_owner,se_mode,se_e_ui,se_e_draw_sequence,se_r_presentation
.import se_l_mode,se_l_pan,se_sel_mark,se_ef_valid,se_ef_generation
.import se_gc_handle,se_gc_epoch,se_gc_width,se_reu_epoch,se_reu_map
.import se_doc_meta,se_doc_generation,se_doc_epoch,se_doc_busy
.import se_r_revision,se_v_length,se_v_top,se_v_pos,se_view_init,se_view_peek
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
 cmp #1
 jeq verify
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
 lda #0
 sta GEX_PHASE
 sta GEC_VALID
 sta GCC_VALID
 lda #2
 clc
 rts
fault:
 sta GEX_ERROR
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
 jsr ordinary
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
 jsr ordinary
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
 cmp #23
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
 ; Equality is considered only for a heading; complete reason/caret-row proof
 ; below still rejects softwrap and all other ambiguous end boundaries.
 lda GP_RECORD+GPR_FLAGS
 lsr
 bcs @found
@next:
 inc GEX_ROW
 jmp @scan
@found:
 lda GEX_ROW
 cmp GEX_HEADER+GPH_CARET_ROW
 jne miss
 ; Every accepted START/interior branch assigns CLASS before use.
 CMP24 GEC_POSITION,GP_RECORD+GPR_START
 bne @interior
 lda GEC_NEW
 ldx GEX_OP
 beq @alpha
 lda se_hot_command
 cmp #4
 jne miss
 lda GP_RECORD+GPR_INLINE
 jne miss
 lda GEC_OLD
@alpha:
 and #$7F
 cmp #$41
 jcc miss
 cmp #$5B
 jcs miss
 lda GP_RECORD+GPR_KIND
 jne miss
 txa
 eor #1
 cmp GP_RECORD+GPR_FLAGS
 jne miss
 txa
 ora #2
 sta GEX_CLASS
@saved_geometry:
 ; Resident saved-caret geometry witnesses the genuinely painted row.
 lda GP_RECORD+GPR_TOP
 cmp GCC_Y
 bne @reason_bad
 lda GP_RECORD+GPR_HEIGHT
 cmp GCC_HEIGHT
 bne @reason_bad
 beq @geometry
@interior:
 ; Plain/code admission is retained; complete heading body gets class4.
 lda GP_RECORD+GPR_KIND
 cmp #2
 bcs @reason_bad
 ora GP_RECORD+GPR_INLINE
 beq :+
 lda #1
: sta GEX_CLASS
 lda GP_RECORD+GPR_FLAGS
 beq @geometry
 cmp #1
 bne @reason_bad
 lda GP_RECORD+GPR_KIND
 bne @reason_bad
 lda #4
 sta GEX_CLASS
 bne @saved_geometry
@geometry:
 lda GP_RECORD+GPR_RASTER_X
 ora GP_RECORD+GPR_RASTER_X+1
 ora GP_RECORD+GPR_COUNT+1
 bne @reason_bad
 lda GP_RECORD+GPR_KIND
 eor #1
 ora #8 ;oldKIND0/1 is already checked on both START/interior paths
 cmp GP_RECORD+GPR_HEIGHT
 bne @reason_bad
 sta GEX_HEIGHT
 lda GP_RECORD+GPR_REASON
 beq @reason_bad
 cmp #3
 bcc :+
@reason_bad:
 jmp miss
: sta GEX_AUX
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
 lda GEX_AUX
 cmp #1
 bne @eof_shape
 COPY24 GEX_OLD_END,GEX_TEMP
 inc GEX_TEMP
 bne :+
 inc GEX_TEMP+1
 bne :+
 inc GEX_TEMP+2
: CMP24 GEX_TEMP,GEX_OLD_NEXT
 jne miss
 jmp @row_shape
@eof_shape:
 CMP24 GEX_OLD_END,GEX_OLD_NEXT
 jne miss
 CMP24 GEX_OLD_END,GEX_OLD_LENGTH
 jne miss
@row_shape:
 lda GEX_CLASS
 beq @plain_semantics
 cmp #1
 beq @row_semantics_ready
 lsr
 bcc @heading_proof
@plain_semantics:
 ; Plain old rows, including inverse heading BACK, prove allstyle/roles0.
 lda #<GPR_STYLES
 ldx #>GPR_STYLES
 jsr zero_field
 jcs fault
 cmp #2
 jeq miss
 lda #<GPR_ROLES
 ldx #>GPR_ROLES
 jsr zero_field
 jcs fault
 cmp #2
 jeq miss
 lda GEX_CLASS
 cmp #3
 beq @prefix_proof
 bne @row_semantics_ready
@heading_proof:
 lda #<GPR_ROLES
 ldx #>GPR_ROLES
 ldy #2
 jsr expected_field
 jcs fault
 cmp #2
 jeq miss
@prefix_proof:
 jsr heading_prefix
 jcs fault
 cmp #2
 jeq miss
@row_semantics_ready:
 jsr refuse_wrap
 jcs fault
 jne miss ;helperreturnsZset onlywhen originaladmission shouldcontinue
 lda GEX_ROW
 beq @first
 sec
 sbc #1
 jsr row
 jcs fault
 lda GP_RECORD+GPR_REASON
 cmp #1
 jne miss
 CMP24 GP_RECORD+GPR_NEXT,GEX_OLD_START
 jne miss
 jmp @first_char
@first:
 lda GEX_OLD_START
 ora GEX_OLD_START+1
 ora GEX_OLD_START+2
 beq @first_char
 COPY24 GEX_OLD_START,se_v_pos
 lda se_v_pos
 bne @preceding_low
 lda se_v_pos+1
 bne @preceding_mid
 dec se_v_pos+2
@preceding_mid:
 dec se_v_pos+1
@preceding_low:
 dec se_v_pos
@preceding:
 jsr se_view_peek
 jcs fault
 cmp #13
 jne miss
@first_char:
 lda GEX_CLASS
 cmp #2
 bcs @byte_witness
 lda GEX_HEIGHT
 cmp #8
 beq @byte_witness
 COPY24 GEX_OLD_START,se_v_pos
 jsr se_view_peek
 jcs fault
 and #$7F
 cmp #$41
 jcc miss
 cmp #$5B
 jcs miss
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
 ; Retain the checked old-header witness; row backups have no consumers.
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
; Anewbuiltrow isalready initsnormalFEslot, stillunderheaderVALID0.
verify:
 lda GEX_PHASE
 cmp #1
 jne miss
 jsr current
 jcs fault
 lda GEX_ROW
 jsr row
 jcs fault
 lda GP_RECORD+GPR_KIND
 eor #1
 clc
 adc #8
 cmp GEX_HEIGHT
 jne miss
 lda GEX_CLASS
 cmp #3
 lda #0
 rol
 eor GP_RECORD+GPR_FLAGS
 ora GP_RECORD+GPR_RASTER_X
 ora GP_RECORD+GPR_RASTER_X+1
 ora GP_RECORD+GPR_COUNT+1
 jne miss
 lda GP_RECORD+GPR_REASON
 cmp GEX_AUX
 jne miss
 lda GP_RECORD+GPR_TOP
 cmp GEX_TOP
 jne miss
 lda GP_RECORD+GPR_HEIGHT
 cmp GEX_HEIGHT
 jne miss
 CMP24 GP_RECORD+GPR_START,GEX_OLD_START
 jne miss
 CMP24 GP_RECORD+GPR_FIRST,GEX_OLD_START
 jne miss
 COPY24 GEX_OLD_END,GEX_TEMP
 jsr delta
 jcs miss
 CMP24 GP_RECORD+GPR_END,GEX_TEMP
 jne miss
 COPY24 GEX_OLD_NEXT,GEX_TEMP
 jsr delta
 jcs miss
 CMP24 GP_RECORD+GPR_NEXT,GEX_TEMP
 jne miss
 SUB24 GP_RECORD+GPR_END,GEX_OLD_START,GEX_TEMP
 lda GEX_TEMP+1
 ora GEX_TEMP+2
 jne miss
 lda GEX_TEMP
 cmp #162
 jcs miss
 cmp GP_RECORD+GPR_COUNT
 jne miss
 sta GEX_BOUNDARIES
 lda GEX_CLASS
 bne @new_semantics_ready
 lda #<GPR_STYLES
 ldx #>GPR_STYLES
 jsr zero_field
 jcs fault
 cmp #2
 jeq miss
 lda #<GPR_ROLES
 ldx #>GPR_ROLES
 jsr zero_field
 jcs fault
 cmp #2
 jeq miss
@new_semantics_ready:
 jsr current
 jcs fault
 lda GEX_PAGE_COUNT
 sta GP_HEADER+GPH_COUNT
 COPY24 GEX_OLD_BOTTOM,GEX_TEMP
 jsr delta
 jcs miss
 COPY24 GEX_TEMP,GP_HEADER+GPH_BOTTOM
 jsr header_write
 jcs fault
 lda GEX_ROW
 clc
 adc #1
 sta GEX_SCAN_ROW
 lda #0
 sta GEX_ARRAY
 lda #2
 sta GEX_PHASE
 jmp pending
rebase:
 lda GEX_PHASE
 cmp #2
 jne miss
 jsr current
 jcs fault
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
 ; ABI3 consumers derive affinities from FIRST; no absolute arrays to shift.
 inc GEX_SCAN_ROW
 jmp pending
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
ordinary:
 cmp #32
 bcc @bad
 cmp #$80
 bcc :+
 cmp #$A0
 bcc @bad
: cmp #'*'
 beq @bad
 cmp #'@'
 beq @bad
 cmp #$5C
 beq @bad
 cmp #'#'
 beq @bad
 cmp #':'
 beq @bad
 cmp #'-'
 beq @bad
 clc
 rts
@bad:
 sec
 rts
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
heading_prefix:
 lda #<GPR_CHARS
 ldx #>GPR_CHARS
 jsr field
 lda #<GEX_BUFFER
 sta GP_IO_POINTER
 lda #>GEX_BUFFER
 sta GP_IO_POINTER+1
 lda GEX_BOUNDARIES
 cmp #8
 bcc :+
 lda #8
: sta GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 jsr se_gp_cache_read
 bcs @done
 ldx #0
 lda GEX_CLASS
 cmp #3
 bne :+
 inx
: ldy #0
@hash:
 lda GEX_BUFFER,x
 cmp #'#'
 bne @space
 inx
 iny
 cpy #7
 bcs @bad
 cpx GEX_BOUNDARIES
 bcs @bad
 bne @hash
@space:
 cmp #' '
 bne @bad
 tya
 beq @bad
 lda GEX_CLASS
 cmp #4
 bne @valid
 ; The known contained <=161-byte row makes low-byte subtraction exact.
 inx
 stx GEX_PAIR
 sec
 lda GEC_POSITION
 sbc GEX_OLD_START
 cmp GEX_PAIR
 bcc @bad
 lda GEC_NEW
 bne @character
 lda se_hot_command
 cmp #4
 bne @bad
 lda GEC_OLD
@character:
 and #$7F
 cmp #$30
 bcc @bad
 cmp #$3A
 bcc @valid
 cmp #$41
 bcc @bad
 cmp #$5B
 bcs @bad
@valid:
 lda #0
 clc
@done:
 rts
@bad:
 lda #2
 clc
 rts
zero_field:
 ldy #0
expected_field:
 sty GEX_ARRAY
 sta GEX_OFFSET
 stx GEX_OFFSET+1
 lda #0
 sta GEX_PAIR
@next:
 sec
 lda GEX_BOUNDARIES
 sbc GEX_PAIR
 beq @zero
 cmp #33
 bcc :+
 lda #32
: sta GEX_CHUNK
 clc
 lda GEX_OFFSET
 adc GEX_PAIR
 pha
 lda GEX_OFFSET+1
 adc #0
 tax
 pla
 jsr field
 lda #<GEX_BUFFER
 sta GP_IO_POINTER
 lda #>GEX_BUFFER
 sta GP_IO_POINTER+1
 lda GEX_CHUNK
 sta GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 jsr se_gp_cache_read
 bcs @return
 ldx #0
@byte:
 lda GEX_BUFFER,x
 cmp GEX_ARRAY
 bne @nonzero
 inx
 cpx GEX_CHUNK
 bcc @byte
 clc
 lda GEX_PAIR
 adc GEX_CHUNK
 sta GEX_PAIR
 jmp @next
@nonzero:
 lda #2
 clc
 rts
@zero:
 lda #0
 clc
@return:
 rts
; Optional early refusal only. Existing actual parser/VERIFY remains authority.
refuse_wrap:
 lda GEX_CLASS
 cmp #4
 bne @done
 lda GEX_OP
 ora GP_RECORD+GPR_INLINE
 bne @done
 lda GEC_NEW
 jsr se_petscii_screen
 cmp #27
 bcc @lower
 cmp #$30
 bcc @done
 cmp #$3A
 bcc @digit
 cmp #$41
 bcc @done
 cmp #$5B
 bcs @done
 sec
 sbc #$27 ;uppercase screen41..5A ->26..51
 bne @width
@digit:
 adc #4 ;Cclear, digits30..39 ->52..61
 bne @width
@lower:
 sbc #0 ;Cclearfrom CMP27: knownalnum screen1..26 ->0..25
@width:
 tax
 lda advances,x
 clc
 adc GP_RECORD+GPR_TAIL_X
 tax
 lda GP_RECORD+GPR_TAIL_X+1
 adc #0
 cmp #1
 bcc @done
 bne @overflow
 cpx #65 ;strictlygreaterthan320; equality still needs actualVERIFY
 bcc @done
@overflow:
 lda #<GPR_STYLES
 ldx #>GPR_STYLES
 jsr zero_field
 bcs @return
 eor #2 ;checked zero_field: A0/allzero ->A2/refuse, A2/nonzero ->A0/continue
 rts ;Cclear from reader; no originaladmission/VERIFY bypass
@done:
 lda #0
 clc
@return:
 rts
advances:
 .byte 5,5,5,5,5,3,5,5,2,2,5,2,8,5,6,5,5,3,4,3,5,6,8,6,5,6,6,5,5,5,4,4,5,6,2,4,6,4,8,6,6,5,6,5,5,4,5,6,8,6,6,6,5,3,4,4,5,4,5,5,5,5
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
