.setcpu "6502"
.macpack longbranch
.include "object/api.inc"
.import se_reu_alloc, se_reu_free, se_reu_epoch
.segment "OBJECTS"
new_owner: .res 1
new_banks: .res 1
new_index: .res 1
new_count: .res 1
new_error: .res 1
.segment "CODE"
; Initialize once after provider init. No REU data clearing, no leaked reset.
.ifdef EDITOR_COLD_OBJECT_INIT
.segment "COLD"
.endif
se_object_init:
    lda se_object_epoch
    cmp se_reu_epoch
    bne @initialize
    lda se_object_epoch+1
    cmp se_reu_epoch+1
    beq @invalid
@initialize:
    lda se_reu_epoch
    ora se_reu_epoch+1
    beq @invalid
    ldx #OBJECT_LIMIT-1
@clear:
    lda #0
    sta object_owner,x
    sta object_banks,x
    sta object_gen_hi,x
    sta object_size_lo,x
    sta object_size_mid,x
    sta object_size_hi,x
    lda #1
    sta object_gen_lo,x
    dex
    bpl @clear
    lda se_reu_epoch
    sta se_object_epoch
    lda se_reu_epoch+1
    sta se_object_epoch+1
    lda #0
    clc
    rts
@invalid:
    lda #$30
    sec
    rts

.ifdef EDITOR_COLD_OBJECT_INIT
.segment "CODE"
.endif

; A private type3..254, X bank count1..16. Reserves all banks before publishing
; the object. Failure frees tentative allocations, changes no REU bytes.
; Success A=ID, X/Y=generation, request token filled including provider epoch.
se_object_create:
    sta new_owner
    stx new_banks
    cmp #3
    jcc @argument
    cmp #$FF
    jeq @argument
    cpx #1
    jcc @argument
    cpx #OBJECT_EXTENTS+1
    jcs @argument
    jsr object_service_valid
    bcs @return
    ldx #0
@slot:
    lda object_owner,x
    beq @found
    inx
    cpx #OBJECT_LIMIT
    bcc @slot
    lda #$35
    sec
    rts
@found:
    stx new_index
    lda #0
    sta new_count
@allocate:
    lda new_owner
    jsr se_reu_alloc
    bcs @rollback
    pha
    jsr extent_index
    pla
    sta object_extents,x
    inc new_count
    lda new_count
    cmp new_banks
    bcc @allocate
    ldx new_index
    lda #0
    sta object_size_lo,x
    sta object_size_mid,x
    sta object_size_hi,x
    lda new_banks
    sta object_banks,x
    lda new_owner
    sta object_owner,x ; publication after complete reservation
    txa
    sta se_object_id
    lda object_gen_lo,x
    sta se_object_generation
    lda object_gen_hi,x
    sta se_object_generation+1
    tay
    lda se_object_epoch
    sta se_object_token_epoch
    lda se_object_epoch+1
    sta se_object_token_epoch+1
    lda object_gen_lo,x
    tax
    lda new_index
    clc
@return:
    rts
@rollback:
    sta new_error
@undo:
    lda new_count
    beq @rolled_back
    dec new_count
    jsr extent_index
    lda object_extents,x
    tax
    jsr se_reu_free
    jmp @undo
@rolled_back:
    lda new_error
    sec
    rts
@argument:
    lda #$36
    sec
    rts
extent_index:
    lda new_index
    asl
    asl
    asl
    asl
    ora new_count
    tax
    rts

se_object_release:
    jsr se_object_validate
    bcs @return
    stx new_index
    lda object_banks,x
    sta new_count
@release:
    dec new_count
    jsr extent_index
    lda object_extents,x
    tax
    jsr se_reu_free
    bcs @return ; impossible with exclusive foreground ownership after validation
    lda new_count
    bne @release
    ldx new_index
    lda #0
    sta object_banks,x
    sta object_size_lo,x
    sta object_size_mid,x
    sta object_size_hi,x
    inc object_gen_lo,x
    bne @free
    inc object_gen_hi,x
    bne @free
    ; Never reuse a generation after wrap: retire this catalog slot this epoch.
    lda #$FF
@free:
    sta object_owner,x
    lda #0
    clc
@return:
    rts
