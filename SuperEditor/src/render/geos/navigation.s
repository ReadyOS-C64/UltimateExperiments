; Sequential proportional navigation controller. C20 is entered only by root.
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/presentation.inc"
.include "render/geos/plain-context.inc"
.include "render/geos/edit-certificate.inc"
.include "render/geos/typing/certificate.inc"
.global se_render_caps,se_ef_visible
.global se_gc_width
.include "seed-witness.inc"
.include "nav-witness.inc"
.include "cache/api.inc"
.include "render/geos/editor.inc"
.include "render/geos/source-line.inc"
.include "render/geos/navigation.inc"
.include "render/geos/semantic.inc"
.include "render/geos/fold-query.inc"
.include "render/geos/checkpoint/codec.inc"
.include "document/math24.inc"
; Private space recovery for the local E_POSITION controller. Every use below
; has disjoint three-byte operands, dead X, and consumes neither A nor N/Z from
; the copy. Carry is preserved. The real arithmetic macros remain unchanged.
.macro NAV_COPY24 source,target
 ldx #2
 ; Force absolute indexing: the backward branch spans exactly3+3+1 bytes.
 ; No named/anonymous macro label may change the caller's cheap-label scope.
 lda a:source,x
 sta a:target,x
 dex
 bpl *-7
.endmacro

; Unsigned24-bit comparison: C/Z exactly match CMP24; A/X are dead.
; Unequal branches preserve the decisive CMP; all-equal LDA0 restores Z
; without changing C=1. N is also equivalent; every use treats X as dead.
; Fixed branches avoid injecting labels into the caller's cheap-label scope.
.macro NAV_EQUAL24 source,target
 ldx #2
 lda a:source,x
 cmp a:target,x
 bne *+7
 dex
 bpl *-9
 lda #0
.endmacro
.import se_f_owner,se_e_command,se_e_target,se_hot_caret,se_v_top,se_view_init
.import se_doc_meta,se_doc_generation,se_doc_epoch,se_reu_epoch,se_r_revision,se_v_length
.import se_l_pan,se_l_mode,se_l_manual,se_l_preferred,se_n_preferred_valid
.import se_i_ready,se_i_count,se_n_cache_count,se_l_valid,se_r_valid,se_l_need_wrap
.import se_ef_valid,se_ef_generation,se_ef_key_match,se_ef_motion_tick
.import se_geos_cancel
.import se_overlay_ids,image_slot,image_size_lo,image_size_hi,image_crc_lo,image_crc_hi
.import se_overlay_capacity
.import se_hot_ready,se_hot_phase
.export entry,se_gn_request,se_gn_operation,se_gn_state
se_gn_request=GN_REQUEST
se_gn_operation=GN_OPERATION
se_gn_state=GN_STATE
L=GEOS_LINE_FRAME
GN_FOLD_VALID=$CF80
GN_FOLD_GENERATION=$CF81
.macro FIELDS action
 action se_doc_meta,0,15
 action se_doc_generation,15,2
 action se_r_revision,17,4
 action se_v_length,21,3
 action se_reu_epoch,24,2
 action se_doc_epoch,26,2
.endmacro
.macro capture source,offset,size
 ldx #size-1
: lda source,x
 sta GN_KEY+offset,x
 dex
 bpl :-
.endmacro
.macro compare source,offset,size
 ldx #size-1
: lda source,x
 cmp GN_KEY+offset,x
 jne changed
 dex
 bpl :-
.endmacro
.segment "GEOS_NAVIGATION"
 OVL_BINDING
entry:
 lda se_overlay_frame
 beq begin
 lda se_f_owner
 cmp #GN_OWNER
 jne busy
 lda se_overlay_frame
 cmp #GN_CANCEL
 jeq se_geos_cancel
 cmp #GN_STEP
 jne argument
 jsr guard
 jcs return
 lda GN_STATE
 cmp #7
 jeq fold_advance
 cmp #1
 jeq cache_query
 cmp #2
 jeq stream
 cmp #3
 jeq cache_target
 cmp #4
 jeq hit_done
 cmp #5
 jeq semantic_ready
 cmp #6
 jeq cache_page_step
 cmp #9
 jeq nav_query_ready
 cmp #10
 jeq metric_ready
 cmp #8
 jeq local_seed_ready
 jmp argument
