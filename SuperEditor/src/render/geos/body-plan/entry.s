.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "object/api.inc"
.include "render/geos/body-plan/api.inc"
.include "document/math24.inc"
.export entry
.segment "CODE"
OVL_BINDING
entry:
 lda se_f_owner
 cmp #4
 jne busy
 lda $9135
 cmp #20
 beq :+
 cmp #26
 jne bad
:
 lda se_overlay_frame
 sta VP_FRAME
 cmp #3
 beq @publication
 cmp #5
 beq @publication
 lda GS_ACTIVE
 cmp #1
 jne bad
 lda GS_CONTEXT_VALID
 cmp #1
 jne bad
 jmp @dispatch
@publication:
 lda GS_ACTIVE
 ora GS_CONTEXT_VALID
 jne bad
 lda GI_ACTIVE
 cmp #1
 jne bad
 lda GI_PHASE
 cmp #4
 jne bad
@dispatch:
 lda VP_FRAME
 cmp #0
 jeq prepare
 cmp #4
 bne :+
 lda VP_VALID
 cmp #$A5
 jne packet_miss
 ldx #4
 lda #0
@token_present:
 ora se_bc_arena,x
 dex
 bpl @token_present
 cmp #0
 jeq packet_miss ;checked optional retirement deliberately publishes NIL
 jsr source_match
 jcs packet_miss
:
 jsr guard
 jcs done
 lda VP_FRAME
 cmp #1
 jeq paint
 cmp #2
 jeq hide
 cmp #3
 jeq collect_done
 cmp #4
 jeq packet
 cmp #5
 jeq publish
 jmp bad
busy:lda #$B2
 sec
 rts
bad:lda #$90
 sec
 rts
stale:lda #$74
 sec
 rts
corrupt:lda #$18
 sec
 rts
miss:lda #2
 clc
done:rts
success:lda #0
 clc
 rts
; Caller source guard/lease is real. The first29 identity bytes name logical content
; through render revision; hot-window transport placement is not presentation input.
source_match:
 ldx #28
@key:lda GS_FS+27,x
 cmp VP_KEY,x
 bne @miss
 dex
 bpl @key
 lda se_render_caps
 cmp VP_CAPS
 bne @miss
 clc
 rts
@miss:sec
 rts
guard:
 jsr source_match
 jcs stale
 COPY24 se_bc_arena,se_object_id
 lda se_bc_arena+3
 sta se_object_token_epoch
 lda se_bc_arena+4
 sta se_object_token_epoch+1
 jsr se_object_validate
 jcs done
 lda object_owner,x
 cmp #$53
 jne stale
 lda object_banks,x
 cmp #1
 jne corrupt
 lda object_size_lo,x
 ora object_size_mid,x
 jne corrupt
 lda object_size_hi,x
 cmp #1
 jne corrupt
 jmp success
context:
 ldx #2
@same:lda GI_START,x
 cmp VP_START,x
 bne @miss
 lda GI_BODY,x
 cmp VP_BODY,x
 bne @miss
 lda GI_END,x
 cmp VP_END,x
 bne @miss
 dex
 bpl @same
 lda GI_BASE
 cmp VP_BASE
 bne @miss
 clc
 rts
@miss:sec
 rts
; BEGIN returns0 complete authenticated reuse,1 new collection,2 legacy fallback.
prepare:
 lda se_r_presentation
 jne miss
 lda VP_VALID
 cmp #$A5
 bne @new
 jsr guard
 bcs @new
 jsr context
 bcs @new
 COPY24 GI_QUERY,VP_DELTA
 lda GI_COUNT
 sta VP_COUNT
 jsr in_range
 bcs @new
 jmp success
@new:
 lda GI_SOURCE_RETURN
 cmp #1
 jne miss ;normal preview/wide remains direct pure-parser fallback
 lda #0
 sta VP_VALID
 ldx #28
