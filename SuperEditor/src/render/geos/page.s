.import se_bc_ring
.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "render/presentation.inc"
.include "cache/api.inc"
.import se_crc_init,se_crc_byte,se_crc_value
.include "render/geos/plain-context.inc"
.global se_render_caps,se_ef_visible
.include "render/geos/checkpoint/codec.inc"
.include "render/geos/editor.inc"
.include "render/geos/source-line.inc"
.include "render/geos/source-certificate.inc"
.include "render/geos/semantic-lex.inc"
.include "render/geos/inline.inc"
.include "render/geos/fold-query.inc"
.include "render/geos/caret-cache.inc"
.include "render/geos/edit-cache.inc"
.include "document/math24.inc"
.import se_v_length
.import se_ef_valid
.import se_r_presentation
.import se_f_owner,se_i_ready,se_i_count,se_n_cache_count
.import se_l_valid,se_r_valid,se_st_request,se_st_cp_valid,se_l_mode,se_l_pan,se_l_manual
.import se_v_top,se_hot_caret,se_view_peek,se_view_advance,se_v_pos,se_v_rows
.import se_v_bottom,se_v_seen,se_v_caret_row,se_l_need_wrap
.importzp screen_ptr
.export entry
P=GP_CONTROL
PS=P
REQUEST=P+1
OP=P+2
LINE=P+3
TOP=P+4
ANCHOR=P+5
INDEX=P+8
CANON=P+9
CHUNK=P+12
BASE=P+13
MAP_DONE=P+14
FOLD_END=P+16
FOLD_PENDING=P+19
FAST_PAINT=P+20
L=GEOS_LINE_FRAME
.segment "GEOS_PAGE"
    OVL_BINDING
entry:
    lda se_r_presentation
    beq :+
    lda se_overlay_frame
    sta OP
    lda #27
    sta REQUEST
    lda #1
    clc
    rts
:
    lda se_overlay_frame
    cmp #0
    jeq begin
    cmp #2
    jeq cancel
    lda se_f_owner
    cmp #4
    jne busy
    lda se_overlay_frame
    cmp #3
    jeq finish
    cmp #4
    jeq finish_caret
    cmp #1
    jne argument
    lda PS
    cmp #50
    jeq resume_after_admission
    ; TOP normalization precedes allocation/admission of the derived page.
    ; Its pending R24 query authenticates the map and source itself.
    lda PS
    cmp #9
    jeq fold_top_step
    cmp #11
    jeq caret_step
    jsr se_gp_cache_guard
    jcs failed
    lda PS
    cmp #1
    jeq source
    cmp #2
    jeq bytes
    cmp #4
    jeq publish_row
    cmp #5
    jeq cached_row
    cmp #13
    jeq gsc_seed_done
    cmp #6
    jeq classified
    cmp #7
    jeq lexed
    cmp #10
    jeq fold_line_step
    cmp #8
    jeq inlined
    jmp argument
begin:
    lda se_f_owner
    jne busy
    lda #4
    sta se_f_owner
    lda #0
    sta se_i_ready
    sta se_i_count
    sta se_n_cache_count
    lda #0
    sta se_bc_flags
    ldx #10
@call:
    lda #7
    jmp request
resume_after_admission:
    lda GEC_VALID
    sta GSC_ALLOW_EDIT
    lda #0
    sta GSC_CAPTURED

    lda #0
    sta GSEM_FRAME+GSEM_CP_VALID
    sta $8B40 ;fresh caller-owned painter state may contain native power-on RAM
    sta $8B41
    sta LINE
    sta FAST_PAINT
    sta GEX_PHASE
    sta se_l_valid
    sta se_r_valid
    sta se_st_request
    sta se_st_cp_valid
    ldx #GP_MAX_GLYPHS-1
@clear_roles:
    sta GP_ROLES,x
    dex
    cpx #$FF
    bne @clear_roles
    lda #16
    sta TOP
    ldx #2
@anchor:
    lda se_v_top,x
    sta ANCHOR,x
    dex
    bpl @anchor
    jsr se_ef_visible
    beq begin_page
    COPY24 ANCHOR,GFQ_QUERY
    lda #0
    sta GFQ_MODE
    jsr fold_call
    jcs failed
    cmp #0
    beq fold_top_done
    lda #9
    sta PS
    jmp own_pending
fold_top_step:
    lda #1
    jsr fold_call
    jcs failed
    cmp #0
    jne own_pending
fold_top_done:
    COPY24 GFQ_RESULT,ANCHOR
    COPY24 GFQ_RESULT,se_v_top
