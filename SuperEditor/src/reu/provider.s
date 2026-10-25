.setcpu "6502"
.macpack longbranch
.import se_reu_banks
.ifdef EDITOR_MANAGED_CODE
.import se_overlay_unverify
.endif
.export se_reu_provider_init, se_reu_alloc, se_reu_bind, se_reu_free
.export se_reu_map, se_reu_logical_owner, se_reu_physical_owner, se_reu_epoch, se_reu_retired

.segment "BSS"
; These are standalone-owned allocations. A ReadyOS provider will populate the
; same logical map from allocator-owned physical banks instead of probing them.
se_reu_map: .res 256
se_reu_logical_owner: .res 256
se_reu_physical_owner: .res 256
se_reu_epoch: .res 2
se_reu_retired: .res 1
provider_owner: .res 1

.segment "CODE"
.ifdef SE_EDITOR_COLD_PROVIDER_INIT
.segment "COLD"
.endif
; Initialize after the nondestructive standalone presence/capacity probe.
; Owner 0 = free, 1 = control, 2..254 = typed app allocations, 255 unavailable.
; Does not alter a single REU data byte. All IRQ/NMI paths avoid these tables.
se_reu_provider_init:
    lda se_reu_retired
    bne provider_retired
    ; Every reset invalidates prior services, even when no REU is present.
    inc se_reu_epoch
    bne @tables
    inc se_reu_epoch+1
    bne @tables
    inc se_reu_retired ; never reuse an epoch in this cold-session lifetime
@tables:
    ldx #0
@next:
    txa
    sta se_reu_map,x
    lda #0
    sta se_reu_logical_owner,x
    lda se_reu_banks+1
    bne @available
    txa
    cmp se_reu_banks
    bcc @available
    lda #$FF
    bne @physical
@available:
    lda #0
@physical:
    sta se_reu_physical_owner,x
    inx
    bne @next
    lda se_reu_retired
    bne provider_retired
    lda se_reu_banks
    ora se_reu_banks+1
    beq @absent
    lda #1
    sta se_reu_logical_owner
    sta se_reu_physical_owner
    clc
    rts
@absent:
    sec
    rts

provider_retired:
    lda #6
    sec
    rts

.segment "CODE"

; A owner type (2..254) -> A logical handle, C clear. No space -> C set, A=1.
se_reu_alloc:
    cmp #2
.ifdef EDITOR_MANAGED_CODE
    jcc provider_bad
.else
    bcc provider_bad
.endif
    cmp #$FF
.ifdef EDITOR_MANAGED_CODE
    jeq provider_bad
.else
    beq provider_bad
.endif
    sta provider_owner
    ldy #1
@physical:
    lda se_reu_physical_owner,y
    beq @logical_start
    iny
    bne @physical
    lda #1
    sec
    rts
@logical_start:
    ldx #1
@logical:
    lda se_reu_logical_owner,x
    beq @bind
    inx
    bne @logical
    lda #1
    sec
    rts
@bind:
    lda provider_owner
    jmp se_reu_bind

; Explicit provider binding: A owner, X logical handle, Y physical bank.
; Used for noncontiguous allocation, later ReadyOS adapter and admission tests.
; Both slots must be unowned; unavailable banks can never be bound.
se_reu_bind:
    cmp #2
    bcc provider_bad
    cmp #$FF
    beq provider_bad
    sta provider_owner
    cpx #0
    beq provider_bad
    cpy #0
    beq provider_bad
    lda se_reu_logical_owner,x
    bne provider_bad
    lda se_reu_physical_owner,y
    bne provider_bad
    lda provider_owner
.ifdef EDITOR_MANAGED_CODE
    cmp #2
    bne :+
    jsr se_overlay_unverify
    lda provider_owner
:
.endif
    sta se_reu_logical_owner,x
    sta se_reu_physical_owner,y
    tya
    sta se_reu_map,x
    txa
    clc
    rts

; X logical handle. Control bank and unowned/corrupt mappings cannot be freed.
se_reu_free:
    cpx #0
    beq provider_bad
    lda se_reu_logical_owner,x
    cmp #2
    bcc provider_bad
    cmp #$FF
    beq provider_bad
    ldy se_reu_map,x
    cmp se_reu_physical_owner,y
    bne provider_bad
.ifdef EDITOR_MANAGED_CODE
    cmp #2
    bne :+
    jsr se_overlay_unverify
:
.endif
    lda #0
    sta se_reu_logical_owner,x
    sta se_reu_physical_owner,y
    clc
    rts

provider_bad:
    lda #4
    sec
    rts