@key:lda GS_FS+27,x
 sta VP_KEY,x
 dex
 bpl @key
 COPY24 GI_QUERY,VP_ORIGIN
 COPY24 GI_START,VP_START
 COPY24 GI_BODY,VP_BODY
 COPY24 GI_END,VP_END
 COPY24 GI_END,VP_LIMIT
 ; Plan at most4096 canonical bytes, never truncates full BODY parser scan.
 sec
 lda GI_END
 sbc GI_QUERY
 sta VP_DELTA
 lda GI_END+1
 sbc GI_QUERY+1
 sta VP_DELTA+1
 lda GI_END+2
 sbc GI_QUERY+2
 jcc @fallback
 bne @cap
 lda VP_DELTA+1
 cmp #16
 bcc @bounded
@cap:
 clc
 lda GI_QUERY+1
 adc #16
 sta VP_LIMIT+1
 lda GI_QUERY+2
 adc #0
 jcs @fallback
 sta VP_LIMIT+2
 lda GI_QUERY
 sta VP_LIMIT
@bounded:
 lda GI_BASE
 sta VP_BASE
 lda se_render_caps
 sta VP_CAPS
 ldx #4
 lda #0
@present:ora se_bc_arena,x
 dex
 bpl @present
 cmp #0
 bne @validate
 lda #$53
 ldx #1
 jsr se_object_create
 bcc @capture
 cmp #$35
 jeq @fallback
 cmp #1
 jeq @fallback
 sec
 rts
@capture:
 ldx #4
@capcopy:lda se_object_id,x
 sta se_bc_arena,x
 dex
 bpl @capcopy
 lda #0
 sta se_object_offset
 sta se_object_offset+1
 lda #1
 sta se_object_offset+2
 jsr se_object_resize
 jcs done
@validate:
 jsr guard
 jcs done
 lda #0
 sta VP_BLOCK
@init:
 lda VP_BASE
 asl
 asl
 ldx #31
@fill:sta VP_IO,x
 dex
 bpl @fill
 jsr store
 jcs done
 inc VP_BLOCK
 lda VP_BLOCK
 cmp #128
 beq @ready
 ; Stop after last partly used32-entry record.
 lda VP_BLOCK
 sta VP_DELTA
 lda #0
 sta VP_DELTA+1
.repeat 5
 asl VP_DELTA
 rol VP_DELTA+1
.endrepeat
 clc
 lda VP_ORIGIN
 adc VP_DELTA
 sta VP_DELTA
 lda VP_ORIGIN+1
 adc VP_DELTA+1
 sta VP_DELTA+1
 lda VP_ORIGIN+2
 adc #0
 sta VP_DELTA+2
 CMP24 VP_DELTA,VP_LIMIT
 bcc @init
@ready:lda #1
 clc
 rts
@fallback:jmp miss
; Input VP_DELTA canonical and count; output offset relative to plan.
in_range:
 CMP24 VP_DELTA,VP_ORIGIN
 bcc @miss
 sec
.repeat 3,I
 lda VP_DELTA+I
 sbc VP_ORIGIN+I
 sta VP_DELTA+I
.endrepeat
 lda VP_DELTA+2
 bne @miss
 lda VP_DELTA+1
 cmp #16
 bcs @miss
 ; count addition checked against exact canonical LIMIT.
 clc
 lda VP_DELTA
 adc VP_COUNT
 sta VP_STOP
 lda VP_DELTA+1
 adc #0
 sta VP_STOP+1
 lda #0
 adc #0
 sta VP_STOP+2
 clc
.repeat 3,I
 lda VP_STOP+I
 adc VP_ORIGIN+I
 sta VP_STOP+I
.endrepeat
 CMP24 VP_LIMIT,VP_STOP
 bcc @miss
 clc
 rts
@miss:sec
 rts
