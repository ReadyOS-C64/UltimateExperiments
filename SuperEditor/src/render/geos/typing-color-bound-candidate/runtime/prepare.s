; Genuine-style local grammar proof. No bitmap/cache mutation before admission.
.setcpu "6502"
.macpack longbranch
.include "render/geos/typing/guard.inc"
.include "render/geos/style-typing/wide.inc"
.include "transform-stage.inc"
.import se_gst_transform
.export se_gst_prepare
P=GTT_PACKET
F=GT_FRAME
S=GST_FRAME
STYLE=S+GST_STYLE
.segment "CODE"
se_gst_prepare:
 ldx P+GPR_COUNT
 jeq bad
 lda #0
 sta S+GST_INVERSE
@roles:
 dex
 lda P+GPR_ROLES,x
 jne bad
 lda P+GPR_STYLES,x
 cmp #4
 jcs bad
 ora S+GST_INVERSE
 sta S+GST_INVERSE
 cpx #0
 bne @roles
 lda S+GST_INVERSE
 ora P+GPR_INLINE
 beq @normal
 ; The edited byte and its unchanged adjacent characters are alphanumeric.
 ; Equal style prevents crossing a matched delimiter; no £ escape adjacency.
 ldx GTT_INDEX
 jeq bad
 cpx P+GPR_COUNT
 jcs bad
 lda P+GPR_STYLES,x
 sta STYLE
 lda P+GPR_CHARS-1,x
 jsr alnum
 jcs bad
 lda P+GPR_STYLES-1,x
 cmp STYLE
 jne bad
 lda P+GPR_CHARS,x
 jsr alnum
 jcs bad
 lda GEC_OP
 beq @insert
 inx
 cpx P+GPR_COUNT
 jcs bad
 lda P+GPR_CHARS,x
 jsr alnum
 jcs bad
 lda P+GPR_STYLES,x
 cmp STYLE
 jne bad
 beq @transform
@insert:
 lda GEC_NEW
 jsr alnum
 jcs bad
 bcc @transform
@normal:
 lda #0
 sta STYLE
@transform:
 ldx #8
@normal_copy:
 lda $8B4A,x
 sta S+GST_NORMAL,x
 dex
 bpl @normal_copy
 lda $8B43
 sta S+GST_WIDTH
 lda #0
 sta S+GST_INVERSE
 jsr se_gst_transform
 jcs bad
 lda S+GST_ADVANCE
 sta F+GT_ADVANCE
 ldx #17
@ink:
 lda S+GST_INK,x
 sta F+GT_GLYPH,x
 dex
 bpl @ink
 clc
 rts
bad:
 sec
 rts
alnum:
 and #$7F
 cmp #$30
 bcc @no
 cmp #$3A
 bcc @yes
 cmp #$41
 bcc @no
 cmp #$5B
 bcs @no
@yes: clc
 rts
@no: sec
 rts
