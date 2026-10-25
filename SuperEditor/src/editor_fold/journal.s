.setcpu "6502"
.macpack longbranch
SE_EF_JOURNAL_IMPLEMENTATION=1
.include "editor_fold/journal.inc"
.include "editor_fold/api.inc"
.include "document/api.inc"
.include "hot/api.inc"
.include "object/api.inc"
.ifdef EDITOR_OVERLAY
.include "editor-api.inc"
.else
.import se_reu_epoch,se_r_revision,se_view_init,se_v_length
.endif
.export se_ej_local,se_ej_commit,se_ej_flush,se_ej_baseline,se_ej_readlog
; Foreground packet scratch, deliberately outside all owner phase unions.
P=$8000
N=P+9
T=P+12
B=P+15
.macro CP from,to,size
 ldx #size-1
:
 lda from,x
 sta to,x
 dex
 bpl :-
.endmacro
.macro EQ left,right,size
 ldx #size-1
:
 lda left,x
 cmp right,x
 jne changed
 dex
 bpl :-
.endmacro
.macro TOKEN source
 CP source,se_object_id,5
 jsr se_object_validate
 jcs failed
.endmacro
 .assert se_doc_edit_delete=se_doc_edit_position+3,lderror,"splice request contiguous"
 .assert se_doc_edit_insert=se_doc_edit_position+6,lderror,"splice request contiguous"
 .assert se_ej_delete=se_ej_position+3,lderror,"journal args contiguous"
 .assert se_ej_insert=se_ej_position+6,lderror,"journal args contiguous"
.segment "FOLD_JOURNAL"
; Full token/epoch graph guard. No key_match: DIRTY intentionally differs in
; revision/length/generation, while immutable graph identity must remain exact.
guard:
 lda se_doc_busy
 jne changed
 EQ se_doc_meta,se_ef_key,5
 EQ se_doc_original,se_ef_key+5,5
 EQ se_doc_append,se_ef_key+10,5
 EQ se_reu_epoch,se_ef_key+24,2
 EQ se_doc_epoch,se_ef_key+26,2
 TOKEN se_doc_meta
 TOKEN se_doc_original
 TOKEN se_doc_append
 TOKEN se_ef_token
 lda object_owner,x
 cmp #$46
 jne changed
 lda object_banks,x
 sta B
 lda se_ef_capacity_banks
 bne :+
 lda #1
:
 cmp B
 jne changed
 lda object_size_hi,x
 cmp B
 jne changed
 lda object_size_lo,x
 ora object_size_mid,x
 jne changed
 ; count*32 <= capacity*65536-1024, proven before any journal DMA.
 lda se_ef_count
 sta T
 lda se_ef_count+1
 sta T+1
 lda #0
 sta T+2
 ldy #5
@scale:
 asl T
 rol T+1
 rol T+2
 dey
 bne @scale
 lda B
 sec
 sbc #1
 cmp T+2
 jcc changed
 bne @ok
 lda T+1
 cmp #$FC
 jcc @ok
 jne changed
 lda T
 jne changed
@ok:
 clc
 rts
armed:
 lda se_ej_status
 cmp #EJ_ARMED
 beq @count
 cmp #EJ_DIRTY
 jne changed
@count:
 lda se_ej_count
 cmp #EJ_LIMIT+1
 jcs changed
 jmp guard
same_generation:
 EQ se_ej_generation,se_doc_generation,2
 clc
 rts
next_generation:
 clc
 lda se_ej_generation
 adc #1
 sta T
 lda se_ej_generation+1
 adc #0
 sta T+1
 jcs changed
 EQ T,se_doc_generation,2
 clc
 rts
