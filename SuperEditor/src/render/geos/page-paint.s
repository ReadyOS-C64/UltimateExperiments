; ABI3 literal source boundaries are implicit FIRST+index; no affinity arrays.
; Bounded foreground GEOS page compositor. Cache reads and renderer calls are
; isolated from bounded preparation/native-cell batches; no same-C nesting.
.setcpu "6502"
.macpack longbranch
.ifdef EDITOR_OVERLAY
.include "editor-api.inc"
.else
.import se_f_owner,se_overlay_call,se_overlay_frame,se_petscii_screen
.import se_sel_mark,se_sel_anchor,se_hot_caret
.importzp text_ptr,screen_ptr
.endif
.include "render/geos/editor.inc"
SE_GEOS_PAGE_PAINT_IMPLEMENTATION=1
.include "render/geos/page-paint.inc"
.include "render/geos/edit-cache.inc"
.include "render/geos/row.inc"
.include "render/geos/native-pan.inc"
.include "render/narrow/grid.inc"
.export se_gp_paint_begin,se_gp_paint_step,se_gp_paint_cancel
.export se_gp_paint_busy,se_gp_paint_valid
.export se_gnp_palette
se_gnp_palette=palette
se_gp_paint_busy=GPP_BUSY
se_gp_paint_valid=GPP_VALID
; Private persistent bytes: all outside the complete R21 frame.
S=GPP_STATE
R=S+$20                     ;saved32B logical record
index=S+$40
scan=S+$41
source=S+$42                ;24bit current canonical boundary
saved_caret=S+$45
saved_start=S+$48
saved_end=S+$4B
saved_mark=S+$4E
extent=S+$4F                 ;word logical glyph count
count_lines=S+$51
strip_y=S+$52
next_phase=S+$53
advance=S+$54
base=S+$55                   ;word bank slot offset
field=S+$57                  ;word requested record-relative offset
host=S+$59                   ;word requested host destination
amount=S+$5B                 ;word request bytes
cell_frame=S+$60             ;11-byte BC input
empty_caret=S+$6B
saved_anchor=S+$6C
; One bounded prefix pass certifies these immutable geometry witnesses. They
; fit the existing caller suffix and survive the complete R21 frame.
tops=S+$6F                  ;22 physical byteY values
bottoms=S+$85               ;22 exclusive physical byteY values
cert_index=S+$9B
first_live=S+$9C
prior_bottom=S+$9D
want_selection=S+$9E
tail_character=S+$5D
tail_role=S+$5E
limit=S+$A0
tail_flags=S+$9F
D=$8D00
CHARS=$8D20
STYLES=$8D60
ROLES=$8DA0
FLAGS=$8DE0
MAP=$8E20
F=GEOS_ROW_FRAME
P_SCAN=1
P_CHARS=2
P_STYLES=3
P_ROLES=4
P_RIGHT=5
P_LEFT=6
P_DRAW=7
P_CELL=8
P_START=9
P_X=10
P_TAIL_RIGHT=11
P_TAIL_LEFT=12
P_TAIL_DRAW=13
P_CERTIFY=14
P_NATIVE=15
P_CLEAR=16
budget=GPP_PRIVATE
.segment "CODE"
se_gp_paint_begin:
    jsr owner
    jcs return
    lda GPP_BUSY
    jne busy
    jsr se_gp_cache_guard
    jcs return
    lda GP_HEADER+GPH_VALID
    cmp #1
    jne changed
    lda GP_HEADER+GPH_COUNT
    cmp #GP_MAX_LINES+1
    jcs argument
    sta count_lines
    lda #6
    sta R+GPR_BACKGROUND
    lda se_sel_mark
    sta saved_mark
    ldx #2
@source:
    lda se_hot_caret,x
    sta saved_caret,x
    lda se_hot_caret,x
    sta saved_start,x
    sta saved_end,x
    lda se_sel_anchor,x
    sta saved_anchor,x
    dex
    bpl @source
    jsr selection_bounds
    jcs fail
    lda #0
    sta want_selection
    sta cert_index
    sta first_live
    ldx #2
@selected:
    lda saved_start,x
    cmp saved_end,x
    bne @nonempty
    dex
    bpl @selected
    jmp @selection_ready