begin:
 lda se_f_owner
 jne busy
 lda se_e_command
 cmp #74
 bcc @ordinary
 cmp #76
 jcs argument
 bcc @valid ;PAN auto-enables logical rows only after successful measurement
@ordinary:
 cmp #47
 beq @valid
 cmp #36
 jcc argument
 cmp #40
 jcs argument
@valid:
 pha
 ; A committed cut/replay can request E_POSITION before the next redraw's
 ; retention safe point. Retire only its stale projection before claiming
 ; GEOS state; the journal retains the old map hints for ordered rebuilding.
 jsr se_ef_visible
 beq @admit
 jsr se_ef_key_match
 bcc @admit
 cmp #$B7
 beq @admit
 tax
 pla
 txa
 sec
 rts
@admit:
 lda #GN_OWNER
 sta se_f_owner
 lda #0
 sta GS_ACTIVE
 sta GFQ_ACTIVE
 sta GS_CONTEXT_VALID
 sta se_i_ready
 sta se_i_count
 sta se_n_cache_count
 sta GN_TOP_VALID
 sta GN_FLAGS
 sta GN_CACHE_INDEX
 sta GN_CACHE_COUNT
 sta GSEM_FRAME+GSEM_CP_VALID
 jsr se_ef_visible
 sta GN_FOLD_VALID
 ldx #1
@fold_generation:
 lda se_ef_generation,x
 sta GN_FOLD_GENERATION,x
 dex
 bpl @fold_generation
 pla
 sta GN_COMMAND
 lda #1
 sta GN_DELTA
 lda GN_COMMAND
 cmp #38
 bcc :+
 lda #GN_PAGE_PIXELS
 sta GN_DELTA
:
 ldx #2
@inputs:
 lda se_hot_caret,x
 ldy GN_COMMAND
 cpy #47
 bne :+
 lda se_e_target,x
:
 sta GN_QUERY,x
 lda se_v_top,x
 sta GN_TOP,x
 lda se_l_pan,x
 sta GN_PAN,x
 lda se_l_preferred,x
 sta GN_PREFERRED,x
 dex
 bpl @inputs
 lda se_l_mode
 sta GN_MODE
 lda se_n_preferred_valid
 cmp #2
 bne :+
 inc GN_FLAGS
:
 jsr se_view_init
 jcs return
 FIELDS capture
 lda GN_COMMAND
 cmp #74
 bcc :+
 lda se_render_caps
 beq cold ;raw PAN must discover logical START with real C20 CR scans
 lda #0
 sta GN_PASS
 NAV_COPY24 GN_QUERY,GN_SCAN
 jmp line_begin ;C24 resolves the actual logical line, never byte-count clamp
:
 ; The page is an optimization only. Stale/unavailable FE falls back to a
 ; bounded canonical scan; C20 still validates actual source reads.
 jsr se_gp_cache_guard
 bcs cold
 lda GP_HEADER+GPH_VALID
 cmp #1
 bne cold
 lda GP_HEADER+GPH_COUNT
 beq cold
 sta GN_CACHE_COUNT
 lda #1
 sta GN_STATE
 jmp own_pending
cold:
 lda GN_FLAGS
 and #1
 sta GN_FLAGS
 lda #0
 sta GN_PASS
 ldx #2
@clear:
 sta GN_SCAN,x
 sta GN_ORDINAL,x
 dex
 bpl @clear
 ; E_POSITION only: a validated incoming parser context at the unchanged
 ; viewport can replace the global scan. PAGE's global pixel origin is not
 ; inferred from a local row. Folded reveal keeps its existing full route.
 lda se_render_caps
 jeq local_seed_miss
 lda GN_COMMAND
 cmp #47
 jne local_seed_miss
 lda GN_FOLD_VALID
 jne local_seed_miss
 NAV_EQUAL24 GN_TOP,GCC_KEY+28
 jne local_seed_miss
 NAV_EQUAL24 GN_PAN,GCC_KEY+31
 jne local_seed_miss
 jsr local_seed_cap
 jcs local_seed_miss
 lda #0
 sta GSC_SELECTOR
 NAV_EQUAL24 GN_QUERY,GN_TOP
 bcs @current
 inc GSC_SELECTOR ;actual predecessor is independently bound to old GCC TOP
 NAV_COPY24 GN_QUERY,GSEM_FRAME+GSEM_QUERY
 jmp @seed