begin_page:
    lda #0
    jsr caret_call
    jcs failed
    cmp #2
    beq edit_attempt
    lda #11
    sta PS
    jmp own_pending
caret_step:
    lda #1
    jsr caret_call
    jcs failed
    cmp #2
    beq edit_attempt
    cmp #0
    jne own_pending
    lda #1
    sta FAST_PAINT
    jmp finish
edit_attempt:
    lda se_render_caps
    beq full_page ;raw source has no parser certificate for R28
    lda #GEX_ADMIT
    jsr edit_call
    jcs failed
    cmp #2
    beq full_page
    lda GEX_AUX
    cmp #3
    lda #3
    bcs :+
    lda #4                    ;complete CR rejoins immediately after dirty row
:
    sta FAST_PAINT
    lda GEX_ROW
    sta LINE
    lda GEX_TOP
    sta TOP
    COPY24 GEX_OLD_START,ANCHOR
    jmp next_line
full_page:
    ; Admission can reject after a dirty row was rebuilt. Restart geometry
    ; from the viewport, never from that abandoned row's continuation.
    lda #0
    sta FAST_PAINT
    sta LINE
    lda #16
    sta TOP
    COPY24 se_v_top,ANCHOR
    ; A source-identical published page already has immutable glyphs, metrics
    ; and affinities. Rebind only its caret and repaint for motion/selection.
    ; Changes to source/top/pan/FE ownership fall back to the normal producer.
    lda se_l_mode
    bne fresh_page
    jsr se_gp_cache_guard
    bcs fresh_page
    lda GP_HEADER+GPH_VALID
    cmp #1
    bne fresh_page
    lda GP_HEADER+GPH_COUNT
    beq fresh_page
    cmp #GP_MAX_LINES+1
    bcs fresh_page
cached_begin:
    lda #0
    sta GP_HEADER+GPH_SEEN
    sta GP_HEADER+GPH_CARET_VISIBLE
    lda #$FF
    sta GP_HEADER+GPH_CARET_ROW
    jsr header_write
    jcs failed
    lda #5
    sta PS
    jmp own_pending
fresh_page:
    jsr se_gp_cache_open
    jcs failed
next_line:
    lda #0
    ldx #31
@clear:
    sta GP_RECORD,x
    dex
    bpl @clear
    lda se_render_caps
    bne @parsed_context
    GS_SET_RAW_CONTEXT
    lda #0
    sta FOLD_PENDING ;C23 uses the same phase suffix; no fold query ran here
    jmp prepare_line
@parsed_context:
@classify:
    COPY24 ANCHOR,GSEM_FRAME+GSEM_QUERY
legacy_classify:
    lda GSEM_FRAME+GSEM_CP_VALID
    bne gsc_classify_direct
    jsr gsc_cap
    bcs gsc_classify_direct
    lda #0
    sta GSC_SELECTOR
    lda #13
    sta PS
    lda #GSEM_ID
    ldx #3
    jmp request
gsc_seed_done:
    lda GSC_PROOF
    bne gsc_classify_direct
    lda GSC_SELECTOR
    bne gsc_classify_direct
    inc GSC_SELECTOR
    lda #GSEM_ID
    ldx #3
    jmp request
gsc_classify_direct:
    lda #0
    sta GSC_CAPTURED

    lda #6
    sta PS
    lda #GSEM_ID
    ldx #GSEM_BEGIN
    jmp request
classified:
    lda GSEM_FRAME+GSEM_ACTIVE
    beq @ready
    lda #GSEM_ID
    ldx #GSEM_STEP
    jmp request
@ready:
    jsr gsc_publish
classification_ready:
    lda #0
    sta FOLD_PENDING
    jsr se_ef_visible
    beq prepare_line
    COPY24 GSEM_FRAME+GSEM_END,GFQ_QUERY
    CMP24 GFQ_QUERY,se_v_length
    bcs prepare_line
    inc GFQ_QUERY
    bne :+
    inc GFQ_QUERY+1
    bne :+
    inc GFQ_QUERY+2
:
    lda #1
    sta GFQ_MODE
    lda #0
    jsr fold_call
    jcs failed
    cmp #0
    beq fold_line_done
    lda #10
    sta PS
    jmp own_pending
fold_line_step:
    lda #1
    jsr fold_call
    jcs failed
    cmp #0
    jne own_pending
fold_line_done:
    lda GFQ_HIDDEN
    sta FOLD_PENDING
    COPY24 GFQ_RESULT,FOLD_END