; Compute block/index from relative VP_DELTA.
locate:
 lda VP_DELTA
 and #31
 sta VP_INDEX
 lda VP_DELTA+1
 asl
 asl
 asl
 sta VP_BLOCK
 lda VP_DELTA
 lsr
 lsr
 lsr
 lsr
 lsr
 ora VP_BLOCK
 sta VP_BLOCK
 rts
; Object offset = block*34; all actual transfers carry complete typed guard.
io:
 pha
 jsr guard
 bcs @fail
 lda VP_BLOCK
 cmp #128
 bcs @range
 sta se_object_offset
 lda #0
 sta se_object_offset+1
.repeat 5
 asl se_object_offset
 rol se_object_offset+1
.endrepeat
 clc
 lda VP_BLOCK
 asl
 adc se_object_offset
 sta se_object_offset
 lda se_object_offset+1
 adc #0
 sta se_object_offset+1
 lda #0
 sta se_object_offset+2
 sta se_object_length+1
 lda #34
 sta se_object_length
 lda #<VP_IO
 sta se_object_c64
 lda #>VP_IO
 sta se_object_c64+1
 pla
 jmp se_object_copy
@range:lda #$7B
 sec
@fail:tax
 pla
 txa
 rts
crc:
 jsr se_crc_init
 ldy #0
@byte:lda VP_IO,y
 jsr se_crc_byte
 iny
 cpy #32
 bne @byte
 rts
fetch:
 lda #1
 jsr io
 jcs done
 jsr crc
 lda se_crc_value
 cmp VP_IO+32
 jne corrupt
 lda se_crc_value+1
 cmp VP_IO+33
 jne corrupt
 ldx #31
@schema:
 lda VP_IO,x
 and #$3C
 cmp #$38
 jcs corrupt
 lda VP_IO,x
 bpl @next
 and #$BF
 cmp #$90
 jne corrupt
@next:dex
 bpl @schema
 jmp success
store:
 jsr crc
 lda se_crc_value
 sta VP_IO+32
 lda se_crc_value+1
 sta VP_IO+33
 lda #0
 jmp io
; Confirmed inline event clipping is the same exclusive-code/OR-style policy.
paint:
 COPY24 GI_FROM,VP_DELTA
 COPY24 GI_TO,VP_STOP
 lda GI_STYLE
 sta VP_MODE
 jmp span
hide:
 COPY24 GI_HIDE_POS,VP_DELTA
 clc
 lda GI_HIDE_POS
 adc GI_HIDE_LEFT
 sta VP_STOP
 lda GI_HIDE_POS+1
 adc #0
 sta VP_STOP+1
 lda GI_HIDE_POS+2
 adc #0
 sta VP_STOP+2
 lda #$40
 sta VP_MODE
span:
 CMP24 VP_DELTA,VP_ORIGIN
 bcs :+
 COPY24 VP_ORIGIN,VP_DELTA
: CMP24 VP_STOP,VP_LIMIT
 bcc :+
 COPY24 VP_LIMIT,VP_STOP
: CMP24 VP_STOP,VP_DELTA
 jcc success
 jeq success
 sec
.repeat 3,I
 lda VP_DELTA+I
 sbc VP_ORIGIN+I
 sta VP_DELTA+I
.endrepeat
 sec
.repeat 3,I
 lda VP_STOP+I
 sbc VP_ORIGIN+I
 sta VP_STOP+I
.endrepeat
 jsr locate
@block:
 jsr fetch
 jcs done
 ldx VP_INDEX
@cell:
 lda VP_MODE
 cmp #$40
 beq @or
 lda VP_MODE
 bmi @code
 lda VP_IO,x
 bmi @next
 lda VP_MODE
@or:ora VP_IO,x
 sta VP_IO,x
 jmp @next
@code:lda VP_IO,x
 and #$40
 ora #$90 ;exclusive + code role4 + style0
 sta VP_IO,x
@next:
 inc VP_DELTA
 bne :+
 inc VP_DELTA+1
 bne :+
 inc VP_DELTA+2