@nonempty:
    lda #1
    sta want_selection
@selection_ready:
    lda #16
    sta prior_bottom
    lda #0
    sta GPP_VALID
    sta GPP_ERROR
    sta GPP_LINE
    sta budget
    ; A certified edit may repaint only intersecting physical8px bands.
    ; Malformed hints conservatively repaint the complete document area.
    lda GP_CONTROL+20
    cmp #2
    bne @all_bands
    lda GEX_FIRST_STRIP
    cmp #2
    bcc @all_bands
    cmp #24
    bcs @all_bands
    sta GPP_ROW
    lda GEX_END_STRIP
    cmp #25
    bcs @all_bands
    cmp GPP_ROW
    bcc @all_bands
    beq @all_bands
    sta limit
    jmp @bands_ready
@all_bands:
    lda #2
    sta GPP_ROW
    lda #24
    sta limit
@bands_ready:
    lda #1
    sta GPP_BUSY
    sta GPP_RESET
    lda #P_CERTIFY
    sta GPP_PHASE
    jmp pending
se_gp_paint_cancel:
    jsr owner
    jcs return
    lda #0
    sta GPP_BUSY
    sta GPP_VALID
    sta GPP_ERROR
    clc
    rts
se_gp_paint_step:
    jsr owner
    jcs return
    lda GPP_BUSY
    jeq argument
    jsr se_gp_cache_guard
    jcs fail
    lda GP_HEADER+GPH_VALID
    cmp #1
    jne changed
    lda GP_HEADER+GPH_COUNT
    cmp count_lines
    jne changed
    ldx #2
@identity:
    lda se_hot_caret,x
    cmp saved_caret,x
    jne changed
    lda se_sel_anchor,x
    cmp saved_anchor,x
    jne changed
    dex
    bpl @identity
    lda se_sel_mark
    cmp saved_mark
    jne changed
    lda #8
    sta budget
dispatch:
    lda GPP_PHASE
    cmp #P_CLEAR
    jeq clear_strip
    cmp #P_CERTIFY
    jeq certify
    cmp #P_SCAN
    jeq scan_line
    cmp #P_CHARS
    jeq read_chars
    cmp #P_RIGHT
    jeq read_right
    cmp #P_LEFT
    jeq read_left
    cmp #P_DRAW
    jeq draw_prose
    cmp #P_CELL
    jeq draw_cell
    cmp #P_START
    jeq start_chunk
    cmp #P_TAIL_RIGHT
    jeq tail_right
    cmp #P_TAIL_LEFT
    jeq tail_left
    cmp #P_TAIL_DRAW
    jeq tail_draw
    cmp #P_NATIVE
    jeq native_step
    jmp argument
; No pixels are touched until every cached prefix has passed ordered,
; nonoverlapping geometry validation. At most eight32-byte prefixes per STEP.
certify:
    lda cert_index
    cmp count_lines
    bcc @record
    lda #0
    sta GPP_LINE
    lda #P_SCAN
    sta GPP_PHASE
    jmp pending
@record:
    sta GPP_LINE
    jsr prefix
    jcs fail
    lda R+GPR_TOP
    cmp #16
    jcc argument
    cmp #192
    jcs argument
    cmp prior_bottom
    jcc argument
    ldx cert_index
    sta tops,x
    lda R+GPR_HEIGHT
    cmp #8
    beq @height
    cmp #9
    jne argument
@height:
    clc
    adc R+GPR_TOP
    jcs argument
    sta bottoms,x
    sta prior_bottom
    jsr record_kind
    jcs fail
    lda R+GPR_COUNT+1
    jne argument
    lda R+GPR_COUNT
    cmp #GP_MAX_GLYPHS+1
    jcs argument
    lda R+GPR_BACKGROUND
    cmp #16
    jcs argument
    inc cert_index
    jmp pending
