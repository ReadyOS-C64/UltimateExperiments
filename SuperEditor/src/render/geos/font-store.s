; Runtime rawfont fetch, logicalFD ownership and trusted faceCRC publication.
.setcpu "6502"
.macpack longbranch
.include "render/geos/font-store.inc"
.include "geos-font-pack.inc"
.import se_reu_epoch,se_reu_logical_owner,se_reu_physical_owner,se_reu_map
.import se_reu_copy,se_reu_logical,se_reu_offset,se_reu_length,se_reu_c64
.import se_overlay_loads,se_crc_init,se_crc_byte,se_crc_value
.importzp text_ptr,screen_ptr
.export se_gf_fetch,se_gf_font_pointer
.ifdef SE_GEOS_PREVIEW_FAST
.import se_f_owner
.export se_gf_fetch_preview
.else
.export se_gf_fetch_preview
se_gf_fetch_preview=se_gf_fetch
.endif
se_gf_font_pointer=GF_BUFFER
S=se_gf_state
.segment "CODE"
se_gf_fetch:
    lda S+GF_VALID
    sta S+GF_TEMP+8
    lda #0
    sta S+GF_VALID
    jsr guard
    jcs fail
    ldx #GF_FACE_COUNT-1
@find:
    lda gf_origins,x
    cmp S+GF_ORIGIN
    bne @next
    lda gf_family_lo,x
    cmp S+GF_FAMILY
    bne @next
    lda gf_family_hi,x
    cmp S+GF_FAMILY+1
    bne @next
    lda gf_points,x
    cmp S+GF_POINT
    beq @found
@next:
    dex
    bpl @find
    lda #GF_NOT_FOUND
    jmp fail
@found:
    cpx S+GF_FACE
    bne @new
    lda S+GF_TEMP+8
    beq @new
    lda S+GF_LOADS
    cmp se_overlay_loads
    bne @new
    lda S+GF_LOADS+1
    cmp se_overlay_loads+1
    jeq verify ;CRC remains mandatory on a loadtag hit
@new:
    stx S+GF_FACE
    txa
    lsr
    lsr
    lsr
    lsr
    sta S+GF_OFFSET+1
    txa
    asl
    asl
    asl
    asl
    clc
    adc #32
    sta S+GF_OFFSET
    bcc :+
    inc S+GF_OFFSET+1
:
    lda #0
    sta S+GF_OFFSET+2
    sta S+GF_IO_LENGTH+1
    sta S+GF_DONE
    lda #>GF_BUFFER
    sta S+GF_DONE+1
    lda #16
    sta S+GF_IO_LENGTH
    jsr read
    jcs fail
    ldx #15
@entry:
    lda GF_BUFFER,x
    sta S+GF_ENTRY,x
    dex
    bpl @entry
    ldx #3
@identity:
    lda S+GF_ENTRY,x
    cmp S+GF_ORIGIN,x
    jne format
    dex
    bpl @identity
    ldx #2
@offset:
    lda S+GF_ENTRY+8,x
    sta S+GF_OFFSET,x
    sta S+GF_POSITION,x
    dex
    bpl @offset
    lda S+GF_ENTRY+11
    sta S+GF_LENGTH
    sta S+GF_IO_LENGTH
    lda S+GF_ENTRY+12
    sta S+GF_LENGTH+1
    sta S+GF_IO_LENGTH+1
    jsr length_guard
    jcs fail
@bounds:
    lda S+GF_OFFSET+2
    cmp #2
    jcs format
    bne @end
    lda S+GF_OFFSET+1
    cmp #>GF_INDEX_END
    jcc format
    bne @end
    lda S+GF_OFFSET
    cmp #<GF_INDEX_END
    jcc format
@end:
    clc
    lda S+GF_OFFSET
    adc S+GF_LENGTH
    sta S+GF_TEMP
    lda S+GF_OFFSET+1
    adc S+GF_LENGTH+1
    sta S+GF_TEMP+1
    lda S+GF_OFFSET+2
    adc #0
    cmp #^GF_PACK_BYTES
    bcc @copy
    jne format
    lda S+GF_TEMP+1
    cmp #>GF_PACK_BYTES
    bcc @copy
    jne format
    lda S+GF_TEMP
    cmp #<GF_PACK_BYTES
    bcc @copy
    jne format
