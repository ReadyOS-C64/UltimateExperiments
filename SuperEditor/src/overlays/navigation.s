.setcpu "6502"
.macpack longbranch
.include "editor-api.inc"
.include "editor/api.inc"
.include "nav/api.inc"
.include "document/api.inc"
.include "document/math24.inc"
.include "hot/api.inc"
.include "search/api.inc"
.include "layout/api.inc"
.include "render/api.inc"
.include "editor_file/api.inc"
.include "render/geos/navigation.inc"
.global se_mode,se_render_caps,se_doc_meta,se_r_revision,se_reu_epoch,se_crc_init,se_crc_byte,se_crc_value

; A successful C8 Plain GEOS GOTO publishes this explicit source-keyed
; handoff into the otherwise inactive C23 frame. Existing state values0..10
; never equal these tags. Consumer checks full key/target/TOP and consumes it.
GH_READY=$FF
GH_CONSUMED=$FE
.macro GH_FIELDS action
 action se_doc_meta,0,15
 action se_doc_generation,15,2
 action se_r_revision,17,4
 action se_v_length,21,3
 action se_reu_epoch,24,2
 action se_doc_epoch,26,2
.endmacro

.macro gh_capture source,offset,size
 ldx #size-1
: lda source,x
 sta GN_KEY+offset,x
 dex
 bpl :-
.endmacro
.segment "CODE"
    OVL_BINDING
entry:
    lda se_f_owner
    jne busy ;FILESTATE temporarily owns the sparse index address range
    lda se_overlay_frame
    cmp #N_EDGE
    jeq editor_edge
    cmp #N_BEGIN
    jeq begin
    cmp #N_STEP
    jne state
    lda se_v_nav_busy
    jeq state
    jsr width
    jcs return
    cmp se_n_view_columns
    jne changed
    cmp se_n_columns
    jne changed
    jsr se_view_init
    jcs return
    lda #128
    sta se_n_budget
    lda se_n_phase
    cmp #N_LOOKUP
    jeq lookup_step
    cmp #N_END
    jeq end_step
    cmp #N_DOWN_END
    jeq down_end_step
    cmp #N_DOWN_PREF
    jeq down_pref_step
corrupt:
    lda #$7B
    sec
    rts
state:
    lda #$70
    sec
return:
    rts
pending:
    lda #1
    clc
    rts
begin:
    lda se_v_nav_busy
    ora se_n_owned
    jne busy
    lda se_hot_pending
    ora se_hot_phase
    jne busy
    jsr width
    jcs return
    cmp se_n_columns
    beq :+
    ldx #0
    stx se_n_preferred_valid
:
    sta se_n_columns
    sta se_n_view_columns
    jsr se_view_init
    jcs return
    lda #0
    ldx #<(se_n_end-se_n_start)
@clear:
    dex
    sta se_n_start,x
    cpx #0
    bne @clear
    jsr index_context
    jcs return
    jsr se_doc_read_acquire
    jcs return
    lda #1
    sta se_n_owned
    sta se_v_nav_busy
    sta se_n_rows
    lda #0
    sta se_n_lookup_action
    sta se_l_manual
    COPY24 se_hot_caret,se_n_target
    lda se_e_command
    cmp #E_GOTO
    jeq goto_begin
    cmp #E_POSITION
    bne :+
    COPY24 se_e_target,se_n_target
    jmp @lookup
:
    cmp #E_TOP
    beq @top
    cmp #E_BOTTOM
    beq @bottom
    cmp #E_PAGEUP
    beq @page
    cmp #E_PAGEDOWN
    bne @lookup
@page:
    lda #EDITOR_PAGE_ROWS
    sta se_n_rows
@lookup:
    COPY24 se_n_target,se_n_query
    jmp lookup_start
@top:
    lda #0
    sta se_n_target
    sta se_n_target+1
    sta se_n_target+2
    sta se_n_line
    sta se_n_line+1
    sta se_n_line+2
    jmp complete
@bottom:
    COPY24 se_v_length,se_n_target
    jmp @lookup
busy:
    lda #$7A
    sec
    rts
; A valid derived prefix has full source identities, generation and bounded
; table count. Unknown outside edits invalidate it instead of guessing a delta.
index_context:
    lda se_i_ready
    beq index_reset
    lda se_i_count
    beq index_reset
    cmp #129
    bcs index_reset
    ldx #4