; Expired/future records need no cache fetch. A9th-row descender remains live
; until its certified exclusive bottom reaches the next physical strip.
scan_line:
    lda GPP_ROW
    asl
    asl
    asl
    sta strip_y
    ldx GPP_LINE
    cpx count_lines
    jcs strip_done
    lda bottoms,x
    cmp strip_y
    bcc expired
    beq expired
    lda strip_y
    clc
    adc #8
    cmp tops,x
    jcc strip_done
    jeq strip_done
    jsr prefix
    jcs fail
    ldx GPP_LINE
    lda R+GPR_TOP
    cmp tops,x
    jne changed
    clc
    adc R+GPR_HEIGHT
    jcs changed
    cmp bottoms,x
    jne changed
    lda R+GPR_TOP
    sec
    sbc strip_y
    sta GPP_Y
    jsr record_kind
    jcs fail
    lda R+GPR_COUNT+1
    jne argument
    lda R+GPR_COUNT
    cmp #GP_MAX_GLYPHS+1
    jcs argument
    sta extent
    lda #0
    sta extent+1
    sta GPP_OFFSET
    sta GPP_OFFSET+1
    sta empty_caret
    jmp read_x
expired:
    inc first_live
    inc GPP_LINE
    jmp pending
; Read initial viewport x; further prose appends use the leaf's exact advance.
read_x:
    lda R+GPR_RASTER_X
    sta GPP_X
    lda R+GPR_RASTER_X+1
    sta GPP_X+1
    cmp #$FF
    bne @positive
    lda GPP_X
    cmp #$F1
    jcc argument
    bcs @ready
@positive:
    lda GPP_X+1
    cmp #2
    jcs argument
    bne @high
    jmp @ready
@high:
    lda GPP_X
    cmp #65
    jcs argument
@ready:
    jmp start_chunk
start_chunk:
    lda GPP_OFFSET
    cmp extent
    jcs end_line
    lda GPP_X+1
    bmi @count ;small signed-left origin is rendered by the clipped leaf
    cmp #1
    bcc @count
    lda GPP_X
    cmp #64
    jcs end_line
@count:
    sec
    lda extent
    sbc GPP_OFFSET
    cmp #65
    bcc :+
    lda #64
:
    sta GPP_COUNT
    lda #P_CHARS
    sta GPP_PHASE
    jmp pending
read_chars:
    lda #<GPR_CHARS
    ldx #>GPR_CHARS
    ldy #>CHARS
    jsr array_request
    jcs fail
    ; CHARS are already in place. The gathered style/role slices begin162
    ; and324 bytes later. Ascending order is required: role destinations may
    ; overlap only style source bytes that were copied earlier in this loop.
    ldx #0
@gather:
    lda CHARS+(GPR_STYLES-GPR_CHARS),x
    sta STYLES,x
    lda CHARS+(GPR_ROLES-GPR_CHARS),x
    sta ROLES,x
    inx
    cpx GPP_COUNT
    bcc @gather
    jmp flags_ready
flags_ready:
    lda want_selection
    bne @maps
    jsr caret_line
    bcs @maps
    lda R+GPR_FLAGS
    and #1
    ldx GPP_COUNT
@flags:
    dex
    sta FLAGS,x
    bne @flags ;STA preserves DEX Z; count is1..64
    jmp choose_draw
@maps:
    lda #P_RIGHT
    sta GPP_PHASE
    jmp pending
; Canonical maps are staged outside all R21 scratch. Flags survive each fetch.
read_right:
    lda #0
    sta index
    sta scan
@flags:
    jsr load_canonical
    jcs fail
    lda R+GPR_FLAGS
    and #1
    ldx index
    sta FLAGS,x
    lda want_selection
    beq @caret
    jsr within_selection
    bcc @caret
    lda FLAGS,x
    ora #2
    sta FLAGS,x
@caret:
    lda GPP_LINE
    cmp GP_HEADER+GPH_CARET_ROW
    bne @next
    lda R+GPR_MEMBER
    beq @next
    jsr at_or_after_caret
    bcc @next
    lda FLAGS,x
    ora #8 ;temporary RIGHT>=caret witness; removed before R21 validates flags
    sta FLAGS,x
@next:
    inc index
    lda index
    cmp GPP_COUNT
    bcc @flags
    jsr caret_line
    jcc choose_draw
    lda #P_LEFT
    sta GPP_PHASE
    jmp pending
read_left:
    lda #0
    sta index
    sta scan