@copy:
    lda #0
    sta S+GF_DONE
    lda #>GF_BUFFER
    sta S+GF_DONE+1
    jsr read
    jcs fail
verify:
    jsr length_guard
    jcs fail
    lda #<GF_BUFFER
    sta text_ptr
    lda #>GF_BUFFER
    sta text_ptr+1
    lda S+GF_LENGTH
    sta S+GF_TEMP
    lda S+GF_LENGTH+1
    sta S+GF_TEMP+1
    jsr se_crc_init
    ldy #0
@crc:
    lda (text_ptr),y
    jsr se_crc_byte
    inc text_ptr
    bne :+
    inc text_ptr+1
:
    lda S+GF_TEMP
    bne :+
    dec S+GF_TEMP+1
:
    dec S+GF_TEMP
    lda S+GF_TEMP
    ora S+GF_TEMP+1
    bne @crc
    ldx S+GF_FACE
    lda gf_crc_lo,x
    cmp se_crc_value
    bne format
    lda gf_crc_hi,x
    cmp se_crc_value+1
    bne format
publish_metrics:
    lda gf_face_info,x
    pha
    and #$7F
    sta S+GF_MAX_WIDTH
    pla
    and #$80
    sta S+GF_MONO
    lda GF_BUFFER
    sta S+GF_BASELINE
    lda GF_BUFFER+3
    sta S+GF_HEIGHT
    lda GF_BUFFER+1
    sta S+GF_STRIDE
    lda GF_BUFFER+2
    sta S+GF_STRIDE+1
    lda GF_BUFFER+6
    sec
    sbc #8
    lsr
    sec
    sbc #1
    sta S+GF_GLYPHS
    lda #32
    sta S+GF_FIRST
    lda se_overlay_loads
    sta S+GF_LOADS
    lda se_overlay_loads+1
    sta S+GF_LOADS+1
    lda #1
    sta S+GF_VALID
    lda #0
    sta S+GF_ERROR
    clc
    rts
length_guard:
    lda S+GF_LENGTH+1
    cmp #>GF_MAX_FONT
    bcc @minimum
    bne @bad
    lda S+GF_LENGTH
    cmp #<GF_MAX_FONT
    bcc @minimum
    bne @bad
@minimum:
    lda S+GF_LENGTH+1
    bne @ok
    lda S+GF_LENGTH
    cmp #10
    bcc @bad
@ok:
    clc
    rts
@bad:
    lda #GF_FORMAT
    sec
    rts
format:
    lda #GF_FORMAT
fail:
    sta S+GF_ERROR
    sec
    rts
guard:
    lda S+GF_READY
    cmp #GF_READY_VALUE
    bne stale
    lda S+GF_BUSY
    bne busy
    ldx #1
@epoch:
    lda S+GF_EPOCH,x
    cmp se_reu_epoch,x
    bne stale
    dex
    bpl @epoch
    ldx #1
@bank:
    lda S+GF_HANDLE0,x
    beq stale
    tay
    lda se_reu_logical_owner,y
    cmp #GF_OWNER
    bne stale
    lda se_reu_map,y
    tay
    lda se_reu_physical_owner,y
    cmp #GF_OWNER
    bne stale
    dex
    bpl @bank
    clc
    rts
stale:
    lda #GF_STALE
    sec
    rts
busy:
    lda #GF_BUSY_ERROR
    sec
    rts
; IO is page-bounded, consequently also logical64KiB-bank bounded. Offset and
; destination advance only after successful checkedDMA. NoCA host transfers.
read:
    lda S+GF_IO_LENGTH
    ora S+GF_IO_LENGTH+1
    bne @page
    clc
    rts
@page:
    lda S+GF_OFFSET+2
    cmp #2
    jcs @bad
    tax
    lda S+GF_HANDLE0,x
    sta se_reu_logical
    lda S+GF_OFFSET
    sta se_reu_offset
    lda S+GF_OFFSET+1
    sta se_reu_offset+1
    lda S+GF_DONE
    sta se_reu_c64
    lda S+GF_DONE+1
    sta se_reu_c64+1
    lda #0
    sta se_reu_length+1
    sec
    sbc S+GF_OFFSET
    sta se_reu_length
    bne :+
    inc se_reu_length+1