prepare_line:
	 ; Preserve the ABI3 language/complement packet contract.
	 lda GSEM_FRAME+GSEM_LANG
 sta GP_RECORD+30
 eor #$FF
 sta GP_RECORD+31
    ; C24's actual parser aliases GL. Prepare every C20 input only after the
    ; query has completed and its checkpoint is safely in the caller suffix.
    lda #0
    ldx #31
@clear_line:
    sta L,x
    dex
    bpl @clear_line
    lda se_l_mode
    sta L+GL_MODE
    lda #<320
    sta L+GL_WIDTH
    lda #>320
    sta L+GL_WIDTH+1
    ldx #2
@inputs:
    lda ANCHOR,x
    sta L+GL_START,x
    sta GP_RECORD+GPR_START,x
    lda se_l_pan,x
    sta L+GL_PAN,x
    lda se_hot_caret,x
    sta L+GL_CARET,x
    dex
    bpl @inputs
    lda GSEM_FRAME+GSEM_HEIGHT
    sta GP_RECORD+GPR_HEIGHT
    cmp #8
    bne @prose
    clc
    lda TOP
    adc #7
    and #$F8
    sta TOP
    cmp #192
    jcs complete_page
    lda #1
    bne @encoding
@prose:
    lda #0
@encoding:
    sta GP_RECORD+GPR_KIND
    sta L+GL_ENCODING
    lda GSEM_FRAME+GSEM_REVERSE
    sta GP_RECORD+GPR_FLAGS
    lda FOLD_PENDING
    beq :+
    lda GP_RECORD+GPR_FLAGS
    ora #$80
    sta GP_RECORD+GPR_FLAGS
:
    lda GSEM_FRAME+GSEM_INLINE
    sta GP_RECORD+GPR_INLINE
    lda #1
    sta PS
    lda #GP_LAYOUT_ID
    ldx #GS_BEGIN
    jmp request
source:
    lda L+GL_STATE
    cmp #2
    beq @ready
    lda #GP_LAYOUT_ID
    ldx #GS_STEP
    jmp request
@ready:
    lda L+GL_MAP_COUNT+1
    jne argument
    lda L+GL_MAP_COUNT
    cmp #GP_MAX_GLYPHS+1
    jcs argument
    sta GP_RECORD+GPR_COUNT
    lda L+GL_REASON
    sta GP_RECORD+GPR_REASON
    lda L+GL_CARET_VALID
    sta GP_RECORD+GPR_MEMBER
    ldx #2
@outputs:
    lda L+GL_END,x
    sta GP_RECORD+GPR_END,x
    lda L+GL_NEXT,x
    sta GP_RECORD+GPR_NEXT,x
    lda L+GL_MAP_FIRST,x
    sta GP_RECORD+GPR_FIRST,x
    dex
    bpl @outputs
    lda GP_RECORD+GPR_FLAGS
    bpl @fold_ready
    lda GP_RECORD+GPR_REASON
    cmp #GL_CR
    beq @fold_skip
    lda GP_RECORD+GPR_FLAGS
    and #$7F
    sta GP_RECORD+GPR_FLAGS
    bpl @fold_ready
@fold_skip:
    COPY24 FOLD_END,GP_RECORD+GPR_NEXT
@fold_ready:
    ldx #1
@raster:
    lda L+GL_RASTER_X,x
    sta GP_RECORD+GPR_RASTER_X,x
    dex
    bpl @raster
    ldx #GL_CARET_X
    jsr viewport_x
    jsr visible_x
    bcs @tail
    lda GP_RECORD+GPR_MEMBER
    beq @tail
    sta GP_RECORD+GPR_CARET_VALID
    lda CANON
    sta GP_RECORD+GPR_CARET_X
    lda CANON+1
    sta GP_RECORD+GPR_CARET_X+1
@tail:
    ldx #GL_X
    jsr viewport_x
    jsr visible_x
    bcc @tail_visible
    lda CANON+2
    and CANON+1
    cmp #$FF
    bne @geometry
    lda #$FC ;-4..-1 intersects the normal5px BSWspace
    bit GP_RECORD+GPR_FLAGS
    bpl :+
    lda #$FB ;-5..-1 intersects the6px foldedplus
:
    ldx GP_RECORD+GPR_KIND
    beq :+
    lda #$F9 ;-7..-1 intersects a native8space
:
    cmp CANON
    bcc @tail_visible
    bne @geometry
@tail_visible:
    lda #1
    sta GP_RECORD+GPR_TAIL_VALID
    lda CANON
    sta GP_RECORD+GPR_TAIL_X
    lda CANON+1
    sta GP_RECORD+GPR_TAIL_X+1