@tokens:
    lda se_i_original,x
    cmp se_doc_original,x
    bne index_reset
    lda se_i_append,x
    cmp se_doc_append,x
    bne index_reset
    dex
    bpl @tokens
    lda se_i_generation
    cmp se_doc_generation
    bne index_reset
    lda se_i_generation+1
    cmp se_doc_generation+1
    bne index_reset
    clc
    rts
index_reset:
    lda #0
    sta se_n_cache_count
    ldx #4
@identity:
    lda se_doc_original,x
    sta se_i_original,x
    lda se_doc_append,x
    sta se_i_append,x
    dex
    bpl @identity
    lda se_doc_generation
    sta se_i_generation
    lda se_doc_generation+1
    sta se_i_generation+1
    lda #0
    ldx #8
@first:
    sta se_index_table,x
    sta se_i_scan,x ;scan,line,number contiguous
    dex
    bpl @first
    lda #1
    sta se_i_count
    sta se_i_ready
    clc
    rts
; Pick a source checkpoint or current scanned frontier.8192-byte stride allows
; complete1MiB coverage with128 nine-byte checkpoints, no extra REU allocation.
lookup_start:
    lda #N_LOOKUP
    sta se_n_phase
    jsr cache_find
    bcs @miss
    lda #1
    sta se_n_cache_hit
    lda #0
    sta se_n_extend
    COPY24 se_n_query,se_n_scan
    jmp pending
@miss:
    lda #0
    sta se_n_cache_hit
    CMP24 se_n_query,se_i_scan
    bcc @checkpoint
    lda #1
    sta se_n_extend
    ldx #8
@frontier:
    lda se_i_scan,x
    sta se_n_scan,x ;scan,line,number contiguous in private frame too
    dex
    bpl @frontier
    jsr cache_prepare
    jmp pending
@checkpoint:
    lda #0
    sta se_n_extend
    lda se_n_query+2
    asl
    asl
    asl
    sta se_n_index
    lda se_n_query+1
    lsr
    lsr
    lsr
    lsr
    lsr
    ora se_n_index
    cmp se_i_count
    bcc @index
    lda se_i_count
    sec
    sbc #1
@index:
    jsr pointer
    ldy #8
@record:
    lda (text_ptr),y
    sta se_n_scan,y
    dey
    bpl @record
    jsr cache_prepare
    jmp pending
pointer:
    sta se_n_index
    sta se_n_temp
    lda #0
    sta se_n_temp+1
    .repeat 3
        asl se_n_temp
        rol se_n_temp+1
    .endrepeat
    clc
    lda se_n_index
    adc se_n_temp
    sta text_ptr
    lda se_n_temp+1
    adc #>INDEX_FIRST
    sta text_ptr+1
    rts
lookup_step:
    COPY24 se_n_scan,se_v_pos
@byte:
    lda se_n_lookup_action
    cmp #N_LOOK_GOTO
    bne @source_bound
    CMP24 se_n_number,se_n_delta
    jeq goto_found
@source_bound:
    CMP24 se_v_pos,se_n_query
    jeq @found
    jcs corrupt
    CMP24 se_v_pos,se_v_length
    jcs corrupt
    jsr se_view_peek
    jcs return
    pha
    jsr se_view_advance
    pla
    cmp #13
    bne @checkpoint
    COPY24 se_v_pos,se_n_line
    inc se_n_number
    bne @cached_line
    inc se_n_number+1
    bne @cached_line
    inc se_n_number+2
@cached_line:
    jsr cache_append
@checkpoint:
    COPY24 se_v_pos,se_n_scan
    lda se_n_extend
    beq @budget
    lda se_v_pos
    bne @budget
    lda se_v_pos+1
    and #31
    bne @budget
    lda se_i_count
    cmp #INDEX_RECORDS
    bcs @budget
    jsr pointer
    ldy #8
@save:
    lda se_n_scan,y
    sta (text_ptr),y
    dey
    bpl @save
    inc se_i_count
@budget:
    dec se_n_budget
    jne @byte
    jsr publish_frontier
    jmp pending
@found:
    lda se_n_lookup_action
    cmp #N_LOOK_GOTO
    bne :+
    lda #$7D ;requested logical line does not exist
    sec
    rts