:
    lda S+GF_IO_LENGTH+1
    bne @copy
    lda se_reu_length+1
    bne @short
    lda S+GF_IO_LENGTH
    cmp se_reu_length
    bcs @copy
@short:
    lda S+GF_IO_LENGTH
    sta se_reu_length
    lda #0
    sta se_reu_length+1
@copy:
    lda #1
    jsr se_reu_copy
    bcs @done
    sec
    lda S+GF_IO_LENGTH
    sbc se_reu_length
    sta S+GF_IO_LENGTH
    lda S+GF_IO_LENGTH+1
    sbc se_reu_length+1
    sta S+GF_IO_LENGTH+1
    clc
    lda S+GF_OFFSET
    adc se_reu_length
    sta S+GF_OFFSET
    lda S+GF_OFFSET+1
    adc se_reu_length+1
    sta S+GF_OFFSET+1
    bcc :+
    inc S+GF_OFFSET+2
:
    clc
    lda S+GF_DONE
    adc se_reu_length
    sta S+GF_DONE
    lda S+GF_DONE+1
    adc se_reu_length+1
    sta S+GF_DONE+1
    lda S+GF_IO_LENGTH
    ora S+GF_IO_LENGTH+1
    jne @page
    clc
@done:
    rts
@bad:
    lda #GF_FORMAT
    sec
    rts
.segment "RODATA"
GF_RUNTIME_METADATA

.segment "CODE"
.ifdef SE_GEOS_PREVIEW_FAST
; This entry is only for the preview-owned working window. The independent
; public FETCH above deliberately retains its complete CRC-on-every-hit ABI.
se_gf_fetch_preview:
    lda se_f_owner
    cmp #4
    beq @owned
    lda #$B2
    sec
    rts ;foreign owner is opaque, including FONT_STORE_STATE
@owned:
    lda S+GF_VALID
    cmp #GF_PREVIEW_VALID
    jne @refill
    jsr guard
    bcc @guarded
    ; Authentication failure closes this preview window lifetime. Keep the
    ; original error while preventing repaired capabilities reviving a hit.
    pha
    lda #0
    sta S+GF_VALID
    pla
    jmp fail
@guarded:
    ldx S+GF_FACE
    cpx #GF_FACE_COUNT
    jcs @refill
    cpx S+GF_FAST_FACE
    jne @refill
    lda gf_origins,x
    cmp S+GF_ORIGIN
    jne @refill
    lda gf_family_lo,x
    cmp S+GF_FAMILY
    jne @refill
    lda gf_family_hi,x
    cmp S+GF_FAMILY+1
    jne @refill
    lda gf_points,x
    cmp S+GF_POINT
    jne @refill
    ldx #1
@capabilities:
    lda S+GF_HANDLE0,x
    cmp S+GF_FAST_HANDLES,x
    jne @refill
    tay
    lda se_reu_map,y
    cmp S+GF_FAST_MAP,x
    jne @refill
    lda S+GF_EPOCH,x
    cmp S+GF_FAST_EPOCH,x
    jne @refill
    lda S+GF_LENGTH,x
    cmp S+GF_FAST_LENGTH,x
    jne @refill
    ; Verified direct overlay loads leave5000 intact. The sticky window fence
    ; plus these full capabilities, face and length define preview lifetime.
    dex
    bpl @capabilities
    ldx S+GF_FACE
    jsr publish_metrics
    jmp @arm
@refill:
    ; An unauthenticated descriptor/window cannot take even the strict
    ; no-DMA cachehit: force a trustedFD refill before fullCRC validation.
    lda #0
    sta S+GF_VALID
    jsr se_gf_fetch
    bcs @return
@arm:
    ldx #1
@save:
    lda S+GF_HANDLE0,x
    sta S+GF_FAST_HANDLES,x
    tay
    lda se_reu_map,y
    sta S+GF_FAST_MAP,x
    lda S+GF_EPOCH,x
    sta S+GF_FAST_EPOCH,x
    lda S+GF_LENGTH,x
    sta S+GF_FAST_LENGTH,x
    dex
    bpl @save
    lda S+GF_FACE
    sta S+GF_FAST_FACE
    lda #GF_PREVIEW_VALID
    sta S+GF_VALID
    lda #0
    clc
@return:
    rts
.endif