@flags:
    ldx index
    lda FLAGS,x
    and #8
    beq @clear
    jsr load_canonical
    jcs fail
    jsr at_or_before_caret
    bcc @clear
    ldx index
    lda FLAGS,x
    ora #4
    sta FLAGS,x
@clear:
    ldx index
    lda FLAGS,x
    and #7
    sta FLAGS,x
    inc index
    clc
    lda scan
    adc #3
    sta scan
    lda index
    cmp GPP_COUNT
    bcc @flags
choose_draw:
    lda GPP_KIND
    beq @prose
    lda #0
    sta GPP_CELL
    lda #P_CELL
    bne @set
@prose:
    lda #P_DRAW
@set:
    sta GPP_PHASE
    jmp pending
; Execute one <=64-glyph R21 call, preserving histogram between all appends.
draw_prose:
    jsr row_setup
    lda #1
    sta F+GR_RUNS
    lda GPP_COUNT
    sta D+GRR_COUNT
    lda GPP_Y
    sta D+GRR_Y
    lda GPP_X
    sta D+GRR_X
    lda GPP_X+1
    sta D+GRR_X+1
    jsr row_call
    jcs fail
    lda D+GRR_NEXT_X
    sta GPP_X
    lda D+GRR_NEXT_X+1
    sta GPP_X+1
    lda D+GRR_DONE
    jeq end_line
    clc
    adc GPP_OFFSET
    sta GPP_OFFSET
    lda #P_START
    sta GPP_PHASE
    jmp pending
; One native8 tile per micro-operation, at most8 per publicSTEP. R21 resets
; are isolated before code cells.
draw_cell:
    lda GPP_RESET
    beq @cell
    lda #P_CELL
    jmp queue_clear
@cell:
    lda GPP_X
    and #7
    jne native_begin
    lda GPP_CELL
    cmp GPP_COUNT
    jcs cells_done
    lda GPP_X+1
    cmp #1
    bcc @visible
    lda GPP_X
    cmp #64
    jcs end_line
@visible:
    lda GPP_X
    lsr
    lsr
    lsr
    sta cell_frame+1
    lda GPP_X+1
    beq :+
    lda cell_frame+1
    ora #32
    sta cell_frame+1
:
    lda GPP_ROW
    sta cell_frame
    ldx GPP_CELL
    lda CHARS,x
    jsr se_petscii_screen
    sta cell_frame+2
    ldx GPP_CELL
    lda FLAGS,x
    and #1
    beq :+
    lda cell_frame+2
    ora #$80
    sta cell_frame+2
:
    lda FLAGS,x
    and #6
    beq :+
    lda cell_frame+2
    eor #$80
    sta cell_frame+2
:
    lda ROLES,x
    cmp #14
    jcs argument
    tax
    lda palette,x
    sta cell_frame+3
    lda R+GPR_BACKGROUND
    cmp #16
    jcs argument
    sta cell_frame+4
    lda #0
    sta cell_frame+5
    sta cell_frame+7
    sta cell_frame+9
    lda #>GRID_NATIVE_FONT
    sta cell_frame+6
    lda #$60
    sta cell_frame+8
    lda #$40
    sta cell_frame+10
    lda #GRID_CELL8
    sta se_overlay_frame
    lda #<cell_frame
    sta se_overlay_frame+1
    lda #>cell_frame
    sta se_overlay_frame+2
    lda #GRID80_ID
    ldx #0
    jsr se_overlay_call
    jcs fail
    clc
    lda GPP_X
    adc #8
    sta GPP_X
    bcc :+
    inc GPP_X+1
:
    inc GPP_CELL
    jmp pending
cells_done:
    clc
    lda GPP_OFFSET
    adc GPP_COUNT
    sta GPP_OFFSET
    lda #P_START
    sta GPP_PHASE
    jmp pending
; An unaligned native packet covers the complete <=41-glyph visible code row.
; Include its virtual CR/EOF space in the same tile vote domain: a separate
; call could otherwise overwrite body ink in the final shared tile.
native_begin:
    lda empty_caret
    bne @setup
    inc empty_caret
    lda R+GPR_TAIL_VALID
    beq @setup
    lda R+GPR_REASON
    cmp #3
    bcs @setup
    jsr tail_selection
    jcs fail
    ldx GPP_COUNT
    lda tail_character
    sta CHARS,x
    lda tail_role
    sta ROLES,x
    lda tail_flags
    sta FLAGS,x
    jsr caret_line
    bcc @append
    jsr equal_caret
    bne @append
    ldx GPP_COUNT
    lda FLAGS,x
    ora #4
    sta FLAGS,x
