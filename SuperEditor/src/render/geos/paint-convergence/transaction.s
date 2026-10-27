; New generation-only packet proof. No semantic carry is inferred or reused.
; All callbacks occur owner4 with GL/FS inactive; snapshot precedes C20.
allowed:
 lda se_mode
 cmp #3
 bne @no
 lda se_render_caps
 beq @no
 cmp #1
 beq :+
 cmp #3
 bne @no
: lda se_r_presentation
 ora se_e_ui
 ora se_e_error
 ora se_h_fault
 ora se_sel_mark
 ora se_ef_valid
 ora se_l_mode
 ora se_l_pan
 ora se_l_pan+1
 ora se_l_pan+2
 ora se_l_manual
 ora $912C
 ora $912D
 bne @no
 clc
 rts
@no:sec
 rts
; These requests never allocate or free; cache.s validates logical/physicalFE.
request_data:
 sta GP_IO_OFFSET
 stx GP_IO_OFFSET+1
 sty GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 lda #<CV_DATA
 sta GP_IO_POINTER
 lda #>CV_DATA
 sta GP_IO_POINTER+1
 rts
read_cert:
 lda #<CV_CERT
 ldx #>CV_CERT
 ldy #CV_SIZE
 jsr request_data
 jmp se_gp_cache_read
read_next:
 lda #<CV_NEXT
 ldx #>CV_NEXT
 ldy #CV_SIZE
 jsr request_data
 jmp se_gp_cache_read
write_next:
 lda #<CV_NEXT
 ldx #>CV_NEXT
 ldy #CV_SIZE
 jsr request_data
 jmp se_gp_cache_write
source_save:
 ldx #58
: lda CV_IDENTITY,x
 sta CV_DATA+CV_SOURCE,x
 dex
 bpl :-
 rts
source_check:
 ldx #58
: lda CV_DATA+CV_SOURCE,x
 sta CV_IDENTITY,x
 dex
 bpl :-
 jmp se_rg_check_source
crc_data:
 jsr se_crc_init
 ldy #1
: lda CV_DATA,y
 jsr se_crc_byte
 iny
 cpy #CV_CRC
 bcc :-
 rts
cert_verify:
 lda CV_DATA
 cmp #$A5
 bne @bad
 lda CV_DATA+1
 cmp #5
 bne @bad
 lda CV_DATA+2
 cmp se_render_caps
 bne @bad
 ldx #15
@binding:
 lda CV_DATA+4,x
 cmp se_overlay_binding_digest,x
 bne @bad
 dex
 bpl @binding
 jsr crc_data
 lda se_crc_value
 cmp CV_DATA+CV_CRC
 bne @bad
 lda se_crc_value+1
 cmp CV_DATA+CV_CRC+1
 bne @bad
 clc
 rts
@bad:sec
 rts
; Initialize a bounded new proof after real source/typedFE validation.
collect_begin:
 jsr allowed
 jcs argument
 jsr se_rg_capture_source
 bcc @propagate_ok_1
 rts
@propagate_ok_1:
 lda se_gc_handle
 jeq argument
 sta CV_HANDLE
 tax
 lda se_reu_map,x
 sta CV_PHYSICAL
 lda se_gc_epoch
 sta CV_EPOCH
 lda se_gc_epoch+1
 sta CV_EPOCH+1
 lda se_render_caps
 sta CV_CAPS
 lda #0
 ldx #CV_SIZE-1
: sta CV_DATA,x
 dex
 cpx #$FF
 bne :-
 jsr source_save
 jsr crc_source
 lda se_crc_value
 sta CV_DATA+234
 lda se_crc_value+1
 sta CV_DATA+235
 lda #5
 sta CV_DATA+1
 lda CV_CAPS
 sta CV_DATA+2
 lda #0
 sta CV_DATA
 sta CV_ROWS
 jsr write_next
 bcc @propagate_ok_2
 rts
@propagate_ok_2:
 lda #$A6
 sta CV_COLLECT
 lda #0
 clc
 rts
failed:rts
; Every later boundary rechecks exact current59 and actual FE incarnation.
current:
 jsr allowed
 jcs argument
 lda se_gc_handle
 cmp CV_HANDLE
 jne changed
 tax
 lda se_reu_map,x
 cmp CV_PHYSICAL
 jne changed
 ldx #1
