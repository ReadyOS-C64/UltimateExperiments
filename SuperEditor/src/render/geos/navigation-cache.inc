; C26 retained-navigation operations6/7. Existing owner4 guard precedes dispatch.
.include "cache/query/api.inc"
.include "cache/arena/api.inc"
.include "cache/query/proof-api.inc"
.include "render/geos/navigation.inc"
.import se_e_job,se_crc_init,se_crc_byte,se_crc_value
NAV_RETAINED=16
NAV_ATTEMPTED=32
NAV_SAVED_CP=64
NAV_TARGETED=128
NAV_CP_BACKUP=$8880 ;140 real C24 CP bytes29..168; inactive R21 beforeC20
NAV_CP_MARKER=$890C ;retain actual valid1post-event/2incoming discriminator
nav_select:
 jsr nav_admit
 jcs argument
 lda GN_STATE
 cmp #9
 jne argument
 lda GN_FLAGS
 and #NAV_RETAINED
 beq @new
 lda se_bc_flags
 and #$2F
 cmp #$21
 bne @new
 lda se_bc_count
 bne @new
 ; Certificate integrity/source tuple is independent of stale overwritten GL.
 jsr se_crc_init
 ldy #82
@crc:lda BCQP,y
 jsr se_crc_byte
 dey
 bpl @crc
 lda se_crc_value
 cmp BCQP_CRC
 bne @new
 lda se_crc_value+1
 cmp BCQP_CRC+1
 bne @new
 ldy #12
@auth:lda BCQP_AUTH,y
 cmp se_bc_arena,y
 bne @new
 dey
 bpl @auth
 ldx #2
@lower:lda GN_SCAN,x
 cmp F+GSEM_START,x
 bcc @new
 bne @upper_start
 dex
 bpl @lower
@upper_start:ldx #2
@upper:lda GN_SCAN,x
 cmp F+GSEM_END,x
 jcc nav_ready
 bne @new
 dex
 bpl @upper
 jmp nav_ready
@new:
 lda GN_FLAGS
 and #($FF-NAV_RETAINED)
 sta GN_FLAGS
 lda se_bc_flags
 and #$0F
 cmp #1
 jne nav_legacy
 lda se_bc_count
 jne nav_legacy
 lda F+GSEM_CP_VALID
 beq @admit
 sta NAV_CP_MARKER
 lda GN_FLAGS
 and #NAV_ATTEMPTED
 jne nav_legacy
 ldy #139
@save_cp:lda F+29,y
 sta NAV_CP_BACKUP,y
 dey
 cpy #$FF
 bne @save_cp
 lda GN_FLAGS
 ora #NAV_SAVED_CP
 sta GN_FLAGS
@admit:lda GN_FLAGS
 ora #NAV_ATTEMPTED
 sta GN_FLAGS
.ifdef SE_EDITOR_NAV_TARGETED
 lda $CF80 ;actual C23 GN_FOLD_VALID; never shortcut a projected fold map
 bne @ordinary_query
 ldx #2
@target_query:lda GN_QUERY,x
 sta F+GSEM_QUERY,x
 dex
 bpl @target_query
 lda GN_FLAGS
 ora #NAV_TARGETED
 sta GN_FLAGS
@ordinary_query:
.endif
 lda #0
 sta F+GSEM_ACTIVE ;dead C22/painter byte is not a live semantic job; nav_admit proved GS0
 lda #35
 ldx #0
 jmp nav_request
nav_query_ready:
 jsr nav_admit
 jcs argument
 lda GN_STATE
 cmp #9
 jne argument
 lda F+GSEM_ERROR
 jne nav_legacy
 jsr bcq_capture_page
 bcs nav_legacy
 lda GN_FLAGS
 and #($FF-NAV_SAVED_CP)
 ora #NAV_RETAINED
 sta GN_FLAGS
.ifdef SE_EDITOR_NAV_TARGETED
 and #NAV_TARGETED
 beq @ordinary_ready
 ldx #2
@target_start:lda F+GSEM_START,x
 sta GN_SCAN,x
 dex
 bpl @target_start
 lda GN_FLAGS
 and #($FF-NAV_TARGETED)
 sta GN_FLAGS
@ordinary_ready:
.endif
 jmp nav_ready
nav_legacy:
.ifdef SE_EDITOR_NAV_TARGETED
 lda GN_FLAGS
 and #NAV_TARGETED
 beq @ordinary_legacy
 ldx #2
@restore_query:lda GN_SCAN,x
 sta F+GSEM_QUERY,x
 dex
 bpl @restore_query
 lda GN_FLAGS
 and #($FF-NAV_TARGETED)
 sta GN_FLAGS
@ordinary_legacy:
.endif
 lda GN_FLAGS
 and #NAV_SAVED_CP
 beq @ordinary
 ldy #139
@restore_cp:lda NAV_CP_BACKUP,y
 sta F+29,y
 dey
 cpy #$FF
 bne @restore_cp
 lda NAV_CP_MARKER
 sta F+GSEM_CP_VALID ;actual1post-event/2incoming, never a manufactured state
@ordinary:lda GN_FLAGS
 and #($FF-NAV_RETAINED-NAV_SAVED_CP)
 sta GN_FLAGS
 lda #5
 sta GN_STATE
 lda #24
 ldx #0
 beq nav_request
nav_ready:
 lda GN_COMMAND
 cmp #74
 bcc @done
 ldx #2
@logical:lda F+GSEM_START,x
 sta GN_SCAN,x
 dex
 bpl @logical
@done:lda #10
 sta GN_STATE
 lda #0
 clc
 rts
nav_request:
 sta GN_REQUEST
 stx GN_OPERATION
 lda #1
 clc
 rts
nav_admit:
 lda se_e_job
 cmp #12
 bne @bad
 lda GS_ACTIVE
 ora GS_CONTEXT_VALID
 beq @ok
@bad:sec
 rts
@ok:clc
 rts
BCQ_PROOF_CAPTURE=1
.include "cache/query/proof.inc"