:
    jsr publish_frontier
    lda se_n_lookup_action
    cmp #N_LOOK_UP
    jeq previous_line
    jmp located
publish_frontier:
    lda se_n_cache_hit
    bne @done
    COPY24 se_n_scan,se_n_cache_end
    lda se_n_extend
    beq @done
    ldx #8
@copy:
    lda se_n_scan,x
    sta se_i_scan,x
    dex
    bpl @copy
@done:
    rts
located:
    lda se_e_command
    cmp #E_WRAP
    bcc :+
    cmp #E_WRAP_OFF+1
    jcc layout_command
:
    cmp #E_POSITION
    jeq complete
    cmp #E_TOP
    jeq complete
    cmp #E_BOTTOM
    jeq complete
    cmp #E_HOME
    beq home
    cmp #E_END
    jeq end_begin
    cmp #E_JBACK
    beq jump_back
    cmp #E_JFORWARD
    jeq jump_forward
    cmp #E_UP
    jeq vertical
    cmp #E_DOWN
    jeq vertical
    cmp #E_PAGEUP
    jeq vertical
    cmp #E_PAGEDOWN
    jeq vertical
    jmp state
home:
    COPY24 se_n_line,se_n_target
    jmp complete
jump_back:
    SUB24 se_n_target,se_n_line,se_n_delta
    lda se_n_delta+2
    ora se_n_delta+1
    bne @forty
    lda se_n_delta
    cmp #40
    bcc home
@forty:
    lda #40
    sta se_n_temp
    lda #0
    sta se_n_temp+1
    sta se_n_temp+2
    SUB24 se_n_target,se_n_temp,se_n_target
    jmp complete
jump_forward:
    lda #40
    bne end_count
end_begin:
    lda #$FF
end_count:
    sta se_n_remaining
    COPY24 se_n_target,se_v_pos
    lda #N_END
    sta se_n_phase
    jmp pending
end_step:
    COPY24 se_n_target,se_v_pos
@scan:
    lda se_n_remaining
    jeq end_done
    CMP24 se_v_pos,se_v_length
    jcs end_done
    jsr se_view_peek
    jcs return
    cmp #13
    jeq end_done
    jsr se_view_advance
    lda se_n_remaining
    cmp #$FF
    beq @budget
    dec se_n_remaining
@budget:
    dec se_n_budget
    bne @scan
    COPY24 se_v_pos,se_n_target
    jmp pending
end_done:
    COPY24 se_v_pos,se_n_target
    jmp complete
;24-bit distance modulo grid width; no whole long-line traversal for visual
; column arithmetic. The index already supplied its logical line start.
column:
    SUB24 se_n_target,se_n_line,se_n_delta
    lda se_l_mode
    beq :+
    COPY24 se_n_delta,se_l_column
    rts
:
    lda #0
    sta se_n_remainder
    ldx #24
@bit:
    asl se_n_delta
    rol se_n_delta+1
    rol se_n_delta+2
    lda se_n_remainder
    rol
    cmp se_n_columns
    bcc :+
    sbc se_n_columns
:
    sta se_n_remainder
    dex
    bne @bit
    rts
vertical:
    jsr column
    lda se_l_mode
    beq :+
    lda se_n_preferred_valid
    bne vertical_next
    COPY24 se_l_column,se_l_preferred
    lda #1
    sta se_n_preferred_valid
    bne vertical_next
:
    lda se_n_preferred_valid
    bne vertical_next
    lda se_n_remainder
    sta se_n_preferred
    lda #1
    sta se_n_preferred_valid
vertical_next:
    lda se_n_reveal
    jne upward
    lda se_e_command
    cmp #E_UP
    beq upward
    cmp #E_PAGEUP
    beq upward
    jmp downward
upward:
    lda se_l_mode
    jne logical_up
    ; Within a long logical line, previous visual row is pure arithmetic.
    SUB24 se_n_target,se_n_line,se_n_delta
    lda se_n_delta+2
    ora se_n_delta+1
    bne @same_line
    lda se_n_delta
    cmp se_n_columns
    bcc @previous