: lda se_gc_epoch,x
 cmp CV_EPOCH,x
 jne changed
 lda se_reu_epoch,x
 cmp CV_EPOCH,x
 jne changed
 dex
 bpl :-
 lda se_render_caps
 cmp CV_CAPS
 jne changed
 jsr read_next
 bcc @propagate_ok_3
 rts
@propagate_ok_3:
 jsr crc_source
 lda se_crc_value
 cmp CV_DATA+234
 jne changed
 lda se_crc_value+1
 cmp CV_DATA+235
 jne changed
 jsr source_check
 bcc @propagate_ok_4
 rts
@propagate_ok_4:
 jmp se_gp_cache_guard
changed:lda #$B1
 sec
 rts
attempt:
 lda #0
 sta CV_ACTIVE
 sta CV_COLLECT
 lda #24
 sta CV_MIN
 lda #2
 sta CV_MAX
 jsr allowed
 jcs zero
 ; A missing FE bank is ordinary cold start. Collect starts after OPEN.
 lda se_gc_handle
 jeq zero
 jsr collect_begin
 jcs miss
 lda GEC_VALID
 cmp #1
 jne miss
 jsr base_bound
 jcs miss
 lda se_hot_ready
 cmp #1
 jne miss
 lda se_hot_pending
 cmp #1
 jne miss
 lda se_hot_phase
 ora se_hot_owned
 jne miss
 ; Structural mutation never reuses the old painted page. This is only a
 ; conservative refusal; current-source collection/publication stays real.
 lda GEC_NEW
 cmp #13
 beq @structural
 lda GEC_OLD
 cmp #13
 bne @nonstructural
@structural:jmp miss
@nonstructural:
 jsr read_cert
 jcs miss
 jsr cert_verify
 jcs miss
 ; A certificate is for one actual complete prior publication, not cursor-
 ; equivalent snapshots. Caret/fast typing publications age it and decline.
 ldx #1
@seq:
 lda CV_DATA+57,x
 cmp se_e_draw_sequence,x
 jne miss
 cmp GCC_SEQUENCE,x
 jne miss
 cmp GEC_SEQUENCE,x
 jne miss
 lda CV_DATA+59,x
 cmp se_gc_epoch,x
 jne miss
 dex
 bpl @seq
 lda CV_DATA+61
 cmp CV_HANDLE
 jne miss
 lda CV_DATA+62
 cmp CV_PHYSICAL
 jne miss
 ldx #36
@oldkey:
 lda CV_DATA+20,x
 cmp GCC_KEY,x
 jne miss
 dex
 bpl @oldkey
 ldx #2
@foldtop:
 lda GCC_FOLD,x
 cmp CV_DATA+64,x
 jne miss
 lda GCC_KEY+28,x
 cmp se_v_top,x
 jne miss
 dex
 bpl @foldtop
 lda GCC_FOLD
 jne miss
 lda CV_DATA+3
 cmp GCC_COUNT
 jne miss
 cmp #1
 jcc miss
 cmp #23
 jcs miss
 sta CV_OLD_COUNT
 ; Exact old FS59, allowing only the one C6 mutation's revision/gap changes.
 ; Window navigation or another prior publication is explicitly inapplicable.
 ldx #58
@shape:
 cpx #25
 bcc @same
 cpx #29
 bcc @skip
 cpx #30
 beq @skip
 cpx #53
 bcs @skip
@same:
 lda CV_DATA+CV_SOURCE,x
 cmp CV_IDENTITY,x
 jne miss
@skip:dex
 bpl @shape
 ldx #3
@revision:
 lda GEC_REVISION,x
 cmp CV_DATA+20+17,x
 jne miss
 dex
 bpl @revision
 clc
 .repeat 4,I
 lda GEC_REVISION+I
 .if I=0
 adc #1
 .else
 adc #0
 .endif
 sta CV_DELTA+I
 .endrepeat
 jcs miss
 ldx #3
@newrevision:
 lda CV_DELTA,x
 cmp se_r_revision,x
 jne miss
 dex
 bpl @newrevision
 ldx #2
@length:
 lda GEC_LENGTH,x
 cmp GCC_KEY+21,x
 jne miss
 dex
 bpl @length
 lda GEC_OP
 cmp #2
 jcs miss
 sta CV_INDEX
 lda #1
 ldx CV_INDEX
 beq :+
 lda #$FF
: sta CV_EXPECT
 lda #0
 cpx #0
 beq :+
 lda #$FF