@current:
 NAV_COPY24 GN_TOP,GSEM_FRAME+GSEM_QUERY
@seed:
 lda GEC_VALID
 sta GSC_ALLOW_EDIT
 lda #8
 sta GN_STATE
 lda #24
 ldx #3
 jmp request
local_seed_ready:
 lda GSC_PROOF
 beq local_seed_miss
 cmp #3
 bcs local_seed_miss
 lda GSC_SELECTOR
 bne @previous
 NAV_EQUAL24 GSC_INCOMING,GN_TOP
 bne local_seed_miss
 jmp @accept
@previous:
 ; Accepted predecessor must not lie after the requested canonical caret.
 NAV_EQUAL24 GSC_INCOMING,GN_QUERY
 bcc @accept
 bne local_seed_miss
@accept:
 NAV_COPY24 GSC_INCOMING,GN_SCAN
local_seed_miss:
 jmp line_begin
; Same resident binding alone does not establish C24's new operation3 ABI.
; The normal loader still authenticates the complete actual image on entry.
local_seed_cap:
 ldy #0
 beq cap_common
nav_selector_cap:
 ldy #5
cap_common:
 ldx #0
@next:
 lda se_overlay_ids,x
 cmp cap_table,y
 bne @advance
 lda image_slot,x
 and #1
 beq @advance
 lda image_size_lo,x
 cmp cap_table+1,y
 bne @bad
 lda image_size_hi,x
 cmp cap_table+2,y
 bne @bad
 lda image_crc_lo,x
 cmp cap_table+3,y
 bne @bad
 lda image_crc_hi,x
 cmp cap_table+4,y
 bne @bad
 clc
 rts
@advance:
 inx
 cpx #<se_overlay_capacity
 bcc @next
@bad:
 lda #$90
 sec
 rts
cache_query:
 lda GN_CACHE_INDEX
 cmp GN_CACHE_COUNT
 jcs cold
 jsr prefix
 jcs return
 NAV_EQUAL24 GN_QUERY,GP_RECORD+GPR_START
 jcc cold
 NAV_EQUAL24 GN_QUERY,GP_RECORD+GPR_END
 bcc @found
 bne @next
 lda GP_RECORD+GPR_REASON
 cmp #GL_EOF+1
 bcc @found
@next:
 inc GN_CACHE_INDEX
 jmp own_pending
@found:
 NAV_COPY24 GP_RECORD+GPR_START,GN_SCAN
 jsr cache_height
 jcs return
 lda GN_CACHE_INDEX
 sta GN_CACHE_ROW
 sta GN_CACHE_TARGET
 lda GN_COMMAND
 cmp #47
 beq cache_fast_ready
 cmp #38
 jcs cache_page
 cmp #36
 beq @up
 cmp #38
 beq @up
 clc
 lda GN_CACHE_INDEX
 adc GN_DELTA
 cmp GN_CACHE_COUNT
 jcs cold
 bcc @target
@up:
 sec
 lda GN_CACHE_INDEX
 sbc GN_DELTA
 jcc cold
@target:
 sta GN_CACHE_TARGET
@ready:
cache_fast_ready:
 lda GN_FLAGS
 ora #2
 sta GN_FLAGS
 lda #2
 sta GN_PASS
 jmp line_begin
cache_target:
 lda GN_CACHE_TARGET
 sta GN_CACHE_INDEX
 jsr prefix
 jcs return
 NAV_COPY24 GP_RECORD+GPR_START,GN_SCAN
 jsr cache_height
 jcs return
 lda #3
 sta GN_PASS
 jmp line_begin
cache_height:
 lda GN_FLAGS
 and #$F3
 sta GN_FLAGS
 lda GP_RECORD+GPR_HEIGHT
 cmp #9
 beq @prose
 cmp #8
 jne argument
 lda GP_RECORD+GPR_KIND
 cmp #1
 jne argument
 lda GN_FLAGS
 ora #4
 sta GN_FLAGS
 clc
 rts
@prose:
 lda GP_RECORD+GPR_KIND
 jne argument
 lda GP_RECORD+GPR_INLINE
 beq :+
 lda GN_FLAGS
 ora #8
 sta GN_FLAGS
:
 clc
 rts
