; Registered C45 lexical gateway and bounded automatic construction.
; First eligible long CR per baseline; retry latch128 never borrows reserved64.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/geos/semantic-lex.inc"
.include "cache/lexical/link.inc"
.import se_f_owner,se_overlay_frame,se_overlay_call,se_render_caps
.import se_fs_state,se_fs_owned,se_fs_end,se_fs_count,se_fs_offset,se_fs_buffer,se_fs_done
.export entry,cache_hit
CTX=$9096
CS=CTX
CI=CTX+1
INDEX=CTX+22
USED=CTX+23
ERROR=CTX+26
PARK=$8F40
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
 lda ERROR
 jne fallback
 lda CS
 cmp #1
 jeq verify
 cmp #2
 jeq resolve_step
 cmp #3
 jeq consume_step
 cmp #4
 jeq allocate_step
 cmp #5
 jeq producer_started
 cmp #6
 jeq producer_ready
 cmp #7
 jeq finalize_step
 cmp #8
 jeq span_acked
 cmp #9
 jeq terminal_acked
 cmp #10
 jeq linked
 jmp argument
begin:
 ; Refuse competing jobs before touching their shared phase or own context.
 lda se_bc_flags
 and #BC_ACTIVE
 ora GLEX_SOURCE_ACTIVE
 ora GLEX_CONTEXT_VALID
 ora se_fs_owned
 jne busy
 lda #0
 sta CS
 sta ERROR
 sta CTX+28
 lda se_render_caps
 cmp #3
 jne fallback
 lda GSEM_FRAME+GSEM_COUNT
 jeq fallback
 cmp #129
 jcs fallback
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
 cmp #3
 jcc fallback
@long:
 CP GSEM_FRAME,CI,21
 ; At most one construction attempt per baseline. Even an authenticated
 ; unsupported topology/fault must not retry on every subsequent window.
 lda se_bc_flags
 and #128
 eor #128
 sta CTX+29
 lda se_bc_flags
 ora #128
 sta se_bc_flags
reopen:
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
 sta LX_LIVE
 sta CS
 lda se_bc_flags
 ora #BC_ACTIVE
 sta se_bc_flags
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
 lda #1
 sta CTX+28
 lda #0
 sta LL_STATE
 CP CI+GSEM_START,LL_QUERY,3
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
 lda #36
 ldx #0
 jmp se_overlay_call
resolve_step:
 lda #1
 jsr resolver
 jcs fallback
 cmp #1
 jeq pending
 cmp #4
 jeq construct
 cmp #0
 jne fallback
 CP CI+GSEM_QUERY,LQ_START,3
 lda CI+GSEM_COUNT
 sta LQ_COUNT
 lda #4
 jsr roles
 jcs fallback
 lda #3
 sta CS
 jmp pending
construct:
 ; R36 has ended its own lease and returned a real checked CR/source receipt.
 lda CTX+29
 jeq fallback
 lda #0
 sta CTX+29
 sta GLEX_SOURCE_ACTIVE
 sta GLEX_CONTEXT_VALID
 lda #5
 sta CS
 lda #0
 ldx #47
 jmp handoff
producer_started:
 lda LX_LIVE
 cmp #1
 jne fallback
 lda #0
 jsr roles
 jcs fallback
 cmp #3
 jeq fallback
 lda #4
 sta CS
 jmp pending
allocate_step:
 lda #1
 jsr roles
 jcs fallback
 cmp #1
 jeq pending
 cmp #0
 jne fallback
 lda #6
 sta CS
 lda #1
 ldx #47
 jmp handoff
producer_ready:
 lda LX_READY
 cmp #1
 beq @span
 cmp #2
 jne fallback
 lda #5
 jsr roles
 jcs fallback
 lda #7
 sta CS
 jmp pending
@span:
 lda #3
 jsr roles
 jcs fallback
 cmp #0
 jne fallback                 ;STREAM/refusal never ACKs an unstored span
 lda #8
 sta CS
 lda #3
 ldx #47
 jmp handoff
span_acked:
 lda #6
 sta CS
 lda #1
 ldx #47
 jmp handoff
finalize_step:
 lda #1
 jsr roles
 jcs fallback
 cmp #1
 jeq pending
 cmp #0
 jne fallback
 lda LP_STATE
 cmp #3
 jne fallback
 lda #9
 sta CS
 lda #3
 ldx #47
 jmp handoff
terminal_acked:
 lda LX_LIVE
 jne fallback
 lda #10
 sta CS
 lda #0
 ldx #49
 jmp handoff
linked:
 lda LL_STATE
 ora LX_LIVE
 jne fallback
 ; C49 uses 8200 as its real CR snapshot. Restore the verified parent packet
 ; before the fresh source comparison; the parked packet is never authority.
 ldx CI+GSEM_COUNT
@packet:dex
 lda PARK,x
 sta GLEX_SOURCE,x
 cpx #0
 bne @packet
 ; Resolve the newly committed root/CR again. Never consume a host/page seed.
 jmp reopen
roles:
 sta se_overlay_frame
 lda #37
 ldx #0
 jmp se_overlay_call
consume_step:
 lda #1
 jsr roles
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
 jsr cleanup
 lda #3
 ldx #25
 jmp handoff
cleanup:
 lda CS
 beq @done
 lda LX_LIVE
 beq @flags
 CP LX_READER,se_fs_state,86
 jsr se_fs_end
 CP se_fs_state,GLEX_SAVED_FS,86
 CP se_fs_state,LX_READER,86
@flags:
 lda se_bc_flags
 and #($FF-BC_ACTIVE)
 sta se_bc_flags
 lda CTX+28
 beq @clear
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
@done:rts
cancel:
 jsr cleanup
 lda #0
 sta GLEX_ACTIVE
 clc
 rts
pending:
 lda #1
 ldx #45
handoff:
 sta $9136
 stx $9135
 lda #1
 clc
 rts
busy:lda #$B2
 sec
 rts
argument:lda #$90
 sec
 rts
changed:
 jsr cleanup
 lda #0
 sta GLEX_ACTIVE
 lda #$B1
 sec
 rts
.include "cache/lexical/handoff.inc"
