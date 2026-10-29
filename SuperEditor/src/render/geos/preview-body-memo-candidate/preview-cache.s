; Operation-sized owner4 preview body cache. Linked only into C27.
.include "render/geos/preview-cache.inc"
.include "render/geos/source-line.inc"
; Public product API supplies absolute bindings; private links import them.
.ifndef object_owner
.import object_owner,object_size_lo,object_size_mid,object_size_hi
.endif
.segment "GEOS_PAGE"
; BEGIN: A0miss, A1pending. Genuine source failure remains Cset.
pc_begin:
 lda #0
 sta PPC_ARMED
 sta PPC_CAPTURE
 jsr pc_source_begin
 bcs pc_return
 jsr pc_owned
 bcs pc_miss
 lda #PPC_META_FIRST
 sta PP_PHASE
 lda #1
 rts ;pc_owned already clearedcarry
pc_miss:
 jsr pc_seed
 jsr pc_release
 lda #1
 sta PPC_ARMED
 lda #0
pc_return: ;pc_release guaranteescarryclear
 rts
; Every pending callback authenticates source, typed bank, view and settings.
pc_step:
 jsr pc_reader_guard
 jcs pc_return
 lda PP_PHASE
 cmp #PPC_META_FIRST
 bne @last
 lda #<PPC_META
 sta se_reu_c64
 lda #>PPC_META
 sta se_reu_c64+1
 lda #<PPC_META_REU
 sta se_reu_offset
 lda #>PPC_META_REU
 sta se_reu_offset+1
 lda #128
 jsr pc_read
 jcs pc_miss
 inc PP_PHASE
 jmp pc_pending
@last:
 cmp #PPC_META_LAST
 bne @body
 lda #<(PPC_META+128)
 sta se_reu_c64
 lda #>(PPC_META+128)
 sta se_reu_c64+1
 lda #<(PPC_META_REU+128)
 sta se_reu_offset
 lda #>(PPC_META_REU+128)
 sta se_reu_offset+1
 lda #PPC_SIZE-128
 jsr pc_read
 jcs pc_miss
 jsr pc_validate
 jcs pc_miss
 jsr pc_context
 jcs pc_miss
 jsr pc_reset
 jmp pc_pending
@body:
 jsr pc_owned
 jcs pc_return
 lda se_gc_handle
 cmp PPC_META+6
 jne pc_stale
 ldx se_gc_handle
 lda se_reu_map,x
 cmp PPC_META+7
 jne pc_stale
 jsr pc_context
 jcs pc_return
 jsr pc_chunk
 lda PPC_CAPTURE
 bne @capture
 lda PPC_BODY_MEMO
 jeq pc_miss ;checked write during an earlier CRC slice revoked it
 lsr a ;1verified =>carry,80verifying =>clear
 jcs pc_restore
 lda #<PPC_CHUNK
 sta se_reu_c64
 lda #>PPC_CHUNK
 sta se_reu_c64+1
 lda PPC_COUNT
 jsr pc_read
 jcs pc_return
 lda #<PPC_CHUNK
 sta text_ptr
 lda #>PPC_CHUNK
 sta text_ptr+1
 jmp @crc
@capture:
 jsr pc_live_pointer
@crc:
 lda PPC_VALUE
 sta se_crc_value
 lda PPC_VALUE+1
 sta se_crc_value+1
 ldy #0
@byte:
 lda (text_ptr),y
 jsr se_crc_byte
 iny
 cpy PPC_COUNT
 bne @byte
 lda se_crc_value
 sta PPC_VALUE
 lda se_crc_value+1
 sta PPC_VALUE+1
 clc
 lda PPC_CURSOR
 adc PPC_COUNT
 sta PPC_CURSOR
 bcc :+
 inc PPC_CURSOR+1
