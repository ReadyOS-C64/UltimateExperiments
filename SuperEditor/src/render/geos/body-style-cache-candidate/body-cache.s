; Owner4-only actual-C26result retention, synchronous bounded416B transfers.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/geos/body-cache.inc"
.include "render/geos/source-line.inc"
.include "render/geos/semantic.inc"
.include "render/geos/inline.inc"
.include "render/geos/source-certificate.inc"
.include "fold/source.inc"
.import se_overlay_ids,image_slot,image_size_lo,image_size_hi,image_crc_lo,image_crc_hi,se_overlay_capacity
.import se_f_owner,se_gc_handle,se_gc_epoch,se_gc_width,se_r_presentation
.import se_reu_retired,se_reu_map,se_reu_logical_owner,se_reu_physical_owner
.import se_reu_copy,se_reu_c64,se_reu_length,se_reu_offset,se_reu_logical
.import se_crc_init,se_crc_byte,se_crc_value,se_doc_invalidate
.export se_bsc_entry
L=GEOS_LINE_FRAME
.segment "CODE"
se_bsc_entry:
    lda se_f_owner
    cmp #4
    jne busy
    lda se_overlay_frame
    cmp #BSC_LOOKUP
    jcc bad
    cmp #BSC_CANCEL+1
    jcs bad
    sta BW_OP
    cmp #BSC_CANCEL
    jeq cancel
    jsr source
    jcs return
    lda BW_OP
    cmp #BSC_COUNT
    jeq count
    jsr cap
    jcs miss
    jsr producer
    jcs miss
    stx BW_ERROR ;catalog index, transient within this synchronous call
    lda BW_OP
    cmp #BSC_STORE
    jeq store
lookup:
    lda #1
    jsr transfer
    jcs return
    lda BSC_BUFFER+BSC_VALID
    cmp #1
    jne miss
    lda BSC_BUFFER+BSC_VERSION
    cmp #1
    jne miss
    lda BSC_BUFFER+BSC_MAGIC
    cmp #$BC
    jne miss
    lda BSC_BUFFER+BSC_COUNT_AT
    jeq miss
    cmp #161
    jcs miss
    sta BW_COUNT
    ldx #58
@key:
    lda GS_FS+27,x
    cmp BSC_BUFFER+BSC_KEY,x
    jne miss
    dex
    bpl @key
    ldx #9
@context:
    lda GSEM_FRAME+GSEM_START,x
    cmp BSC_BUFFER+BSC_CONTEXT,x
    jne miss
    dex
    bpl @context
    lda se_gc_handle
    cmp BSC_BUFFER+BSC_CAP
    jne miss
    tax
    lda se_reu_map,x
    cmp BSC_BUFFER+BSC_CAP+1
    jne miss
    ldx #1
@epoch:
    lda se_gc_epoch,x
    cmp BSC_BUFFER+BSC_CAP+2,x
    jne miss
    lda BSC_BUFFER+BSC_CRC,x
    sta BW_CRC,x
    dex
    bpl @epoch
    ldx BW_ERROR
    lda image_size_lo,x
    cmp BSC_BUFFER+BSC_PRODUCER
    jne miss
    lda image_size_hi,x
    cmp BSC_BUFFER+BSC_PRODUCER+1
    jne miss
    lda image_crc_lo,x
    cmp BSC_BUFFER+BSC_PRODUCER+2
    jne miss
    lda image_crc_hi,x
    cmp BSC_BUFFER+BSC_PRODUCER+3
    jne miss
    jsr crc
    ldx #1
@crc:
    lda se_crc_value,x
    cmp BW_CRC,x
    jne miss
    dex
    bpl @crc
    sec
    ldx #0
    ldy #3
@offset:
    lda L+GL_SCAN,x
    sbc BSC_BUFFER+BSC_START,x
    sta SC_TEMP,x
    inx
    dey
    bne @offset
    jcc miss
    lda SC_TEMP+1
    ora SC_TEMP+2
    jne miss
    lda SC_TEMP
    cmp BW_COUNT
    jcs miss
    sta BW_OFFSET
    clc
    adc L+GL_PACKET_COUNT
    bcs @last
    cmp BW_COUNT
    bcc @hit
    beq @hit
@last:
    jsr record_end
    jcs miss
    ldx #2
@logical_end:
    lda SC_TEMP,x
    cmp GSEM_FRAME+GSEM_END,x
    jne miss
    dex
    bpl @logical_end
@hit:
    lda BW_COUNT
    sta SW_COUNT
    ldx #2
