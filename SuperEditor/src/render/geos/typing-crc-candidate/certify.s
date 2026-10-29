; Private C6 extension. Called immediatelyafterse_gec_capture at MARK.
; Readonlyeligibility/packetcertification; normalC6 mutation followsreturn.
.setcpu "6502"
.macpack longbranch
GP_CACHE_IMPLEMENTATION=1
.include "render/geos/editor.inc"
.include "render/geos/edit-certificate.inc"
.include "render/geos/typing-crc-candidate/certificate.inc"
.include "render/geos/typing-crc-candidate/buffered-api.inc"
.include "render/geos/typing-crc-candidate/font-cache.inc"
.include "document/math24.inc"
.import se_f_owner,se_mode,se_e_ui,se_r_presentation,se_l_mode,se_l_pan
.import se_ef_valid,se_sel_mark,se_e_error,se_h_fault,se_h_trimmed
.import se_gp_cache_read,se_gp_cache_slot
.import se_crc_init,se_crc_byte,se_crc_value,se_petscii_screen
.export se_gtt_certify
T=$90F0                    ;3-byte transient withinowner4 foregroundscratch
S=$9000                    ;160B checkedtransferbuffer
.segment "CODE"
se_gtt_certify:
 lda se_f_owner
 jne no_claim
 lda #4
 sta se_f_owner
 lda #0
 sta GTC_VALID
 lda GEC_VALID
 cmp #1
 jne release
 lda se_mode
 cmp #3
 jne release
 lda se_e_ui
 ora se_r_presentation
 ora se_l_mode
 ora se_l_pan
 ora se_l_pan+1
 ora se_l_pan+2
 ora se_ef_valid
 ora se_sel_mark
 ora se_e_error
 ora se_h_fault
 ora se_h_trimmed
 ora se_h_trimmed+1
 ora $912C
 ora $912D
 jne release
 lda GEC_OP
 cmp #2
 jcs release
 beq :+
 lda GEC_OLD
 bne @ordinary
: lda GEC_NEW
@ordinary:
 jsr ordinary
 jcs release
 ; The existingproducer authenticated GEC againstfullGCC key andsequence.
 ; Read the actualtypedFE header andrequire its exactsame publishedcontext.
 lda #0
 sta GP_IO_OFFSET
 sta GP_IO_OFFSET+1
 lda #<GP_HEADER
 ldx #>GP_HEADER
 ldy #64
 jsr read
 jcs release
 lda GP_HEADER+GPH_VALID
 cmp #1
 jne release
 lda GP_HEADER+GPH_MAGIC
 cmp #$47
 jne release
 lda GP_HEADER+GPH_VERSION
 cmp #GTC_PACKET_VERSION
 jne release
 ldx #36
@key:
 lda GP_HEADER+GPH_KEY,x
 cmp GCC_KEY,x
 jne release
 dex
 bpl @key
 ldx #2
@fold:
 lda GP_HEADER+GPH_FOLD_VALID,x
 cmp GCC_FOLD,x
 jne release
 dex
 bpl @fold
 lda GP_HEADER+GPH_COUNT
 jeq release
 cmp #23
 jcs release
 cmp GCC_COUNT
 jne release
 lda GP_HEADER+GPH_CARET_ROW
 cmp GP_HEADER+GPH_COUNT
 jcs release
 sta GTC_ROW
 jsr slot
 lda #<GP_RECORD
 ldx #>GP_RECORD
 ldy #32
 jsr read
 jcs release
 ldx #31
@prefix:
 lda GP_RECORD,x
 sta GTC_PREFIX,x
 dex
 bpl @prefix
 lda GP_RECORD+GPR_KIND
 ora GP_RECORD+GPR_FLAGS
 ora GP_RECORD+GPR_INLINE
 ora GP_RECORD+GPR_RASTER_X
 ora GP_RECORD+GPR_RASTER_X+1
 ora GP_RECORD+GPR_COUNT+1
 jne release
 lda GP_RECORD+GPR_HEIGHT
 cmp #9
 jne release
 lda GP_RECORD+GPR_TOP
 cmp #16
 jcc release
 cmp #184
 jcs release
 lda GP_RECORD+GPR_REASON
 jeq release
 cmp #3
 jcs release
 lda GP_RECORD+GPR_COUNT
 jeq release
 cmp #161
 jcs release
 CMP24 GP_RECORD+GPR_FIRST,GP_RECORD+GPR_START
 jne release
 SUB24 GP_RECORD+GPR_END,GP_RECORD+GPR_START,T
 lda T+1
 ora T+2
 jne release
 lda T
 cmp GP_RECORD+GPR_COUNT
 jne release
 SUB24 GEC_POSITION,GP_RECORD+GPR_START,T
 lda T+1
 ora T+2
 jne release
 lda T
 jeq release
 cmp GP_RECORD+GPR_COUNT
 bcc @inside
 jne release
 lda GEC_OP
 jne release                 ;delete atCR/EOF isnotordinary