:
 lda PPC_CURSOR
 cmp #<PPC_DATA_LEN
 bne pc_pending
 lda PPC_CURSOR+1
 cmp #>PPC_DATA_LEN
 bne pc_pending
 lda PPC_CAPTURE
 jne pc_commit
 lda PPC_VALUE
 cmp PPC_META+PPC_CRC
 jne pc_miss
 lda PPC_VALUE+1
 cmp PPC_META+PPC_CRC+1
 jne pc_miss
 lda #1
 sta PPC_BODY_MEMO
pc_restore:
 ; No foreground yield after checksum before live DMA; IRQ never touches REU.
 lda #1
 jsr pc_body_dma
 jcs pc_return
 ldx #65
@anchors:
 lda PPC_META+PPC_ANCHORS,x
 sta se_v_rows,x
 dex
 bpl @anchors
 ldx #2
@bottom:
 lda PPC_META+PPC_BOTTOM,x
 sta PP_POSITION,x
 dex
 bpl @bottom
 lda PPC_META+PPC_ROWS
 sta PP_LINE
 jsr pc_release
 lda #0
 sta PPC_ARMED
 lda #2
 clc
 rts
pc_pending:
 lda #1
 clc
 rts
; After full producer completion: arm bounded capture only if initial key holds.
pc_capture_begin:
 lda PPC_ARMED
 beq @skip
 lda #0
 sta PPC_ARMED
 jsr pc_source_begin
 bcs @skip
 jsr pc_context
 bcs @release
 lda se_gc_handle
 bne @existing
 lda #$FE
 jsr se_reu_alloc
 bcs @release
 sta se_gc_handle
 lda #0
 sta se_gc_valid
 lda se_reu_epoch
 sta se_gc_epoch
 lda se_reu_epoch+1
 sta se_gc_epoch+1
@existing:
 jsr pc_owned
 bcs @release
 lda se_gc_handle
 sta PPC_META+6
 tax
 lda se_reu_map,x
 sta PPC_META+7
 ; Unpublish before any cache-image write. Keep font/header/source packets.
 lda #0
 sta PPC_META+5
 lda #<(PPC_META+5)
 sta se_reu_c64
 lda #>(PPC_META+5)
 sta se_reu_c64+1
 lda #<(PPC_META_REU+5)
 sta se_reu_offset
 lda #>(PPC_META_REU+5)
 sta se_reu_offset+1
 lda #1
 jsr pc_write
 bcs @release
 lda #1
 sta PPC_CAPTURE
 jsr pc_reset
 jmp pc_pending
@release:
 jsr pc_release
@skip:
 lda #0
 clc
 rts
pc_commit:
 lda PPC_VALUE
 sta PPC_META+PPC_CRC
 lda PPC_VALUE+1
 sta PPC_META+PPC_CRC+1
 ldx #2
@bottom:
 lda PP_POSITION,x
 sta PPC_META+PPC_BOTTOM,x
 dex
 bpl @bottom
 lda PP_LINE
 sta PPC_META+PPC_ROWS
 ldx #65
@anchors:
 lda se_v_rows,x
 sta PPC_META+PPC_ANCHORS,x
 dex
 bpl @anchors
 lda #1
 sta PPC_META+5
 jsr pc_header_crc
 lda se_crc_value
 sta PPC_META+PPC_META_CRC
 lda se_crc_value+1
 sta PPC_META+PPC_META_CRC+1
 lda #0
 jsr pc_body_dma
 bcs @release
 lda #0
 sta PPC_META+5
 lda #<PPC_META
 sta se_reu_c64
 lda #>PPC_META
 sta se_reu_c64+1
 lda #<PPC_META_REU
 sta se_reu_offset
 lda #>PPC_META_REU
 sta se_reu_offset+1
 lda #PPC_SIZE
 jsr pc_write
 bcs @release
 lda #1
 sta PPC_META+5
 lda #<(PPC_META+5)
 sta se_reu_c64
 lda #>(PPC_META+5)
 sta se_reu_c64+1
 lda #<(PPC_META_REU+5)
 sta se_reu_offset
 lda #>(PPC_META_REU+5)
 sta se_reu_offset+1
 lda #1
 jsr pc_write ;VALID publication last; failure merely disables optional capture
 bcs @release
 lda #1
 sta PPC_BODY_MEMO