:
 CMP24 VP_DELTA,VP_STOP
 beq @last
 inx
 cpx #32
 bcc @cell
 jsr store
 jcs done
 inc VP_BLOCK
 lda #0
 sta VP_INDEX
 jmp @block
@last:jmp store
collect_done:
 lda #$A5
 sta VP_VALID
 jmp success
; Real C20 packet fetch; miss invokes old complete-body path before publication.
packet:
 lda VP_VALID
 cmp #$A5
 jne packet_miss
 lda GEOS_LINE_FRAME+GL_MAP_COUNT+1
 jne bad
 lda GEOS_LINE_FRAME+GL_MAP_COUNT
 cmp #162
 jcs bad
 COPY24 GEOS_LINE_FRAME+GL_SCAN,VP_DELTA
 lda #0
 sta VP_COUNT
 lda GSEM_FRAME+GSEM_ROLE
 cmp VP_BASE
 jne packet_miss
 COPY24 GSEM_FRAME+GSEM_START,VP_STOP
 CMP24 VP_STOP,VP_START
 jne packet_miss
 COPY24 GSEM_FRAME+GSEM_BODY,VP_STOP
 CMP24 VP_STOP,VP_BODY
 jne packet_miss
 COPY24 GSEM_FRAME+GSEM_END,VP_STOP
 CMP24 VP_STOP,VP_END
 jne packet_miss
 jsr in_range
 jcs packet_miss
 ; Refill existing checked160B window, not each32B source packet.
 SUB24 VP_LIMIT,GEOS_LINE_FRAME+GL_SCAN,VP_STOP
 lda VP_STOP+1
 ora VP_STOP+2
 bne @maximum
 lda VP_STOP
 cmp #160
 bcc @amount
@maximum:lda #160
@amount:
 sta VP_COUNT
 sta SW_COUNT
 COPY24 GEOS_LINE_FRAME+GL_SCAN,SW_START
 lda #0
 sta SW_VALID ;never consume partial output after an integrity failure
 lda #4
 jmp output
packet_miss:lda #2
 sec
 rts
publish:
 COPY24 GI_QUERY,VP_DELTA
 lda GI_COUNT
 sta VP_COUNT
 jsr in_range
 jcs stale
 lda #5
output:
 sta VP_FRAME
 lda VP_COUNT
 jeq output_done
 lda #0
 sta VP_OUTPUT
 ldx #20
@hidden:sta GI_OUTPUT_HIDDEN,x
 dex
 bpl @hidden
@start:
 jsr locate
@block:
 jsr fetch
 jcs done
@entry:
 ldy VP_OUTPUT
 ldx VP_INDEX
 lda VP_IO,x
 sta VP_BITS
 and #3
 sta GI_OUTPUT_STYLES,y
 lda VP_BITS
 lsr
 lsr
 and #15
 cpy #160
 bne :+
 sta GI_OUTPUT_ROLE_LAST
 jmp @hiddenbit
:sta GI_OUTPUT_ROLES,y
@hiddenbit:
 lda VP_BITS
 and #$40
 beq @next
 tya
 and #7
 tax
 lda bits,x
 sta VP_BITS
 tya
 lsr
 lsr
 lsr
 tax
 lda VP_BITS
 ora GI_OUTPUT_HIDDEN,x
 sta GI_OUTPUT_HIDDEN,x
 jmp @next
@next:
 inc VP_OUTPUT
 lda VP_OUTPUT
 cmp VP_COUNT
 jeq output_done
 inc VP_INDEX
 lda VP_INDEX
 cmp #32
 bcc @entry
 lda #0
 sta VP_INDEX
 inc VP_BLOCK
 jmp @block
output_done:
 lda VP_FRAME
 cmp #4
 jne success
 lda #1
 sta SW_VALID
 jmp success
.segment "RODATA"
bits:.byte $80,$40,$20,$10,$08,$04,$02,$01