@geometry:
    lda #6
    sta GP_RECORD+GPR_BACKGROUND
    lda TOP
    sta GP_RECORD+GPR_TOP
    lda #<GPR_X
    jsr field
    inc GP_IO_OFFSET+1
    inc GP_IO_OFFSET+1
    lda #< (L+GL_MAP)
    sta GP_IO_POINTER
    lda #> (L+GL_MAP)
    sta GP_IO_POINTER+1
    lda GP_RECORD+GPR_COUNT
    clc
    adc #1
    asl
    sta GP_IO_LENGTH
    lda #0
    rol
    sta GP_IO_LENGTH+1
    jsr se_gp_cache_write
    jcs failed
    lda #0
    sta INDEX
    ldx #GP_MAX_GLYPHS-1
@styles:
    sta GP_ROLES,x
    dex
    cpx #$FF ;160 entries: sign flag cannot terminate a >128-byte loop
    bne @styles
    lda #2
    sta PS
    jmp own_pending
bytes:
    lda INDEX
    cmp GP_RECORD+GPR_COUNT
    beq @write
    ldx #2
@pos:
    lda GP_RECORD+GPR_FIRST,x
    sta se_v_pos,x
    dex
    bpl @pos
    clc
    lda se_v_pos
    adc INDEX
    sta se_v_pos
    bcc :+
    inc se_v_pos+1
    bne :+
    inc se_v_pos+2
:
    lda #32
    sta CHUNK
@read:
    jsr se_view_peek
    jcs failed
    ldx INDEX
    sta GP_SOURCE,x
    inc INDEX
    jsr se_view_advance
    lda INDEX
    cmp GP_RECORD+GPR_COUNT
    beq @write
    dec CHUNK
    bne @read
    jmp own_pending
@write:
    lda GP_RECORD+GPR_COUNT
    jeq begin_maps
    sta GP_IO_LENGTH
    lda #0
    sta GP_IO_LENGTH+1
    lda #<GP_SOURCE
    sta GP_IO_POINTER
    lda #>GP_SOURCE
    sta GP_IO_POINTER+1
    lda #GPR_CHARS
    jsr field
    jsr se_gp_cache_write
    jcs failed
    lda #<GP_ROLES
    sta GP_IO_POINTER
    lda #>GP_ROLES
    sta GP_IO_POINTER+1
    lda #GPR_STYLES
    jsr field
    jsr se_gp_cache_write
    jcs failed
    lda GP_RECORD+GPR_KIND
    beq @roles
    lda se_render_caps
    and #RENDER_CODE_COLOR
    beq @plain_roles
    COPY24 GP_RECORD+GPR_FIRST,GSEM_FRAME+GSEM_QUERY
    lda GSEM_FRAME+GSEM_LANG
    sta GSEM_FRAME+GSEM_LANGUAGE
    lda GP_RECORD+GPR_COUNT
    sta GSEM_FRAME+GSEM_COUNT
    lda #7
    sta PS
    lda #GLEX_ID
    ldx #GLEX_BEGIN
    jmp request
@roles:
    lda GSEM_FRAME+GSEM_KIND
    cmp #4
    bcs @plain_roles
    lda GSEM_FRAME+GSEM_INLINE
    beq @plain_roles
    COPY24 GP_RECORD+GPR_FIRST,GSEM_FRAME+GSEM_QUERY
    lda GP_RECORD+GPR_COUNT
    sta GSEM_FRAME+GSEM_COUNT
    lda #8
    sta PS
    lda SC_VALID
    cmp #2
    bne :+
    lda #GP_LAYOUT_ID
    ldx #SC_CONSUME
    jmp request
:
    lda #GI_ID
    ldx #GI_BEGIN
    ldy GP_RECORD+GPR_COUNT
    cpy #161
    bne :+
    ldx #GI_BEGIN_WIDE
:
    jmp request
@plain_roles:
    lda GSEM_FRAME+GSEM_ROLE
    ldx #GP_MAX_GLYPHS-1
@fill:
    sta GP_ROLES,x
    dex
    cpx #$FF
    bne @fill
    jsr write_roles
    jcs failed
begin_maps:
    ; ABI3 literal source affinities are implicit FIRST+boundary index.
    lda #4
    sta PS
    jmp own_pending
lexed:
    lda GLEX_ACTIVE
    beq @ready
    lda #GLEX_ID
    ldx #GLEX_STEP
    jmp request