@release:
 jsr pc_release
 lda #2
 clc
 rts
pc_reset:
 lda PPC_BODY_MEMO
 bne :+
 lda #$80
 sta PPC_BODY_MEMO ;arm sweep; any inter-slice checkedwrite returns it to0
:
 lda #0
 sta PPC_CURSOR
 sta PPC_CURSOR+1
 lda #$FF
 sta PPC_VALUE
 sta PPC_VALUE+1
 lda #PPC_CRC_PHASE
 sta PP_PHASE
 rts
pc_chunk:
 lda #128
 sta PPC_COUNT
 lda PPC_CURSOR+1
 cmp #>(PPC_DATA_LEN-128)
 bcc @offset
 lda PPC_CURSOR
 cmp #<(PPC_DATA_LEN-128)
 bcc @offset
 lda #<PPC_DATA_LEN
 sec
 sbc PPC_CURSOR
 sta PPC_COUNT
@offset:
 clc
 lda PPC_CURSOR
 adc #<PPC_DATA_REU
 sta se_reu_offset
 lda PPC_CURSOR+1
 adc #>PPC_DATA_REU
 sta se_reu_offset+1
 rts
pc_live_pointer:
 lda PPC_CURSOR+1
 cmp #>PPC_BITMAP_LEN
 bcc @bitmap
 bne @attrs
 lda PPC_CURSOR
 cmp #<PPC_BITMAP_LEN
 bcc @bitmap
@attrs:
 clc
 lda PPC_CURSOR
 adc #<($4050-PPC_BITMAP_LEN)
 sta text_ptr
 lda PPC_CURSOR+1
 adc #>($4050-PPC_BITMAP_LEN)
 sta text_ptr+1
 rts
@bitmap:
 clc
 lda PPC_CURSOR
 adc #<$6280
 sta text_ptr
 lda PPC_CURSOR+1
 adc #>$6280
 sta text_ptr+1
 rts
; A=direction, one full bitmap plus attributes; source is frozen for this call.
pc_body_dma:
 sta PPC_SAVED
 lda #<$6280
 sta se_reu_c64
 lda #>$6280
 sta se_reu_c64+1
 lda #<PPC_DATA_REU
 sta se_reu_offset
 lda #>PPC_DATA_REU
 sta se_reu_offset+1
 lda #<PPC_BITMAP_LEN
 sta se_reu_length
 lda #>PPC_BITMAP_LEN
 sta se_reu_length+1
 jsr pc_handle
 lda PPC_SAVED
 jsr se_reu_copy
 jcs pc_return
 lda #<$4050
 sta se_reu_c64
 lda #>$4050
 sta se_reu_c64+1
 lda #<(PPC_DATA_REU+PPC_BITMAP_LEN)
 sta se_reu_offset
 lda #>(PPC_DATA_REU+PPC_BITMAP_LEN)
 sta se_reu_offset+1
 lda #<PPC_ATTR_LEN
 sta se_reu_length
 lda #>PPC_ATTR_LEN
 sta se_reu_length+1
 jsr pc_handle
 lda PPC_SAVED
 jmp se_reu_copy
pc_read:
 jsr pc_length
 lda #1
 jmp se_reu_copy
pc_write:
 jsr pc_length
 lda #0
 jmp se_reu_copy
pc_length:
 sta se_reu_length
 lda #0
 sta se_reu_length+1
pc_handle:
 lda se_gc_handle
 sta se_reu_logical
 rts
pc_owned:
 lda se_reu_retired
 bne pc_stale
 lda se_gc_epoch
 cmp se_reu_epoch
 bne pc_stale
 lda se_gc_epoch+1
 cmp se_reu_epoch+1
 bne pc_stale
 ldx se_gc_handle
 beq pc_stale
 lda se_reu_logical_owner,x
 cmp #$FE
 bne pc_stale
 ldy se_reu_map,x
 beq pc_stale
 lda se_reu_physical_owner,y
 cmp #$FE
 bne pc_stale
 clc
 rts
