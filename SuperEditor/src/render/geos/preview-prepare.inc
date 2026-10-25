; C24-owned operation-sized preparation for no-fold preview packets.
; Ordinary source/nav, fence skips and all published fold maps retain C27.
; Existing PP fields only; GSEM_ACTIVE2 means own R14 packet lease, not parser.
.include "render/geos/preview.inc"
.include "render/geos/settings.inc"
.import se_ef_valid,se_editor_settings
PP_TEMP24=PP_STATE+51
.segment "GEOS_SEMANTIC"
gpc_complete:
 lda se_r_presentation
 cmp #1
 jne se_gp_preview_complete
 lda se_e_job
 cmp #11
 jne se_gp_preview_complete
 lda se_ef_valid
 jne se_gp_preview_complete
 lda F+GSEM_KIND
 cmp #SM_CODE_OPEN
 jeq se_gp_preview_complete
 cmp #SM_CODE_CLOSE
 jeq se_gp_preview_complete
 cmp #SM_REGION_CLOSE
 jeq se_gp_preview_complete
 lda #0
 sta PP_COLLAPSED
 COPY24 PP_POSITION,PP_ANCHOR ;canonical raw prefix, before BODY adjustment
 lda #SES_BODY
 ldx #0
 stx PP_CODE
 lda F+GSEM_KIND
 cmp #SM_CODE_LINE
 bne @heading
 inc PP_CODE
 lda #SES_CODE
 bne @profile
@heading:
 cmp #SM_HEADING
 bne @body
 lda F+GSEM_LEVEL
 cmp #1
 bcc @body
 cmp #7
 bcs @body
 tax
 lda #SES_BODY
@level:
 clc
 adc #7
 dex
 bne @level
 jmp @profile
@body:
 lda #SES_BODY
@profile:
 sta PP_PROFILE_INDEX
 tax
 ldy #0
@copy:
 lda se_editor_settings,x
 sta PP_BASE_PROFILE,y
 sta PP_PROFILE,y
 inx
 iny
 cpy #7
 bcc @copy
 lda #0
 sta PP_HEIGHT
 lda F+GSEM_KIND
 cmp #SM_LIST
 beq @window
 CMP24 PP_POSITION,F+GSEM_BODY
 bcs @window
 COPY24 F+GSEM_BODY,PP_POSITION
@window:
 COPY24 PP_POSITION,PP_WINDOW
 SUB24 F+GSEM_END,PP_POSITION,PP_TEMP24
 lda PP_TEMP24+1
 ora PP_TEMP24+2
 bne @full
 lda PP_TEMP24
 cmp #161
 bcc @count
@full:
 lda #160
@count:
 sta PP_COUNT
 lda #0
 sta PP_READ
 sta PP_INDEX
 jsr reader ;fresh actual R14 BEGIN after semantic cleanup, no guessed lease
 jcs fail
 lda #2
 sta F+GSEM_ACTIVE
 sta PP_PHASE
 jmp pending

gpc_step:
 lda #1
 jsr reader
 jcs fail
 lda PP_READ
 cmp PP_COUNT
 beq gpc_handoff
 ; An exact32-byte source slice, bounded by actual logical END and visiblelen.
 lda PP_COUNT
 sec
 sbc PP_READ
 cmp #33
 bcc :+
 lda #32
:
 sta se_fs_count
 clc
 lda PP_READ
 adc PP_WINDOW
 sta se_fs_offset
 lda PP_WINDOW+1
 adc #0
 sta se_fs_offset+1
 lda PP_WINDOW+2
 adc #0
 sta se_fs_offset+2
 lda #<GS_PACKET
 sta se_fs_buffer
 lda #>GS_PACKET
 sta se_fs_buffer+1
 lda #2
 jsr reader
 jcs fail
 lda se_fs_done
 jeq range
 cmp se_fs_count
 bcc :+
 jne range
:
 ldx #0
 ldy PP_READ
@copy_packet:
 lda GS_PACKET,x
 sta $8200,y
 iny
 inx
 cpx se_fs_done
 bcc @copy_packet
 lda se_fs_done
 clc
 adc PP_READ
 sta PP_READ
 jmp pending

gpc_handoff:
 jsr cleanup ;never hold this lease across another C-slot worker
 COPY24 PP_WINDOW,F+GSEM_QUERY
 lda PP_COUNT
 sta F+GSEM_COUNT
 lda PP_CODE
 beq @inline
 lda F+GSEM_LANG
 sta F+GSEM_LANGUAGE
 lda #4
 sta PP_PHASE
 lda #25
 bne @request
@inline:
 lda #3
 sta PP_PHASE
 lda #26
@request:
 sta $9135
 lda #0
 sta $9136
 lda #1
 clc
 rts