cache_page:
 ; A reanchored prose viewport may shift the next code tile alignment by
 ;1..7px relative to the canonical global walk. Its TOPs cannot certify the
 ;global PAGE threshold; ordinary cached arrows still avoid all C24 scans.
 lda GN_TOP
 ora GN_TOP+1
 ora GN_TOP+2
 jne cold
 lda #0
 sta GN_TEMP+1
 sta GN_TEMP+2
 lda GN_COMMAND
 cmp #38
 beq @up
 clc
 lda GP_RECORD+GPR_TOP
 adc #GN_PAGE_PIXELS
 sta GN_TEMP
 bcc :+
 inc GN_TEMP+1
:
 lda GN_TEMP+1
 jne cold
 lda GN_TEMP
 cmp #192
 jcs cold
 bcc @search
@up:
 sec
 lda GP_RECORD+GPR_TOP
 sbc #GN_PAGE_PIXELS
 jcc cold
 cmp #16
 jcc cold
 sta GN_TEMP
@search:
 lda #0
 sta GN_CACHE_INDEX
 sta GN_CACHE_TARGET
 lda #6
 sta GN_STATE
 jmp own_pending
cache_page_step:
 lda GN_CACHE_INDEX
 cmp GN_CACHE_COUNT
 bcc @read
 lda GN_COMMAND
 cmp #38
 jeq cache_fast_ready
 jmp cold
@read:
 jsr prefix
 jcs return
 lda GN_COMMAND
 cmp #38
 beq @up
 lda GP_RECORD+GPR_TOP
 cmp GN_TEMP
 bcc @next
 lda GN_CACHE_INDEX
 sta GN_CACHE_TARGET
 jmp cache_fast_ready
@up:
 lda GP_RECORD+GPR_TOP
 cmp GN_TEMP
 bcc @candidate
 beq @candidate
 jmp cache_fast_ready
@candidate:
 lda GN_CACHE_INDEX
 sta GN_CACHE_TARGET
@next:
 inc GN_CACHE_INDEX
 jmp own_pending
prefix:
 lda GN_CACHE_INDEX
 jsr se_gp_cache_slot
 jcs return
 lda #<GP_RECORD
 sta GP_IO_POINTER
 lda #>GP_RECORD
 sta GP_IO_POINTER+1
 lda #32
 sta GP_IO_LENGTH
 lda #0
 sta GP_IO_LENGTH+1
 jmp se_gp_cache_read
line_begin:
 lda se_render_caps
 bne @parsed_context
 GS_SET_RAW_CONTEXT
 jmp metric_ready
@parsed_context:
 lda GN_FLAGS
 and #2
 beq @query
 lda GN_FLAGS
 and #8
 bne @query ;styled metrics need their full logical-body context
 lda #0
 sta GSEM_FRAME+GSEM_INLINE
 sta GSEM_FRAME+GSEM_KIND
 lda #9
 ldx GN_FLAGS
 txa
 and #4
 beq :+
 lda #8
 bne :++
:
 lda #9
:
 sta GSEM_FRAME+GSEM_HEIGHT
 jmp metric_ready
@query:
 NAV_COPY24 GN_SCAN,GSEM_FRAME+GSEM_QUERY
 lda GN_COMMAND
 cmp #47
 bne nav_legacy
 lda GN_FLAGS
 and #2
 bne nav_legacy
 jsr nav_selector_cap
 bcc :+
 rts
:
 lda #9
 sta GN_STATE
 lda #26
 ldx #6
 jmp request
nav_legacy:
 lda #5
 sta GN_STATE
 lda #GSEM_ID
 ldx #GSEM_BEGIN
 jmp request
nav_query_ready:
 lda #26
 ldx #7
 jmp request
semantic_ready:
 lda GSEM_FRAME+GSEM_ACTIVE
 bne @step
 lda GN_COMMAND
 cmp #74
 bcc metric_ready
 NAV_COPY24 GSEM_FRAME+GSEM_START,GN_SCAN
 jmp metric_ready
@step:
 lda #GSEM_ID
 ldx #GSEM_STEP
 jmp request
metric_ready:
 lda GSEM_FRAME+GSEM_HEIGHT
 cmp #8
 beq @height
 cmp #9
 jne argument