@same_line:
    lda se_n_remainder
    clc
    adc se_n_columns
    sta se_n_temp
    lda #0
    sta se_n_temp+1
    sta se_n_temp+2
    SUB24 se_n_target,se_n_temp,se_n_target
    lda se_n_preferred
    sta se_n_temp
    ADD24 se_n_target,se_n_temp,se_n_target
    jmp vertical_done
@previous:
    lda se_n_line
    ora se_n_line+1
    ora se_n_line+2
    bne @has_previous
    lda #0
    sta se_n_target
    sta se_n_target+1
    sta se_n_target+2
    jmp complete
@has_previous:
    COPY24 se_n_line,se_n_query
    sec
    lda se_n_query
    sbc #1
    sta se_n_query
    lda se_n_query+1
    sbc #0
    sta se_n_query+1
    lda se_n_query+2
    sbc #0
    sta se_n_query+2
    lda #N_LOOK_UP
    sta se_n_lookup_action
    jmp lookup_start
previous_line:
    ; Query is the preceding CR, hence line metadata belongs to the preceding
    ; line. Its last visual row may be short or empty after an exact-width run.
    COPY24 se_n_query,se_n_target
    jsr column
    lda se_l_mode
    beq @wrapped
    CMP24 se_l_column,se_l_preferred
    bcc @logical_clamp
    COPY24 se_l_preferred,se_l_column
@logical_clamp:
    ADD24 se_n_line,se_l_column,se_n_target
    jmp vertical_done
@wrapped:
    lda se_n_remainder
    cmp se_n_preferred
    bcc @clamp
    lda se_n_preferred
@clamp:
    sta se_n_remaining
    lda se_n_remainder
    sta se_n_temp
    lda #0
    sta se_n_temp+1
    sta se_n_temp+2
    SUB24 se_n_target,se_n_temp,se_n_target
    lda se_n_remaining
    sta se_n_temp
    ADD24 se_n_target,se_n_temp,se_n_target
    jmp vertical_done
downward:
    lda se_l_mode
    beq :+
    lda #N_DOWN_END
    sta se_n_phase
    jmp pending
:
    lda se_n_columns
    sec
    sbc se_n_remainder
    sta se_n_remaining
    lda #N_DOWN_END
    sta se_n_phase
    jmp pending
down_end_step:
    COPY24 se_n_target,se_v_pos
@scan:
    CMP24 se_v_pos,se_v_length
    jcs bottom_clamp
    jsr se_view_peek
    jcs return
    cmp #13
    beq @newline
    lda se_l_mode
    bne @advance
    lda se_n_remaining
    beq next_visual_row
@advance:
    jsr se_view_advance
    dec se_n_remaining
    dec se_n_budget
    bne @scan
    COPY24 se_v_pos,se_n_target
    jmp pending
@newline:
    ; At an exact-width boundary, the CR itself is the next blank row, not
    ; part of the previous full row. Do not skip that row.
    lda se_l_mode
    bne @consume_cr
    lda se_n_remaining
    beq next_visual_row
@consume_cr:
    jsr se_view_advance
    COPY24 se_v_pos,se_n_line
next_visual_row:
    COPY24 se_v_pos,se_n_target
    lda se_n_preferred
    sta se_n_remaining
    COPY24 se_l_preferred,se_l_remaining
    lda #N_DOWN_PREF
    sta se_n_phase
    jmp pending
down_pref_step:
    COPY24 se_n_target,se_v_pos
@scan:
    lda se_l_mode
    beq :+
    lda se_l_remaining
    ora se_l_remaining+1
    ora se_l_remaining+2
    beq @done
    jmp @source
:
    lda se_n_remaining
    beq @done
@source:
    CMP24 se_v_pos,se_v_length
    bcs @done
    jsr se_view_peek
    jcs return
    cmp #13
    beq @done
    jsr se_view_advance
    dec se_n_remaining
    lda se_l_mode
    beq :+
    sec
    lda se_l_remaining
    sbc #1
    sta se_l_remaining
    lda se_l_remaining+1
    sbc #0
    sta se_l_remaining+1
    lda se_l_remaining+2
    sbc #0
    sta se_l_remaining+2
:
    dec se_n_budget
    bne @scan
    COPY24 se_v_pos,se_n_target
    jmp pending
@done:
    COPY24 se_v_pos,se_n_target
