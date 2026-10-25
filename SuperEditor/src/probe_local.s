.setcpu "6502"
.macpack longbranch
.include "platform.inc"
.include "document/api.inc"
.include "document/math24.inc"
.include "object/api.inc"
.import se_doc_probe, se_doc_result, se_reu_free, se_print, se_hex_byte
.importzp text_ptr, screen_ptr
.export se_local_probe, se_local_screen, se_local_result, se_local_cases, se_local_error
.segment "BSS"
se_local_result: .res 1
se_local_cases: .res 1
se_local_error: .res 1
local_packets: .res 1
.segment "OBJECTS"
local_journal: .res 5
.segment "COLD"
se_local_probe:
    jsr se_doc_probe
    lda se_doc_result
    cmp #1
    jne failed
    inc se_local_cases
    ldx #190
    jsr se_reu_free
    jcs failed
    ldx #191
    jsr se_reu_free
    jcs failed
    lda #6
    ldx #1
    jsr se_object_create
    jcs failed
    ldy #4
@token:
    lda se_object_id,y
    sta local_journal,y
    sta se_replay_token,y
    sta se_doc_refs_token,y
    dey
    bpl @token
    lda #0
    sta se_object_offset
    sta se_object_offset+1
    lda #1
    sta se_object_offset+2
    jsr se_object_resize
    jcs failed
    inc se_local_cases
    ; Nine identical packets of16 noncontiguous references. Repeating offset0
    ; deliberately prevents coalescing, proving a real3-leaf producer graph.
    ldx #0
    ldy #16
@packet:
    lda se_doc_original
    sta $8000,x
    lda #1
    sta $8001,x
    sta $8006,x
    lda #0
    sta $8002,x
    sta $8003,x
    sta $8004,x
    sta $8005,x
    sta $8007,x
    sta $8008,x
    txa
    clc
    adc #9
    tax
    dey
    bne @packet
    lda #0
    sta se_object_offset
    sta se_object_offset+1
    sta se_object_offset+2
    lda #9
    sta local_packets
@stash:
    DOC_TOKEN local_journal
    lda #144
    sta se_object_length
    lda #0
    sta se_object_length+1
    sta se_object_c64
    lda #$80
    sta se_object_c64+1
    lda #0
    jsr se_object_copy
    jcs failed
    clc
    lda se_object_offset
    adc #144
    sta se_object_offset
    bcc :+
    inc se_object_offset+1
:
    dec local_packets
    bne @stash
    ; A separate redo reference uses the first immutable append byte, which
    ; will be committed by the initial local byte replacement below.
    lda se_doc_append
    sta $8000
    lda #0
    sta se_object_offset
    lda #6
    sta se_object_offset+1
    lda #9
    sta se_object_length
    DOC_TOKEN local_journal
    lda #0
    jsr se_object_copy
    jcs failed
    inc se_local_cases
    lda #0
    sta se_replay_offset
    sta se_replay_offset+1
    sta se_replay_offset+2
    sta se_replay_pieces+1
    sta se_replay_length+1
    sta se_replay_length+2
    lda #144
    sta se_replay_pieces
    sta se_replay_length
    jsr se_replay_begin
    jcs failed
@replay:
    jsr se_replay_step
    jcs failed
    cmp #1
    beq @replay
    inc se_local_cases
    lda #0
    sta se_doc_edit_position+1
    sta se_doc_edit_position+2
    sta se_doc_edit_delete+1
    sta se_doc_edit_delete+2
    sta se_doc_edit_insert+1
    sta se_doc_edit_insert+2
    lda #70
    sta se_doc_edit_position
    lda #1
    sta se_doc_edit_delete
    sta se_doc_edit_insert
    jsr se_doc_splice_local_begin
    jcs failed
    lda #'X'
    sta $8000
    lda #0
    sta se_doc_count+1
    sta se_doc_c64
    lda #$80
    sta se_doc_c64+1
    lda #1
    sta se_doc_count
    jsr se_doc_splice_feed
    jcs failed
    jsr finish_local
    jcs failed
    inc se_local_cases
    lda #0
    sta se_doc_refs_offset
    sta se_doc_refs_offset+1
    sta se_doc_refs_offset+2
    sta se_doc_refs_pieces+1
    lda #1
    sta se_doc_refs_pieces
    jsr se_doc_splice_local_refs_begin
    jcs failed
    jsr finish_local
    jcs failed
    inc se_local_cases
    lda #6
    sta se_doc_refs_offset+1
    jsr se_doc_splice_local_refs_begin
    jcs failed
    jsr finish_local
    jcs failed
    inc se_local_cases
    ; Bounded reads cross a metadata leaf, then include the changed byte.
    lda #0
    sta se_doc_offset+1
    sta se_doc_offset+2
    sta se_doc_count+1
    sta se_doc_c64
    lda #$80
    sta se_doc_c64+1
    lda #60
    sta se_doc_offset
    lda #84
    sta se_doc_count
    jsr partial_read
    jcs failed
    inc se_local_cases
    lda #66
    sta se_doc_offset
    lda #78
    sta se_doc_count
    jsr partial_read
    jcs failed
    lda $8004
    cmp #'X'
    jne failed
    inc se_local_cases
    lda #0
    sta se_doc_offset
    sta se_doc_offset+1
    sta se_doc_offset+2
    sta se_doc_count+1
    sta se_doc_c64
    lda #$80
    sta se_doc_c64+1
    lda #144
    sta se_doc_count
    jsr se_doc_read
    jcs failed
    ldx #143
@content:
    cpx #70
    beq @changed
    lda $8000,x
    cmp #$A5
    jne failed
    jmp @next
@changed:
    lda $8000,x
    cmp #'X'
    jne failed
@next:
    dex
    bpl @content
    lda se_doc_generation
    cmp #6
    jne failed
    inc se_local_cases
    lda #1
    sta se_local_result
    rts
failed:
    sta se_local_error
    lda #$EE
    sta se_local_result
    rts
finish_local:
    jsr se_doc_splice_step
    bcs @return
    cmp #1
    beq finish_local
    lda se_doc_reused_roots
    cmp #2
    bne @bad
    clc
@return:
    rts
@bad:
    lda #$EE
    sec
    rts
partial_read:
    jsr se_doc_read_some
    bcs @return
    cmp #1
    bne @bad
    lda se_doc_read_done
    cmp #8
    bne @bad
    lda se_doc_read_done+1
    bne @bad
    clc
@return:
    rts
@bad:
    lda #$EE
    sec
    rts
se_local_screen:
    PRINT_AT summary,16,1
    lda se_local_result
    jsr se_hex_byte
    stx VIC_SCREEN+16*40+25
    sta VIC_SCREEN+16*40+26
    PRINT_AT shared,18,1
    lda se_doc_reused_roots
    jsr se_hex_byte
    stx VIC_SCREEN+18*40+27
    sta VIC_SCREEN+18*40+28
    PRINT_AT changed,20,1
    PRINT_AT bounded,22,1
    rts
summary: .asciiz "Local/reference result: "
shared: .asciiz "Unchanged roots retained: "
changed: .asciiz "Byte70: X / reference restore+redo"
bounded: .asciiz "Reads: <=8 pieces per work slice"