: sta CV_EXPECT+1
 clc
 .repeat 3,I
 lda GEC_LENGTH+I
 .if I=0
 adc CV_EXPECT
 .else
 adc CV_EXPECT+1
 .endif
 sta CV_DELTA+I
 .endrepeat
 CMP24 CV_DELTA,se_v_length
 jne miss
 ; The old certified gap and caret must be at the one mutation position.
 clc
 lda CV_DATA+CV_SOURCE+48
 adc CV_DATA+CV_SOURCE+55
 sta CV_DELTA
 lda CV_DATA+CV_SOURCE+49
 adc CV_DATA+CV_SOURCE+56
 sta CV_DELTA+1
 lda CV_DATA+CV_SOURCE+50
 adc #0
 sta CV_DELTA+2
 ldx #2
@oldcaret:
 lda CV_DELTA,x
 cmp GCC_CARET,x
 jne miss
 dex
 bpl @oldcaret
 lda CV_INDEX
 beq @insert
 lda se_hot_command
 cmp #4
 jne miss
 lda GEC_NEW
 jne miss
 SUB24 CV_DELTA,one,CV_DELTA
 jmp @position
@insert:
 lda se_hot_command
 cmp #3
 jne miss
 lda GEC_OLD
 jne miss
@position:
 CMP24 CV_DELTA,GEC_POSITION
 jne miss
 lda CV_INDEX
 bne :+
 ADD24 CV_DELTA,one,CV_DELTA
: CMP24 CV_DELTA,se_hot_caret
 jne miss
 lda CV_INDEX
 cmp se_hot_delete
 jne miss
 ; Exact gap-size/left transition; right and original window extent unchanged.
 ldx #1
@gap:
 lda CV_DATA+CV_SOURCE+57,x
 cmp se_hot_right,x
 jne miss
 dex
 bpl @gap
 clc
 lda CV_DATA+CV_SOURCE+53
 adc CV_EXPECT
 sta CV_DELTA
 lda CV_DATA+CV_SOURCE+54
 adc CV_EXPECT+1
 sta CV_DELTA+1
 ldx #1
@hotlen:
 lda CV_DELTA,x
 cmp se_hot_length,x
 jne miss
 dex
 bpl @hotlen
 clc
 lda CV_DATA+CV_SOURCE+55
 adc CV_EXPECT
 sta CV_DELTA
 lda CV_DATA+CV_SOURCE+56
 adc CV_EXPECT+1
 sta CV_DELTA+1
 ldx #1
@hotleft:
 lda CV_DELTA,x
 cmp se_hot_left,x
 jne miss
 dex
 bpl @hotleft
 ; Authenticate the entire prior header, not only convenient geometry fields.
 lda #0
 sta GP_IO_OFFSET
 sta GP_IO_OFFSET+1
 lda #<CV_CHUNK
 sta GP_IO_POINTER
 lda #>CV_CHUNK
 sta GP_IO_POINTER+1
 lda #64
 sta GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 jsr se_gp_cache_read
 jcs miss
 ldx #63
@header:
 lda CV_CHUNK,x
 cmp CV_DATA+CV_HEADER,x
 jne miss
 dex
 bpl @header
 ; Preserve existing short-row admission/traffic: only a soft continuation
 ; begins this prototype. Full CR/EOF/code rows retain the original path.
 lda CV_DATA+CV_HEADER+GPH_CARET_ROW
 cmp CV_DATA+3
 jcs miss
 jsr se_gp_cache_slot
 jcs miss
 lda #32
 sta GP_IO_LENGTH
 jsr se_gp_cache_read
 jcs miss
 lda CV_CHUNK+GPR_REASON
 cmp #3
 jcc miss
 ; CurrentVIC must equal authenticated caret-free base outside oldcaret strips.
 lda #24
 sta CV_SKIP_FIRST
 lda #0
 sta CV_SKIP_END
 lda GCC_RECT
 beq @rectangle
 cmp #1
 jne miss
 lda GCC_HEIGHT
 cmp #8
 beq @height_ok
 cmp #9
 jne miss
@height_ok:
 lda GCC_Y
 cmp #16
 jcc miss
 cmp #192
 jcs miss
 lsr
 lsr
 lsr
 sta CV_SKIP_FIRST
 sta CV_MIN
 lda GCC_Y
 clc
 adc GCC_HEIGHT
 jcs miss
 cmp #193
 jcs miss
 adc #7
 lsr
 lsr
 lsr
 sta CV_SKIP_END
 sta CV_MAX
