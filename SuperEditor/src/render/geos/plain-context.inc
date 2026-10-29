; Internal literal-source context. This is NOT a SuperMark parser event.
; C20's actual geometry alone discovers CR/EOF/wrap boundaries. No checkpoint
; or semantic range is invented; all previous semantic outputs are cleared.
.ifndef SE_GEOS_PLAIN_CONTEXT
SE_GEOS_PLAIN_CONTEXT=1
.ifndef GS_RAW_SOURCE_KIND
GS_RAW_SOURCE_KIND=9
.endif
.macro GS_SET_RAW_CONTEXT
 ldx #GSEM_HEIGHT-GSEM_KIND
 lda #0
:
 sta GSEM_FRAME+GSEM_KIND,x
 dex
 bpl :-
 sta GSEM_FRAME+GSEM_CP_VALID
 sta GSEM_FRAME+GSEM_INLINE
 lda #GS_RAW_SOURCE_KIND
 sta GSEM_FRAME+GSEM_KIND
 sta GSEM_FRAME+GSEM_HEIGHT ;raw BSW pitch is explicitly9
.endmacro
.endif
