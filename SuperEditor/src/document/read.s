.setcpu "6502"
.macpack longbranch
.include "document/api.inc"
.include "object/api.inc"
.segment "ZEROPAGE"
doc_root_ptr: .res 2
doc_piece_ptr: .res 2
.segment "DOCSTATE"
read_pos: .res 3
read_host: .res 2
read_left: .res 2
seek_pos: .res 3
read_root: .res 1
read_records: .res 1
read_slot: .res 1
read_record: .res 1
read_chunk: .res 2
read_piece_left: .res 3
read_root_left: .res 3
read_budget: .res 1
read_limited: .res 1
se_doc_read_done: .res 2
.segment "CODE"
corrupt:
    lda #$42
    sec
    rts

; Exact byte read into8000-83FF. Does not edit document or request.
; Root byte counts seek one leaf, cached until slot/generation changes.
se_doc_read:
    lda #0
    sta read_limited
    jmp read_start
; Same unchanged request, at most8 source descriptors. A1=partial, A0=full;
; actual copied byte count is se_doc_read_done. No retained cursor or lease.
se_doc_read_some:
    lda #1
    sta read_limited
read_start:
    lda #0
    sta se_doc_read_done
    sta se_doc_read_done+1
    lda #8
    sta read_budget
    jsr se_doc_validate
    jcs @return
    lda se_doc_count
    ora se_doc_count+1
    jeq @argument
    lda se_doc_c64+1
    cmp #$80
    jcc @host
    clc
    lda se_doc_c64
    adc se_doc_count
    sta seek_pos
    lda se_doc_c64+1
    adc se_doc_count+1
    jcs @host
    cmp #$84
    bcc @end
    jne @host
    lda seek_pos
    jne @host
@end:
    clc
    lda se_doc_offset
    adc se_doc_count
    sta seek_pos
    lda se_doc_offset+1
    adc se_doc_count+1
    sta seek_pos+1
    lda se_doc_offset+2
    adc #0
    sta seek_pos+2
    jcs @range
    ldx #2
@compare:
    lda seek_pos,x
    cmp se_doc_length,x
    bcc @valid
    jne @range
    dex
    bpl @compare
@valid:
    ldx #2
@position:
    lda se_doc_offset,x
    sta read_pos,x
    dex
    bpl @position
    ldx #1
@buffers:
    lda se_doc_count,x
    sta read_left,x
    lda se_doc_c64,x
    sta read_host,x
    dex
    bpl @buffers
@next:
    jsr seek_piece
    jcs @return
@have_piece:
    ; Make object request from piece. Only immutable original/append sources.
    ldy #0
    lda (doc_piece_ptr),y
    cmp se_doc_original
    beq @source
    cmp se_doc_append
    jne corrupt
@source:
    sta se_object_id
    iny
    lda (doc_piece_ptr),y
    sta se_object_generation
    iny
    lda (doc_piece_ptr),y
    sta se_object_generation+1
    lda se_doc_epoch
    sta se_object_token_epoch
    lda se_doc_epoch+1
    sta se_object_token_epoch+1
    sec
    ldy #6
    lda (doc_piece_ptr),y
    sbc seek_pos
    sta read_piece_left
    iny
    lda (doc_piece_ptr),y
    sbc seek_pos+1
    sta read_piece_left+1
    iny
    lda (doc_piece_ptr),y
    sbc seek_pos+2
    sta read_piece_left+2
    lda read_left
    sta read_chunk
    lda read_left+1
    sta read_chunk+1
    lda read_piece_left+2
    bne @chunk
    lda read_piece_left+1
    cmp read_left+1
    bcc @short
    bne @chunk
    lda read_piece_left
    cmp read_left
    bcs @chunk
@short:
    lda read_piece_left
    sta read_chunk
    lda read_piece_left+1
    sta read_chunk+1
@chunk:
    ; A corrupt root must not let this fragment run into the next root.
    sec
    lda read_root_left
    sbc read_chunk
    sta read_root_left
    lda read_root_left+1
    sbc read_chunk+1
    sta read_root_left+1
    lda read_root_left+2
    sbc #0
    sta read_root_left+2
    jcc corrupt
    clc
    ldy #3
    lda (doc_piece_ptr),y
    adc seek_pos
    sta se_object_offset
    iny
    lda (doc_piece_ptr),y
    adc seek_pos+1
    sta se_object_offset+1
    iny
    lda (doc_piece_ptr),y
    adc seek_pos+2
    sta se_object_offset+2
    jcs corrupt
    ldx #1
@copy_request:
    lda read_chunk,x
    sta se_object_length,x
    lda read_host,x
    sta se_object_c64,x
    dex
    bpl @copy_request
    lda #1
    jsr se_object_copy
    jcs @return
    clc
    lda se_doc_read_done
    adc read_chunk
    sta se_doc_read_done
    lda se_doc_read_done+1
    adc read_chunk+1
    sta se_doc_read_done+1
    sec
    lda read_left
    sbc read_chunk
    sta read_left
    lda read_left+1
    sbc read_chunk+1
    sta read_left+1
    beq :+
    jmp @advance
