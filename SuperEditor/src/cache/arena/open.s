.setcpu "6502"
.macpack longbranch
.include "cache/arena/api.inc"
.include "object/api.inc"
.import se_crc_value
.import bca_owner,bca_guard,bca_validate,bca_transfer,bca_crc_root,bca_pending,bca_done,bca_bad,bca_stale,bca_corrupt
.export se_bc_arena_open,bca_open_step,bca_root_check
; BCA_OUTER_VALIDATED is a narrow R36 profile contract: link_guard has
; completed in this same uninterrupted entry before bca_open_step. Do not
; enable it for general arena consumers or substitute an across-yield bit.
.segment "CODE"
se_bc_arena_open:
 jsr bca_owner
 jcs @return
 lda BCA_PHASE
 jeq @idle
 lda #BCA_BUSY
 sec
 rts
@idle:
 lda se_bc_flags
 and #BC_MUTATING
 jne bca_stale
 lda #0
 sta BCA_PROOF
 sta BCA_ERROR
 ldy #3
@identity:lda se_bc_incarnation,y
 sta BCA_INC,y
 sta BCA_TEMP+8,y
 lda se_bc_ticket,y
 sta BCA_TICKET,y
 dey
 bpl @identity
 ldy #4
 lda #0
@present:ora se_bc_arena,y
 dey
 bpl @present
 cmp #0
.ifdef BCA_READONLY_OPEN
 beq @miss
.else
 beq @create
.endif
 ldy #4
@capture:lda se_bc_arena,y
 sta BCA_BOUND,y
 dey
 bpl @capture
 jsr bca_guard
 jcs @return
 lda #$FF
 sta BCA_SELECTED
 lda #2
 sta BCA_PHASE
 jmp bca_pending
.ifndef BCA_READONLY_OPEN
@create:
 ; Incarnation wrap refuses before allocation, never aliases an ancient root.
 ldx #0
@inc:inc BCA_INC,x
 bne @allocate
 inx
 cpx #4
 bne @inc
 jmp bca_stale
@allocate:
 lda #BC_OBJECT_TYPE
 ldx #1
 jsr se_object_create
 jcs @return
 ldy #4
@candidate:lda se_object_id,y
 sta BCA_BOUND,y
 dey
 bpl @candidate
 lda #1
 sta BCA_PHASE
 lda #0
 sta se_object_offset
 sta se_object_offset+1
 sta BCA_CURSOR
 sta BCA_CURSOR+1
 sta BCA_CURSOR+2
 lda #1
 sta se_object_offset+2
 jsr se_object_resize
 jcs @return                 ; candidate retained for explicit CANCEL cleanup
 jmp bca_pending
.else
@miss:lda #2
 clc
 rts
.endif
@return:rts
; Phases1 init one128B chunk, 2/3 inspect roots, 4refetch selected,
; 5write uncommitted empty root, 6VALID-last byte then CPU token publication.
bca_open_step:
.ifndef BCA_READONLY_OPEN
 lda BCA_PHASE
 cmp #1
 jeq @initialize
 cmp #5
 bcc @live_guard
 jsr candidate_guard
 jcs @return
 jmp @guarded
@live_guard:jsr bca_guard
 jcs @return
@guarded:lda BCA_PHASE
 cmp #5
 jeq @write_root
 cmp #6
 jeq @commit
.else
.ifndef BCA_OUTER_VALIDATED
 jsr bca_guard
 jcs @return
.endif
 lda BCA_PHASE
.endif
 cmp #4
 jeq @selected
 lda BCA_PHASE
 cmp #2
 beq @root_a
 cmp #3
 jne bca_bad
 lda #128
 bne @read_root
@root_a:lda #0
@read_root:
 sta BCA_OFFSET
 lda #0
 sta BCA_OFFSET+1
 sta BCA_OFFSET+2
 lda #128
 sta BCA_LENGTH
 lda #1
 jsr bca_transfer
 jcs @return
 jsr bca_root_check
 bcs @next
 lda BCA_SELECTED
 cmp #$FF
 beq @choose
 ldy #3
@sequence:lda BC_IO+BC_ROOT_SEQUENCE,y
 cmp BCA_SEQUENCE,y
 bne @different
 dey
 bpl @sequence
 ; Equal sequence distinct roots are ambiguous, not arbitrary A preference.
 jmp bca_corrupt
@different:bcc @next
@choose:
 lda BCA_OFFSET
 sta BCA_SELECTED
 ldy #3
@save:lda BC_IO+BC_ROOT_SEQUENCE,y
 sta BCA_SEQUENCE,y
 dey
 bpl @save
@next:
 inc BCA_PHASE
 lda BCA_PHASE
 cmp #4
 jne bca_pending
 lda BCA_SELECTED
 cmp #$FF
 jeq bca_corrupt
 jmp bca_pending
@selected:
 lda BCA_SELECTED
 sta BCA_OFFSET
 lda #1
 jsr bca_transfer
 jcs @return
 jsr bca_root_check
 jcs @return
 ldy #3
@stable_sequence:lda BC_IO+BC_ROOT_SEQUENCE,y
 cmp BCA_SEQUENCE,y
 jne bca_stale
 dey
 bpl @stable_sequence
 lda #0
 sta BCA_PHASE
 jmp bca_done
.ifndef BCA_READONLY_OPEN
@initialize:
 jsr candidate_guard
 jcs @return
 lda #0
 ldy #127
@zero:sta BC_IO,y
 dey
 bpl @zero
 ldy #2