@height:
 lda GN_FLAGS
 and #2
 jne @prepare
 lda GN_COMMAND
 cmp #38
 bcc @mark_top
 cmp #40
 bcs @mark_top
 lda GSEM_FRAME+GSEM_HEIGHT
 cmp #8
 bne @page_up
 ; Physical VIC code rows align their global origin relative bodyY16.
 clc
 lda GN_ORDINAL
 adc #7
 and #$F8
 sta GN_ORDINAL
 lda GN_ORDINAL+1
 adc #0
 sta GN_ORDINAL+1
 lda GN_ORDINAL+2
 adc #0
 sta GN_ORDINAL+2
@page_up:
 lda GN_PASS
 cmp #1
 bne @mark_top
 lda GN_COMMAND
 cmp #38
 bne @mark_top
 NAV_EQUAL24 GN_ORDINAL,GN_TARGET_ROW
 bcc @mark_top
 beq @mark_top
 NAV_COPY24 GN_CACHE_ROW,GN_SCAN
 NAV_COPY24 GN_TEMP,GN_ORDINAL
 lda #3
 sta GN_PASS
 jmp line_begin
@mark_top:
 ; Mark the original viewport's canonical row while cold reconstructing.
 NAV_EQUAL24 GN_SCAN,GN_TOP
 bne :+
 NAV_COPY24 GN_ORDINAL,GN_TOP_ROW
 lda #1
 sta GN_TOP_VALID
:
@prepare:
 lda #0
 ldx #31
@clear:
 sta L,x
 dex
 bpl @clear
 lda GN_MODE
 ldx GN_COMMAND
 cpx #74
 bcc :+
 lda #1 ;measure the complete logical row even when starting in wrapped mode
:
 sta L+GL_MODE
 lda #0
 ldx GSEM_FRAME+GSEM_HEIGHT
 cpx #8
 bne :+
 lda #1
:
 sta L+GL_ENCODING
 lda #<320
 sta L+GL_WIDTH
 lda #>320
 sta L+GL_WIDTH+1
 NAV_COPY24 GN_SCAN,L+GL_START
 NAV_COPY24 GN_QUERY,L+GL_CARET
 NAV_COPY24 GN_PAN,L+GL_PAN
 lda GN_COMMAND
 cmp #47
 beq @zero_origin
 cmp #74
 bcc :+
@zero_origin:
 lda #0 ;PAN/reveal need logical metrics, not viewport mapping; an old out-of-range origin must not overflow
 sta L+GL_PAN
 sta L+GL_PAN+1
 sta L+GL_PAN+2
:
 lda GN_PASS
 and #1
 beq @ready
 ; A no-wrap target map straddles the preferred logical pixel rather than
 ; limiting long logical lines to the original viewport's visible map.
 lda GN_MODE
 beq @ready
 lda #0
 sta L+GL_PAN
 sta L+GL_PAN+1
 sta L+GL_PAN+2
 lda GN_PREFERRED+2
 ora GN_PREFERRED+1
 bne @pan
 lda GN_PREFERRED
 cmp #161
 bcc @ready
@pan:
 sec
 lda GN_PREFERRED
 sbc #160
 sta L+GL_PAN
 lda GN_PREFERRED+1
 sbc #0
 sta L+GL_PAN+1
 lda GN_PREFERRED+2
 sbc #0
 sta L+GL_PAN+2
@ready:
 lda #2
 sta GN_STATE
 lda #20
 ldx #GS_BEGIN
 jmp request
stream:
 lda L+GL_STATE
 cmp #2
 beq @complete
 lda #20
 ldx #GS_STEP
 jmp request
@complete:
 lda GN_COMMAND
 cmp #74
 bcc :+
 lda L+GL_CARET_VALID
 jeq advance ;raw PAN may start before the queried logical line
 jmp pan_complete
:
 lda GN_PASS
 and #1
 jne target_line
 lda L+GL_CARET_VALID
 jeq advance
 lda GN_FLAGS
 and #1
 bne :+
 NAV_COPY24 L+GL_CARET_X,GN_PREFERRED
 lda GN_FLAGS
 ora #1
 sta GN_FLAGS
:
 lda GN_COMMAND
 cmp #47
 jeq reveal_done
 lda GN_PASS
 cmp #2
 bne @cold_target
 lda #3
 sta GN_STATE
 jmp own_pending
