; PRIVATE actual FE packet memo; no C20 layout reconstruction or host events.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "cache/layout-compact/api.inc"
.include "render/geos/editor.inc"
.include "cache/api.inc"
.import se_fs_active,se_fs_owned
.import se_ef_key_match,se_object_id,se_object_validate,object_owner,object_size_lo,object_size_mid,object_size_hi
.import se_f_owner,se_mode,se_render_caps,se_l_mode,se_l_pan,se_r_presentation
.import se_editor_settings,se_ef_token,se_ef_count,se_ef_generation,se_ef_visible
.import se_gc_handle,se_gc_epoch,se_reu_epoch,se_reu_map
.import se_crc_init,se_crc_byte,se_crc_value
.import se_bc_arena,se_bc_flags,se_bc_count
.import se_overlay_ids,se_overlay_capacity,image_slot,image_crc_lo,image_crc_hi,image_size_lo,image_size_hi
.import se_overlay_managed_verification
.importzp text_ptr
.export se_lm_capture,se_lm_restore,se_lm_step,se_lm_cancel,se_lm_revoke
.segment "CODE"
se_lm_capture:
 jsr owner
 jcs return
 jsr begin_ready
 jcs return
 jsr se_gp_cache_guard
 jcs return
 lda GP_HEADER
 cmp #1
 jne miss
 lda GP_HEADER+GPH_COUNT
 cmp #23
 jcs bad
 sta LM_ROWS
 asl
 clc
 adc #2
 sta LM_RECORDS
 lda #0
 ldx #LM_META_BYTES/2-1
@zero:
 sta LM_META,x
 sta LM_META+LM_META_BYTES/2,x
 dex
 cpx #$FF
 bne @zero
 ldx #63
@header:
 lda GP_HEADER,x
 sta LM_META+LMM_HEADER,x
 dex
 bpl @header
 lda #LM_MAGIC
 sta LM_META+1
 lda #LM_VERSION
 sta LM_META+2
 lda LM_ROWS
 sta LM_META+3
 jsr fold_guard
 jcs return
 jsr capture_context
 jcs return
 jsr native_crc
 lda se_crc_value
 sta LM_META+LMM_FONT
 lda se_crc_value+1
 sta LM_META+LMM_FONT+1
 lda #0
 sta LM_MODE
 sta LM_WRITING
 jsr reset
 ; Revoke any prior metadata before the first payload overwrite.
 lda #0
 sta LM_META
 jsr valid_write
 jcs fail
 lda #LM_VALID
 sta LM_ACTIVE
 lda #0
 sta LM_RECORD
 lda #7 ;collect checked actual prefix COUNTs before packing
 sta LM_PHASE
 jmp pending
se_lm_restore:
 jsr owner
 jcs return
 jsr begin_ready
 jcs return
 jsr se_gp_cache_guard
 jcs return
 lda GP_HEADER
 cmp #1
 jne miss
 lda #1
 sta LM_MODE
 lda #0
 sta LM_WRITING
 sta LM_METAPOS
 sta LM_METAPOS+1
 jsr memo_reset
 lda #LM_VALID
 sta LM_ACTIVE
 lda #3
 sta LM_PHASE
 jmp pending
se_lm_step:
 jsr owner
 jcs return
 lda LM_ACTIVE
 cmp #LM_VALID
 jne bad
 lda LM_PHASE
 jeq bad
 jsr se_gp_cache_guard
 jcs fail
 lda LM_PHASE
 cmp #3
 jeq meta_read
 jsr context
 jcs fail
 lda LM_PHASE
 cmp #7
 jeq scan_counts
 cmp #1
 jeq capture
 cmp #2
 jeq meta_write
 cmp #4
 jeq verify
 cmp #5
 jeq record_read
 cmp #6
 jeq record_write
 jmp bad
