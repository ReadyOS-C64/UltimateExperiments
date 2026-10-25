.setcpu "6502"
.macpack longbranch
.include "editor_file/api.inc"
.include "fileio/api.inc"
.include "document/api.inc"
.include "document/math24.inc"
.include "object/api.inc"
.include "history/api.inc"
.import f_request,f_done,f_fail
.export f_open_step,f_release_candidates,f_restore
.segment "CODE"
f_open_step:
    lda se_f_phase
    cmp #2
    beq preflight
    cmp #3
    beq preflight
    cmp #4
    jeq read_packet
    cmp #5
    jeq adopt
    cmp #6
    jeq published
    lda #FIO_STATE
    jmp f_fail
preflight:
    lda se_f_result
    beq allocate
    lda #3
    sta se_f_phase
    lda #FT_PREFLIGHT_STEP
    jmp f_request
allocate:
    COPY24 se_f_preflight_length,se_f_length
    ; max ceil(length/65536), at least1; meta always1bank.
    lda se_f_length+2
    ldx se_f_length
    bne :+
    ldx se_f_length+1
    beq @banks
:   clc
    adc #1
@banks:
    cmp #17
    jcs capacity
    cmp #0
    bne :+
    lda #1
:   sta se_f_banks
    lda #3
    ldx #1
    jsr se_object_create
    jcs capacity
    ldx #0
    jsr remember
    lda #4
    ldx se_f_banks
    jsr se_object_create
    jcs capacity
    ldx #5
    jsr remember
    ; Borrow old append without writing/resizing before publication. Initial
    ; candidate has only an original root. This saves one bank/slot on512KiB.
    ldx #4
@borrow:
    lda se_doc_append,x
    sta se_f_candidate+10,x
    dex
    bpl @borrow
    ; Publish committed size of metadata; source remains old throughout input.
    DOC_TOKEN se_f_candidate
    lda #0
    sta se_object_offset
    sta se_object_offset+1
    lda #1
    sta se_object_offset+2
    jsr se_object_resize
    jcs fail
    lda #4
    sta se_f_phase
    lda #FT_OPEN
    jmp f_request
capacity:
    lda #F_CAPACITY
fail:
    jmp f_fail
remember:
    ldy #0
@token:
    lda se_object_id,y
    sta se_f_candidate,x
    inx
    iny
    cpy #5
    bcc @token
    inc se_f_allocated
    rts
read_packet:
    ; First OPEN completion has done reset by caller; subsequent reads carry data.
    lda se_io_done
    ora se_io_done+1
    jeq @check_eof
    COPY24 se_f_position,se_object_offset
    DOC_TOKEN se_f_candidate+5
    lda se_io_done
    sta se_object_length
    lda se_io_done+1
    sta se_object_length+1
    lda #0
    sta se_object_c64
    lda #$80
    sta se_object_c64+1
    lda #0
    jsr se_object_copy
    jcs fail
    clc
    lda se_f_position
    adc se_io_done
    sta se_f_position
    lda se_f_position+1
    adc se_io_done+1
    sta se_f_position+1
    lda se_f_position+2
    adc #0
    sta se_f_position+2
    lda #0
    sta se_io_done
    sta se_io_done+1
    ; Detect changing media/growing input before publishing anything.
    CMP24 se_f_position,se_f_length
    jcc @check_eof
    jeq @check_eof
    lda #F_CHANGED
    jmp f_fail
@check_eof:
    lda se_io_eof
    beq @next
    CMP24 se_f_position,se_f_length
    jne changed
    lda #5
    sta se_f_phase
    lda #FT_CLOSE
    jmp f_request
@next:
    lda #0
    sta se_io_count ;256 bytes per operation
    lda #FT_READ
    jmp f_request
changed:
    lda #F_CHANGED
    jmp f_fail
adopt:
    ; Validate all old tokens before irreversible publication/release.
    ldx #14
@old:
    lda se_doc_meta,x
    sta se_f_old,x
    dex
    bpl @old
    ldx #0
@validate:
    stx se_f_compare
    ldy #0
@vt:
    lda se_f_old,x
    sta se_object_id,y
    inx
    iny
    cpy #5
    bcc @vt
    jsr se_object_validate
    jcs fail
    ldx se_f_compare
    txa
    clc
    adc #5
    tax
    cpx #15
    bcc @validate
    ; Backup only canonical fields, not transient reader scratch.
    ldx #0
@roots:
    lda se_doc_roots,x
    sta se_f_backup,x
    lda #0
    sta se_doc_roots,x
    inx
    bne @roots
    ldx #21
@canonical:
    lda se_doc_ready,x
    sta se_f_backup+256,x
    lda #0
    sta se_doc_ready,x
    dex
    bpl @canonical
    lda se_doc_epoch
    sta se_f_backup+278
    lda se_doc_epoch+1
    sta se_f_backup+279
    ldx #14
@install:
    lda se_f_candidate,x
    sta se_doc_meta,x
    dex
    bpl @install
    lda #1
    sta se_doc_ready
    sta se_doc_generation
    sta se_f_committed ; temporarily installed; rollback still required
    COPY24 se_f_length,se_doc_source_length
    jsr se_doc_adopt_original
    jcs fail
    lda #6
    sta se_f_phase
    lda #FA_HISTORY_INIT
    jmp f_request
published:
    ; H_INIT new-context only has infallible stores after admission validation.
    lda #2
    sta se_f_committed
    ; Filename/device association commits with H_INIT, before any fallible
    ; retirement. A recovered new source must never retain the previous name.
    ldx #15
@name:
    lda se_f_name,x
    sta se_f_current_name,x
    dex
    bpl @name
    lda se_f_name_len
    sta se_f_current_len
    lda se_f_device
    sta se_f_current_device
    ; Canonical candidate tokens are now in DOCSTATE. Reuse this private queue
    ; for the two old objects, retaining a failed retirement for recovery.
    ldx #9
@retire:
    lda se_f_old,x
    sta se_f_candidate,x
    dex
    bpl @retire
    lda #2
    sta se_f_allocated
    ; H_INIT succeeded; old append bytes are unreachable in the new document.
    DOC_TOKEN se_doc_append
    lda #0
    sta se_object_offset
    sta se_object_offset+1
    sta se_object_offset+2
    jsr se_object_resize
    jcs recovery
    jsr f_release_candidates
    jcs recovery
    lda #0
    sta se_f_phase
    jmp f_done
recovery:
    lda #F_RECOVERY
    sta se_f_error
    lda #0
    sta se_f_phase
    lda #F_RECOVERY
    sec
    rts
f_restore:
    ldx #0
@roots:
    lda se_f_backup,x
    sta se_doc_roots,x
    inx
    bne @roots
    ldx #21
@canonical:
    lda se_f_backup+256,x
    sta se_doc_ready,x
    dex
    bpl @canonical
    lda se_f_backup+278
    sta se_doc_epoch
    lda se_f_backup+279
    sta se_doc_epoch+1
    lda #0
    sta se_f_committed
    jmp se_doc_invalidate
f_release_candidates:
    lda se_f_allocated
    beq @done
    sec
    sbc #1
    sta se_f_compare
    asl
    asl
    clc
    adc se_f_compare
    tax
    ldy #0
@token:
    lda se_f_candidate,x
    sta se_object_id,y
    inx
    iny
    cpy #5
    bcc @token
    jsr se_object_release
    bcs @retained
    dec se_f_allocated
    jmp f_release_candidates
@retained:
    ; Keep the failed token queued; do not silently release the union owner.
    lda #F_RECOVERY
    sta se_f_error
@done:
    rts