@ready:
    jsr write_roles
    jcs failed
    jmp begin_maps
inlined:
    lda GI_ACTIVE
    beq @ready
    lda #GI_ID
    ldx #GI_STEP
    jmp request
@ready:
    lda GP_RECORD+GPR_COUNT
    sta GP_IO_LENGTH
    lda #0
    sta GP_IO_LENGTH+1
    lda #<GI_OUTPUT_STYLES
    sta GP_IO_POINTER
    lda #>GI_OUTPUT_STYLES
    sta GP_IO_POINTER+1
    lda #GPR_STYLES
    jsr field
    jsr se_gp_cache_write
    jcs failed
    lda GP_RECORD+GPR_COUNT
    cmp #161
    bne :+
    lda #160
:
    sta GP_IO_LENGTH
    lda #<GI_OUTPUT_ROLES
    sta GP_IO_POINTER
    lda #>GI_OUTPUT_ROLES
    sta GP_IO_POINTER+1
    lda #<GPR_ROLES
    jsr field
    inc GP_IO_OFFSET+1
    jsr se_gp_cache_write
    jcs failed
    lda GP_RECORD+GPR_COUNT
    cmp #161
    bne @complete
    lda #1
    sta GP_IO_LENGTH
    lda #<GI_OUTPUT_ROLE_LAST
    sta GP_IO_POINTER
    lda #>GI_OUTPUT_ROLE_LAST
    sta GP_IO_POINTER+1
    clc
    lda GP_IO_OFFSET
    adc #160
    sta GP_IO_OFFSET
    bcc :+
    inc GP_IO_OFFSET+1
:
    jsr se_gp_cache_write
    jcs failed
@complete:
    jmp begin_maps
write_roles:
    lda GP_RECORD+GPR_COUNT
    sta GP_IO_LENGTH
    lda #0
    sta GP_IO_LENGTH+1
    lda #<GP_ROLES
    sta GP_IO_POINTER
    lda #>GP_ROLES
    sta GP_IO_POINTER+1
    lda #<GPR_ROLES
    jsr field
    inc GP_IO_OFFSET+1
    jmp se_gp_cache_write
publish_row:
    lda #GP_RECORD/256
    sta GP_IO_POINTER+1
    lda #<GP_RECORD
    sta GP_IO_POINTER
    lda #GPR_PREFIX
    sta GP_IO_LENGTH
    lda #0
    sta GP_IO_LENGTH+1
    lda LINE
    jsr slot
    jsr se_gp_cache_write
    jcs failed
    lda FAST_PAINT
    cmp #3
    bne :+
    jsr convergence_compare
    jcs failed
:
    ; Publish canonical row anchors only after its complete immutable packet.
    lda LINE
    asl
    clc
    adc LINE
    tax
    ldy #0
@rows:
    lda GP_RECORD+GPR_START,y
    sta se_v_rows,x
    inx
    iny
    cpy #3
    bne @rows
    lda GP_RECORD+GPR_MEMBER
    beq :+
    lda #1
    sta GP_HEADER+GPH_SEEN
    lda GP_RECORD+GPR_CARET_VALID
    sta GP_HEADER+GPH_CARET_VISIBLE
    lda LINE
    sta GP_HEADER+GPH_CARET_ROW
    lda GP_RECORD+GPR_CARET_X
    sta GP_HEADER+GPH_CARET_X
    lda GP_RECORD+GPR_CARET_X+1
    sta GP_HEADER+GPH_CARET_X+1
:
    inc LINE
    lda LINE
    sta GP_HEADER+GPH_COUNT
    ldx #2
@bottom:
    lda GP_RECORD+GPR_NEXT,x
    sta ANCHOR,x
    sta GP_HEADER+GPH_BOTTOM,x
    dex
    bpl @bottom
    lda GP_RECORD+GPR_REASON
    cmp #GL_EOF
    beq complete_page
    clc
    lda TOP
    adc GP_RECORD+GPR_HEIGHT
    sta TOP
    cmp #192
    bcs complete_page
    lda LINE
    cmp #GP_MAX_LINES
    bcs complete_page
    jsr header_write
    jcs failed
    lda FAST_PAINT
    cmp #4
    beq convergence_rebase
    jsr convergence_capture
    jcs failed
    jmp next_line
complete_page:
    lda #1
    sta GP_HEADER+GPH_VALID
    jsr header_write
    jcs failed
    jmp paint_start
convergence_rebase:
    lda LINE
    sta GEX_SCAN_ROW
    lda #GEX_REBASE
    jsr edit_call
    bcc :+
    tax                         ;set Z from the overlay ABI return value
    jeq full_page
    jmp failed