se_lm_cancel:
 jsr owner
 bcs return
 lda LM_ACTIVE
 cmp #LM_VALID
 bne zero
 lda LM_PHASE
 beq zero
 lda LM_MODE
 beq @capture
 lda LM_WRITING
 beq @forget
 lda #0
 sta GP_RECORD
 jsr primary_valid
 jmp @forget
@capture:
 lda #0
 sta LM_META
 jsr valid_write
@forget:
 jsr forget
zero:
 lda #0
 clc
return:
 rts
pending:
 lda #1
 clc
 rts
owner:
 lda se_f_owner
 cmp #4
 beq zero
 lda #$B2
 sec
 rts
busy:
 lda #$91
 sec
 rts
bad:
 lda #$90
 sec
 rts
miss:
 lda #2
 clc
 rts
fail:
 pha
 jsr forget
 lda LM_WRITING
 beq :+
 lda #0
 sta GP_RECORD
 jsr primary_valid
:
 pla
 sec
 rts

; Whole-payload checksum pass completes before primary VALID0 or any row write.
verify:
 jsr record_chunk
 jsr memo_read
 jcs fail
 jsr crc_data
 jsr advance
 jcc pending
 lda LM_CRC
 cmp LM_META+6
 jne corrupt
 lda LM_CRC+1
 cmp LM_META+7
 jne corrupt
 jsr native_check
 jcs fail
 jsr reset
 lda #0
 sta GP_RECORD
 jsr primary_valid
 jcs fail
 lda #1
 sta LM_WRITING
 lda #5
 sta LM_PHASE
 jmp pending
corrupt:
 lda #$94
 jmp fail
capture:
 jsr record_chunk
 jsr live_read
 jcs fail
 lda LM_PROGRESS+1
 bne :+
 lda LM_PROGRESS
 cmp #32
 bcs :+
 clc
 adc LM_COUNT
 cmp #32
 bcc :+
 jsr packet_shape
 jcs fail
:
 jsr crc_data
 jsr memo_write
 jcs fail
 jsr advance
 jcc pending
 lda LM_CRC
 sta LM_META+6
 lda LM_CRC+1
 sta LM_META+7
 jsr native_check
 jcs fail
 jsr meta_crc
 lda se_crc_value
 sta LM_META+8
 lda se_crc_value+1
 sta LM_META+9
 lda #0
 sta LM_METAPOS
 sta LM_METAPOS+1
 jsr memo_reset
 lda #2
 sta LM_PHASE
 jmp pending
meta_write:
 jsr metadata_chunk
 jsr memo_write
 jcs fail
 jsr metadata_advance
 jcc pending
 lda #LM_VALID
 sta LM_META
 jsr valid_write
 jcs fail
 lda #0
 sta LM_PHASE
 jsr forget
 jmp zero
meta_read:
 jsr metadata_chunk
 jsr memo_read
 jcs fail
 jsr metadata_advance
 jcc pending
 lda LM_META
 cmp #LM_VALID
 jne miss_clear
 lda LM_META+1
 cmp #LM_MAGIC
 jne miss_clear
 lda LM_META+2
 cmp #LM_VERSION
 jne miss_clear
 lda LM_META+3
 cmp #23
 jcs miss_clear
 sta LM_ROWS
 asl
 clc
 adc #2
 sta LM_RECORDS
 jsr meta_crc
 lda se_crc_value
 cmp LM_META+8
 jne miss_clear
 lda se_crc_value+1
 cmp LM_META+9
 jne miss_clear
 jsr context
 jcs miss_clear
 ldx #2
@top:
 lda LM_TARGET,x
 cmp LM_META+LMM_HEADER+GPH_TOP,x
 jne miss_clear
 dex
 bpl @top
 jsr native_check
 jcs miss_clear
 jsr reset
 lda #4
 sta LM_PHASE
 jmp pending
miss_clear:
 jsr forget
 jmp miss