@start:
    lda BSC_BUFFER+BSC_START,x
    sta SW_START,x
    dex
    bpl @start
    ldx #0
@outputs:
    lda BSC_BUFFER+BSC_STYLES,x
    cmp #4
    jcs miss
    lda BSC_BUFFER+BSC_ROLES,x
    cmp #14
    jcs miss
    inx
    cpx BW_COUNT
    bcc @outputs
    ldx #0
@restore:
    lda BSC_BUFFER+BSC_STYLES,x
    sta GI_OUTPUT_STYLES,x
    lda BSC_BUFFER+BSC_ROLES,x
    sta GI_OUTPUT_ROLES,x
    inx
    cpx BW_COUNT
    bcc @restore
    lda BW_OFFSET
    sta SW_OFFSET
    lda #1
    sta SW_VALID
    ldx #0
    ldy BW_OFFSET
@packet:
    cpy BW_COUNT
    bcs @base
    lda GI_OUTPUT_STYLES,y
    sta GS_STYLES,x
    lda GI_OUTPUT_ROLES,y
    jmp @role
@base:
    lda #0
    sta GS_STYLES,x
    lda GSEM_FRAME+GSEM_ROLE
@role:
    sta SW_ROLES,x
    iny
    inx
    cpx L+GL_PACKET_COUNT
    bcc @packet
    jmp zero
store:
    lda SW_COUNT
    jeq miss
    cmp #161
    jcs bad
    sta BW_COUNT
    jsr se_doc_invalidate
    lda #0
    ldx #0
@clear_page:
    sta BSC_BUFFER,x
    inx
    bne @clear_page
    ldx #159
@clear_tail:
    sta BSC_BUFFER+256,x
    dex
    bpl @clear_tail
    lda #1
    sta BSC_BUFFER+BSC_VERSION
    lda #$BC
    sta BSC_BUFFER+BSC_MAGIC
    lda BW_COUNT
    sta BSC_BUFFER+BSC_COUNT_AT
    ldx #58
@key:
    lda GS_FS+27,x
    sta BSC_BUFFER+BSC_KEY,x
    dex
    bpl @key
    ldx #9
@context:
    lda GSEM_FRAME+GSEM_START,x
    sta BSC_BUFFER+BSC_CONTEXT,x
    dex
    bpl @context
    ldx #2
@start:
    lda SW_START,x
    sta BSC_BUFFER+BSC_START,x
    dex
    bpl @start
    jsr record_end
    jcs bad
    ldx #2
@within:
    lda GSEM_FRAME+GSEM_END,x
    cmp SC_TEMP,x
    jcc bad
    bne @bounds_ok
    dex
    bpl @within
@bounds_ok:
    lda se_gc_handle
    sta BSC_BUFFER+BSC_CAP
    tax
    lda se_reu_map,x
    sta BSC_BUFFER+BSC_CAP+1
    ldx #1
@epoch:
    lda se_gc_epoch,x
    sta BSC_BUFFER+BSC_CAP+2,x
    dex
    bpl @epoch
    ldx BW_ERROR
    lda image_size_lo,x
    sta BSC_BUFFER+BSC_PRODUCER
    lda image_size_hi,x
    sta BSC_BUFFER+BSC_PRODUCER+1
    lda image_crc_lo,x
    sta BSC_BUFFER+BSC_PRODUCER+2
    lda image_crc_hi,x
    sta BSC_BUFFER+BSC_PRODUCER+3
    ldx #0
@outputs:
    lda GI_OUTPUT_STYLES,x
    cmp #4
    jcs bad
    sta BSC_BUFFER+BSC_STYLES,x
    lda GI_OUTPUT_ROLES,x
    cmp #14
    jcs bad
    sta BSC_BUFFER+BSC_ROLES,x
    inx
    cpx BW_COUNT
    bcc @outputs
    jsr crc
    ldx #1
@save_crc:
    lda se_crc_value,x
    sta BSC_BUFFER+BSC_CRC,x
    dex
    bpl @save_crc
    ; Revoke previousrecord before any partial bulk publication.
    jsr request
    jcs return
    lda #1
    sta se_reu_length
    lda #0
    sta se_reu_length+1
    jsr se_reu_copy
    jcs return
    lda #0
    jsr transfer
    jcs return
    jsr source ;recheck after bulkwrite, before VALID-last publication
    jcs return
    ; VALID-last: all actualbytes +completekey/CRC alreadystored.
    lda #1
    sta BSC_BUFFER
    jsr request
    jcs return
    lda #1
    sta se_reu_length
    lda #0
    sta se_reu_length+1
    jmp se_reu_copy