:   lda #2
    sta FAST_PAINT
    lda #0
    sta LINE
    jmp cached_begin
cached_row:
    lda LINE
    jsr slot
    lda #<GP_RECORD
    sta GP_IO_POINTER
    lda #>GP_RECORD
    sta GP_IO_POINTER+1
    lda #GPR_PREFIX
    sta GP_IO_LENGTH
    lda #0
    sta GP_IO_LENGTH+1
    jsr se_gp_cache_read
    jcs failed
    lda GP_RECORD+GPR_COUNT+1
    jne argument
    lda GP_RECORD+GPR_COUNT
    cmp #GP_MAX_GLYPHS+1
    jcs argument
    lda #0
    sta GP_RECORD+GPR_CARET_VALID
    sta GP_RECORD+GPR_MEMBER
    sta GP_RECORD+GPR_CARET_X
    sta GP_RECORD+GPR_CARET_X+1
    CMP24 se_hot_caret,GP_RECORD+GPR_START
    jcc @store
    CMP24 se_hot_caret,GP_RECORD+GPR_END
    bcc @mapped
    jne @store
    lda GP_RECORD+GPR_REASON
    cmp #GL_CR
    beq @mapped
    cmp #GL_EOF
    jne @store
@mapped:
    SUB24 se_hot_caret,GP_RECORD+GPR_FIRST,CANON
    lda CANON+1
    ora CANON+2
    jne @store
    lda CANON
    cmp GP_RECORD+GPR_COUNT
    bcc :+
    jne @store
:
    lda LINE
    jsr slot
    lda CANON
    asl
    sta GP_IO_OFFSET
    lda GP_IO_OFFSET+1
    adc #>GPR_X
    sta GP_IO_OFFSET+1
    clc
    lda GP_IO_OFFSET
    adc #<GPR_X
    sta GP_IO_OFFSET
    bcc :+
    inc GP_IO_OFFSET+1
:
    lda #<(GP_RECORD+GPR_CARET_X)
    sta GP_IO_POINTER
    lda #>(GP_RECORD+GPR_CARET_X)
    sta GP_IO_POINTER+1
    lda #2
    sta GP_IO_LENGTH
    lda #0
    sta GP_IO_LENGTH+1
    jsr se_gp_cache_read
    jcs failed
    lda #1
    sta GP_RECORD+GPR_CARET_VALID
    sta GP_RECORD+GPR_MEMBER
    sta GP_HEADER+GPH_SEEN
    sta GP_HEADER+GPH_CARET_VISIBLE
    lda LINE
    sta GP_HEADER+GPH_CARET_ROW
    ldx #1
@x:
    lda GP_RECORD+GPR_CARET_X,x
    sta GP_HEADER+GPH_CARET_X,x
    dex
    bpl @x
@store:
    ; VIEW rows may have been replaced by a different display mode since this
    ; page was cached. Republish them from the authenticated canonical packet.
    lda LINE
    asl
    clc
    adc LINE
    tax
    ldy #0
@anchor:
    lda GP_RECORD+GPR_START,y
    sta se_v_rows,x
    inx
    iny
    cpy #3
    bne @anchor
    lda LINE
    jsr slot
    lda #<GP_RECORD
    sta GP_IO_POINTER
    lda #>GP_RECORD
    sta GP_IO_POINTER+1
    lda #GPR_PREFIX
    sta GP_IO_LENGTH
    lda #0
    sta GP_IO_LENGTH+1
    jsr se_gp_cache_write
    jcs failed
    jsr header_write
    jcs failed
    inc LINE
    lda LINE
    cmp GP_HEADER+GPH_COUNT
    jcc own_pending
paint_start:
    lda GP_HEADER+GPH_SEEN
    beq @reveal
    lda se_l_manual
    bne @visible ;manual pan may deliberately leave the caret offscreen
    lda GP_HEADER+GPH_CARET_VISIBLE
    bne @visible
@reveal:
    ; A paste/history replay, changing wrap or a taller mixed page can push
    ; the caret beyond this newly built page. Do not publish a hidden caret.
    ; Return to the resident command path so pending input is flushed before
    ; C23 reveal/W_LOAD; no C-to-C overlay nesting and no lost pending bytes.
    lda #0
    sta se_f_owner
    sta se_l_valid
    sta se_r_valid
    lda #2
    clc
    rts