; After global verification stage one complete <=842B record, check its own
; protected CRC, then publish <=128B at a time from CPU-owned immutable bytes.
record_read:
 jsr record_chunk
 jsr memo_read
 jcs fail
 jsr crc_record
 lda LM_RCRC
 sta LM_TEMP+2
 lda LM_RCRC+1
 sta LM_TEMP+3
 jsr advance
 lda LM_TEMP+1
 jeq pending
 ldx LM_RECORD
 dex
 txa
 asl
 tax
 lda LM_TEMP+2
 cmp LM_META+LMM_RECORD_CRC,x
 jne corrupt
 lda LM_TEMP+3
 cmp LM_META+LMM_RECORD_CRC+1,x
 jne corrupt
 ; advance already selected the next record; recover this record for writes.
 dec LM_RECORD
 jsr descriptor
 jsr packet_shape
 jcs fail
 lda #0
 sta LM_PROGRESS
 sta LM_PROGRESS+1
 lda #6
 sta LM_PHASE
 jmp pending
record_write:
 jsr live_chunk
 ; Header VALID stays0 until every record and final source/font guard passed.
 lda LM_RECORD
 bne :+
 lda #0
 sta LM_BUFFER
:
 jsr live_write
 jcs fail
 clc
 lda LM_PROGRESS
 adc LM_COUNT
 sta LM_PROGRESS
 bcc :+
 inc LM_PROGRESS+1
:
 lda LM_PROGRESS
 cmp LM_LENGTH
 jne pending
 lda LM_PROGRESS+1
 cmp LM_LENGTH+1
 jne pending
 inc LM_RECORD
 lda LM_RECORD
 cmp LM_RECORDS
 beq @complete
 jsr descriptor
 lda #0
 sta LM_PROGRESS
 sta LM_PROGRESS+1
 lda #$FF
 sta LM_RCRC
 sta LM_RCRC+1
 lda #5
 sta LM_PHASE
 jmp pending
@complete:
 jsr native_check
 jcs fail
 lda #1
 sta GP_RECORD
 jsr primary_valid
 jcs fail
 lda #0
 sta LM_WRITING
 sta LM_PHASE
 jsr forget
 jmp zero

reset:
 jsr memo_reset
 ; Metadata occupies exactly320 logical scatter bytes.
 lda #128
 sta LM_COUNT
 jsr memo_advance
 jsr memo_advance
 lda #64
 sta LM_COUNT
 jsr memo_advance
 lda #0
 sta LM_RECORD
 sta LM_PROGRESS
 sta LM_PROGRESS+1
 lda #$FF
 sta LM_CRC
 sta LM_CRC+1
 sta LM_RCRC
 sta LM_RCRC+1
 jmp descriptor
; Each new descriptor is derived from bounded record number, never source bytes.
descriptor:
 lda #0
 sta LM_PACKED
 sta LM_LIVE
 sta LM_LENGTH+1
 lda LM_RECORD
 beq @header
 clc
 adc #1
 cmp LM_RECORDS
 beq @incoming
 lda LM_RECORD
 lsr
 bcs @packet
 ; even2->row0 certificate0700,4->row1certificate0F00.
 sec
 sbc #1
 asl
 asl
 asl
 clc
 adc #7
 sta LM_LIVE+1
 lda #64
 sta LM_LENGTH
 rts
@packet:
 tax
 lda LM_META+LMM_COUNTS,x
 sta LM_N
 sta LM_LENGTH
 lda #1
 sta LM_PACKED
 txa
 asl
 asl
 asl
 clc
 adc #2
 sta LM_LIVE+1
 asl LM_LENGTH
 rol LM_LENGTH+1
 asl LM_LENGTH
 rol LM_LENGTH+1
 clc
 lda LM_LENGTH
 adc LM_N
 sta LM_LENGTH
 bcc :+
 inc LM_LENGTH+1
:
 clc
 lda LM_LENGTH
 adc #34
 sta LM_LENGTH
 bcc :+
 inc LM_LENGTH+1
:
 rts