@rectangle:
 jsr screen_crc ;exactVIC/base comparison; publication is the base authority
 jcs miss
 lda #$A7
 sta CV_ACTIVE
 lda #3
 clc
 rts
crc_source:
 jsr se_crc_init
 ldy #CV_SOURCE
: lda CV_DATA,y
 jsr se_crc_byte
 iny
 cpy #CV_SOURCE+59
 bcc :-
 rts
; Current-source guard uses the60-independent exactFS59 field list. Metadata
; and chunk loan addresses never survive a callback without reauthentication.
snapshot=zero
abandon:
 lda #0
 sta CV_ACTIVE
 clc
 rts
chunk_length:
 lda #128
 ldx CV_REMAIN+1
 bne :+
 cmp CV_REMAIN
 bcc :+
 lda CV_REMAIN
: sta CV_LENGTH
 sta GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 lda #<CV_CHUNK
 sta GP_IO_POINTER
 lda #>CV_CHUNK
 sta GP_IO_POINTER+1
 rts
slot_request:
 lda CV_SLOT
 clc
 adc CV_OFFSET
 sta GP_IO_OFFSET
 lda CV_SLOT+1
 adc CV_OFFSET+1
 sta GP_IO_OFFSET+1
 rts
crc_chunk:
 ldy #0
: lda CV_CHUNK,y
 jsr se_crc_byte
 iny
 cpy CV_LENGTH
 bcc :-
 rts
advance_chunk:
 clc
 lda CV_OFFSET
 adc CV_LENGTH
 sta CV_OFFSET
 bcc :+
 inc CV_OFFSET+1
: sec
 lda CV_REMAIN
 sbc CV_LENGTH
 sta CV_REMAIN
 lda CV_REMAIN+1
 sbc #0
 sta CV_REMAIN+1
 rts
; Read the real newly derived prefix plus fields; never fabricate semantic data.
compare:
 lda CV_ACTIVE
 cmp #$A7
 bne :+
 jsr read_cert
 bcc @cert_read_ok
 rts
@cert_read_ok:
 jsr cert_verify
 jcs changed
 lda GP_CONTROL+3
 cmp CV_DATA+3
 bcc @old_row
 jsr abandon
 jmp @after_stage
@old_row:
 asl
 tax
 lda CV_DATA+CV_CRCS,x
 sta CV_EXPECT
 lda CV_DATA+CV_CRCS+1,x
 sta CV_EXPECT+1
 jsr verify_stage
 bcc @propagate_ok_12
 rts
@propagate_ok_12:
@after_stage:
: lda GP_CONTROL+3
 cmp CV_ROWS
 jne changed
 cmp #22
 jcs changed
 sta CV_LINE
 jsr se_gp_cache_slot
 bcc @propagate_ok_13
 rts
@propagate_ok_13:
 lda GP_IO_OFFSET
 sta CV_SLOT
 lda GP_IO_OFFSET+1
 sta CV_SLOT+1
 lda #0
 sta CV_DIFFERENT
 ; Every old snapshot wasCRC-checked before storing. Source/FE owns this job;
 ; compare is called before any other writer can use the reserved old buffer.
 lda CV_ACTIVE
 cmp #$A7
 bne @newcrc
 ldx #29
@prefix:
 cpx #23
 beq @skip
 lda CV_DATA,x
 cmp GP_RECORD,x
 beq @skip
 inc CV_DIFFERENT
@skip:dex
 cpx #11
 bne @prefix
@newcrc:
 jsr se_crc_init
 ldy #0
@prefixcrc:
 lda GP_RECORD,y
 jsr se_crc_byte
 iny
 cpy #32
 bcc @prefixcrc
 lda GP_RECORD+12
 ldx GP_RECORD+13
 jsr packet_count
 bcc @propagate_ok_14
 rts
@propagate_ok_14:
 lda #1
 sta CV_FIELD
 jsr packet_set
@chunks:
 jsr chunk_length
 jsr slot_request
 jsr se_gp_cache_read
 bcc @propagate_ok_15
 rts
@propagate_ok_15:
 jsr crc_chunk
 lda CV_ACTIVE
 cmp #$A7
 bne @next
 ; Retain the new bytes inOTHER while reading the corresponding oldchunk.
 ldy #0
