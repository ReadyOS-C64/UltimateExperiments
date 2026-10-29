.setcpu "6502"
.macpack longbranch
.include "overlay/format.inc"
.ifdef EDITOR_INLINE_HALF_CRC
.ifndef FAST_EDITOR_CRC
.error "EDITOR_INLINE_HALF_CRC requires FAST_EDITOR_CRC"
.endif
.ifndef EDITOR_HALF_CRC
.error "EDITOR_INLINE_HALF_CRC requires EDITOR_HALF_CRC"
.endif
.endif
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
.ifdef EDITOR_MANAGED_CODE
; Managed backing is valid only under checked-write/provider notifications.
; Generic arbitrary-entry/strict-cache clients must leave this feature undefined.
.assert EDITOR_MANAGED_CODE=1,error,"managed-code flag must be1"
.if (EDITOR_CATALOG_TAIL .and EDITOR_FIXED_ENTRY) = 0
.fatal "managed code requires editor fixed catalog"
.endif
.export se_overlay_unverify,se_overlay_managed_verification
se_overlay_managed_verification=1
.endif
.export se_overlay_asset, se_overlay_active, se_overlay_busy, se_overlay_frame
.export se_overlay_loads, se_overlay_hits, se_overlay_calls, se_overlay_ids
.export se_overlay_capacity, se_overlay_fixed_entry, se_overlay_stage, se_overlay_asset_count
se_overlay_stage = OVL_STAGE
.if EDITOR_CATALOG_TAIL .and EDITOR_FIXED_ENTRY
se_overlay_asset_count = 4
.elseif EDITOR_CATALOG_TAIL
se_overlay_asset_count = 2
.else
se_overlay_asset_count = 1
.endif
se_overlay_capacity = OVL_LIMIT
se_overlay_fixed_entry = EDITOR_FIXED_ENTRY
.segment "ZEROPAGE"
ovl_ptr: .res 2
.segment "BSS"
se_overlay_asset: .res 1
.if EDITOR_CATALOG_TAIL .and EDITOR_FIXED_ENTRY
.export se_overlay_asset_second,se_overlay_asset_third,se_overlay_asset_fourth
se_overlay_asset_second: .res 1
se_overlay_asset_third: .res 1
se_overlay_asset_fourth: .res 1 ;contiguous lazy handles, one shared provider epoch
asset_epoch: .res 2
.segment "OVERLAY_CATALOG"
.else
asset_epoch: .res 2
.if EDITOR_CATALOG_TAIL
.export se_overlay_asset_second
se_overlay_asset_second: .res 1 ;lazy, same owner/epoch as the first asset bank
.segment "OVERLAY_CATALOG"
.endif
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
 .if EDITOR_CATALOG_TAIL .and EDITOR_FIXED_ENTRY
    ldx #3
@handles:
    sta se_overlay_asset,x
    sta se_overlay_active,x ;active2+busy2 are contiguous
    dex
    bpl @handles
 .else
    sta se_overlay_asset
.if EDITOR_CATALOG_TAIL
    sta se_overlay_asset_second
.endif
    sta se_overlay_active
    sta se_overlay_active+1
    sta se_overlay_busy
    sta se_overlay_busy+1
 .endif
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

.ifdef EDITOR_MANAGED_CODE
se_overlay_unverify:
    txa
    pha
    ldx #OVL_LIMIT-1
@clear:
    lda image_slot,x
    and #1
    sta image_slot,x
    dex
    bpl @clear
    lda #0
    sta se_overlay_active
    sta se_overlay_active+1
    sta $CBD5 ;sharedfont/executable5000windowwitness
    sta $CC4D ;preview body verification cannot survive provider/resume
    pla
    tax
    rts
.endif
asset_valid:
 .if EDITOR_CATALOG_TAIL .and EDITOR_FIXED_ENTRY
    lda se_overlay_asset
    beq stale
    ldx #3
@handles:
    lda se_overlay_asset,x
    beq @next
    tay
    lda se_reu_logical_owner,y
    cmp #OVL_OWNER
    bne stale
@next:
    dex
    bpl @handles
    ldx #1
@epoch:
    lda asset_epoch,x
    cmp se_reu_epoch,x
    bne stale
    dex
    bpl @epoch
 .else
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
 .endif
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
.ifdef EDITOR_MANAGED_CODE
    and #1