@incoming:
 lda #6
 sta LM_LIVE+1
 lda #128
 bne @length
@header:
 lda #0
 sta LM_LIVE+1
 lda #64
@length:
 sta LM_LENGTH
 rts
chunk_count:
 sec
 lda LM_LENGTH
 sbc LM_PROGRESS
 sta LM_COUNT
 lda LM_LENGTH+1
 sbc LM_PROGRESS+1
 bne @max
 lda LM_COUNT
 cmp #129
 bcc @memo
@max:
 lda #128
 sta LM_COUNT
@memo:
 rts
record_chunk:
 jsr chunk_count
 sec
 lda LM_MEMEND
 sbc LM_MEMO
 sta LM_TEMP
 lda LM_MEMEND+1
 sbc LM_MEMO+1
 bne chunk_pointer
 lda LM_TEMP
 cmp LM_COUNT
 bcs chunk_pointer
 sta LM_COUNT
 jmp chunk_pointer
live_chunk:
 jsr chunk_count
chunk_pointer:
 clc
 lda #<LM_BUFFER
 adc LM_PROGRESS
 sta GP_IO_POINTER
 lda #>LM_BUFFER
 adc LM_PROGRESS+1
 sta GP_IO_POINTER+1
 jmp count_request
advance:
 lda #0
 sta LM_TEMP+1
 jsr memo_advance
 clc
 lda LM_PROGRESS
 adc LM_COUNT
 sta LM_PROGRESS
 bcc :+
 inc LM_PROGRESS+1
:
 lda LM_PROGRESS
 cmp LM_LENGTH
 bne @more
 lda LM_PROGRESS+1
 cmp LM_LENGTH+1
 bne @more
 lda #1
 sta LM_TEMP+1
 lda LM_MODE
 bne @next
 ldx LM_RECORD
 txa
 asl
 tax
 lda LM_RCRC
 sta LM_META+LMM_RECORD_CRC,x
 lda LM_RCRC+1
 sta LM_META+LMM_RECORD_CRC+1,x
@next:
 inc LM_RECORD
 lda LM_RECORD
 cmp LM_RECORDS
 beq @end
 jsr descriptor
 lda #0
 sta LM_PROGRESS
 sta LM_PROGRESS+1
 lda #$FF
 sta LM_RCRC
 sta LM_RCRC+1
@end:
 lda LM_RECORD
 cmp LM_RECORDS
 beq :+
 clc
 rts
:sec
 rts
@more:
 clc
 rts

; Opaque scatter stream: relative0400..0500 +0540..0800 in each primary
; slot, excluding absolute0600..067F and1600..167F unconditionally.
memo_reset:
 lda #0
 sta LM_MROW
 sta LM_MPART
 lda #$80
 sta LM_MEMO
 lda #6
 sta LM_MEMO+1
 lda #0
 sta LM_MEMEND
 lda #7
 sta LM_MEMEND+1
 rts
memo_advance:
 clc
 lda LM_MEMO
 adc LM_COUNT
 sta LM_MEMO
 bcc :+
 inc LM_MEMO+1
:
 lda LM_MEMO
 cmp LM_MEMEND
 bne @return
 lda LM_MEMO+1
 cmp LM_MEMEND+1
 bne @return
 lda LM_MPART
 bne @row
 inc LM_MPART
 lda #$40
 sta LM_MEMO
 clc
 lda LM_MEMEND+1
 adc #3
 sta LM_MEMEND+1
 rts
@row:
 lda #0
 sta LM_MPART
 inc LM_MROW
 lda LM_MROW
 asl
 asl
 asl
 clc
 adc #6
 sta LM_MEMO+1
 clc
 adc #1
 sta LM_MEMEND+1
 lda LM_MROW
 cmp #2
 bne @return
 lda #$80
 sta LM_MEMO
@return:
 rts