: lda CV_CHUNK,y
 sta CV_OTHER,y
 iny
 cpy CV_LENGTH
 bcc :-
 lda CV_OFFSET
 clc
 adc CV_BACKUP
 sta GP_IO_OFFSET
 lda CV_OFFSET+1
 adc CV_BACKUP+1
 sta GP_IO_OFFSET+1
 jsr se_gp_cache_read
 bcc @propagate_ok_16
 rts
@propagate_ok_16:
 ldy #0
@equal:
 lda CV_CHUNK,y
 cmp CV_OTHER,y
 beq :+
 lda #1
 sta CV_DIFFERENT
: iny
 cpy CV_LENGTH
 bcc @equal
@next:
 jsr advance_chunk
 lda CV_REMAIN
 ora CV_REMAIN+1
 bne @chunks
 jsr packet_next
 bcc @chunks
 lda se_crc_value
 sta CV_HEADERCRC
 lda se_crc_value+1
 sta CV_HEADERCRC+1
 lda CV_ACTIVE
 cmp #$A7
 bne @save_crc
 lda CV_DIFFERENT
 beq @save_crc
 ; Prefix retained by successful full compact-stage CRC.
 lda CV_DATA+15
 ldx CV_DATA+14
 jsr dirty
 bcc @propagate_ok_17
 rts
@propagate_ok_17:
 lda GP_RECORD+15
 ldx GP_RECORD+14
 jsr dirty
 bcc @propagate_ok_18
 rts
@propagate_ok_18:
@save_crc:
 jsr read_next
 bcc @propagate_ok_19
 rts
@propagate_ok_19:
 lda CV_LINE
 asl
 tax
 lda CV_HEADERCRC
 sta CV_DATA+CV_CRCS,x
 lda CV_HEADERCRC+1
 sta CV_DATA+CV_CRCS+1,x
 jsr write_next
 bcc @propagate_ok_20
 rts
@propagate_ok_20:
 inc CV_ROWS
 jmp zero
; A=Y X=height. Dirty physical strips include every old/new contribution.
dirty:
 cmp #16
 jcc argument
 cmp #192
 jcs argument
 sta CV_INDEX
 txa
 cmp #8
 beq :+
 cmp #9
 jne argument
: clc
 adc CV_INDEX
 jcs argument
 cmp #193
 jcs argument
 adc #7
 lsr
 lsr
 lsr
 cmp CV_MAX
 bcc :+
 sta CV_MAX
: lda CV_INDEX
 lsr
 lsr
 lsr
 cmp CV_MIN
 bcs :+
 sta CV_MIN
: clc
 rts
complete:
 lda CV_COLLECT
 cmp #$A6
 beq @current
 jsr allowed
 jcs zero
 jsr collect_begin
 bcc @current
 rts
@current:
 jsr current
 bcc @work
 rts
@work:
 lda #4
 sta CV_BUDGET
@row:
 lda CV_ROWS
 cmp GP_HEADER+GPH_COUNT
 bcs @done
 sta GP_CONTROL+3
 jsr se_gp_cache_slot
 bcc @request
 rts
@request:
 lda #<GP_RECORD
 sta GP_IO_POINTER
 lda #>GP_RECORD
 sta GP_IO_POINTER+1
 lda #32
 sta GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 jsr se_gp_cache_read
 bcc @compare
 rts
@compare:
 jsr compare
 bcc @next
 rts
@next:
 dec CV_BUDGET
 bne @row
 lda #1
 clc
 rts
@done:
 sta GP_CONTROL+3 ;restore ordinary completed LINE=count
 lda CV_ACTIVE
 cmp #$A7
 jne zero
 jsr read_cert
 bcc @verify
 rts
@verify:
 jsr cert_verify
 jcs changed
 lda CV_DATA+3
 cmp CV_ROWS
 jne abandon
 lda CV_MIN
 cmp CV_MAX
 jcs abandon
 lda #2
 sta GP_CONTROL+20
 jmp zero
; ActualR27CAPTURE has generated the new caret-free base and publication key.
certify:
 lda CV_COLLECT
 cmp #$A6
 jne zero
 jsr current
 bcc @propagate_ok_23
 rts
@propagate_ok_23:
 lda GP_HEADER+GPH_VALID
 cmp #1
 jne changed
 lda GP_HEADER+GPH_COUNT
 cmp CV_ROWS
 jne changed
 jsr base_bound
 jcs abandon
 ldx #36