.endif
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
 .if EDITOR_FIXED_ENTRY
    ; CRC precedes lazy allocation of any of the four independent logical banks.
    jsr asset_index
    lda se_overlay_asset,x
    bne :+
    lda #OVL_OWNER
    jsr se_reu_alloc
    bcs @return
    pha
    jsr asset_index
    pla
    sta se_overlay_asset,x
:
 .else
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
 .endif
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
.ifdef EDITOR_MANAGED_CODE
    ora #$80
.endif
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
.ifdef EDITOR_MANAGED_CODE
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
    and #1
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
    ; Managedverified backing may copydirectly; unverified keepsstaging+CRC.
    jsr header_from_catalog
    ldx candidate
    lda image_slot,x
    bmi @copy_slot
    jsr request_stage
    lda #1
    jsr se_reu_copy
    jcs @return
    jsr crc_stage
    jcs @return
    ldx candidate
    lda image_slot,x
    ora #$80
    sta image_slot,x
@copy_slot:
    jsr request_slot
    lda #1
    jsr se_reu_copy
    jcs @return
    ; SuccessfulDMAchangedthe destination; rejectanybadbindingwithnoactiveclaim.
    ldx call_slot
    lda #0
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
.if EDITOR_FIXED_ENTRY
    lda #0
    sta ovl_ptr
    ldx call_slot
    lda slot_high,x
    sta ovl_ptr+1
    jsr binding_at_pointer
    jcs @return
    lda #OVL_BINDING_BYTES
    sta ovl_ptr
    lda candidate
    clc
    adc #1
    sta se_overlay_active,x
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
    ldx call_slot
    lda #1
    sta se_overlay_busy,x
    txa
    pha ;slot survives all child operations
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

.else
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

.endif
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
 .if EDITOR_CATALOG_TAIL .and EDITOR_FIXED_ENTRY
asset_index:
    lda candidate
    lsr
    lsr
    lsr
    lsr
    tax
    rts
 .endif
.ifdef EDITOR_MANAGED_CODE
request_stage:
    lda #0
    sta $CBD5
    lda #>OVL_STAGE
    bne request_common
request_slot:
    lda call_slot
    clc
    adc #$0A
    asl
    asl
    asl
    asl
request_common:
    sta se_reu_c64+1
    jsr asset_index
    lda se_overlay_asset,x
    sta se_reu_logical
    lda #0
    sta se_reu_c64
    sta se_reu_offset
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
binding_stage:
    lda #<OVL_STAGE
    sta ovl_ptr
    lda #>OVL_STAGE
    sta ovl_ptr+1
binding_at_pointer:
    ldy #OVL_BINDING_BYTES-1
@binding:
    lda (ovl_ptr),y
    cmp se_overlay_binding_digest,y
    bne @abi
    dey
    bpl @binding
    clc
    rts
@abi:
    lda #$11
    sec
    rts
crc_stage:
    jsr binding_stage
    bcc :+
    rts
:
.else
request_stage:
.if EDITOR_CATALOG_TAIL
 .if EDITOR_FIXED_ENTRY
    jsr asset_index
    lda se_overlay_asset,x
    sta se_reu_logical
 .else
    ldx se_overlay_asset
    lda candidate
    cmp #16
    bcc :+
    ldx se_overlay_asset_second
:
    stx se_reu_logical
 .endif
.else
    lda se_overlay_asset
    sta se_reu_logical
.endif
    lda #0
.if EDITOR_CATALOG_TAIL .and EDITOR_FIXED_ENTRY
    sta $CBD5 ;sticky font-window invalidation BEFORE any stage overwrite
.endif
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
.endif
    lda se_overlay_header+8
    sta crc_remaining
    lda se_overlay_header+9
    sta crc_remaining+1
    jsr se_crc_init
.ifdef FAST_EDITOR_CRC
.ifdef EDITOR_INLINE_HALF_CRC
    ; Public SEO header validation guarantees a nonzero payload before this
    ; private CRC stage. Bias the first partial page so one inline loop covers
    ; exactly5000..5000+length-1, then continue through whole256-byte pages.
    ; This removes per-byte JSR/RTS; all binding and checksum checks remain.
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
.endif ;EDITOR_INLINE_HALF_CRC
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