metadata_chunk:
 sec
 lda #<LM_META_BYTES
 sbc LM_METAPOS
 sta LM_COUNT
 lda #>LM_META_BYTES
 sbc LM_METAPOS+1
 bne @max
 lda LM_COUNT
 cmp #129
 bcc @pointer
@max:
 lda #128
 sta LM_COUNT
@pointer:
 clc
 lda #<LM_META
 adc LM_METAPOS
 sta GP_IO_POINTER
 lda #>LM_META
 adc LM_METAPOS+1
 sta GP_IO_POINTER+1
 jmp count_request
metadata_advance:
 lda #0
 sta LM_TEMP+1
 jsr memo_advance
 clc
 lda LM_METAPOS
 adc LM_COUNT
 sta LM_METAPOS
 bcc :+
 inc LM_METAPOS+1
:
 lda LM_METAPOS
 cmp #<LM_META_BYTES
 bne @more
 lda LM_METAPOS+1
 cmp #>LM_META_BYTES
 beq @done
@more:
 clc
 rts
@done:
 sec
 rts
count_request:
 lda LM_COUNT
 sta GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 rts
memo_request:
 lda LM_MEMO
 sta GP_IO_OFFSET
 lda LM_MEMO+1
 sta GP_IO_OFFSET+1
 rts
memo_read:
 jsr memo_request
 jmp se_gp_cache_read
memo_write:
 jsr memo_request
 jmp se_gp_cache_write
live_request:
 lda LM_PACKED
 bne packed_request
 clc
 lda LM_LIVE
 adc LM_PROGRESS
 sta GP_IO_OFFSET
 lda LM_LIVE+1
 adc LM_PROGRESS+1
 sta GP_IO_OFFSET+1
 rts
live_read:
 jsr live_request
 jmp se_gp_cache_read
live_write:
 jsr live_request
 jmp se_gp_cache_write
 ; COUNT-packed coordinate to original ABI3 field. Unused tails are neither
; stored nor restored. The caller sees the same live prefix/arrays/boundaries.
packed_request:
 lda LM_PROGRESS
 sta LM_OFFSET
 lda LM_PROGRESS+1
 sta LM_OFFSET+1
 bne @arrays
 lda LM_OFFSET
 cmp #32
 bcs @arrays
 lda #32
 sec
 sbc LM_OFFSET
 sta LM_REMAIN
 lda #0
 sta LM_REMAIN+1
 jmp @offset
@arrays:
 sec
 lda LM_OFFSET
 sbc #32
 sta LM_OFFSET
 lda LM_OFFSET+1
 sbc #0
 sta LM_OFFSET+1
 ldx #0
@field:
 lda LM_OFFSET+1
 bne @next
 lda LM_OFFSET
 cmp LM_N
 bcc @found
@next:
 sec
 lda LM_OFFSET
 sbc LM_N
 sta LM_OFFSET
 lda LM_OFFSET+1
 sbc #0
 sta LM_OFFSET+1
 inx
 cpx #3
 bne @field
 ; X boundaries contain COUNT+1 words, including the final boundary.
 lda LM_N
 clc
 adc #1
 sta LM_REMAIN
 lda #0
 rol
 sta LM_REMAIN+1
 asl LM_REMAIN
 rol LM_REMAIN+1
 jmp @remaining
@found:
 lda LM_N
 sta LM_REMAIN
 lda #0
 sta LM_REMAIN+1
@remaining:
 sec
 lda LM_REMAIN
 sbc LM_OFFSET
 sta LM_REMAIN
 lda LM_REMAIN+1
 sbc LM_OFFSET+1
 sta LM_REMAIN+1
 txa
 asl
 tax
 clc
 lda LM_OFFSET
 adc field_offsets,x
 sta LM_OFFSET
 lda LM_OFFSET+1
 adc field_offsets+1,x
 sta LM_OFFSET+1
@offset:
 lda LM_REMAIN+1
 bne @address
 lda LM_REMAIN
 cmp LM_COUNT
 bcs @address
 sta LM_COUNT
 jsr count_request
