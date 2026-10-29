.setcpu "6502"
.macpack longbranch
.include "render/geos/semantic-previous-candidate/codec.inc"
.include "document/math24.inc"
.import se_f_owner,se_e_draw_sequence
.import se_doc_meta,se_doc_generation,se_r_revision,se_doc_epoch,se_reu_epoch
.import se_fs_active,se_fs_owned,se_fs_length
.import se_crc_init,se_crc_byte,se_crc_value
.import se_sm_init,se_sm_at_line,se_sm_pos,se_sm_state,se_sm_state_size
.import se_sm_fence,se_sm_language,se_sm_regions
; These private block fields are not public exports. Derive only from the
; actual linked79B block state, never the editor style parser aliases.
sm_line=se_sm_state+20
sm_region_overflow=se_sm_state+76
.assert se_sm_state_size=79,lderror,"incoming parser state ABI changed"
.export se_gsc_restore,se_gsc_record_valid
.ifndef GSC_RESTORE_ONLY
.export se_gsc_encode
.endif
.segment "CODE"
.ifndef GSC_RESTORE_ONLY
se_gsc_encode:
 jsr owner
 jcs return
 jsr current
 jcs miss
 lda #0
 ldx #63
@clear:
 sta GSC_RECORD,x
 dex
 bpl @clear
 lda #$53
 sta GSC_RECORD
 lda #2
 sta GSC_RECORD+1
 lda #1
 sta GSC_RECORD+3
 lda #64
 sta GSC_RECORD+2
 COPY24 sm_line,GSC_RECORD+GSC_ANCHOR
 ldx #27
@key:
 lda GSC_CURRENT,x
 sta GSC_RECORD+GSC_KEY,x
 dex
 bpl @key
 lda se_sm_fence
 sta GSC_RECORD+GSC_CARRY
 lda se_sm_language
 sta GSC_RECORD+GSC_CARRY+1
 lda se_sm_regions
 sta GSC_RECORD+GSC_CARRY+2
 COPY24 sm_region_overflow,GSC_RECORD+GSC_CARRY+3
 jsr crc
 lda se_crc_value
 sta GSC_RECORD+GSC_CRC
 lda se_crc_value+1
 sta GSC_RECORD+GSC_CRC+1
 jmp zero
 .endif
se_gsc_restore:
 jsr owner
 jcs return
 lda #0
 sta GSC_PROOF
 jsr current
 jcs miss
 jsr se_gsc_record_valid
 jcs miss
 lda GSC_RECORD+GSC_CARRY
 beq :+
 cmp #3
 jcc miss
: lda GSC_RECORD+GSC_CARRY+1
 cmp #3
 jcs miss
 CMP24 GSC_RECORD+GSC_ANCHOR,GSEM_FRAME+GSEM_QUERY
 jcs @equal_query
 jmp @key_guard
@equal_query:
 jne miss
@key_guard:
 ; Tokens, committedgeneration and both epochs never change under the only
 ; admitted local GEC mutation. No representation-only rekey is guessed.
 ldx #16
@immutable:
 lda GSC_CURRENT,x
 cmp GSC_RECORD+GSC_KEY,x
 jne miss
 dex
 bpl @immutable
 ldx #3
@epochs:
 lda GSC_CURRENT+24,x
 cmp GSC_RECORD+GSC_KEY+24,x
 jne miss
 dex
 bpl @epochs
 ldx #6
@visible:
 lda GSC_CURRENT+17,x
 cmp GSC_RECORD+GSC_KEY+17,x
 bne edit_guard
 dex
 bpl @visible
 lda #1
 sta GSC_PROOF
 jmp restore
edit_guard:
 lda GSC_ALLOW_EDIT
 cmp #1
 jne miss
 ldx #1
@sequence:
 lda GEC_SEQUENCE,x
 cmp se_e_draw_sequence,x
 jne miss
 cmp GCC_SEQUENCE,x
 jne miss
 lda GEC_DOC_EPOCH,x
 cmp GSC_RECORD+GSC_KEY+26,x
 jne miss
 lda GEC_REU_EPOCH,x
 cmp GSC_RECORD+GSC_KEY+24,x
 jne miss
 dex
 bpl @sequence
 ldx #3
@revision:
 lda GEC_REVISION,x
 cmp GSC_RECORD+GSC_KEY+17,x
 jne miss
 sta GSC_TEMP,x
 dex
 bpl @revision
 ldx #0
