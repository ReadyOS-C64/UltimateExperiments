; Private R14 operation-sized wire encoder: no editor producer/consumer wiring.
.setcpu "6502"
.macpack longbranch
.include "fold/source.inc"
.include "render/geos/preview.inc"
.include "render/geos/semantic.inc"
.include "render/geos/inline.inc"
.include "render/geos/source-line.inc"
.import se_f_owner,se_gc_handle,se_gc_epoch,se_ef_valid,se_editor_settings
.import se_reu_copy,se_reu_c64,se_reu_length,se_reu_offset,se_reu_logical
.import se_reu_retired,se_reu_map,se_reu_logical_owner,se_reu_physical_owner
.import se_crc_init,se_crc_byte,se_crc_value
.export se_gpk_begin,se_gpk_step,se_gpk_cancel
K=$CC50
K_ACTIVE=K
K_INDEX=K+1 ;word; wire payload0..531 thenCRC
K_CRC=K+3
K_HANDLE=K+5
K_PHYS=K+6
K_EPOCH=K+7
K_DEST=K+9 ;caller16-bit offset, BEGIN preserves as destination witness
K_COUNT=K+11
K_DONE=K+12
K_CODE=K+13
K_SOURCE_COUNT=K+14
K_START=K+15 ;word current fragment's starting wire index
KH=$9000 ;32B header; below retained GS_FS9040
KB=$8880 ;128B packet encoder buffer, dead CG outputs before next font call
.segment "FOLD_SOURCE_CODE"
se_gpk_begin:
 jsr gpk_owner
 jcs gpk_return
 lda K_ACTIVE
 jne gpk_busy
 lda #0
 sta K_DONE
 lda se_ef_valid
 jne gpk_bad
 lda K_DEST+1
 cmp #$B2
 jcc gpk_bad
 clc
 lda K_DEST
 adc #<$216 ;534 inclCRC
 sta se_reu_offset
 lda K_DEST+1
 adc #>$216
 sta se_reu_offset+1
 jcs gpk_bad
 cmp #$E5
 bcc :+
 jne gpk_bad
 lda se_reu_offset
 cmp #$69 ;end<=E568, exclusive
 jcs gpk_bad
:
 lda PP_PHASE
 cmp #3
 beq :+
 cmp #4
 jne gpk_bad
:
 lda PP_COUNT
 cmp #161
 jcs gpk_bad
 sta K_SOURCE_COUNT
 lda PP_CODE
 sta K_CODE
 lda #0
 sta K_INDEX
 sta K_INDEX+1
 jsr se_fs_begin
 jcs gpk_return
 jsr gpk_snapshot
 jsr gpk_context
 jcs gpk_fail
 lda PP_CODE
 cmp #2
 jcs gpk_bad_open
 lda PP_COUNT
 cmp GSEM_FRAME+GSEM_COUNT
 jne gpk_bad_open
 ldx #2
@query:
 lda PP_WINDOW,x
 cmp GSEM_FRAME+GSEM_QUERY,x
 jne gpk_bad_open
 dex
 bpl @query
 CMP24 GSEM_FRAME+GSEM_START,PP_WINDOW
 bcc :+
 jne gpk_bad_open
:
 CMP24 GSEM_FRAME+GSEM_BODY,GSEM_FRAME+GSEM_END
 bcc :+
 jne gpk_bad_open
:
 CMP24 GSEM_FRAME+GSEM_END,se_fs_length
 bcc :+
 jne gpk_bad_open
:
 clc
 lda PP_WINDOW
 adc PP_COUNT
 sta se_fs_temp
 lda PP_WINDOW+1
 adc #0
 sta se_fs_temp+1
 lda PP_WINDOW+2
 adc #0
 sta se_fs_temp+2
 jcs gpk_bad_open
 CMP24 se_fs_temp,GSEM_FRAME+GSEM_END
 bcc :+
 jne gpk_bad_open
:
 lda se_gc_handle
 sta K_HANDLE
 tax
 lda se_reu_map,x
 sta K_PHYS
 ldx #1
@epoch:
 lda se_gc_epoch,x
 sta K_EPOCH,x
 dex
 bpl @epoch
 ldx #15
@semantic:
 lda GSEM_FRAME+GSEM_KIND,x
 sta KH,x
 dex
 bpl @semantic
 ldx #2
@anchors:
 lda PP_WINDOW,x
 sta KH+16,x
 lda PP_ANCHOR,x
 sta KH+20,x
 dex
 bpl @anchors
 lda PP_COUNT
 sta KH+19
 ldx #6
@profile:
 lda PP_BASE_PROFILE,x
 sta KH+23,x
 dex
 bpl @profile
 lda PP_PROFILE_INDEX
 sta KH+30
 lda PP_CODE
 sta KH+31
 lda PP_HEIGHT
 bne :+
 lda KH+31
 ora #$80 ;first band metrics/anchor; never a claimed display row boundary
 sta KH+31
:
 jsr se_crc_init
 lda se_crc_value
 sta K_CRC
 lda se_crc_value+1
 sta K_CRC+1
 lda #1
 sta K_ACTIVE
 clc
 rts
se_gpk_step:
 jsr gpk_owner
 jcs gpk_return
 lda K_ACTIVE
 cmp #1
 jne gpk_bad
 jsr se_fs_guard
 jcs gpk_fail
 jsr gpk_context
 jcs gpk_fail
 ldx #1