se_ej_baseline:
 jsr guard
 jcs return
 lda se_ef_valid
 cmp #1
 jne changed
 jsr view_checked
 jcs return
 EQ se_ef_key+15,se_doc_generation,2
 EQ se_ef_key+17,se_r_revision,4
 EQ se_ef_key+21,se_v_length,3
 CP se_doc_generation,se_ej_generation,2
 CP se_v_length,se_ej_length,3
 lda #0
 sta se_ej_count
 lda #EJ_ARMED
 sta se_ej_status
 jmp okay
se_ej_local:
 jsr armed
 jcs return
 jsr same_generation
 jcs return
 jsr view_checked
 jcs return
 EQ se_v_length,se_ej_length,3
 CP se_hot_caret,se_ej_position,3
 lda se_hot_delete
 cmp #2
 jcs changed
 sta se_ej_delete
 eor #1
 sta se_ej_insert
 lda #0
 sta se_ej_delete+1
 sta se_ej_delete+2
 sta se_ej_insert+1
 sta se_ej_insert+2
 jsr shape
 jcs return
 jmp append
se_ej_commit:
 jsr armed
 jcs return
 jsr next_generation
 jcs return
 lda se_hot_pending
 jne changed
 CP se_doc_edit_position,se_ej_position,9
 jsr shape
 jcs return
 EQ N,se_doc_length,3
 jsr append
 jcs return
 CP se_doc_generation,se_ej_generation,2
 jmp okay
; The hot flush publishes bytes already accounted for by LOCAL. Source-edit
; request still describes minimal prefix/suffix replacement at this boundary.
se_ej_flush:
 jsr armed
 jcs return
 jsr next_generation
 jcs return
 lda se_hot_phase
 cmp #2
 jne changed
 lda se_hot_pending
 cmp #1
 jne changed
 EQ se_hot_generation,se_ej_generation,2
 EQ se_doc_length,se_ej_length,3
 clc
 lda se_hot_base
 adc se_hot_prefix
 sta T
 lda se_hot_base+1
 adc se_hot_prefix+1
 sta T+1
 lda se_hot_base+2
 adc #0
 sta T+2
 jcs changed
 EQ T,se_doc_edit_position,3
 sec
 lda se_hot_old_length
 sbc se_hot_prefix
 sta T
 lda se_hot_old_length+1
 sbc se_hot_prefix+1
 sta T+1
 jcc changed
 sec
 lda T
 sbc se_hot_suffix
 sta T
 lda T+1
 sbc se_hot_suffix+1
 sta T+1
 jcc changed
 lda #0
 sta T+2
 EQ T,se_doc_edit_delete,3
 sec
 lda se_hot_length
 sbc se_hot_prefix
 sta T
 lda se_hot_length+1
 sbc se_hot_prefix+1
 sta T+1
 jcc changed
 sec
 lda T
 sbc se_hot_suffix
 sta T
 lda T+1
 sbc se_hot_suffix+1
 sta T+1
 jcc changed
 lda #0
 sta T+2
 EQ T,se_doc_edit_insert,3
 CP se_doc_generation,se_ej_generation,2
 jmp okay
; Candidate position+delete within old visible length; new visible length24bit.
; N receives proposed new size, but witness changes only after successful DMA.
shape:
 clc
 .repeat 3,I
 lda se_ej_position+I
 adc se_ej_delete+I
 sta T+I
 .endrepeat
 jcs changed
 ldx #2
@bound:
 lda T,x
 cmp se_ej_length,x
 jcc @size
 jne changed
 dex
 bpl @bound
@size:
 sec
 .repeat 3,I
 lda se_ej_length+I
 sbc se_ej_delete+I
 sta N+I
 .endrepeat
 jcc changed
 clc
 .repeat 3,I
 lda N+I
 adc se_ej_insert+I
 sta N+I
 .endrepeat
 jcs changed
 clc
 rts