@currentkey:
 lda GCC_KEY,x
 cmp GP_HEADER+GPH_KEY,x
 jne abandon
 dex
 bpl @currentkey
 ldx #2
@currentfold:
 lda GCC_FOLD,x
 cmp GP_HEADER+GPH_FOLD_VALID,x
 jne abandon
 dex
 bpl @currentfold
 lda GCC_COUNT
 cmp GP_HEADER+GPH_COUNT
 jne abandon
 clc
 lda se_e_draw_sequence
 adc #1
 sta CV_EXPECT
 lda se_e_draw_sequence+1
 adc #0
 cmp GCC_SEQUENCE+1
 jne abandon
 lda CV_EXPECT
 cmp GCC_SEQUENCE
 jne abandon
 jsr read_next
 bcc @propagate_ok_25
 rts
@propagate_ok_25:
 lda #0
 sta CV_DATA
 lda CV_ROWS
 sta CV_DATA+3
 ldx #15
@binding:
 lda se_overlay_binding_digest,x
 sta CV_DATA+4,x
 dex
 bpl @binding
 ldx #36
@key:
 lda GCC_KEY,x
 sta CV_DATA+20,x
 dex
 bpl @key
 ldx #1
@meta:
 lda GCC_SEQUENCE,x
 sta CV_DATA+57,x
 lda CV_EPOCH,x
 sta CV_DATA+59,x
 dex
 bpl @meta
 lda CV_HANDLE
 sta CV_DATA+61
 lda CV_PHYSICAL
 sta CV_DATA+62
 ldx #2
@fold:
 lda GCC_FOLD,x
 sta CV_DATA+64,x
 dex
 bpl @fold
 ldx #63
@header:
 lda GP_HEADER,x
 sta CV_DATA+CV_HEADER,x
 dex
 bpl @header
 jsr crc_data
 lda se_crc_value
 sta CV_DATA+CV_CRC
 lda se_crc_value+1
 sta CV_DATA+CV_CRC+1
 lda #<CV_CERT
 ldx #>CV_CERT
 ldy #CV_SIZE
 jsr request_data
 jsr se_gp_cache_write
 bcc @propagate_ok_26
 rts
@propagate_ok_26:
 ; LiteralVALID-last1byte after all descriptor and body/packetCRC metadata.
 lda #$A5
 sta CV_DATA
 lda #1
 sta GP_IO_LENGTH
 jmp se_gp_cache_write
.segment "RODATA"
one:.byte 1,0,0
.segment "CODE"
; CRC the exact body base and compare actualVIC outside the caret's two strips.
; Those strips are unconditionally dirty, so no unchecked old pixel is reused.
screen_crc:
 lda #< (GCC_BITMAP+640)
 sta CV_BITMAP
 lda #> (GCC_BITMAP+640)
 sta CV_BITMAP+1
 lda #< (GCC_ATTRIBUTES+80)
 sta CV_ATTR
 lda #> (GCC_ATTRIBUTES+80)
 sta CV_ATTR+1
 lda #2
 sta CV_SCREEN
@strip:
 lda CV_BITMAP
 sta CV_SLOT
 sta CV_VIC
 lda CV_BITMAP+1
 sta CV_SLOT+1
 sec
 sbc #$52
 sta CV_VIC+1
 lda #<320
 sta CV_REMAIN
 lda #>320
 sta CV_REMAIN+1
 lda #1
 sta CV_DIFFERENT
 lda CV_SCREEN
 cmp CV_SKIP_FIRST
 bcc @bitmap
 cmp CV_SKIP_END
 bcs @bitmap
 lda #0
 sta CV_DIFFERENT
@bitmap:
 jsr screen_piece
 bcc @propagate_ok_27
 rts
@propagate_ok_27:
 lda CV_ATTR
 sta CV_SLOT
 sec
 sbc #$40
 sta CV_VIC
 lda CV_ATTR+1
 sta CV_SLOT+1
 sbc #$91
 sta CV_VIC+1
 lda #40
 sta CV_REMAIN
 lda #0
 sta CV_REMAIN+1
 lda #1
 sta CV_DIFFERENT
 jsr screen_piece
 bcc @propagate_ok_28
 rts