@bind:
 lda se_reu_epoch,x
 cmp K_EPOCH,x
 jne gpk_stale
 dex
 bpl @bind
 lda se_gc_handle
 cmp K_HANDLE
 jne gpk_stale
 tax
 lda se_reu_map,x
 cmp K_PHYS
 jne gpk_stale
 lda K_INDEX
 sta K_START
 lda K_INDEX+1
 sta K_START+1
 lda K_CRC
 sta se_crc_value
 lda K_CRC+1
 sta se_crc_value+1
 ldy #0
@encode:
 jsr gpk_byte
 sta KB,y
 jsr se_crc_byte
 inc K_INDEX
 bne :+
 inc K_INDEX+1
:
 iny
 cpy #128
 beq @stash
 lda K_INDEX+1
 cmp #2
 bne @encode
 lda K_INDEX
 cmp #$14 ;532 payloadbytes beforeCRC2
 bne @encode
@stash:
 sty K_COUNT
 lda se_crc_value
 sta K_CRC
 lda se_crc_value+1
 sta K_CRC+1
 jsr gpk_write
 jcs gpk_fail
 lda K_INDEX+1
 cmp #2
 bne gpk_pending
 lda K_INDEX
 cmp #$14
 bne gpk_pending
 lda K_CRC
 sta KB
 lda K_CRC+1
 sta KB+1
 lda K_INDEX
 sta K_START
 lda K_INDEX+1
 sta K_START+1
 lda #2
 sta K_COUNT
 jsr gpk_write
 jcs gpk_fail
 jsr gpk_end
 lda #1
 sta K_DONE ;only a caller-owned completion witness, not published batchVALID
 lda #0
 clc
 rts
gpk_pending:
 lda #1
 clc
gpk_return:
 rts
se_gpk_cancel:
 jsr gpk_owner
 bcs gpk_return
 lda K_ACTIVE
 beq :+
 jsr gpk_end
:
 lda #0
 clc
 rts
gpk_byte:
 lda K_INDEX+1
 bne @high
 lda K_INDEX
 cmp #32
 bcs @source
 tax
 lda KH,x
 rts
@source:
 sec
 sbc #32
 cmp #160
 bcs @style
 tax
 cpx K_SOURCE_COUNT
 bcs @zero
 lda $8200,x
 rts
@style:
 sec
 sbc #160 ;0..63 of styles
 jmp @style_index
@high:
 cmp #1
 bne @tail
 lda K_INDEX
 cmp #96
 bcs @role
 clc
 adc #64
@style_index:
 tax
 cpx K_SOURCE_COUNT
 bcs @zero
 lda K_CODE
 bne @zero
 lda GI_OUTPUT_STYLES,x
 rts
@role:
 sec
 sbc #96
 tax
 cpx K_SOURCE_COUNT
 bcs @zero
 lda K_CODE
 beq :+
 lda $8300,x ;actual C25 result, before C27lexed copies8400
 rts
:
 lda GI_OUTPUT_ROLES,x
 rts
@tail:
 ldx K_INDEX
 lda K_CODE
 bne @zero
 lda GI_OUTPUT_HIDDEN,x
 rts
@zero:
 lda #0
 rts
gpk_write:
 lda K_HANDLE
 sta se_reu_logical
 clc
 lda K_START
 adc K_DEST
 sta se_reu_offset
 lda K_START+1
 adc K_DEST+1
 sta se_reu_offset+1
 lda #<KB
 sta se_reu_c64
 lda #>KB
 sta se_reu_c64+1
 lda K_COUNT
 sta se_reu_length
 lda #0
 sta se_reu_length+1
 jmp se_reu_copy
gpk_owner:
 lda se_f_owner
 cmp #4
 beq :+
gpk_busy:
 lda #$B2
 sec
 rts
:
 clc
 rts
gpk_context:
 ldx #58
@source:
 lda se_fs_identity,x
 cmp $8908,x
 jne gpk_stale
 dex
 bpl @source
 ldx #63
@settings:
 lda se_editor_settings,x
 cmp $8943,x
 jne gpk_stale
 dex
 bpl @settings
 lda se_reu_retired
 jne gpk_stale
 ldx #1
@epoch:
 lda se_gc_epoch,x
 cmp se_reu_epoch,x
 jne gpk_stale
 dex
 bpl @epoch
 ldx se_gc_handle
 beq gpk_stale
 lda se_reu_logical_owner,x
 cmp #$FE
 bne gpk_stale
 lda se_reu_map,x
 tax
 beq gpk_stale
 lda se_reu_physical_owner,x
 cmp #$FE
 bne gpk_stale
 clc
 rts
gpk_stale:
 lda #$B1
 bne gpk_fail
gpk_bad:
 lda #$90
 sec
 rts
gpk_bad_open:
 lda #$90
 jmp gpk_fail
gpk_fail:
 pha
 jsr gpk_end
 pla
 sec
 rts
gpk_end:
 jsr se_fs_end
 lda #0
 sta K_ACTIVE
 sta GS_ACTIVE
 sta GS_CONTEXT_VALID
 rts
gpk_snapshot:
 ldx #85
@copy:
 lda se_fs_state,x
 sta GS_FS,x
 dex
 bpl @copy
 lda se_fs_owned
 sta GS_ACTIVE
 sta GS_CONTEXT_VALID
 rts