; Checked packet count and ticket before any data write. Failure disables only
; optional retention, never changes count/ticket/length or a canonical source.
append:
 lda se_ej_count
 cmp #EJ_LIMIT
 jcs changed
 lda se_ej_ticket
 and se_ej_ticket+1
 and se_ej_ticket+2
 and se_ej_ticket+3
 cmp #$FF
 jeq changed
 CP se_ej_position,P,9
 jsr log_offset
 lda #9
 sta se_object_length
 lda #0
 sta se_object_length+1
 sta se_object_c64
 lda #$80
 sta se_object_c64+1
 lda #0
 jsr se_object_copy
 jcs failed
 CP N,se_ej_length,3
 inc se_ej_count
 inc se_ej_ticket
 bne @status
 inc se_ej_ticket+1
 bne @status
 inc se_ej_ticket+2
 bne @status
 inc se_ej_ticket+3
@status:
 lda #EJ_DIRTY
 sta se_ej_status
 jmp okay
; Fold token was authenticated and remains in se_object_id from GUARD.
log_offset:
 lda se_ej_count
 sta se_object_offset
 lda #0
 sta se_object_offset+1
 ldy #3
@eight:
 asl se_object_offset
 rol se_object_offset+1
 dey
 bne @eight
 clc
 lda se_object_offset
 adc se_ej_count
 sta se_object_offset
 lda se_object_offset+1
 adc #$FC
 sta se_object_offset+1
 lda B
 sec
 sbc #1
 sta se_object_offset+2
 rts
; Current merged source guard is used only outside transitional publication.
; No phase reads; shape is proven before se_view_init arithmetic is trusted.
view_checked:
 lda se_hot_phase
 ora se_hot_owned
 ora se_hot_fault
 jne changed
 lda se_hot_pending
 cmp #2
 jcs changed
 lda se_hot_ready
 cmp #1
 jne changed
 EQ se_hot_epoch,se_reu_epoch,2
 ldx #0
@lengthbounds:
 lda se_hot_old_length+1,x
 cmp #8
 jcc @nextlength
 jne changed
 lda se_hot_old_length,x
 jne changed
@nextlength:
 inx
 inx
 cpx #4
 bcc @lengthbounds
 lda se_hot_right+1
 cmp #8
 jcc @leftbound
 jne changed
 lda se_hot_right
 jne changed
@leftbound:
 lda se_hot_left+1
 cmp se_hot_right+1
 jcc @shape
 jne changed
 lda se_hot_left
 cmp se_hot_right
 jcc @shape
 jne changed
@shape:
 sec
 lda se_hot_left
 sbc se_hot_right
 sta T
 lda se_hot_left+1
 sbc se_hot_right+1
 clc
 adc #8
 cmp se_hot_length+1
 jne changed
 lda T
 cmp se_hot_length
 jne changed
 clc
 lda se_hot_base
 adc se_hot_old_length
 sta T
 lda se_hot_base+1
 adc se_hot_old_length+1
 sta T+1
 lda se_hot_base+2
 adc #0
 sta T+2
 jcs changed
 ldx #2
@within:
 lda T,x
 cmp se_doc_length,x
 jcc @valid
 jne changed
 dex
 bpl @within
@valid:
 jsr se_view_init
 jcs failed
 clc
 rts
se_ej_readlog:
 jsr armed
 jcs return
 jsr same_generation
 jcs return
 jsr view_checked
 jcs return
 EQ se_v_length,se_ej_length,3
 lda se_ej_count
 jeq okay
 ; Prefix length =9*count, offset stays at the start of the reserved tail.
 jsr log_offset
 lda se_object_offset
 sta se_object_length
 lda se_object_offset+1
 sec
 sbc #$FC
 sta se_object_length+1
 lda #0
 sta se_object_offset
 sta se_object_c64
 lda #$FC
 sta se_object_offset+1
 lda #$80
 sta se_object_c64+1
 lda #1
 jsr se_object_copy
 jcs failed
okay:
 lda #0
 clc
return:
 rts
changed:
 lda #$B7
failed:
 pha
 lda #EJ_FAILED
 sta se_ej_status
 pla
 sec
 rts
