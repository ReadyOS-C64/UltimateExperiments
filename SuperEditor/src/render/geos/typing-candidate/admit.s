; R28: certify one pending edit, preserve/rebase derived page, atomic publication.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/geos/typing-candidate/worker.inc"
.include "render/geos/edit-certificate.inc"
.include "document/math24.inc"
.import se_f_owner,se_mode,se_e_ui,se_e_draw_sequence,se_r_presentation
.import se_l_mode,se_l_pan,se_sel_mark,se_ef_valid,se_ef_generation
.import se_gc_handle,se_gc_epoch,se_gc_width,se_reu_epoch,se_reu_map
.import se_doc_meta,se_doc_generation,se_doc_epoch,se_doc_busy
.import se_r_revision,se_v_length,se_v_top,se_v_pos,se_view_init,se_view_peek
.import se_hot_caret,se_hot_pending,se_hot_phase,se_hot_ready,se_hot_command,se_hot_delete
.import se_object_id,se_object_validate
.importzp screen_ptr
.export se_gtt_admit
.segment "CODE"
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
se_gtt_admit:
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
 cmp #3
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
 beq @next
 CMP24 GEC_POSITION,GP_RECORD+GPR_END
 bcc @found
@next:
 inc GEX_ROW
 jmp @scan
@found:
 lda GEX_ROW
 cmp GEX_HEADER+GPH_CARET_ROW
 jne miss
 lda GP_RECORD+GPR_KIND
 ora GP_RECORD+GPR_FLAGS
 ora GP_RECORD+GPR_INLINE
 ora GP_RECORD+GPR_RASTER_X
 ora GP_RECORD+GPR_RASTER_X+1
 ora GP_RECORD+GPR_COUNT+1
 jne miss
 lda GP_RECORD+GPR_HEIGHT
 cmp #9
 jne miss
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
 jcc miss
 cmp #184
 jcs miss
 sta GEX_TOP
 lsr
 lsr
 lsr
 sta GEX_FIRST_STRIP
 lda GEX_TOP
 clc
 adc #16 ;ceil((Y+9)/8)
 lsr
 lsr
 lsr
 sta GEX_END_STRIP
 lda GP_RECORD+GPR_COUNT
 beq @reason_bad
 cmp #162
 jcs miss
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
 ; No styles/roles, includinganempty/unmatchedinline reinterpretation.
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
 COPY24 GEX_OLD_START,se_v_pos
 jsr se_view_peek
 jcs fault
 and #$7F
 cmp #$41
 jcc miss
 cmp #$5B
 jcs miss
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
 lda #1
 sta GEX_PHASE
 clc
 rts
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
zero_field:
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
; Entire2KiBslotcopy through128B scratch; the64Bheldoldheader isnotclobbered.
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