vertical_done:
    dec se_n_rows
    jeq complete
    lda #0
    sta se_n_lookup_action
    jsr column
    jmp vertical_next
bottom_clamp:
    COPY24 se_v_length,se_n_target
    jmp complete
complete:
    lda se_n_reveal
    jne reveal_done
    COPY24 se_n_target,se_e_target
    ; Publication/replay invalidates the old map. Its numeric bounds may still
    ; contain this caret even though its top now denotes EOF in the new source.
    ; Only a valid painted map can prove the target already has context.
    lda se_r_valid
    beq reveal
    CMP24 se_n_target,se_v_top
    bcc reveal
    CMP24 se_n_target,se_v_bottom
    jcc release
reveal:
    ; Keep up to21 real preceding source rows, rather than starting a blank
    ; viewport at EOF/CR. Reuse the bounded upward machine while retaining the
    ; user's final caret and preferred column separately.
    COPY24 se_n_target,se_n_result
    lda se_n_preferred
    sta se_n_saved_preferred
    lda se_n_preferred_valid
    sta se_n_saved_valid
    COPY24 se_l_preferred,se_l_saved_preferred
    lda #0
    sta se_n_preferred
    sta se_l_preferred
    sta se_l_preferred+1
    sta se_l_preferred+2
    lda #1
    sta se_n_reveal
    lda #EDITOR_PAGE_ROWS
    sta se_n_rows
    lda se_l_mode
    beq :+
    COPY24 se_n_line,se_n_target
    jmp upward
:
    jsr column
    lda se_n_remainder
    sta se_n_temp
    lda #0
    sta se_n_temp+1
    sta se_n_temp+2
    SUB24 se_n_target,se_n_temp,se_n_target
    lda #0 ;target is aligned; upward must not subtract its old column again
    sta se_n_remainder
    jmp upward
reveal_done:
    COPY24 se_n_target,se_v_top
    COPY24 se_n_result,se_e_target
    lda se_n_saved_preferred
    sta se_n_preferred
    lda se_n_saved_valid
    sta se_n_preferred_valid
    COPY24 se_l_saved_preferred,se_l_preferred
    lda #0
    sta se_n_reveal
release:
    jsr se_navigation_cancel
    lda se_mode
    cmp #3
    jne @handoff_done
    lda se_render_caps
    jne @handoff_done
    lda se_e_command
    cmp #E_GOTO
    jne @handoff_done
    lda #0
    sta GN_STATE
    GH_FIELDS gh_capture
    COPY24 se_e_target,GN_QUERY
    COPY24 se_v_top,GN_TOP
    COPY24 se_n_line,GN_SCAN
    lda #E_GOTO
    sta GN_COMMAND
    jsr se_crc_init
    ldy #46
@handoff_crc:
    lda GN_COMMAND,y
    jsr se_crc_byte
    dey
    bpl @handoff_crc
    ldx #1
@handoff_crc_copy:
    lda se_crc_value,x
    sta GN_TEMP,x
    dex
    bpl @handoff_crc_copy
    lda #GH_READY
    sta GN_STATE ;VALID-last, no yield/call between fields and publication
@handoff_done:
    lda #0
    clc
    rts

; Cache covers one continuously scanned source segment. Checkpoints may begin
; inside a long logical line; their saved line start/number remain authoritative.
cache_prepare:
    lda se_n_cache_count
    beq @reset
    cmp #26
    bcs @reset
    lda se_n_cache_head
    cmp #25
    bcs @reset
    CMP24 se_n_scan,se_n_cache_end
    beq @done
@reset:
    lda #0
    sta se_n_cache_head
    lda #1
    sta se_n_cache_count
    COPY24 se_n_scan,se_n_cache_end
    COPY24 se_n_number,se_n_cache_base
    COPY24 se_n_line,se_n_cache_starts
@done:
    rts
; The next logical line is consecutive with the cache's last one. Source edits
; clear count; discontinuous source seeks reset it in cache_prepare.
cache_append:
    lda se_n_cache_count
    cmp #25
    bcc @room
    lda se_n_cache_head
    sta se_n_index
    inc se_n_cache_head
    lda se_n_cache_head
    cmp #25
    bcc :+
    lda #0
    sta se_n_cache_head
:
    inc se_n_cache_base
    bne @slot
    inc se_n_cache_base+1
    bne @slot
    inc se_n_cache_base+2
    jmp @slot