@append:
    inc GPP_COUNT
@setup:
    lda GPP_ROW
    sta GNP_FRAME+GNP_ROW
    lda GPP_X
    sta GNP_FRAME+GNP_ORIGIN
    lda GPP_X+1
    sta GNP_FRAME+GNP_ORIGIN+1
    lda GPP_COUNT
    sta GNP_FRAME+GNP_COUNT
    ldx #5
@pointers:
    lda native_pointers,x
    sta GNP_FRAME+GNP_CHARS,x
    dex
    bpl @pointers
    jsr se_gnp_begin
    jcs fail
    lda #P_NATIVE
    sta GPP_PHASE
    jmp pending
native_step:
    jsr se_gnp_step
    jcs fail
    cmp #0
    jne pending
    jmp line_finished
end_line:
    lda empty_caret
    bne line_finished
    lda #1
    sta empty_caret
    jsr tail_selection
    jcs fail
    jsr caret_line
    jcc selected_tail
    ; A source boundary can be offscreen while its virtual cell intersects.
    ; TAIL_VALID authenticates the signed/clipped cell, not a clamped point.
    lda R+GPR_TAIL_VALID
    jeq selected_tail
@tail:
    lda #P_TAIL_RIGHT
    sta GPP_PHASE
    jmp pending
line_finished:
    ldx GPP_LINE
    cpx first_live
    bne @phase
    lda strip_y
    clc
    adc #8
    cmp bottoms,x
    bcc @phase
    inc first_live
@phase:
    lda #P_SCAN
    sta GPP_PHASE
    inc GPP_LINE
    jmp pending
tail_right:
    jsr load_tail
    jcs fail
    jsr at_or_after_caret
    jcc selected_tail
    lda #P_TAIL_LEFT
    sta GPP_PHASE
    jmp pending
tail_left:
    jsr load_tail
    jcs fail
    jsr at_or_before_caret
    jcc selected_tail
    lda tail_flags
    ora #4
    sta tail_flags
    lda #P_TAIL_DRAW
    sta GPP_PHASE
    jmp pending
selected_tail:
    lda tail_flags
    and #3
    jeq line_finished
    lda #P_TAIL_DRAW
    sta GPP_PHASE
    jmp pending
tail_draw:
    lda tail_character
    sta CHARS
    lda #0
    sta STYLES
    sta GPP_CELL
    lda tail_role
    sta ROLES
    lda tail_flags
    sta FLAGS
    lda #1
    sta GPP_COUNT
    lda R+GPR_TAIL_X
    sta GPP_X
    lda R+GPR_TAIL_X+1
    sta GPP_X+1
    lda GPP_KIND
    beq @prose
    lda #P_CELL
    bne @set
@prose:
    lda #P_DRAW
@set:
    sta GPP_PHASE
    jmp pending
strip_done:
    lda GPP_RESET
    beq @next
    lda #P_SCAN
    jmp queue_clear
@next:
    inc GPP_ROW
    lda GPP_ROW
    cmp limit
    bcc @strip
    lda #0
    sta GPP_BUSY
    lda #1
    sta GPP_VALID
    lda #0
    clc
    rts
@strip:
    lda first_live
    sta GPP_LINE
    lda #1
    sta GPP_RESET
    lda #P_SCAN
    sta GPP_PHASE
    jmp pending
; A public STEP keeps its full checked guard only across this bounded slice.
; Every R21 operation is entered/exited through a public yield; IRQ only queues
; input during the <=8 preparation/native-cell micro-operations between them.
queue_clear:
    sta next_phase
    lda #P_CLEAR
    sta GPP_PHASE
    jmp yield
clear_strip:
    jsr row_setup
    lda #0
    sta F+GR_RUNS
    jsr row_call
    jcs fail
    lda next_phase
    sta GPP_PHASE
    jmp yield