@propagate_ok_28:
 clc
 lda CV_BITMAP
 adc #<320
 sta CV_BITMAP
 lda CV_BITMAP+1
 adc #>320
 sta CV_BITMAP+1
 clc
 lda CV_ATTR
 adc #40
 sta CV_ATTR
 bcc :+
 inc CV_ATTR+1
: inc CV_SCREEN
 lda CV_SCREEN
 cmp #24
 jcc @strip
 clc
 rts
screen_piece:
 lda #0
 sta CV_OFFSET
 sta CV_OFFSET+1
@piece:
 jsr chunk_length
 jsr slot_request
 jsr se_gp_cache_read
 bcc @propagate_ok_29
 rts
@propagate_ok_29:
 lda CV_VIC
 sta text_ptr
 lda CV_VIC+1
 sta text_ptr+1
 ldy #0
@byte:
 lda CV_DIFFERENT
 beq @nextbyte
 lda CV_CHUNK,y
 cmp (text_ptr),y
 jne changed
@nextbyte:
 iny
 cpy CV_LENGTH
 bcc @byte
 clc
 lda CV_VIC
 adc CV_LENGTH
 sta CV_VIC
 bcc :+
 inc CV_VIC+1
: jsr advance_chunk
 lda CV_REMAIN
 ora CV_REMAIN+1
 bne @piece
 clc
 rts

verify_stage:
 lda GP_CONTROL+3
 cmp #2
 beq @special
 jsr se_gp_cache_slot
 lda #$80
 sta CV_SLOT
 clc
 lda GP_IO_OFFSET+1
 adc #4
 bne @set
@special:
 lda #<CV_PACKET
 sta CV_SLOT
 lda #>CV_PACKET
@set:
 sta CV_SLOT+1
 sta CV_BACKUP+1
 lda CV_SLOT
 sta CV_BACKUP
 lda #0
 sta CV_FIELD
 jsr packet_set
 jsr se_crc_init
@chunks:
 jsr chunk_length
 jsr slot_request
 jsr se_gp_cache_read
 bcc @propagate_ok_30
 rts
@propagate_ok_30:
 jsr crc_chunk
 jsr advance_chunk
 lda CV_REMAIN
 ora CV_REMAIN+1
 bne @chunks
 jsr packet_next
 bcc @chunks
 lda se_crc_value
 cmp CV_EXPECT
 jne changed
 lda se_crc_value+1
 cmp CV_EXPECT+1
 jne changed
 clc
 rts

; One canonical prefix and exactly the arrays that C22 can consume. Padding is
; not paint authority. Prefix CRC authenticates count before any reuse; the
; checked bounded count controls transfers even when malformed.
packet_count:
 cpx #0
 jne argument
 cmp #162
 jcs argument
 sta CV_COUNT
 clc
 rts
packet_next:
 lda CV_FIELD
 bne :+
 ldx #31
@prefix:
 lda CV_CHUNK,x
 sta CV_DATA,x
 dex
 bpl @prefix
 lda CV_CHUNK+12
 ldx CV_CHUNK+13
 jsr packet_count
 bcc @propagate_ok_31
 rts
@propagate_ok_31:
:inc CV_FIELD
packet_set:
 ldx CV_FIELD
 cpx #5
 bcs @done
 lda field_lo,x
 sta CV_OFFSET
 lda field_hi,x
 sta CV_OFFSET+1
 lda #0
 sta CV_REMAIN+1
 lda CV_COUNT
 cpx #0
 bne :+
 lda #32
 bne @size
:cpx #4
 bne :+
 clc
 adc #1
 asl
 rol CV_REMAIN+1
 bne @size
:cmp #0
 beq packet_next
@size:
 sta CV_REMAIN
 clc
 rts
@done:sec
 rts
.segment "RODATA"
field_lo:.byte 0,32,<194,<356,<518
field_hi:.byte 0,0,>194,>356,>518

; Actual completed R27CAPTURE publication, not an assumed clean display. Its
; base is reusable only in the same typedFE incarnation. Exact currentVIC is
; independently compared against that base outside mandatory caret-dirty rows.
base_bound:
 lda GCC_VALID
 cmp #1
 bne @no
 lda GCC_HANDLE
 cmp CV_HANDLE
 bne @no
 lda GCC_PHYSICAL
 cmp CV_PHYSICAL
 bne @no
 ldx #1
@epoch:
 lda GCC_EPOCH,x
 cmp CV_EPOCH,x
 bne @no
 dex
 bpl @epoch
 clc
 rts
@no:sec
 rts