@room:
    clc
    adc se_n_cache_head
    cmp #25
    bcc :+
    sbc #25
:
    sta se_n_index
    inc se_n_cache_count
@slot:
    lda se_n_index
    asl
    clc
    adc se_n_index
    tay
    lda se_n_line
    sta se_n_cache_starts,y
    lda se_n_line+1
    sta se_n_cache_starts+1,y
    lda se_n_line+2
    sta se_n_cache_starts+2,y
    rts
cache_find:
    lda se_n_cache_count
    beq @miss
    cmp #26
    bcs @miss
    lda se_n_cache_head
    cmp #25
    bcs @miss
    CMP24 se_n_query,se_n_cache_end
    bcc @begin
    bne @miss
@begin:
    lda se_n_cache_count
    sec
    sbc #1
    sta se_n_looked
@line:
    lda se_n_looked
    clc
    adc se_n_cache_head
    cmp #25
    bcc :+
    sbc #25
:
    sta se_n_index
    asl
    clc
    adc se_n_index
    tay
    lda se_n_cache_starts+2,y
    cmp se_n_query+2
    bcc @found
    bne @previous
    lda se_n_cache_starts+1,y
    cmp se_n_query+1
    bcc @found
    bne @previous
    lda se_n_cache_starts,y
    cmp se_n_query
    bcc @found
    beq @found
@previous:
    dec se_n_looked
    bpl @line
@miss:
    sec
    rts
@found:
    lda se_n_cache_starts,y
    sta se_n_line
    lda se_n_cache_starts+1,y
    sta se_n_line+1
    lda se_n_cache_starts+2,y
    sta se_n_line+2
    clc
    lda se_n_cache_base
    adc se_n_looked
    sta se_n_number
    lda se_n_cache_base+1
    adc #0
    sta se_n_number+1
    lda se_n_cache_base+2
    adc #0
    sta se_n_number+2
    clc
    rts

; One-based logical line seek. Reuse the newest valid source checkpoint whose
; line number precedes the request, then the existing bounded/indexing walker.
goto_begin:
    COPY24 se_g_line,se_n_delta
    lda se_n_delta
    ora se_n_delta+1
    ora se_n_delta+2
    jeq goto_bad
    sec
    lda se_n_delta
    sbc #1
    sta se_n_delta
    lda se_n_delta+1
    sbc #0
    sta se_n_delta+1
    lda se_n_delta+2
    sbc #0
    sta se_n_delta+2
    CMP24 se_n_delta,se_i_number
    bcc @records
    lda #1
    sta se_n_extend
    ldx #8
@frontier:
    lda se_i_scan,x
    sta se_n_scan,x
    dex
    bpl @frontier
    jmp @ready
@records:
    lda se_i_count
    sec
    sbc #1
@record:
    jsr pointer
    ldy #8
@number:
    lda (text_ptr),y
    cmp se_n_delta-6,y
    bcc @chosen
    bne @previous
    dey
    cpy #5
    bne @number
    beq @chosen
@previous:
    lda se_n_index
    beq @chosen
    sec
    sbc #1
    jmp @record
@chosen:
    ldy #8
@copy:
    lda (text_ptr),y
    sta se_n_scan,y
    dey
    bpl @copy
@ready:
    jsr cache_prepare
    lda #0
    sta se_n_cache_hit
    lda #N_LOOK_GOTO
    sta se_n_lookup_action
    lda #N_LOOKUP
    sta se_n_phase
    COPY24 se_v_length,se_n_query
    jmp pending
goto_found:
    COPY24 se_v_pos,se_n_scan
    jsr publish_frontier
    COPY24 se_n_line,se_n_target
    jmp complete
goto_bad:
    lda #$7C
    sec
    rts

.include "overlays/nav-layout.s"
.include "overlays/editor-edge.s"

; Dimension validation is side-effect free; zero and explicit40 are aliases.
width:
    lda se_v_columns
    beq @legacy
    cmp #40
    beq @valid
    cmp #60
    beq @valid
    cmp #80
    bne @bad
@valid:
    clc
    rts
@legacy:
    lda #40
    clc
    rts
@bad:
    jmp corrupt
changed:
    lda #$74
    sec
    rts