pc_stale:
 lda #$18
 sec
 rts
pc_source_begin:
 lda #0
 ldx #85
@clear:
 sta se_fs_state,x
 dex
 bpl @clear
 jmp pc_reader
pc_reader_guard:
 lda #1
pc_reader:
 sta se_overlay_frame
 lda #14
 ldx #0
 jsr se_overlay_call
 php
 pha
 ldx #85
@snapshot:
 lda se_fs_state,x
 sta GS_FS,x
 dex
 bpl @snapshot
 lda se_fs_owned
 sta GS_ACTIVE
 sta GS_CONTEXT_VALID
 pla
 plp
 rts
pc_release:
 jsr se_fs_end
 lda #0
 sta GS_ACTIVE
 sta GS_CONTEXT_VALID
 rts
pc_header_crc:
 jsr se_crc_init
 ldy #0
@byte:
 lda PPC_META,y
 jsr se_crc_byte
 iny
 cpy #PPC_META_CRC
 bne @byte
 rts
pc_validate:
 lda PPC_META
 cmp #'P'
 jne pc_changed
 lda PPC_META+1
 cmp #'V'
 jne pc_changed
 lda PPC_META+2
 cmp #1
 jne pc_changed
 lda PPC_META+5
 cmp #1
 jne pc_changed
 jsr pc_header_crc
 lda se_crc_value
 cmp PPC_META+PPC_META_CRC
 jne pc_changed
 lda se_crc_value+1
 cmp PPC_META+PPC_META_CRC+1
 bne pc_changed
 lda PPC_META+PPC_ROWS
 cmp #23
 bcs pc_changed
 ldx #2
@first:
 lda PPC_META+PPC_ANCHORS,x
 cmp PPC_META+PPC_TOP,x
 bne pc_changed
 dex
 bpl @first
 ; Canonical anchors are checked by the source builder and protected by CRC.
 ; Bound every published row at/before the captured bottom and source length.
 CMP24 PPC_META+PPC_BOTTOM,se_v_length
 bcc @rows
 bne pc_changed
@rows:
 ldx #0
 ldy PPC_META+PPC_ROWS
 beq @done
@row:
 lda PPC_META+PPC_ANCHORS+2,x
 cmp PPC_META+PPC_BOTTOM+2
 bcc @next
 bne pc_changed
 lda PPC_META+PPC_ANCHORS+1,x
 cmp PPC_META+PPC_BOTTOM+1
 bcc @next
 bne pc_changed
 lda PPC_META+PPC_ANCHORS,x
 cmp PPC_META+PPC_BOTTOM
 bcc @next
 bne pc_changed
@next:
 cpx #0
 beq @advance
 lda PPC_META+PPC_ANCHORS+2,x
 cmp PPC_META+PPC_ANCHORS-1,x
 bcc pc_changed
 bne @advance
 lda PPC_META+PPC_ANCHORS+1,x
 cmp PPC_META+PPC_ANCHORS-2,x
 bcc pc_changed
 bne @advance
 lda PPC_META+PPC_ANCHORS,x
 cmp PPC_META+PPC_ANCHORS-3,x
 bcc pc_changed
@advance:
 inx
 inx
 inx
 dey
 bne @row
@done:
 clc
 rts
pc_changed:
 lda #$74
 sec
 rts
pc_seed:
 lda #0
 ldx #PPC_SIZE-1
@zero:
 sta PPC_META,x
 dex
 cpx #$FF
 bne @zero
 lda #'P'
 sta PPC_META
 lda #'V'
 sta PPC_META+1
 lda #1
 sta PPC_META+2
 ldx #58
@source:
 lda se_fs_identity,x
 sta PPC_META+PPC_SOURCE,x
 dex
 bpl @source
 ldx #63
