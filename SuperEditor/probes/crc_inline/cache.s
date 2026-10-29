; Private measured candidate; production source unchanged.
.setcpu "6502"
.macpack longbranch
.include "overlay/format.inc"
.import se_overlay_header, se_overlay_validate, se_overlay_binding_digest
.import se_crc_init, se_crc_byte, se_crc_value
.ifdef FAST_EDITOR_CRC
.import se_crc_table_low,se_crc_table_high
.export se_overlay_crc_page_byte,se_overlay_crc_tail_byte
.macro CACHE_CRC_BYTE
.ifdef EDITOR_HALF_CRC
    jsr se_crc_byte
.else
    eor se_crc_value+1
    tax
    lda se_crc_value
    eor se_crc_table_high,x
    sta se_crc_value+1
    lda se_crc_table_low,x
    sta se_crc_value
.endif
.endmacro
.endif
.import se_reu_alloc, se_reu_epoch, se_reu_logical_owner
.import se_reu_copy, se_reu_c64, se_reu_offset, se_reu_length, se_reu_logical
.export se_overlay_init, se_overlay_import, se_overlay_call
.export se_overlay_asset, se_overlay_active, se_overlay_busy, se_overlay_frame
.export se_overlay_loads, se_overlay_hits, se_overlay_calls, se_overlay_ids
.export se_overlay_capacity, se_overlay_fixed_entry
se_overlay_capacity = OVL_LIMIT
se_overlay_fixed_entry = EDITOR_FIXED_ENTRY
.segment "ZEROPAGE"
ovl_ptr: .res 2
.segment "BSS"
se_overlay_asset: .res 1
asset_epoch: .res 2
.if EDITOR_CATALOG_TAIL
.export se_overlay_asset_second
se_overlay_asset_second: .res 1 ;lazy, same owner/epoch as the first asset bank
.segment "OVERLAY_CATALOG"
.endif
se_overlay_ids: .res OVL_LIMIT ; zero invalid; published last
image_slot: .res OVL_LIMIT
image_size_lo: .res OVL_LIMIT
image_size_hi: .res OVL_LIMIT
.if !EDITOR_FIXED_ENTRY
image_entry_lo: .res OVL_LIMIT
image_entry_hi: .res OVL_LIMIT
.endif
image_crc_lo: .res OVL_LIMIT
image_crc_hi: .res OVL_LIMIT
.if EDITOR_CATALOG_TAIL
.segment "BSS"
.endif
se_overlay_active: .res 2 ; index+1; zero invalid
se_overlay_busy: .res 2
se_overlay_frame: .res 16 ; resident command parameters/results; no overlay ptrs
se_overlay_loads: .res 2
se_overlay_hits: .res 2
se_overlay_calls: .res 2
candidate: .res 1
call_slot: .res 1
call_id: .res 1
call_result: .res 1
crc_remaining: .res 2
.segment "CODE"
; Once per provider epoch, after se_reu_provider_init. Does not clear REU.
; Reinitialization in the same epoch is refused to prevent allocation leaks.
se_overlay_init:
    lda se_overlay_asset
    beq @allocate
    lda asset_epoch
    cmp se_reu_epoch
    bne @allocate
    lda asset_epoch+1
    cmp se_reu_epoch+1
.if EDITOR_CATALOG_TAIL
    beq stale
.else
    jeq stale
.endif
@allocate:
    lda #0
    sta se_overlay_asset
.if EDITOR_CATALOG_TAIL
    sta se_overlay_asset_second
.endif
    sta se_overlay_active
    sta se_overlay_active+1
    sta se_overlay_busy
    sta se_overlay_busy+1
    ldx #OVL_LIMIT-1
@clear:
    sta se_overlay_ids,x
    dex
    bpl @clear
    lda #OVL_OWNER
    jsr se_reu_alloc
    bcs @done
    sta se_overlay_asset
    lda se_reu_epoch
    sta asset_epoch
    lda se_reu_epoch+1
    sta asset_epoch+1
    lda #0
    clc
@done:
    rts

asset_valid:
    ldx se_overlay_asset
    beq stale
    lda se_reu_logical_owner,x
    cmp #OVL_OWNER
    bne stale
.if EDITOR_CATALOG_TAIL
    ldx se_overlay_asset_second
    beq :+
    lda se_reu_logical_owner,x
    cmp #OVL_OWNER
    bne stale
:
.endif
    lda asset_epoch
    cmp se_reu_epoch
    bne stale
    lda asset_epoch+1
    cmp se_reu_epoch+1
    bne stale
    clc
    rts
stale:
    lda #$18
    sec
    rts