@cursor:lda BCA_CURSOR,y
 sta BCA_OFFSET,y
 dey
 bpl @cursor
 lda #128
 sta BCA_LENGTH
 lda #0
 jsr bca_transfer
 jcs @return
 clc
 lda BCA_CURSOR
 adc #128
 sta BCA_CURSOR
 bcc @initialized
 inc BCA_CURSOR+1
@initialized:
 lda BCA_CURSOR+1
 cmp #16
 jne bca_pending
 ; All4096 page0 bytes now zero. Empty format root has no reader authority.
 ldy #3
@magic:lda magic,y
 sta BC_IO,y
 dey
 bpl @magic
 lda #BC_ABI
 sta BC_IO+BC_ROOT_ABI
 lda #128
 sta BC_IO+BC_ROOT_LENGTH
 lda #BC_OBJECT_TYPE
 sta BC_IO+BC_ROOT_TYPE
 ldy #4
@root_token:lda BCA_BOUND,y
 sta BC_IO+BC_ROOT_TOKEN,y
 dey
 bpl @root_token
 ldy #3
@root_inc:lda BCA_INC,y
 sta BC_IO+BC_ROOT_INCARNATION,y
 lda BCA_TICKET,y
 sta BC_IO+BC_ROOT_TICKET,y
 sta BC_IO+BC_ROOT_OLDEST,y
 dey
 bpl @root_inc
 lda #1
 sta BC_IO+BC_ROOT_SEQUENCE
 lda #$FF
 ldy #3
@nil:sta BC_IO+BC_ROOT_FIRST,y
 sta BC_IO+BC_ROOT_LAST,y
 sta BC_IO+BC_ROOT_INDEX,y
 dey
 bpl @nil
 jsr bca_crc_root
 lda se_crc_value
 sta BC_IO+BC_ROOT_CRC
 lda se_crc_value+1
 sta BC_IO+BC_ROOT_CRC+1
 lda #5
 sta BCA_PHASE
 ; Candidate isn't yet live: phase5 must use candidate validation only.
 jmp bca_pending
@write_root:
 lda BC_IO+BC_ROOT_VALID
 jne bca_corrupt
 inc BC_IO+BC_ROOT_VALID
 jsr bca_root_check
 php
 dec BC_IO+BC_ROOT_VALID
 plp
 jcs @return
 lda #0
 sta BCA_OFFSET
 sta BCA_OFFSET+1
 sta BCA_OFFSET+2
 lda #128
 sta BCA_LENGTH
 lda #0
 jsr bca_transfer
 jcs @return
 inc BCA_PHASE
 jmp bca_pending
@commit:
 lda #1
 sta BC_IO
 sta BCA_LENGTH
 lda #5
 sta BCA_OFFSET
 lda #0
 jsr bca_transfer
 jcs @return
 ldy #3
@publish_inc:lda BCA_INC,y
 sta se_bc_incarnation,y
 dey
 bpl @publish_inc
 ldy #4
@publish_token:lda BCA_BOUND,y
 sta se_bc_arena,y
 dey
 bpl @publish_token
 lda #0
 sta BCA_PHASE
 ; Do not set ARMED, clear LOST, or claim zero source snapshot valid.
 jmp bca_done
.endif
@return:rts
.ifndef BCA_READONLY_OPEN
candidate_guard:
 jsr bca_owner
 bcs @done
 lda se_bc_flags
 and #BC_MUTATING
 jne bca_stale
 ldy #4
 lda #0
@absent:ora se_bc_arena,y
 dey
 bpl @absent
 cmp #0
 jne bca_stale
 ldy #3
@identity:lda se_bc_incarnation,y
 cmp BCA_TEMP+8,y
 jne bca_stale
 lda se_bc_ticket,y
 cmp BCA_TICKET,y
 jne bca_stale
 dey
 bpl @identity
 jmp bca_validate
@done:rts
.endif
; Root128 in IO; pure format/capability validity, no semantic certification.
bca_root_check:
 ldy #3
@magic:lda BC_IO,y
 cmp magic,y
 jne bca_corrupt
 dey
 bpl @magic
 lda BC_IO+BC_ROOT_ABI
 cmp #BC_ABI
 jne bca_corrupt
 lda BC_IO+BC_ROOT_VALID
 cmp #1
 jne bca_corrupt
 lda BC_IO+BC_ROOT_LENGTH
 cmp #128
 jne bca_corrupt
 lda BC_IO+BC_ROOT_LENGTH+1
 jne bca_corrupt
 lda BC_IO+BC_ROOT_TYPE
 cmp #BC_OBJECT_TYPE
 jne bca_corrupt
 ldy #4
@token:lda BC_IO+BC_ROOT_TOKEN,y
 cmp BCA_BOUND,y
 jne bca_corrupt
 dey
 bpl @token
 ldy #3
@inc:lda BC_IO+BC_ROOT_INCARNATION,y
 cmp BCA_INC,y
 jne bca_corrupt
 dey
 bpl @inc
 lda BC_IO+BC_ROOT_COUNT
 cmp #BC_JOURNAL_LIMIT+1
 jcs bca_corrupt
 ldy #127
@reserved:lda BC_IO,y
 jne bca_corrupt
 dey
 cpy #BC_ROOT_RESERVED-1
 bne @reserved
 jsr bca_crc_root
 lda se_crc_value
 cmp BC_IO+BC_ROOT_CRC
 jne bca_corrupt
 lda se_crc_value+1
 cmp BC_IO+BC_ROOT_CRC+1
 jne bca_corrupt
 clc
 rts
.segment "RODATA"
magic:.byte "BCA1"
