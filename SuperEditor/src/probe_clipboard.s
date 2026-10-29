.setcpu "6502"
.macpack longbranch
.include "platform.inc"
.include "document/api.inc"
.include "object/api.inc"
.include "clipboard/api.inc"
.include "document/math24.inc"
.import se_doc_probe, se_doc_result, se_reu_free, se_print
.importzp text_ptr, screen_ptr
.export se_clip_probe, se_clip_probe_screen, se_clip_result, se_clip_cases, se_clip_error
.segment "BSS"
se_clip_result: .res 1
se_clip_cases: .res 1
se_clip_error: .res 1
.segment "OBJECTS"
probe_journal: .res 5
; Probe-only startup helpers occupy the cold BOOT area, outside the future
; warm snapshot. No editor/IRQ/resume path can call them after startup.
.segment "COLD"
se_clip_probe:
    jsr se_doc_probe
    lda se_doc_result
    cmp #1
    jne @failed
    inc se_clip_cases
    ; Release synthetic noncontiguity reservations, retaining the actual
    ; document banks. This admits clipboard+journal on the512KiB profile.
    ldx #190
    jsr se_reu_free
    jcs @failed
    ldx #191
    jsr se_reu_free
    jcs @failed
    jsr se_clip_init
    jcs @failed
    inc se_clip_cases
    jsr tail_range
    jsr se_clip_copy_begin
    jcs @failed
    jsr finish_copy
    jcs @failed
    inc se_clip_cases
    lda #0
    sta se_clip_position+2
    sta se_clip_span
    lda #8
    sta se_clip_span+1
    jsr se_clip_copy_begin
    jcs @failed
    jsr se_clip_copy_step
    jcs @failed
    cmp #1
    jne @failed
    jsr se_clip_copy_cancel
    lda se_doc_read_locks
    jne @failed
    inc se_clip_cases
    jsr prefix_range
    jsr se_clip_paste_begin
    jcs @failed
    jsr se_clip_paste_step
    jcs @failed
    jsr se_clip_paste_cancel
    lda se_doc_length
    jne @failed
    inc se_clip_cases
    jsr tail_range
    jsr se_clip_copy_begin
    jcs @failed
    jsr finish_copy
    jcs @failed
    lda se_clip_generation
    cmp #3
    jne @failed
    inc se_clip_cases
    lda #6
    ldx #1
    jsr se_object_create
    jcs @failed
    ldy #4
@journal:
    lda se_object_id,y
    sta probe_journal,y
    sta se_snapshot_token,y
    sta se_replay_token,y
    dey
    bpl @journal
    lda #0
    sta se_object_offset
    sta se_object_offset+1
    lda #1
    sta se_object_offset+2
    jsr se_object_resize
    jcs @failed
    lda #0
    sta se_snapshot_offset
    sta se_snapshot_offset+1
    sta se_snapshot_offset+2
    jsr se_snapshot_begin
    jcs @failed
    jsr finish_snapshot
    jcs @failed
    inc se_clip_cases
    jsr prefix_range
    jsr se_clip_paste_begin
    jcs @failed
    jsr finish_paste
    jcs @failed
    lda #1
    sta se_snapshot_offset+1
    jsr se_snapshot_begin
    jcs @failed
    jsr finish_snapshot
    jcs @failed
    inc se_clip_cases
    lda #0
    sta se_replay_offset
    sta se_replay_offset+1
    sta se_replay_offset+2
    sta se_replay_pieces+1
    sta se_replay_length
    lda #1
    sta se_replay_pieces
    sta se_replay_length+2
    lda #$10
    sta se_replay_length+1
    jsr se_replay_begin
    jcs @failed
    jsr finish_replay
    jcs @failed
    lda se_doc_length
    jne @failed
    inc se_clip_cases
    lda #1
    sta se_replay_offset+1
    lda #2
    sta se_replay_pieces
    lda #tail_end-tail
    sta se_replay_length
    jsr se_replay_begin
    jcs @failed
    jsr finish_replay
    jcs @failed
    lda se_doc_length
    cmp #tail_end-tail
    jne @failed
    lda se_doc_generation
    cmp #5
    jne @failed
    lda #0
    sta se_doc_offset
    sta se_doc_offset+1
    sta se_doc_offset+2
    sta se_doc_count+1
    sta se_doc_c64
    lda #$80
    sta se_doc_c64+1
    lda #tail_end-tail
    sta se_doc_count
    jsr se_doc_read
    jcs @failed
    ldx #tail_end-tail-1
@content:
    lda tail,x
    cmp $8000,x
    jne @failed
    dex
    bpl @content
    inc se_clip_cases
    lda #0
    sta $8000+tail_end-tail
    lda #1
    sta se_clip_result
    rts
@failed:
    sta se_clip_error
    lda #$EE
    sta se_clip_result
    rts
finish_copy:
    jsr se_clip_copy_step
    bcs @return
    cmp #1
    beq finish_copy
@return:
    rts
finish_paste:
    jsr se_clip_paste_step
    bcs @return
    cmp #1
    beq finish_paste
@return:
    rts
finish_snapshot:
    jsr se_snapshot_step
    bcs @return
    cmp #1
    beq finish_snapshot
@return:
    rts
finish_replay:
    jsr se_replay_step
    bcs @return
    cmp #1
    beq finish_replay
@return:
    rts
tail_range:
    lda #0
    sta se_clip_position
    sta se_clip_position+1
    sta se_clip_span+1
    sta se_clip_span+2
    lda #1
    sta se_clip_position+2
    lda #tail_end-tail
    sta se_clip_span
    rts
prefix_range:
    lda #0
    sta se_clip_position
    sta se_clip_position+1
    sta se_clip_position+2
    sta se_clip_span
    sta se_clip_span+1
    sta se_clip_span+2
    rts
se_clip_probe_screen:
    lda se_clip_result
    cmp #1
    bne @return
    PRINT_AT $8000,18,1
@return:
    rts
tail: .byte "Beyond 64 KiB: PETSCII source survives"
tail_end:
