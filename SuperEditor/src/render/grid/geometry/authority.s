; Geometry lifetime: called only inside one nonyielding C33 transaction.
; Capture/check the exact public FS59 tuple; no source lease or semantic state is
; fabricated. Existing C33/R25 still authenticates old NC and proves one actual
; source insertion/deletion byte-for-byte before invoking geometry PREPARE.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "fold/source.inc"
.import se_view_init,se_doc_validate,se_object_validate
.import se_doc_busy,se_doc_read_locks,se_hot_phase,se_hot_owned,se_h_phase
.import se_b_phase,se_clip_busy,se_snapshot_busy
.importzp text_ptr
.export se_rg_capture_source,se_rg_check_source
G=$8D80
TABLE_INDEX=G+25
DEST_INDEX=G+26
FIELD_SIZE=G+27
CHECK=G+28
IDENTITY=G+32
.assert IDENTITY+59<=$8E00,error,"geometry authority exceeds its declared phase"
.segment "CODE"
se_rg_capture_source:
 lda #0
 beq authority
se_rg_check_source:
 lda #1
authority:
 sta CHECK
 jsr se_doc_validate
 jcs return
 jsr se_view_init ;real gap geometry, current typed source and merged length
 jcs return
 lda se_doc_busy
 ora se_doc_read_locks
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
 jsr se_object_validate
 jcs return
 lda #0
 sta TABLE_INDEX
 sta DEST_INDEX
@field:
 ldx TABLE_INDEX
 lda fields,x
 sta text_ptr
 inx
 lda fields,x
 sta text_ptr+1
 inx
 lda fields,x
 sta FIELD_SIZE
 inx
 stx TABLE_INDEX
 ldx DEST_INDEX
 ldy #0
@byte:
 lda (text_ptr),y
 ; Preserve the actual source byte while selecting capture/check.
 pha
 lda CHECK
 bne @compare
 pla
 sta IDENTITY,x
 jmp @next
@compare:
 pla
 cmp IDENTITY,x
 jne changed
@next:
 inx
 iny
 cpy FIELD_SIZE
 bcc @byte
 stx DEST_INDEX
 cpx #59
 bcc @field
 lda #0
 clc
return:rts
changed:
 lda #$B1
 sec
 rts
.segment "RODATA"
.macro FIELD_DESCRIPTOR source,offset,n
 .assert offset<59,error,"FS59 field offset"
 .word source
 .byte n
.endmacro
fields:
 FS_FIELDS FIELD_DESCRIPTOR
.assert *-fields=23*3,error,"public FS59 field list changed"