:
    ora read_left
    jeq @done
@advance:
    dec read_budget
    lda read_limited
    beq @continue
    lda read_budget
    bne @continue
    lda #1
    clc
    rts
@continue:
    clc
    lda read_host
    adc read_chunk
    sta read_host
    lda read_host+1
    adc read_chunk+1
    sta read_host+1
    clc
    lda read_pos
    adc read_chunk
    sta read_pos
    lda read_pos+1
    adc read_chunk+1
    sta read_pos+1
    bcc :+
    inc read_pos+2
:
    ; The whole previous fragment was consumed. Keep the in-leaf cursor
    ; instead of re-seeking the first descriptor for every source fragment.
    inc read_record
    lda read_root_left
    ora read_root_left+1
    ora read_root_left+2
    bne @same_root
    lda read_record
    cmp read_records
    jne corrupt
    jmp @next ; one root seek per crossed leaf, not per descriptor
@same_root:
    lda read_record
    cmp read_records
    jcs corrupt
    clc
    lda doc_piece_ptr
    adc #16
    sta doc_piece_ptr
    bcc :+
    inc doc_piece_ptr+1
:
    lda #0
    sta seek_pos
    sta seek_pos+1
    sta seek_pos+2
    ldy #6
    lda (doc_piece_ptr),y
    iny
    ora (doc_piece_ptr),y
    iny
    ora (doc_piece_ptr),y
    jeq corrupt
    jmp @have_piece
@done:
    lda #0
    clc
@return:
    rts
@range:
    lda #$32
    sec
    rts
@argument:
    lda #$36
    sec
    rts
@host:
    lda #$33
    sec
    rts

seek_piece:
    ldx #2
@position:
    lda read_pos,x
    sta seek_pos,x
    dex
    bpl @position
    lda #<se_doc_roots
    sta doc_root_ptr
    lda #>se_doc_roots
    sta doc_root_ptr+1
    lda #0
    sta read_root
@root:
    lda read_root
    cmp se_doc_root_count
    jcs corrupt
    ldx #2
    ldy #4
@compare_root:
    lda seek_pos,x
    cmp (doc_root_ptr),y
    bcc @found_root
    bne @skip_root
    dey
    dex
    bpl @compare_root
@skip_root:
    sec
    ldy #2
    lda seek_pos
    sbc (doc_root_ptr),y
    sta seek_pos
    iny
    lda seek_pos+1
    sbc (doc_root_ptr),y
    sta seek_pos+1
    iny
    lda seek_pos+2
    sbc (doc_root_ptr),y
    sta seek_pos+2
    clc
    lda doc_root_ptr
    adc #8
    sta doc_root_ptr
    bcc :+
    inc doc_root_ptr+1
:
    inc read_root
    jmp @root
@found_root:
    sec
    ldy #2
    lda (doc_root_ptr),y
    sbc seek_pos
    sta read_root_left
    iny
    lda (doc_root_ptr),y
    sbc seek_pos+1
    sta read_root_left+1
    iny
    lda (doc_root_ptr),y
    sbc seek_pos+2
    sta read_root_left+2
    jcc corrupt
    ldy #0
    lda (doc_root_ptr),y
    cmp #64
    jcs corrupt
    sta read_slot
    iny
    lda (doc_root_ptr),y
    beq @corrupt
    cmp #65
    bcs @corrupt
    sta read_records
    ldx read_slot
    jsr se_doc_leaf_load
    bcs @return
@loaded:
    lda #<DOC_LEAF
    sta doc_piece_ptr
    lda #>DOC_LEAF
    sta doc_piece_ptr+1
    lda #0
    sta read_record
@piece:
    ldy #6
    lda (doc_piece_ptr),y
    iny
    ora (doc_piece_ptr),y
    iny
    ora (doc_piece_ptr),y
    beq @corrupt
    ldx #2
    ldy #8
@compare_piece:
    lda seek_pos,x
    cmp (doc_piece_ptr),y
    bcc @success
    bne @skip_piece
    dey
    dex
    bpl @compare_piece
@skip_piece:
    sec
    ldy #6
    lda seek_pos
    sbc (doc_piece_ptr),y
    sta seek_pos
    iny
    lda seek_pos+1
    sbc (doc_piece_ptr),y
    sta seek_pos+1
    iny
    lda seek_pos+2
    sbc (doc_piece_ptr),y
    sta seek_pos+2
    inc read_record
    lda read_record
    cmp read_records
    bcs @corrupt
    clc
    lda doc_piece_ptr
    adc #16
    sta doc_piece_ptr
    bcc @piece
    inc doc_piece_ptr+1
    jmp @piece
@success:
    clc
@return:
    rts
@corrupt:
    jmp corrupt