pending:
    lda GPP_PHASE
    cmp #P_DRAW
    beq yield
    cmp #P_CLEAR
    beq yield
    lda budget
    beq yield
    dec budget
    jne dispatch
yield:
    lda #1
    clc
return:
    rts
owner:
    lda se_f_owner
    cmp #4
    bne busy
    clc
    rts
busy:
    lda #GPP_BUSY_ERROR
    sec
    rts
argument:
    lda #GPP_ARGUMENT
    jmp fail
changed:
    lda #GPP_CHANGED
fail:
    sta GPP_ERROR
    pha
    lda #0
    sta GPP_BUSY
    sta GPP_VALID
    pla
    sec
    rts
prefix:
    lda #0
    sta field
    sta field+1
    lda #<GP_RECORD
    sta host
    lda #>GP_RECORD
    sta host+1
    lda #GPR_PREFIX
    sta amount
    lda #0
    sta amount+1
    jsr fetch
    bcs @return
    ldx #GPR_PREFIX-1
@save:
    lda GP_RECORD,x
    sta R,x
    dex
    bpl @save
    clc
@return:
    rts
record_kind:
    lda R+GPR_KIND
    cmp #2
    jcs argument
    sta GPP_KIND
    tax
    bne @code
    lda R+GPR_HEIGHT
    cmp #9
    jne argument
    clc
    rts
@code:
    lda R+GPR_HEIGHT
    cmp #8
    jne argument
    lda R+GPR_TOP
    and #7
    jne argument
    lda R+GPR_COUNT
    cmp #42
    jcs argument
    clc
    rts
; Request one field slice from the current logical line. No nested service.
fetch:
    lda GPP_LINE
    jsr se_gp_cache_slot
    jcs return
    clc
    lda GP_IO_OFFSET
    adc field
    sta GP_IO_OFFSET
    lda GP_IO_OFFSET+1
    adc field+1
    sta GP_IO_OFFSET+1
    lda host
    sta GP_IO_POINTER
    lda host+1
    sta GP_IO_POINTER+1
    lda amount
    sta GP_IO_LENGTH
    lda amount+1
    sta GP_IO_LENGTH+1
    jmp se_gp_cache_read
; A/X record field, Y destination high. Four arrays are64-byte aligned.
array_request:
    clc
    adc GPP_OFFSET
    sta field
    txa
    adc #0
    sta field+1
    sty host+1
    ldy GPP_PHASE
    lda destination_lo-P_CHARS,y
    sta host
    lda GPP_COUNT
    jeq argument
    cmp #65
    jcs argument
    sta amount
    lda #0
    sta amount+1
    lda GPP_PHASE
    cmp #P_CHARS
    bne @fetch
    ; One checked contiguous transfer covers the same three field slices.
    ; Existing public chunks are1..64; no source or worker loop is enlarged.
    clc
    lda amount
    adc #<(GPR_ROLES-GPR_CHARS)
    sta amount
    lda #>(GPR_ROLES-GPR_CHARS)
    adc #0
    sta amount+1
@fetch:
    jmp fetch
row_setup:
    lda GPP_ROW
    sta F+GR_ROW
    lda GPP_RESET
    sta F+GR_RESET
    lda R+GPR_BACKGROUND
    cmp #16
    bcc :+
    lda #6
:
    sta F+GR_BACKGROUND
    lda #<D
    sta F+GR_RUN_POINTER
    lda #>D
    sta F+GR_RUN_POINTER+1
    lda #<GP_ROW_FONT
    sta F+GR_FONT
    lda #>GP_ROW_FONT
    sta F+GR_FONT+1
    lda #<GP_ROW_WIDTHS
    sta F+GR_WIDTHS
    lda #>GP_ROW_WIDTHS
    sta F+GR_WIDTHS+1
    lda #<GP_NATIVE_FONT
    sta F+GR_NATIVE
    lda #>GP_NATIVE_FONT
    sta F+GR_NATIVE+1
    lda #<palette
    sta F+GR_PALETTE
    lda #>palette
    sta F+GR_PALETTE+1
    lda #0
    sta F+GR_LEFT
    sta F+GR_LEFT+1
    sta F+GR_TOP
    lda #<320
    sta F+GR_RIGHT
    lda #>320
    sta F+GR_RIGHT+1
    lda #8
    sta F+GR_BOTTOM
    ldx #7