@visible:
 ;C22 aliases the85B queryproof
    lda #0
    sta GSEM_FRAME+GSEM_CP_VALID
    sta $8B40
    sta $8B41
    lda #GP_PAINT_ID
    ldx #0
    jmp request
finish:
    jsr se_gp_cache_guard
    jcs failed
    lda GP_HEADER+GPH_VALID
    jeq argument
    ldx #2
@bottom:
    lda GP_HEADER+GPH_BOTTOM,x
    sta se_v_bottom,x
    dex
    bpl @bottom
    lda GP_HEADER+GPH_SEEN
    sta se_v_seen
    lda GP_HEADER+GPH_CARET_ROW
    sta se_v_caret_row
    lda #1
    sta se_l_valid
    lda FAST_PAINT
    cmp #1
    beq finish_done
    ; Populate/reuse the checked normal-font tail once before capturing a base.
    ; C30 retains its own bounded continuation and returns to this image op4.
    lda #30
    ldx #3
    jmp request
finish_caret:
    jsr se_gp_cache_guard
    jcs failed
    lda #2
    jsr caret_call
    jcs failed
finish_done:
    lda #0
    sta se_l_need_wrap
    sta se_f_owner
    ; Root switches C images before invoking the shared chrome in C16.
    lda #16
    ldx #4
    jmp request
cancel:
    lda se_f_owner
    cmp #4
    jne busy
    lda #0
    sta se_f_owner
    sta se_l_valid
    clc
    rts
own_pending:
    lda #GP_PAGE_ID
    ldx #1
request:
    sta REQUEST
    stx OP
    lda #1
    clc
    rts
header_write:
    lda #0
    sta GP_IO_OFFSET
    sta GP_IO_OFFSET+1
    sta GP_IO_LENGTH+1
    lda #<GP_HEADER
    sta GP_IO_POINTER
    lda #>GP_HEADER
    sta GP_IO_POINTER+1
    lda #GP_HEADER_SIZE
    sta GP_IO_LENGTH
    jmp se_gp_cache_write
slot:
    jmp se_gp_cache_slot
field:
    pha
    lda LINE
    jsr slot
    pla
    clc
    adc GP_IO_OFFSET
    sta GP_IO_OFFSET
    bcc :+
    inc GP_IO_OFFSET+1
:
    rts
; X selects a logical24bit metric. Wrap has no horizontal origin. The signed
; result is only exposed after the caller has checked its viewport range.
viewport_x:
    lda L+GL_MODE
    bne @subtract
    lda L,x
    sta CANON
    lda L+1,x
    sta CANON+1
    lda L+2,x
    sta CANON+2
    rts
@subtract:
    sec
    lda L,x
    sbc L+GL_PAN
    sta CANON
    lda L+1,x
    sbc L+GL_PAN+1
    sta CANON+1
    lda L+2,x
    sbc L+GL_PAN+2
    sta CANON+2
    rts
visible_x:
    lda CANON+2
    bne @no
    lda CANON+1
    beq @yes
    cmp #1
    bne @no
    lda CANON
    cmp #64
    bcs @no
@yes:
    clc
    rts
@no:
    sec
    rts
failed:
    sec
    rts
busy:
    lda #$B2
    sec
    rts
argument:
    lda #$90
    sec
    rts

; Private no-extra-load row comparator. R28 admission owns authority and the
; first unused row-slot shadow; C21 compares/captures synchronously.
convergence_compare:
	lda LINE
	cmp GEX_ROW
	jeq @dirty
	    lda #<GEX_OLD_ROW
	    sta GP_IO_OFFSET
	    lda #>GEX_OLD_ROW
	    sta GP_IO_OFFSET+1
    jsr convergence_host
    jsr se_gp_cache_read
    jcs @return
    lda #0
    sta screen_ptr
    lda #$80
    sta screen_ptr+1
    ldx #4
@anchor:
    ldy #0
    lda GEX_OP
    bne @minus
    clc
    lda (screen_ptr),y
    adc #1
    sta (screen_ptr),y
    iny
    lda (screen_ptr),y
    adc #0
    sta (screen_ptr),y
    iny
    lda (screen_ptr),y
    adc #0
    sta (screen_ptr),y
    jcs @not_exact
    bcc @next_anchor
@minus:
    sec
    lda (screen_ptr),y
    sbc #1
    sta (screen_ptr),y
    iny
    lda (screen_ptr),y
    sbc #0
    sta (screen_ptr),y
    iny
    lda (screen_ptr),y
    sbc #0
    sta (screen_ptr),y
    jcc @not_exact
@next_anchor:
    clc
    lda screen_ptr
    adc #3
    sta screen_ptr
    dex
    bne @anchor