@cold_target:
 NAV_COPY24 GN_ORDINAL,GN_TARGET_ROW
 lda GN_COMMAND
 cmp #36
 beq @up
 cmp #38
 beq @up
 clc
 lda GN_TARGET_ROW
 adc GN_DELTA
 sta GN_TARGET_ROW
 bcc @forward
 inc GN_TARGET_ROW+1
 bne @forward
 inc GN_TARGET_ROW+2
@forward:
 lda #1
 sta GN_PASS
 jmp advance
@up:
 sec
 lda GN_TARGET_ROW
 sbc GN_DELTA
 sta GN_TARGET_ROW
 lda GN_TARGET_ROW+1
 sbc #0
 sta GN_TARGET_ROW+1
 lda GN_TARGET_ROW+2
 sbc #0
 sta GN_TARGET_ROW+2
 bcs :+
 lda #0
 sta GN_TARGET_ROW
 sta GN_TARGET_ROW+1
 sta GN_TARGET_ROW+2
:
 lda #1
 sta GN_PASS
 NAV_EQUAL24 GN_TARGET_ROW,GN_ORDINAL
 jeq target_line
 lda #0
 sta GN_SCAN
 sta GN_SCAN+1
 sta GN_SCAN+2
 sta GN_ORDINAL
 sta GN_ORDINAL+1
 sta GN_ORDINAL+2
 jmp line_begin
advance:
 lda L+GL_REASON
 cmp #GL_EOF
 bne @next
 lda GN_PASS
 and #1
 jne target_line
 jmp argument ;query was outside the actual source
@next:
 lda GN_PASS
 cmp #1
 bne @move
 lda GN_COMMAND
 cmp #38
 bne @move
 NAV_COPY24 GN_SCAN,GN_CACHE_ROW ;previous anchor in now-unused cachedrow/target/delta
 NAV_COPY24 GN_ORDINAL,GN_TEMP
@move:
 NAV_COPY24 L+GL_NEXT,GN_SCAN
 lda GN_COMMAND
 cmp #38
 bcc @one
 cmp #40
 bcs @one
 clc
 lda GN_ORDINAL
 adc GSEM_FRAME+GSEM_HEIGHT
 sta GN_ORDINAL
 lda GN_ORDINAL+1
 adc #0
 sta GN_ORDINAL+1
 lda GN_ORDINAL+2
 adc #0
 sta GN_ORDINAL+2
 jmp @metric_done
@one:
 inc GN_ORDINAL
 bne :+
 inc GN_ORDINAL+1
 bne :+
 inc GN_ORDINAL+2
:
@metric_done:
 lda GN_PASS
 and #1
 beq @begin
 ; The preceding comparison result was dead before the next command load.
 ; The target must be reconstructed before hit testing its map.
@begin:
 ; Explicit canonical targets may lie inside a collapsed interval. Locate
 ; them in source first; after W_LOAD the resident motion safe point opens
 ; their ancestors. Directional movement continues to use projected rows.
 lda GN_COMMAND
 cmp #47
 beq @plain
 jsr se_ef_visible
 beq @plain
 lda L+GL_REASON
 cmp #GL_CR
 bne @plain
 NAV_COPY24 GN_SCAN,GFQ_QUERY
 lda #1
 sta GFQ_MODE
 lda #0
 jsr fold_call
 jcs return
 cmp #0
 beq fold_advanced
 lda #7
 sta GN_STATE
 jmp own_pending
@plain:
 jmp line_begin
fold_advance:
 lda #1
 jsr fold_call
 jcs return
 cmp #0
 jne own_pending
fold_advanced:
 NAV_COPY24 GFQ_RESULT,GN_SCAN
 jmp line_begin
fold_call:
 sta se_overlay_frame
 lda #24
 ldx #0
 jmp se_overlay_call
; PAN owns no source edit and publishes only after complete line measurement.
; GN_TEMP=max(logicalPixelWidth-320,0); GN_TARGET_ROW is the proposed pan.
pan_complete:
 sec
 lda L+GL_X
 sbc #<320
 sta GN_TEMP
 lda L+GL_X+1
 sbc #>320
 sta GN_TEMP+1
 lda L+GL_X+2
 sbc #0
 sta GN_TEMP+2
 bcs @maximum
 lda #0
 sta GN_TEMP
 sta GN_TEMP+1
 sta GN_TEMP+2