@inside:
 sta GTC_INDEX
 ; Read/verify bothwhole style/role arrays withoneboundedrequesteach.
 lda #<GPR_STYLES
 ldx #>GPR_STYLES
 jsr zeros
 jcs release
 lda #<GPR_ROLES
 ldx #>GPR_ROLES
 jsr zeros
 jcs release
 ; Checkplain alphabetic opener andthe exact deleted source byte.
 lda #GPR_CHARS
 ldx #0
 jsr field
 lda #<S
 ldx #>S
 ldy GP_RECORD+GPR_COUNT
 jsr read
 jcs release
 lda S
 and #$7F
 cmp #$41
 jcc release
 cmp #$5B
 jcs release
 lda GEC_OP
 beq @x
 ldx GTC_INDEX
 lda S,x
 cmp GEC_OLD
 jne release
@x:
 lda GTC_INDEX
 asl
 sta T
 lda #0
 rol
 tax
 clc
 lda T
 adc #<GPR_X
 bcc :+
 inx
: pha
 txa
 clc
 adc #>GPR_X
 tax
 pla
 jsr field
 lda #<S
 ldx #>S
 ldy #4
 jsr read
 jcs release
 lda S
 sta GTC_X
 lda S+1
 sta GTC_X+1
 lda #0
 sta GTC_ADVANCE
 lda GTC_INDEX
 cmp GP_RECORD+GPR_COUNT
 beq @width
 sec
 lda S+2
 sbc S
 sta GTC_ADVANCE
 lda S+3
 sbc S+1
 jne release
 lda GTC_ADVANCE
 jeq release
 cmp #9
 jcs release
@width:
 lda GP_RECORD+GPR_COUNT
 asl
 sta T
 lda #0
 rol
 tax
 clc
 lda T
 adc #<GPR_X
 bcc :+
 inx
: pha
 txa
 clc
 adc #>GPR_X
 tax
 pla
 jsr field
 lda #<S
 ldx #>S
 ldy #2
 jsr read
 jcs release
 lda S
 sta GTC_WIDTH
 lda S+1
 sta GTC_WIDTH+1
 beq @revision
 cmp #1
 jne release
 lda S
 cmp #65
 jcs release
@revision:
 ldx #3
@copy:
 lda GEC_REVISION,x
 sta GTC_REVISION,x
 dex
 bpl @copy
 ; Prefetch normalfont glyph/advance into retiredphase. R30 independently
 ; authenticates the fonttag and CRC9+width against its trustedtable.
 lda GEC_OP
 beq @newchar
 lda GEC_OLD
 bne @screen
@newchar:
 lda GEC_NEW
@screen:
 jsr se_petscii_screen
 sta GTC_RESERVED
 lda #0
 sta GP_IO_OFFSET+1
 lda GTC_RESERVED
 asl
 rol GP_IO_OFFSET+1
 asl
 rol GP_IO_OFFSET+1
 asl
 rol GP_IO_OFFSET+1
 clc
 adc GTC_RESERVED
 sta GP_IO_OFFSET
 lda GP_IO_OFFSET+1
 adc #0
 sta GP_IO_OFFSET+1
 clc
 lda GP_IO_OFFSET
 adc #<GTF_DATA
 sta GP_IO_OFFSET
 lda GP_IO_OFFSET+1
 adc #>GTF_DATA
 sta GP_IO_OFFSET+1
 lda #<(GT_FRAME+GT_GLYPH)
 ldx #>(GT_FRAME+GT_GLYPH)
 ldy #9
 jsr read
 jcs release
 clc
 lda GTC_RESERVED
 adc #<GTF_WIDTHS
 sta GP_IO_OFFSET
 lda #>GTF_WIDTHS
 adc #0
 sta GP_IO_OFFSET+1
 lda #<(GT_FRAME+GT_ADVANCE)
 ldx #>(GT_FRAME+GT_ADVANCE)
 ldy #1
 jsr read
 jcs release
 jsr se_crc_init
 ldy #1
@crc:
 lda GTC,y
 jsr se_crc_byte
 iny
 cpy #45
 bcc @crc
 lda se_crc_value
 sta GTC_CRC
 lda se_crc_value+1
 sta GTC_CRC+1
 lda #1
 sta GTC_VALID
release:
 lda #0
 sta se_f_owner
no_claim:
 rts
ordinary:
 cmp #32
 bcc @bad
 cmp #$80
 bcc :+
 cmp #$A0
 bcc @bad
: cmp #'*'
 beq @bad
 cmp #'@'
 beq @bad
 cmp #$5C
 beq @bad
 cmp #'#'
 beq @bad
 cmp #':'
 beq @bad
 cmp #'-'
 beq @bad
 clc
 rts
@bad:
 sec
 rts
slot:
 lda GTC_ROW
 jmp se_gp_cache_slot
field:
 pha
 txa
 pha
 jsr slot
 pla
 tax
 pla
 clc
 adc GP_IO_OFFSET
 sta GP_IO_OFFSET
 txa
 adc GP_IO_OFFSET+1
 sta GP_IO_OFFSET+1
 rts
read:
 sta GP_IO_POINTER
 stx GP_IO_POINTER+1
 sty GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 jmp se_gp_cache_read
zeros:
 jsr field
 lda #<S
 ldx #>S
 ldy GP_RECORD+GPR_COUNT
 jsr read
 bcs @return
 ldy GP_RECORD+GPR_COUNT
@byte:
 dey
 lda S,y
 bne @bad
 tya
 bne @byte
 clc
@return:
 rts
@bad:
 sec
 rts