@normalized:
    ; Both rows must be soft wraps of the same complete logical event.
    ldx #2
@event_start:
    lda GSEM_FRAME+GSEM_START,x
    cmp GEX_TEMP,x
    jne @not_exact
    dex
    bpl @event_start
    ; The completed descending event-start loop leaves X=$FF.
    inx
    stx screen_ptr
    stx GEX_OFFSET
    stx GEX_OFFSET+1
    lda #$80
    sta screen_ptr+1
    lda #<GPR_USED
    sta GEX_COPY_LEFT
    lda #>GPR_USED
    sta GEX_COPY_LEFT+1
@chunk:
    lda GEX_COPY_LEFT+1
    beq @tail
    lda #192
    bne @amount
@tail:
    lda GEX_COPY_LEFT
    cmp #192
    bcc @amount
    lda #192
@amount:
    sta GEX_CHUNK
    lda LINE
    jsr slot
    clc
    lda GP_IO_OFFSET
    adc GEX_OFFSET
    sta GP_IO_OFFSET
    lda GP_IO_OFFSET+1
    adc GEX_OFFSET+1
    sta GP_IO_OFFSET+1
    lda #<GEX_BUFFER
    sta GP_IO_POINTER
    lda #>GEX_BUFFER
    sta GP_IO_POINTER+1
    lda GEX_CHUNK
    sta GP_IO_LENGTH
    lda #0
    sta GP_IO_LENGTH+1
    jsr se_gp_cache_read
    jcs @return
    ldy #0
@byte:
    lda (screen_ptr),y
    cmp GEX_BUFFER,y
    jne @not_exact
    iny
    cpy GEX_CHUNK
    bcc @byte
    clc
    lda screen_ptr
    adc GEX_CHUNK
    sta screen_ptr
    bcc :+
    inc screen_ptr+1
:   clc
    lda GEX_OFFSET
    adc GEX_CHUNK
    sta GEX_OFFSET
    bcc :+
    inc GEX_OFFSET+1
:   sec
    lda GEX_COPY_LEFT
    sbc GEX_CHUNK
    sta GEX_COPY_LEFT
    lda GEX_COPY_LEFT+1
    sbc #0
    sta GEX_COPY_LEFT+1
    ora GEX_COPY_LEFT
    jne @chunk
    lda #4
    sta FAST_PAINT
    bne @reload
@dirty:
    ; Preserve this row's complete-event START across the following row job.
    ldx #2
@save_event_start:
    lda GSEM_FRAME+GSEM_START,x
    sta GEX_TEMP,x
    dex
    bpl @save_event_start
    clc
    rts
@not_exact:
    lda #0
    sta FAST_PAINT
    ; Abandon the staged R28 transaction before the full-page continuation.
    ; GEC/GCC were already consumed when R28 published phase 1.
    sta GEX_PHASE
@reload:
    lda LINE
    jsr slot
    lda #<GP_RECORD
    sta GP_IO_POINTER
    lda #>GP_RECORD
    sta GP_IO_POINTER+1
    lda #GPR_PREFIX
    sta GP_IO_LENGTH
    lda #0
    sta GP_IO_LENGTH+1
    jmp se_gp_cache_read
@return:
    rts

convergence_host:
    lda #0
    sta GP_IO_POINTER
    lda #$80
    sta GP_IO_POINTER+1
    lda #<GPR_USED
    sta GP_IO_LENGTH
    lda #>GPR_USED
    sta GP_IO_LENGTH+1
    rts

convergence_capture:
    lda FAST_PAINT
    cmp #3
    bne @done
    lda LINE
    jsr slot
    jsr convergence_host
    jsr se_gp_cache_read
    jcs @return
	    lda #<GEX_OLD_ROW
	    sta GP_IO_OFFSET
	    lda #>GEX_OLD_ROW
	    sta GP_IO_OFFSET+1
    jmp se_gp_cache_write
@done:
    clc
@return:
    rts

.segment "GEOS_PAGE"
fold_call:
    sta se_overlay_frame
    lda #24
    ldx #0
    jmp se_overlay_call
caret_call:
    sta se_overlay_frame
    lda #GCC_ID
    ldx #0
    jmp se_overlay_call
edit_call:
    sta se_overlay_frame
    lda #GEX_ID
    ldx #0
    jmp se_overlay_call

gsc_publish:
 lda #7
 sta se_overlay_frame
 lda #19
 ldx #0
 jmp se_overlay_call


.include "render/geos/checkpoint/consumer.inc"