@address:
 clc
 lda LM_LIVE
 adc LM_OFFSET
 sta GP_IO_OFFSET
 lda LM_LIVE+1
 adc LM_OFFSET+1
 sta GP_IO_OFFSET+1
 rts
field_offsets: .word GPR_CHARS,GPR_STYLES,GPR_ROLES,GPR_X

scan_counts:
 lda LM_RECORD
 cmp LM_ROWS
 beq @done
 jsr se_gp_cache_slot
 lda #<LM_BUFFER
 sta GP_IO_POINTER
 lda #>LM_BUFFER
 sta GP_IO_POINTER+1
 lda #32
 sta GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 jsr se_gp_cache_read
 jcs fail
 lda LM_BUFFER+GPR_COUNT+1
 jne corrupt
 lda LM_BUFFER+GPR_COUNT
 cmp #162
 jcs corrupt
 ldx LM_RECORD
 sta LM_META+LMM_COUNTS,x
 inc LM_RECORD
 jmp pending
@done:
 jsr reset
 lda #1
 sta LM_PHASE
 jmp pending
packet_shape:
 lda LM_PACKED
 beq @good
 lda LM_BUFFER+GPR_COUNT+1
 bne @bad
 lda LM_BUFFER+GPR_COUNT
 cmp LM_N
 bne @bad
@good:
 clc
 rts
@bad:
 lda #$94
 sec
 rts

valid_write:
 lda #$80
 sta GP_IO_OFFSET
 lda #6
 sta GP_IO_OFFSET+1
 lda #<LM_META
 sta GP_IO_POINTER
 lda #>LM_META
 sta GP_IO_POINTER+1
 bne one
primary_valid:
 lda #0
 sta GP_IO_OFFSET
 sta GP_IO_OFFSET+1
 lda #<GP_RECORD
 sta GP_IO_POINTER
 lda #>GP_RECORD
 sta GP_IO_POINTER+1
one:
 lda #1
 sta GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 jmp se_gp_cache_write

crc_data:
 lda LM_CRC
 sta se_crc_value
 lda LM_CRC+1
 sta se_crc_value+1
 jsr crc_chunk
 lda se_crc_value
 sta LM_CRC
 lda se_crc_value+1
 sta LM_CRC+1
crc_record:
 lda LM_RCRC
 sta se_crc_value
 lda LM_RCRC+1
 sta se_crc_value+1
 jsr crc_chunk
 lda se_crc_value
 sta LM_RCRC
 lda se_crc_value+1
 sta LM_RCRC+1
 rts
crc_chunk:
 lda GP_IO_POINTER
 sta text_ptr
 lda GP_IO_POINTER+1
 sta text_ptr+1
 ldy #0
@byte:
 lda (text_ptr),y
 jsr se_crc_byte
 iny
 cpy LM_COUNT
 bne @byte
 rts
native_crc:
 jsr se_crc_init
 lda #<$4800
 sta text_ptr
 lda #>$4800
 sta text_ptr+1
 lda #4
 sta LM_STATE+38
 ldy #0
@byte:
 lda (text_ptr),y
 jsr se_crc_byte
 iny
 bne @byte
 inc text_ptr+1
 dec LM_STATE+38
 bne @byte
 rts
native_check:
 jsr native_crc
 lda se_crc_value
 cmp LM_META+LMM_FONT
 bne @bad
 lda se_crc_value+1
 cmp LM_META+LMM_FONT+1
 bne @bad
 clc
 rts
@bad:
 lda #$94
 sec
 rts
meta_crc:
 jsr se_crc_init
 lda #<(LM_META+1)
 sta text_ptr
 lda #>(LM_META+1)
 sta text_ptr+1
 ldy #0
@first:
 lda (text_ptr),y
 jsr se_crc_byte
 iny
 cpy #7
 bne @first
 lda #<(LM_META+10)
 sta text_ptr
 lda #>(LM_META+10)
 sta text_ptr+1
 ldy #0