@maximum:
 NAV_COPY24 GN_PAN,GN_TARGET_ROW
 lda GN_COMMAND
 cmp #75
 beq @right
 sec
 lda GN_TARGET_ROW
 sbc #20
 sta GN_TARGET_ROW
 lda GN_TARGET_ROW+1
 sbc #0
 sta GN_TARGET_ROW+1
 lda GN_TARGET_ROW+2
 sbc #0
 sta GN_TARGET_ROW+2
 bcs @clamp
 lda #0
 sta GN_TARGET_ROW
 sta GN_TARGET_ROW+1
 sta GN_TARGET_ROW+2
 beq @clamp
@right:
 clc
 lda GN_TARGET_ROW
 adc #20
 sta GN_TARGET_ROW
 lda GN_TARGET_ROW+1
 adc #0
 sta GN_TARGET_ROW+1
 lda GN_TARGET_ROW+2
 adc #0
 sta GN_TARGET_ROW+2
 bcs @use_maximum
@clamp:
 NAV_EQUAL24 GN_TARGET_ROW,GN_TEMP
 bcc @publish
@use_maximum:
 NAV_COPY24 GN_TEMP,GN_TARGET_ROW
@publish:
 NAV_COPY24 GN_TARGET_ROW,se_l_pan
 NAV_COPY24 GN_QUERY,se_e_target
 lda #1
 sta se_l_manual
 sta se_l_mode
 sta se_l_need_wrap
 lda #0
 sta se_gc_width
 sta GCC_VALID
 sta GEC_VALID
 sta GTC_VALID ;owner4; target/PAN inputs have already been fully consumed
 sta se_f_owner
 sta se_l_valid
 sta se_r_valid
 lda #2 ;distinct view-only completion; resident must not reload/flush the gap
 clc
 rts
target_line:
 lda GN_PASS
 cmp #1
 bne @hit
 NAV_EQUAL24 GN_ORDINAL,GN_TARGET_ROW
 beq @hit
 lda GN_COMMAND
 cmp #39
 bne @reason
 NAV_EQUAL24 GN_ORDINAL,GN_TARGET_ROW
 bcs @hit
@reason:
 lda L+GL_REASON
 cmp #GL_EOF
 jne advance
@hit:
 ; C20 HIT consumes the line's immutable map and exact midpoint policy.
 lda GN_MODE
 beq @wrap_hit
 SUB24 GN_PREFERRED,L+GL_PAN,GN_TEMP
 bcs @relative
 lda #0
 sta GN_TEMP
 sta GN_TEMP+1
@relative:
 lda GN_TEMP+2
 beq @use_temp
 lda #<320
 sta GN_TEMP
 lda #>320
 sta GN_TEMP+1
@use_temp:
 lda GN_TEMP
 sta L+GL_HIT_X
 lda GN_TEMP+1
 sta L+GL_HIT_X+1
 jmp @request
@wrap_hit:
 lda GN_PREFERRED
 sta L+GL_HIT_X
 lda GN_PREFERRED+1
 sta L+GL_HIT_X+1
@request:
 lda #4
 sta GN_STATE
 lda #20
 ldx #GS_HIT
 jmp request
hit_done:
 ; A soft endpoint belongs to the following visual row. Keep a vertical
 ; destination on its intended row even at a preferred X near320.
 lda L+GL_REASON
 cmp #GL_EOF+1
 bcc @publish
 NAV_EQUAL24 L+GL_HIT_SOURCE,L+GL_END
 bcc @publish
 NAV_COPY24 L+GL_END,L+GL_HIT_SOURCE
 sec
 lda L+GL_HIT_SOURCE
 sbc #1
 sta L+GL_HIT_SOURCE
 lda L+GL_HIT_SOURCE+1
 sbc #0
 sta L+GL_HIT_SOURCE+1
 lda L+GL_HIT_SOURCE+2
 sbc #0
 sta L+GL_HIT_SOURCE+2
@publish:
 NAV_COPY24 L+GL_HIT_SOURCE,GN_QUERY
 jmp publish
reveal_done:
 ; Exact canonical reveal never replaces the requested target with a hit.