cancel:
    jsr cap
    jcs zero
    jsr se_doc_invalidate
    lda #0
    sta BSC_BUFFER
    jsr request
    jcs return
    lda #1
    sta se_reu_length
    lda #0
    sta se_reu_length+1
    jmp se_reu_copy
record_end:
    clc
    lda BSC_BUFFER+BSC_START
    adc BW_COUNT
    sta SC_TEMP
    lda BSC_BUFFER+BSC_START+1
    adc #0
    sta SC_TEMP+1
    lda BSC_BUFFER+BSC_START+2
    adc #0
    sta SC_TEMP+2
    rts
count:
    sec
    ldx #0
    ldy #3
@distance:
    lda GSEM_FRAME+GSEM_END,x
    sbc L+GL_SCAN,x
    sta SC_TEMP,x
    inx
    dey
    bne @distance
    bcc @zero
    lda SC_TEMP+1
    ora SC_TEMP+2
    bne @max
    lda SC_TEMP
    cmp #160
    bcc @ready
@max:
    lda #160
    bne @ready
@zero:
    lda #0
@ready:
    sta SW_COUNT
    clc
    rts
.macro CHECK source,offset,n
    ldx #n-1
:   lda source,x
    cmp GS_FS+27+offset,x
    jne changed
    dex
    bpl :-
.endmacro
source:
    lda GS_ACTIVE
    cmp #1
    jne changed
    lda GS_CONTEXT_VALID
    cmp #1
    jne changed
    lda GS_FS+7
    and GS_FS+8
    cmp #1
    jne changed
    lda se_r_presentation
    jne changed
    jsr se_doc_validate
    jcs return
    FS_FIELDS CHECK
    lda se_doc_busy
    ora se_hot_phase
    ora se_hot_owned
    ora se_h_phase
    ora se_b_phase
    ora se_clip_busy
    ora se_snapshot_busy
    jne changed
    DOC_TOKEN se_doc_meta
    jsr se_object_validate
    jcs return
    DOC_TOKEN se_doc_original
    jsr se_object_validate
    jcs return
    DOC_TOKEN se_doc_append
    jmp se_object_validate
producer:
    ldx #0
@find:
    lda se_overlay_ids,x
    cmp #26
    bne @next
    lda image_slot,x
    and #1 ;managed bit7 isverification metadata, not slot identity
    cmp #1
    beq @found
@next:
    inx
    cpx #<se_overlay_capacity
    bcc @find
    sec
    rts
@found:
    clc
    rts
cap:
    lda se_reu_retired
    bne @miss
    lda se_gc_epoch
    cmp se_reu_epoch
    bne @miss
    lda se_gc_epoch+1
    cmp se_reu_epoch+1
    bne @miss
    lda se_gc_epoch
    ora se_gc_epoch+1
    beq @miss
    ldx se_gc_handle
    beq @miss
    lda se_reu_logical_owner,x
    cmp #$FE
    bne @miss
    ldy se_reu_map,x
    beq @miss
    lda se_reu_physical_owner,y
    cmp #$FE
    bne @miss
    clc
    rts
@miss:
    sec
    rts
transfer:
    pha
    jsr request
    bcc :+
    tax
    pla
    txa
    sec
    rts
:   jsr se_doc_invalidate
    pla
    jmp se_reu_copy
request:
    jsr cap
    jcs stale
    lda se_gc_handle
    sta se_reu_logical
    lda #>BSC_REU
    sta se_reu_offset+1
    lda #<BSC_REU
    sta se_reu_offset
    lda #<BSC_BUFFER
    sta se_reu_c64
    lda #>BSC_BUFFER
    sta se_reu_c64+1
    lda #<BSC_SIZE
    sta se_reu_length
    lda #>BSC_SIZE
    sta se_reu_length+1
    clc
    rts
crc:
    jsr se_crc_init
    ldy #1
@first:
    cpy #BSC_CRC
    beq @skip
    cpy #BSC_CRC+1
    beq @skip
    lda BSC_BUFFER,y
    jsr se_crc_byte
@skip:
    iny
    bne @first
    ldy #0
@second:
    lda BSC_BUFFER+256,y
    jsr se_crc_byte
    iny
    cpy #160
    bcc @second
    rts
miss:
    lda #2
    clc
return:
    rts
zero:
    lda #0
    clc
    rts
busy:
    lda #$B2
    sec
    rts
bad:
    lda #$90
    sec
    rts
changed:
    lda #$B1
    sec
    rts

stale:
    lda #$18
    sec
    rts