; Import se_overlay_header + payload at5000. Header and CRC verified before
; allocating a catalog entry or touching REU. No replacement of existing IDs.
se_overlay_import:
    jsr asset_valid
    jcs @return
    lda se_overlay_busy
    ora se_overlay_busy+1
    jne busy
    jsr se_overlay_validate
    jcs @return
    ldx #0
@duplicate:
    lda se_overlay_ids,x
    cmp se_overlay_header+6
    bne @next
    lda image_slot,x
    cmp se_overlay_header+5
    jeq duplicate
@next:
    inx
    cpx #OVL_LIMIT
    bcc @duplicate
    ldx #0
@free:
    lda se_overlay_ids,x
    beq @found
    inx
    cpx #OVL_LIMIT
    bcc @free
    lda #$15 ; catalog full
    sec
    rts
@found:
    stx candidate
    jsr crc_stage
.if EDITOR_CATALOG_TAIL
    bcs @return
    ; A valid payload owns its second bank only when a slot16..31 is needed.
    ; Allocation failure publishes no catalog ID, handle, or executable state.
    lda candidate
    cmp #16
    bcc :+
    lda se_overlay_asset_second
    bne :+
    lda #OVL_OWNER
    jsr se_reu_alloc
    bcs @return
    sta se_overlay_asset_second
:
.else
    jcs @return
.endif
    jsr request_stage
    lda #0
    jsr se_reu_copy
.if EDITOR_CATALOG_TAIL
    bcs @return
.else
    jcs @return
.endif
    ldx candidate
    lda se_overlay_header+5
    sta image_slot,x
    lda se_overlay_header+8
    sta image_size_lo,x
    lda se_overlay_header+9
    sta image_size_hi,x
.if !EDITOR_FIXED_ENTRY
    lda se_overlay_header+10
    sta image_entry_lo,x
    lda se_overlay_header+11
    sta image_entry_hi,x
.endif
    lda se_overlay_header+12
    sta image_crc_lo,x
    lda se_overlay_header+13
    sta image_crc_hi,x
    lda se_overlay_header+6
    sta se_overlay_ids,x
    lda #0
    clc
@return:
    rts

; A module ID, X slot0 renderer /1 command. C/A returned from module;
; X/Y/P otherwise clobbered. Same-slot nesting forbidden. Command->renderer
; allowed; renderer->command forbidden. All returns pass through resident code.
se_overlay_call:
    cpx #2
    jcs identity
    cmp #0
    jeq identity
    sta call_id
    stx call_slot
    lda se_overlay_busy,x
    jne busy
    cpx #0
    beq @admitted
    lda se_overlay_busy
    jne busy
@admitted:
    jsr asset_valid
    jcs @return
    ldx #0
@find:
    lda se_overlay_ids,x
    cmp call_id
    bne @next
    lda image_slot,x
    cmp call_slot
    beq @found
@next:
    inx
    cpx #OVL_LIMIT
    bcc @find
    lda #$17 ; unknown ID in this slot
    sec
    rts
@found:
    stx candidate
    inx
    txa
    ldx call_slot
    cmp se_overlay_active,x
    beq @hit
    ; Fetch to stage and verify before touching the previous executable slot.
    jsr header_from_catalog
    jsr request_stage
    lda #1
    jsr se_reu_copy
.if EDITOR_CATALOG_TAIL
    bcs @return
.else
    jcs @return
.endif
    jsr crc_stage
.if EDITOR_CATALOG_TAIL
    bcs @return
.else
    jcs @return
.endif
    jsr request_stage
    lda call_slot
    clc
    adc #$0A
    asl
    asl
    asl
    asl
    sta se_reu_c64+1 ; A0 or B0
    lda #1
    jsr se_reu_copy
.if EDITOR_CATALOG_TAIL
    bcs @return
.else
    jcs @return
.endif
    ldx call_slot
    lda candidate
    clc
    adc #1
    sta se_overlay_active,x
    inc se_overlay_loads
    bne @execute
    inc se_overlay_loads+1
    jmp @execute
@hit:
    inc se_overlay_hits
    bne @execute
    inc se_overlay_hits+1
@execute:
    ldx call_slot
    lda #1
    sta se_overlay_busy,x
    txa
    pha ; slot survives child calls and all overlay register clobbers
.if EDITOR_FIXED_ENTRY
    ; Every imported editor image was validated to enter just after its binding.
    ; No per-image executable pointer survives in the warm catalog.
    lda #OVL_BINDING_BYTES
    sta ovl_ptr
    ldx call_slot
    lda slot_high,x
    sta ovl_ptr+1
.else
    ldx candidate
    lda image_entry_lo,x
    sta ovl_ptr
    lda image_entry_hi,x
    ldx call_slot
    clc
    adc slot_high,x
    sta ovl_ptr+1