@page:
 lda (text_ptr),y
 jsr se_crc_byte
 iny
 bne @page
 inc text_ptr+1
@tail:
 lda (text_ptr),y
 jsr se_crc_byte
 iny
 cpy #54
 bne @tail
 rts

; Context is observed from actual checked live GP/source state, not a host key.
capture_context:
 ldx #63
@settings:
 lda se_editor_settings,x
 sta LM_META+LMM_SETTINGS,x
 dex
 bpl @settings
 lda se_render_caps
 sta LM_META+LMM_CAP
 lda se_l_mode
 sta LM_META+LMM_WRAP
 lda se_mode
 sta LM_META+LMM_MODE
 lda se_r_presentation
 sta LM_META+LMM_PRESENT
 ldx #12
@auth:
 lda se_bc_arena,x
 sta LM_META+LMM_AUTH,x
 dex
 bpl @auth
 lda se_bc_flags
 and #15 ;ARMED/LOST/MUTATING/ACTIVE remain stable at every boundary
 sta LM_META+LMM_FLAGS
 lda se_bc_count
 sta LM_META+LMM_QUEUE
 ldx #4
@fold:
 lda se_ef_token,x
 sta LM_META+LMM_FTOKEN,x
 dex
 bpl @fold
 ldx #1
@count:
 lda se_ef_count,x
 sta LM_META+LMM_FCOUNT,x
 lda se_ef_generation,x
 sta LM_META+LMM_FGEN,x
 lda se_gc_epoch,x
 sta LM_META+LMM_EPOCH,x
 dex
 bpl @count
 jsr se_ef_visible
 sta LM_META+LMM_FVIS
 lda se_gc_handle
 sta LM_META+LMM_HANDLE
 tax
 lda se_reu_map,x
 sta LM_META+LMM_PHYSICAL
 jsr raster_cap
 bcs @return
 lda image_crc_lo,x
 sta LM_META+LMM_R21_CRC
 lda image_crc_hi,x
 sta LM_META+LMM_R21_CRC+1
 lda image_size_lo,x
 sta LM_META+LMM_R21_SIZE
 lda image_size_hi,x
 sta LM_META+LMM_R21_SIZE+1
@return:
 rts
context:
 jsr fold_guard
 jcs @return
 lda LM_MODE
 bne @source
 ldx #2
@capture_top:
 lda GP_HEADER+GPH_TOP,x
 cmp LM_META+LMM_HEADER+GPH_TOP,x
 jne stale
 dex
 bpl @capture_top
 lda GP_HEADER+GPH_COUNT
 cmp LM_ROWS
 jne stale
@source:
 lda se_mode
 cmp #3
 jne stale
 lda se_r_presentation
 jne stale
 lda $912C
 ora $912D
 jne stale
 ldx #27
@key:
 lda GP_HEADER+GPH_KEY,x
 cmp LM_META+LMM_HEADER+GPH_KEY,x
 jne stale
 dex
 bpl @key
 ldx #2
@pan:
 lda se_l_pan,x
 cmp LM_META+LMM_HEADER+GPH_PAN,x
 jne stale
 dex
 bpl @pan
 ldx #63
@settings:
 lda se_editor_settings,x
 cmp LM_META+LMM_SETTINGS,x
 jne stale
 dex
 bpl @settings
 lda se_render_caps
 cmp LM_META+LMM_CAP
 jne stale
 lda se_l_mode
 cmp LM_META+LMM_WRAP
 jne stale
 ldx #12
@auth:
 lda se_bc_arena,x
 cmp LM_META+LMM_AUTH,x
 jne stale
 dex
 bpl @auth
 lda se_bc_flags
 and #15 ;ARMED/LOST/MUTATING/ACTIVE remain stable at every boundary
 cmp LM_META+LMM_FLAGS
 jne stale
 lda se_bc_count
 cmp LM_META+LMM_QUEUE
 jne stale
 ldx #4