@settings:
 lda se_editor_settings,x
 sta PPC_META+PPC_SETTINGS,x
 dex
 bpl @settings
 ldx #2
@top:
 lda se_v_top,x
 sta PPC_META+PPC_TOP,x
 dex
 bpl @top
 lda se_ef_valid
 sta PPC_META+PPC_FOLD_VALID
 ldx #6
@fold:
 lda se_ef_token,x
 sta PPC_META+PPC_FOLD_TOKEN,x
 dex
 bpl @fold
 ; token/count/key are not contiguous with generation; copy fields explicitly.
 ldx #1
@fold_generation:
 lda se_ef_generation,x
 sta PPC_META+PPC_FOLD_GENERATION,x
 dex
 bpl @fold_generation
 lda $CBC0
 sta PPC_META+PPC_FONT_READY
 ldx #1
@font:
 lda $CBC1,x
 sta PPC_META+PPC_FONT_HANDLES,x
 tay
 lda se_reu_map,y
 sta PPC_META+PPC_FONT_MAP,x
 lda $CBC3,x
 sta PPC_META+PPC_FONT_EPOCH,x
 dex
 bpl @font
 rts
pc_context:
 ldx #58
@source:
 lda se_fs_identity,x
 cmp PPC_META+PPC_SOURCE,x
 jne pc_changed
 dex
 bpl @source
 ldx #63
@settings:
 lda se_editor_settings,x
 cmp PPC_META+PPC_SETTINGS,x
 jne pc_changed
 dex
 bpl @settings
 ldx #2
@top:
 lda se_v_top,x
 cmp PPC_META+PPC_TOP,x
 jne pc_changed
 dex
 bpl @top
 lda se_ef_valid
 cmp PPC_META+PPC_FOLD_VALID
 jne pc_changed
 lda se_ef_valid
 jeq @font
 ldx #4
@token:
 lda se_ef_token,x
 cmp PPC_META+PPC_FOLD_TOKEN,x
 jne pc_changed
 dex
 bpl @token
 ldx #1
@fold:
 lda se_ef_count,x
 cmp PPC_META+PPC_FOLD_COUNT,x
 jne pc_changed
 lda se_ef_generation,x
 cmp PPC_META+PPC_FOLD_GENERATION,x
 jne pc_changed
 dex
 bpl @fold
 ; Derived map remains a live full typed capability, not just matching bytes.
 ldx #4
@map_token:
 lda se_ef_token,x
 sta se_object_id,x
 dex
 bpl @map_token
 jsr se_object_validate
 jcs pc_return
 lda object_owner,x
 cmp #$46
 jne pc_changed
 lda se_ef_count
 sta se_object_offset
 lda se_ef_count+1
 sta se_object_offset+1
 lda #0
 sta se_object_offset+2
 ldy #5
@map_size:
 asl se_object_offset
 rol se_object_offset+1
 rol se_object_offset+2
 dey
 bne @map_size
 lda object_size_hi,x
 cmp se_object_offset+2
 jcc pc_changed
 bne @font
 lda object_size_mid,x
 cmp se_object_offset+1
 jcc pc_changed
 bne @font
 lda object_size_lo,x
 cmp se_object_offset
 jcc pc_changed
@font:
 lda $CBC0
 cmp #$A5
 jne pc_changed
 cmp PPC_META+PPC_FONT_READY
 jne pc_changed
 ldx #1
@face:
 lda $CBC3,x
 cmp se_reu_epoch,x
 jne pc_changed
 cmp PPC_META+PPC_FONT_EPOCH,x
 jne pc_changed
 lda $CBC1,x
 cmp PPC_META+PPC_FONT_HANDLES,x
 jne pc_changed
 tay
 lda se_reu_logical_owner,y
 cmp #$FD
 jne pc_changed
 lda se_reu_map,y
 cmp PPC_META+PPC_FONT_MAP,x
 jne pc_changed
 tay
 lda se_reu_physical_owner,y
 cmp #$FD
 jne pc_changed
 dex
 bpl @face
 clc
 rts
