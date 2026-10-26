; PRIVATEINLINE-only coreprofile: uncalled rootCRC omitted.
.setcpu "6502"
.macpack longbranch
.include "cache/arena/api.inc"
.include "object/api.inc"
.import se_f_owner,se_crc_init,se_crc_byte,se_crc_value
.export bca_owner,bca_guard,bca_validate,bca_transfer,bca_pending,bca_done,bca_bad,bca_stale,bca_corrupt,bca_fail
.segment "CODE"
bca_owner:
 lda se_f_owner
 cmp #4
 beq @ok
 lda #$B2
 sec
 rts
@ok:clc
 rts
; Validate captured capability and every logical/physical extent. Caller holds4.
bca_validate:
 ldy #4
@token:lda BCA_BOUND,y
 sta se_object_id,y
 dey
 bpl @token
 jsr se_object_validate
 bcs @done
 lda object_owner,x
 cmp #BC_OBJECT_TYPE
 jne bca_bad
 lda object_banks,x
 sta BCA_BANKS
 lda object_size_lo,x
 ora object_size_mid,x
 jne bca_corrupt
 lda object_size_hi,x
 cmp BCA_BANKS
 jne bca_corrupt
 clc
@done:rts
; Every yield binds live descriptor, ticket and incarnation; MUTATING refuses.
; LOST is deliberately not semantic authority here: this transport may inspect
; format-valid metadata while its optional observer baseline remains lost.
bca_guard:
 jsr bca_owner
 bcs @done
 ldy #4
@token:lda se_bc_arena,y
 cmp BCA_BOUND,y
 jne bca_stale
 dey
 bpl @token
 ldy #3
@identity:lda se_bc_incarnation,y
 cmp BCA_INC,y
 jne bca_stale
 lda se_bc_ticket,y
 cmp BCA_TICKET,y
 jne bca_stale
 dey
 bpl @identity
 lda se_bc_flags
 and #BC_MUTATING
 jne bca_stale
 jmp bca_validate
@done:rts
; A direction; request from OFFSET/LENGTH, fixed IO. No unchecked host pointer.
bca_transfer:
 pha
 ldy #2
@offset:lda BCA_OFFSET,y
 sta se_object_offset,y
 dey
 bpl @offset
 lda BCA_LENGTH
 beq @bad
 cmp #129
 bcs @bad
 sta se_object_length
 lda #0
 sta se_object_length+1
 lda #<BC_IO
 sta se_object_c64
 lda #>BC_IO
 sta se_object_c64+1
 pla
 jmp se_object_copy
@bad:pla
 jmp bca_bad
bca_pending:lda #1
 clc
 rts
bca_done:lda #0
 clc
 rts
bca_bad:lda #BCA_BAD
 jne bca_fail
bca_stale:lda #BCA_STALE
 jne bca_fail
bca_corrupt:lda #BCA_CORRUPT
bca_fail:sec
 rts