@fold:
 lda se_ef_token,x
 cmp LM_META+LMM_FTOKEN,x
 jne stale
 dex
 bpl @fold
 ldx #1
@count:
 lda se_ef_count,x
 cmp LM_META+LMM_FCOUNT,x
 jne stale
 lda se_ef_generation,x
 cmp LM_META+LMM_FGEN,x
 jne stale
 lda se_gc_epoch,x
 cmp LM_META+LMM_EPOCH,x
 jne stale
 dex
 bpl @count
 jsr se_ef_visible
 cmp LM_META+LMM_FVIS
 jne stale
 lda se_gc_handle
 cmp LM_META+LMM_HANDLE
 jne stale
 tax
 lda se_reu_map,x
 cmp LM_META+LMM_PHYSICAL
 jne stale
 jsr raster_cap
 bcs @return
 lda image_crc_lo,x
 cmp LM_META+LMM_R21_CRC
 bne stale
 lda image_crc_hi,x
 cmp LM_META+LMM_R21_CRC+1
 bne stale
 lda image_size_lo,x
 cmp LM_META+LMM_R21_SIZE
 bne stale
 lda image_size_hi,x
 cmp LM_META+LMM_R21_SIZE+1
 bne stale
 clc
@return:
 rts
raster_cap:
 ldx #0
@slot:
 lda se_overlay_ids,x
 cmp #21
 bne @next
 lda image_slot,x
 and #$7F
 beq raster_found
@next:
 inx
 cpx #<se_overlay_capacity
 bne @slot
stale:
 lda #$74
 sec
 rts
raster_found:
 clc
 rts

begin_ready:
 lda LM_PHASE
 ora LM_ACTIVE
 jne busy
 lda $912C
 ora $912D
 ora se_fs_active
 ora se_fs_owned
 jne busy
 lda se_bc_flags
 and #(BC_ACTIVE|BC_MUTATING)
 jne busy
 clc
 rts
forget:
 lda #0
 sta LM_PHASE
 sta LM_ACTIVE
 sta se_fs_active
 sta se_fs_owned
 rts

; Caller must invoke on freshFEallocation/cold/resume before permitting a hit.
; Session capability tuples must not be assumed unique across a cleared coldBSS.
se_lm_revoke:
 jsr owner
 jcs return
 jsr begin_ready
 jcs return
 jsr se_gp_cache_guard
 jcs return
 lda #0
 sta LM_META
 jmp valid_write

; Published fold records are immutable within their exact token/generation.
; Authenticate the full typed46 capability and count*32 logical extent; a
; numeric token alone is not a provider ownership proof. Plain never reads it.
fold_guard:
 jsr se_ef_visible
 beq @zero
 jsr se_ef_key_match
 bcs @return
 ldx #4
@token:
 lda se_ef_token,x
 sta se_object_id,x
 dex
 bpl @token
 jsr se_object_validate
 bcs @return
 lda object_owner,x
 cmp #$46
 bne @bad
 lda se_ef_count+1
 cmp #$80
 bcc @length
 bne @bad
 lda se_ef_count
 bne @bad
@length:
 lda se_ef_count
 sta LM_STATE+40
 lda se_ef_count+1
 sta LM_STATE+41
 lda #0
 sta LM_STATE+42
 ldy #5
@shift:
 asl LM_STATE+40
 rol LM_STATE+41
 rol LM_STATE+42
 dey
 bne @shift
 lda object_size_hi,x
 cmp LM_STATE+42
 bcc @bad
 bne @zero
 lda object_size_mid,x
 cmp LM_STATE+41
 bcc @bad
 bne @zero
 lda object_size_lo,x
 cmp LM_STATE+40
 bcc @bad
@zero:
 lda #0
 clc
@return:
 rts
@bad:
 lda #$94
 sec
 rts