publish:
 lda GN_FLAGS
 and #2
 bne @keep_top
 lda GN_TOP_VALID
 beq @new_top
 NAV_EQUAL24 GN_ORDINAL,GN_TOP_ROW
 bcc @new_top
 SUB24 GN_ORDINAL,GN_TOP_ROW,GN_TEMP
 lda GN_TEMP+2
 ora GN_TEMP+1
 bne @new_top
 lda GN_TEMP
 ldx GN_COMMAND
 cpx #38
 bcc @row_limit
 cpx #40
 bcs @row_limit
 cmp #176
 bcc @keep_top
 bcs @new_top
@row_limit:
 ldx GN_CACHE_COUNT
 beq :+
 cmp GN_CACHE_COUNT
 bcc @keep_top
 bcs @new_top
:
 cmp #20
 bcc @keep_top
@new_top:
 NAV_COPY24 GN_SCAN,GN_TOP
@keep_top:
 NAV_COPY24 GN_QUERY,se_e_target
 NAV_COPY24 GN_TOP,se_v_top
 lda GN_COMMAND
 cmp #47
 bne @preferred
 jsr se_ef_motion_tick
 jsr reveal_pan
 jmp @release
@preferred:
 NAV_COPY24 GN_PREFERRED,se_l_preferred
 lda #2
 sta se_n_preferred_valid
@release:
 lda #0
 sta se_f_owner
 sta se_l_valid
 sta se_r_valid
 lda #1
 sta se_l_need_wrap
 ; A reveal of the already loaded caret is a view-only completion. W_LOAD
 ; refuses a live pending window; it is also unnecessary for this exact
 ; target. Reuse the resident A2 path already used by pixel panning.
 lda GN_COMMAND
 cmp #47
 bne @ordinary
 lda se_hot_ready
 beq @ordinary
 lda se_hot_phase
 bne @ordinary
 ldx #2
@same_caret:
 lda GN_QUERY,x
 cmp se_hot_caret,x
 bne @ordinary
 dex
 bpl @same_caret
 lda #2
 bne @complete
@ordinary:
 lda #0
@complete:
 clc
return:
 rts
; E47 reveals the canonical target's logical pixel origin. Keep manual and
; preferred state untouched; the caller decides whether auto-reveal is allowed.
; Delta avoids overflow from oldPan+320. Right edge is exclusive: x-319.
reveal_pan:
 lda GN_MODE
 beq @done
 NAV_EQUAL24 L+GL_CARET_X,GN_PAN
 bcc @left
 SUB24 L+GL_CARET_X,GN_PAN,GN_TEMP
 lda GN_TEMP+2
 bne @right
 lda GN_TEMP+1
 cmp #>320
 bcc @done
 bne @right
 lda GN_TEMP
 cmp #<320
 bcc @done
@right:
 sec
 lda L+GL_CARET_X
 sbc #<319
 sta GN_TEMP
 lda L+GL_CARET_X+1
 sbc #>319
 sta GN_TEMP+1
 lda L+GL_CARET_X+2
 sbc #0
 sta GN_TEMP+2
 NAV_COPY24 GN_TEMP,se_l_pan
 rts
@left:
 NAV_COPY24 L+GL_CARET_X,se_l_pan
@done:
 rts
guard:
 jsr se_ef_visible
 cmp GN_FOLD_VALID
 jne changed
 ldx #1
@fold_generation:
 lda se_ef_generation,x
 cmp GN_FOLD_GENERATION,x
 jne changed
 dex
 bpl @fold_generation
 jsr se_view_init
 jcs return
 FIELDS compare
 lda se_l_mode
 cmp GN_MODE
 bne changed
 NAV_EQUAL24 se_l_pan,GN_PAN
 bne changed
 lda GN_COMMAND
 cmp #47
 beq @target
 NAV_EQUAL24 se_hot_caret,GN_QUERY
 bne changed
 clc
 rts
@target:
 NAV_EQUAL24 se_e_target,GN_QUERY
 bne changed
 clc
 rts
own_pending:
 lda #GN_ID
 ldx #GN_STEP
request:
 sta GN_REQUEST
 stx GN_OPERATION
 lda #1
 clc
 rts
busy:
 lda #$B2
 sec
 rts
changed:
 lda #$74
 sec
 rts
argument:
 lda #$90
 sec
 rts

cap_table:.byte 24,<SEED_SIZE,>SEED_SIZE,<SEED_CRC,>SEED_CRC,26,<NAV_SIZE,>NAV_SIZE,<NAV_CRC,>NAV_CRC
