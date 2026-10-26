; Private C25 source-window gateway. Actual parent GSEM inputs are immutable.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/geos/semantic-lex.inc"
.include "cache/lexical-link-probe/api.inc"
.import se_f_owner,se_overlay_frame,se_overlay_call,se_render_caps
.import se_fs_state,se_fs_owned,se_fs_end,se_fs_count,se_fs_offset,se_fs_buffer,se_fs_done
.export entry,cache_hit
CTX=$9096
CS=CTX
CI=CTX+1                    ;actual GSEM bytes0..20
INDEX=CTX+22
USED=CTX+23
PARK=$8F40                   ;preserve COUNT<=128 callerpacket across role read
.macro CP source,target,n
 ldx #n-1
:
 lda source,x
 sta target,x
 dex
 bpl :-
.endmacro
.segment "CODE"
 OVL_BINDING
entry:
 lda se_f_owner
 cmp #4
 jne busy
 lda se_overlay_frame
 jeq begin
 cmp #2
 jeq cancel
 cmp #1
 jne argument
 lda CS
 jeq argument
 ldx #20
@frozen:lda GSEM_FRAME,x
 cmp CI,x
 jne changed
 dex
 bpl @frozen
 lda CS
 cmp #1
 jeq verify
 cmp #2
 jeq resolve_step
 cmp #3
 jeq consume_step
 jmp argument
begin:
 lda #0
 sta CS
 lda se_render_caps
 cmp #3
 jne fallback
 lda GSEM_FRAME+GSEM_COUNT
 jeq fallback
 cmp #129
 jcs fallback
 ; Proven short25B case loses. Private admission threshold is conservative,
 ; not a claimed measured universal optimum; actual retainedref stillrequired.
 sec
 lda GSEM_FRAME+GSEM_END
 sbc GSEM_FRAME+GSEM_BODY
 lda GSEM_FRAME+GSEM_END+1
 sbc GSEM_FRAME+GSEM_BODY+1
 tax
 lda GSEM_FRAME+GSEM_END+2
 sbc GSEM_FRAME+GSEM_BODY+2
 jcc fallback
 bne @long
 txa
 jeq fallback
@long:
 lda GLEX_SOURCE_ACTIVE
 ora GLEX_CONTEXT_VALID
 ora se_fs_owned
 jne busy
 CP GSEM_FRAME,CI,21
 lda #0
 sta INDEX
 ldx #85
@clear:sta se_fs_state,x
 dex
 bpl @clear
 jsr source
 jcs fallback
 lda #1
 sta GLEX_SOURCE_ACTIVE
 sta GLEX_CONTEXT_VALID
 sta CS
 jmp pending
source:
 sta se_overlay_frame
 lda #14
 ldx #0
 jsr se_overlay_call
 php
 pha
 CP se_fs_state,GLEX_SAVED_FS,86
 CP se_fs_state,LX_READER,86
 pla
 plp
 rts
verify:
 ; One actual <=32-byte source read perforegroundslice, packet equality is
 ; retained from strictC25 ratherthan trusting a rendered byte/name alone.
 lda CI+GSEM_COUNT
 sec
 sbc INDEX
 cmp #33
 bcc :+
 lda #32
:
 sta USED
 sta se_fs_count
 clc
 lda CI+GSEM_QUERY
 adc INDEX
 sta se_fs_offset
 lda CI+GSEM_QUERY+1
 adc #0
 sta se_fs_offset+1
 lda CI+GSEM_QUERY+2
 adc #0
 sta se_fs_offset+2
 lda #<GLEX_PACKET
 sta se_fs_buffer
 lda #>GLEX_PACKET
 sta se_fs_buffer+1
 lda #2
 jsr source
 jcs fallback
 lda se_fs_done
 jeq fallback
 cmp USED
 bcc @actual
 jne fallback
@actual:sta USED
 ldy #0
 ldx INDEX
@byte:lda GLEX_SOURCE,x
 cmp GLEX_PACKET,y
 jne fallback
 sta PARK,x
 inx
 iny
 cpy USED
 bne @byte
 stx INDEX
 cpx CI+GSEM_COUNT
 jne pending
 lda #0
 sta LL_STATE
 lda #1
 sta LX_LIVE
 CP CI+GSEM_BODY,LL_QUERY,3
 lda #3
 jsr resolver
 jcs fallback
 cmp #2
 jeq fallback
 lda #2
 sta CS
 jmp pending
resolver:
 sta se_overlay_frame
 lda #30
 ldx #0
 jmp se_overlay_call
resolve_step:
 lda #1
 jsr resolver
 jcs fallback
 cmp #1
 jeq pending
 cmp #0
 jne fallback
 CP CI+GSEM_QUERY,LQ_START,3
 lda CI+GSEM_COUNT
 sta LQ_COUNT
 lda #4
 jsr consumer
 jcs fallback
 lda #3
 sta CS
 jmp pending
consumer:
 sta se_overlay_frame
 lda #26
 ldx #0
 jmp se_overlay_call
consume_step:
 lda #1
 jsr consumer
 jcs fallback
 cmp #1
 jeq pending
 cmp #0
 jne fallback
 lda LQ_READY
 cmp #1
 jne fallback
cache_hit:
 ldx CI+GSEM_COUNT
@roles:dex
 lda LX_ROLES,x
 sta GLEX_ROLES,x
 lda PARK,x
 sta GLEX_SOURCE,x
 cpx #0
 bne @roles
 jsr cleanup
 lda #0
 sta GLEX_ACTIVE
 jmp se_gp_preview_complete
fallback:
 sta CTX+24
 lda CS
 sta CTX+25
 ; The originalC25lexer/controller is a distinct privateC39 image. Its only
 ; changedconstant is ownREQUEST id39; actual rootoddworker protocol resumesC21.
 jsr cleanup
 lda #0
 sta $9136
 lda #39
 sta $9135
 lda #1
 clc
 rts
cleanup:
 lda GLEX_CONTEXT_VALID
 beq @clear
 CP LX_READER,se_fs_state,86
 jsr se_fs_end
 CP se_fs_state,GLEX_SAVED_FS,86
 CP se_fs_state,LX_READER,86
 ; Consumer may have partiallywritten provisionalroles into rawpacket8200.
 lda INDEX
 cmp CI+GSEM_COUNT
 bne @clear
 ldx CI+GSEM_COUNT
@packet:dex
 lda PARK,x
 sta GLEX_SOURCE,x
 cpx #0
 bne @packet
@clear:lda #0
 sta CS
 sta GLEX_CONTEXT_VALID
 sta GLEX_SOURCE_ACTIVE
 sta LX_LIVE
 rts
cancel:
 jsr cleanup
 lda #0
 sta GLEX_ACTIVE
 clc
 rts
pending:
 lda #25
 sta $9135
 lda #1
 sta $9136
 clc
 rts
busy:lda #$B2
 sec
 rts
argument:lda #$90
 sec
 rts
.include "render/geos/preview-handoff.inc"

changed:
 jsr cleanup
 lda #0
 sta GLEX_ACTIVE
 lda #$B1
 sec
 rts