.endif
    inc se_overlay_calls
    bne :+
    inc se_overlay_calls+1
:
    jsr jump_overlay
    sta call_result
    ; PLA/TAX/LDA/STA preserve the module carry result.
    pla
    tax
    lda #0
    sta se_overlay_busy,x
    lda call_result
@return:
    rts
jump_overlay:
    jmp (ovl_ptr)

header_from_catalog:
    ldx candidate
    lda image_size_lo,x
    sta se_overlay_header+8
    lda image_size_hi,x
    sta se_overlay_header+9
    lda image_crc_lo,x
    sta se_overlay_header+12
    lda image_crc_hi,x
    sta se_overlay_header+13
    rts
request_stage:
.if EDITOR_CATALOG_TAIL
    ldx se_overlay_asset
    lda candidate
    cmp #16
    bcc :+
    ldx se_overlay_asset_second
:
    stx se_reu_logical
.else
    lda se_overlay_asset
    sta se_reu_logical
.endif
    lda #0
    sta se_reu_c64
    sta se_reu_offset
    lda #>OVL_STAGE
    sta se_reu_c64+1
    lda candidate
    asl
    asl
    asl
    asl
    sta se_reu_offset+1
    lda se_overlay_header+8
    sta se_reu_length
    lda se_overlay_header+9
    sta se_reu_length+1
    rts
crc_stage:
    ldx #OVL_BINDING_BYTES-1
@binding:
    lda OVL_STAGE,x
    cmp se_overlay_binding_digest,x
    bne @abi
    dex
    bpl @binding
.if EDITOR_CATALOG_TAIL
    bcs @crc ;last binding CMP matched; DEX/BPL preserved carry
.else
    jmp @crc
.endif
@abi:
    lda #$11
    sec
    rts
@crc:
    lda #<OVL_STAGE
    sta ovl_ptr
    lda #>OVL_STAGE
    sta ovl_ptr+1
    lda se_overlay_header+8
    sta crc_remaining
    lda se_overlay_header+9
    sta crc_remaining+1
    jsr se_crc_init
.ifdef FAST_EDITOR_CRC
.ifdef PRIVATE_INLINE_HALF_CRC
    ldy crc_remaining
    beq inline_byte ;validated nonzero payload: public header guard rejects0
    sty ovl_ptr
    dec ovl_ptr+1
    inc crc_remaining+1
    tya
    eor #$FF
    tay
    iny
se_overlay_crc_page_byte:
se_overlay_crc_tail_byte:
inline_byte:
    lda (ovl_ptr),y
    eor se_crc_value+1
    bmi inline_upper
    tax
    lda se_crc_value
    eor se_crc_table_high,x
    sta se_crc_value+1
    lda se_crc_table_low,x
    jmp inline_store
inline_upper:
    and #$7F
    tax
    lda se_crc_value
    eor se_crc_table_high,x
    eor #$91
    sta se_crc_value+1
    lda se_crc_table_low,x
    eor #$88
inline_store:
    sta se_crc_value
    iny
    bne inline_byte
    inc ovl_ptr+1
    dec crc_remaining+1
    bne inline_byte
fast_crc_finished:
.else
    ldy #0
    lda crc_remaining+1
    beq fast_crc_tail
se_overlay_crc_page_byte:
@page_byte:
    lda (ovl_ptr),y
    CACHE_CRC_BYTE
    iny
    bne @page_byte
    inc ovl_ptr+1
    dec crc_remaining+1
    bne @page_byte
fast_crc_tail:
    lda crc_remaining
    beq fast_crc_finished
    ldy #0
se_overlay_crc_tail_byte:
@tail_byte:
    lda (ovl_ptr),y
    CACHE_CRC_BYTE
    iny
    cpy crc_remaining
    bne @tail_byte
fast_crc_finished:
.endif ;PRIVATE_INLINE_HALF_CRC
.else
    ldy #0
@byte:
    lda (ovl_ptr),y
    jsr se_crc_byte
    inc ovl_ptr
    bne :+
    inc ovl_ptr+1
:
    lda crc_remaining
    bne :+
    dec crc_remaining+1
:
    dec crc_remaining
    lda crc_remaining
    ora crc_remaining+1
    bne @byte
.endif
    lda se_crc_value
    cmp se_overlay_header+12
    bne checksum
    lda se_crc_value+1
    cmp se_overlay_header+13
    bne checksum
    clc
    rts
checksum:
    lda #$14
    sec
    rts
duplicate:
    lda #$16
    sec
    rts
identity:
    lda #$12
    sec
    rts
busy:
    lda #$19
    sec
    rts
.segment "RODATA"
slot_high: .byte $A0,$B0