@increment:
 inc GSC_TEMP,x
 bne @compare_revision
 inx
 cpx #4
 bcc @increment
 jmp miss ;visible revision may not wrap
@compare_revision:
 ldx #3
: lda GSC_TEMP,x
 cmp GSC_CURRENT+17,x
 jne miss
 dex
 bpl :-
 ldx #2
@length:
 lda GEC_LENGTH,x
 cmp GSC_RECORD+GSC_KEY+21,x
 jne miss
 sta GSC_TEMP,x
 dex
 bpl @length
 CMP24 GEC_POSITION,GSC_RECORD+GSC_ANCHOR
 jcc miss ;prefix changed before this record's original anchor
 CMP24 GEC_POSITION,GEC_LENGTH
 bcc @operation
 jne miss
 lda GEC_OP
 jne miss ;delete cannot target old EOF
@operation:
 lda GEC_OP
 beq @insert
 cmp #1
 jne miss
 lda GEC_NEW
 jne miss
 sec
 lda GSC_TEMP
 sbc #1
 sta GSC_TEMP
 lda GSC_TEMP+1
 sbc #0
 sta GSC_TEMP+1
 lda GSC_TEMP+2
 sbc #0
 sta GSC_TEMP+2
 jcc miss
 jmp @compare_length
@insert:
 lda GEC_OLD
 jne miss
 inc GSC_TEMP
 bne @compare_length
 inc GSC_TEMP+1
 bne @compare_length
 inc GSC_TEMP+2
 jeq miss
@compare_length:
 CMP24 GSC_TEMP,GSC_CURRENT+21
 jne miss
 lda #2
 sta GSC_PROOF
restore:
 ; All guards complete before touching the parser. Full init resets partial
 ; prefix/list state; actual incoming carry is restored without inference.
 jsr se_sm_init
 COPY24 GSC_RECORD+GSC_ANCHOR,se_sm_pos
 jsr se_sm_at_line
 lda GSC_RECORD+GSC_CARRY
 sta se_sm_fence
 lda GSC_RECORD+GSC_CARRY+1
 sta se_sm_language
 lda GSC_RECORD+GSC_CARRY+2
 sta se_sm_regions
 COPY24 GSC_RECORD+GSC_CARRY+3,sm_region_overflow
 lda #1
 clc
 rts
miss:
zero:
 lda #0
 clc
return:
 rts
owner:
 lda se_f_owner
 cmp #4
 beq zero
 lda #$B2
 sec
 rts
; Current frame must agree with actual globals and the counted reader snapshot.
; Caller additionally GUARDs R14 immediately before this no-overlay operation.
current:
 lda se_fs_active
 cmp #1
 bne @bad
 lda se_fs_owned
 cmp #1
 bne @bad
 ldx #14
@tokens:
 lda se_doc_meta,x
 cmp GSC_CURRENT,x
 bne @bad
 dex
 bpl @tokens
 ldx #1
@epochs:
 lda se_doc_generation,x
 cmp GSC_CURRENT+15,x
 bne @bad
 lda se_reu_epoch,x
 cmp GSC_CURRENT+24,x
 bne @bad
 lda se_doc_epoch,x
 cmp GSC_CURRENT+26,x
 bne @bad
 dex
 bpl @epochs
 ldx #3
@revision:
 lda se_r_revision,x
 cmp GSC_CURRENT+17,x
 bne @bad
 dex
 bpl @revision
 ldx #2
@length:
 lda se_fs_length,x
 cmp GSC_CURRENT+21,x
 bne @bad
 dex
 bpl @length
 clc
 rts
@bad:
 sec
 rts
crc:
 jsr se_crc_init
 ldy #0
@byte:
 lda GSC_RECORD,y
 jsr se_crc_byte
 iny
 cpy #GSC_CRC
 bcc @byte
 rts

; Shared structural+CRC validity for the coherent dual-record producer.
se_gsc_record_valid:
 lda GSC_RECORD
 cmp #$53
 bne gsc_record_bad
 lda GSC_RECORD+1
 cmp #2
 bne gsc_record_bad
 lda GSC_RECORD+3
 cmp #1
 bne gsc_record_bad
 lda GSC_RECORD+2
 cmp #64
 bne gsc_record_bad
 jsr crc
 ldx #1
@crc:
 lda se_crc_value,x
 cmp GSC_RECORD+GSC_CRC,x
 bne gsc_record_bad
 dex
 bpl @crc
 clc
 rts
gsc_record_bad:
 sec
 rts