@pointers:
    lda pointers,x
    sta D+GRR_CHARACTERS,x
    dex
    bpl @pointers
    lda #<MAP
    sta D+GRR_BOUNDARIES
    lda #>MAP
    sta D+GRR_BOUNDARIES+1
    rts
row_call:
    lda #0
    sta se_overlay_frame
    lda #<F
    sta se_overlay_frame+1
    lda #>F
    sta se_overlay_frame+2
    lda #GP_ROW_ID
    ldx #0
    jsr se_overlay_call
    jcs return
    lda #0
    sta GPP_RESET
    sta budget
    clc
    rts
; Compute range in private state, preserving all selection fields. Only the
; actual canonical mark/anchor/caret identify selection across paint slices.
caret_line:
    lda GPP_LINE
    cmp GP_HEADER+GPH_CARET_ROW
    bne @no
    lda R+GPR_MEMBER
    beq @no
    sec
    rts
@no:
    clc
    rts
; Cset iff source lies in frozen canonical selection [start,end).
within_selection:
    ldy #2
@lo:
    lda source,y
    cmp saved_start,y
    bcc @no
    bne @hi_start
    dey
    bpl @lo
@hi_start:
    ldy #2
@hi:
    lda source,y
    cmp saved_end,y
    bcc @yes
    bne @no
    dey
    bpl @hi
@no:
    clc
    rts
@yes:
    sec
    rts
; Canonical virtual-cell position and selection are shared by aligned and
; clipped code paths. Only a real, visible CR owns a selectable trailing cell.
lo=saved_start
hi=saved_end
want=want_selection
flags=tail_flags
char=tail_character
role=tail_role
.include "render/geos/tail-policy.inc"
equal_caret:
    ldy #2
@compare:
    lda source,y
    cmp saved_caret,y
    bne @return
    dey
    bpl @compare
    lda #0
@return:
    rts
; Literal identity source boundaries; X remains caller scratch. No affine
; arrays are read. ABI3 marks the old affinity area non-live.
load_canonical:
    clc
    lda GPP_OFFSET
    adc index
    sta advance
    lda GPP_OFFSET+1
    adc #0
    sta amount+1
    bcs identity_bad
    jmp identity_source
load_tail:
    lda extent
    sta advance
    lda extent+1
    sta amount+1
identity_source:
    ; Bound the local canonical index before adding it to the full24bit FIRST.
    lda amount+1
    cmp extent+1
    bcc @add
    bne identity_bad
    lda advance
    cmp extent
    bcc @add
    bne identity_bad
@add:
    clc
    lda R+GPR_FIRST
    adc advance
    sta source
    lda R+GPR_FIRST+1
    adc amount+1
    sta source+1
    lda R+GPR_FIRST+2
    adc #0
    sta source+2
    bcs identity_bad
    ; The complete logical row may extend beyond the clipped visible packet.
    ldy #2
@bound:
    lda source,y
    cmp R+GPR_END,y
    bcc @okay
    bne identity_bad
    dey
    bpl @bound
@okay:
    clc
    rts
identity_bad:
    lda #$90
    sec
    rts
; Cset source>=caret. Cset source<=caret respectively, including affinities.
at_or_after_caret:
    ldy #2
@compare:
    lda source,y
    cmp saved_caret,y
    bne @done
    dey
    bpl @compare
    lda #0
    cmp #0
@done:
    rts
at_or_before_caret:
    jsr at_or_after_caret
    beq @yes
    bcc @yes
    clc
    rts
@yes:
    sec
    rts
.segment "RODATA"
palette: .byte 1,3,7,10,14,1,1,7,13,5,15,7,3,1
pointers: .word CHARS,STYLES,ROLES,FLAGS
destination_lo: .byte <CHARS,<STYLES,<ROLES
native_pointers: .word CHARS,ROLES,FLAGS
.assert tail_flags+1<=GPP_STATE_END,error,"paint private state overflow"
.assert MAP+130<=$8EE0,error,"paint arrays overlap reader context"
