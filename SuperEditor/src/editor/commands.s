.setcpu "6502"
.macpack longbranch
.include "editor/api.inc"
.include "document/api.inc"
.include "document/math24.inc"
.include "hot/api.inc"
.include "history/api.inc"
.include "nav/api.inc"
.include "search/api.inc"
.include "block/api.inc"
.include "render/api.inc"
.include "layout/api.inc"
.include "diagnostics/api.inc"
.include "editor_file/api.inc"
.include "aux/api.inc"
.import se_editor_file_call,se_editor_file_pump,se_style_input
.import se_ef_dispatch,se_ef_motion_tick,se_ef_motion_ack
.import se_overlay_call,se_overlay_frame,se_editor_error,se_editor_render_call
.import se_geos_service,se_geos_cancel,se_geos_navigate,se_mode
.export se_editor_reload
.import se_input_get,se_input_nmi_pending,se_input_tail,se_input_head,se_input_chars,se_input_mods,se_editor_latch_event
.segment "CODE"
; Keep the key-to-command route resident: ordinary typing never swaps C to a
; decoder before entering the cached gap module. Matrix/modifiers stay attached.
se_editor_input:
    jsr se_style_input
    lda #0
    sta se_e_error
    lda se_e_ui
    cmp #3
    jeq file_key ;global keys must not escape an owned file modal
    lda se_e_key
    cmp #$8B
    beq help_key
    cmp #$85
    beq menu
    cmp #$88
    beq command_line
    cmp #$8C
    beq mode_key
    lda se_e_ui
    beq document_key
    lda #U_KEY
    bne ui
mode_key:
    lda #E_MODENEXT
    jmp se_editor_command
help_key:
    lda #E_HELP
    jmp se_editor_command
menu:
    lda #U_MENU
    bne ui
command_line:
    lda #U_COMMAND
ui:
    sta se_overlay_frame
    lda #EDITOR_UI_ID
    ldx #1
    jsr se_overlay_call
    jcs se_editor_error
    lda se_e_command
    bne se_editor_command
    jmp redraw
document_key:
    lda se_e_mods
    and #4
    beq @unmodified
    lda se_e_key
    cmp #$13 ;CTRL-S shares HOME's native byte
    bne :+
    lda #E_SAVE
    jmp se_editor_command
:
    cmp #$0F
    bne @unmodified
    lda #E_OPEN
    jmp se_editor_command
@unmodified:
    lda se_e_key
    cmp #3
    bne @ordinary
    lda se_e_mods
    and #4 ;KERNAL CTRL flag; RUN/STOP shares native byte03
    beq @stop
    lda #E_COPY
    jmp se_editor_command
@stop:
    lda #E_UNMARK
    jmp se_editor_command
@ordinary:
    lda se_e_key
    ldx #key_end-key_bytes-1
@find:
    cmp key_bytes,x
    beq @command
    dex
    bpl @find
    cmp #$0D
    beq @insert
    cmp #$20
    bcc @unknown
    cmp #$80
    bcc @insert
    cmp #$A0
    bcs @insert
@unknown:
    lda #$77
    jmp se_editor_error
@insert:
    sta se_hot_byte
    lda #E_INSERT
    bne se_editor_command
@command:
    lda se_e_key
    cmp #$94
    bne :+
    lda #32
    sta se_hot_byte
    sta se_e_key
:
    lda key_commands,x
se_editor_command:
    pha
    jsr se_style_input
    pla
    sta se_e_command
    jeq redraw
    cmp #E_INSERT+1
    bcc @motion
    cmp #E_HOME
    bcc @motion_done
    cmp #E_FINDNEXT+1
    bcs @motion_done
@motion:
    jsr se_ef_motion_tick
@motion_done:
    lda se_e_command
    cmp #E_DIAG
    jeq diagnose ;read merged pending source without a flush or caret change
    lda #0
    sta se_e_after_load
    lda se_e_command
    cmp #E_UP
    bcc @reset_preferred
    cmp #E_PAGEDOWN+1
    bcc @preferred_done
@reset_preferred:
    and #$FE
    cmp #E_PANLEFT ;manual panning retains the logical preferred pixel column
    beq @preferred_done
    lda #0
    sta se_n_preferred_valid
@preferred_done:
    lda se_e_command
    cmp #E_MENU
    jeq menu
    cmp #E_COMMAND
    jeq command_line
    cmp #E_FINDPROMPT
    jeq find_prompt
    cmp #E_GOTOPROMPT
    jeq goto_prompt
    cmp #E_MARK
    jeq mark
    cmp #E_UNMARK
    jeq unmark
    cmp #E_COPY
    jeq flush_first
    cmp #E_CUT
    jeq flush_first
    cmp #E_PASTE
    beq flush_first
    cmp #E_CLEARUNDO
    beq flush_first
    cmp #E_OPEN
    bcc :+
    cmp #E_SAVEAS+1
    bcc flush_first
:
    cmp #E_WRAP
    bcc :+
    cmp #E_WRAP_OFF+1
    bcc wrap_dispatch
:
    cmp #E_HELP
    beq help
    cmp #E_SOURCE
    jeq display_mode
    cmp #E_MODE40
    bcc :+
    cmp #E_NEXTPAGE+1
    bcc display_mode
:
    cmp #E_FOLD
    bcc :+
    cmp #E_REVEAL+1
    jcc flush_first
:
    cmp #E_INSERT
    jeq local
    cmp #E_BACK
    jeq local
    cmp #E_DELETE
    jeq local
    cmp #E_LEFT
    beq flush_first
    cmp #E_RIGHT
    beq flush_first
    cmp #E_UNDO
    beq flush_first
    cmp #E_REDO
    beq flush_first
    cmp #E_HOME
    bcc unavailable
    cmp #E_FINDNEXT+1
    bcc flush_first
display_mode:
    lda #3 ;C16 mode change validates leaf before publishing settings
    sta se_overlay_frame
    lda #16
    ldx #1
    jsr se_overlay_call
    jcs se_editor_error
    jmp redraw
unavailable:
    lda #$77
    jmp se_editor_error
help:
    lda #U_HELP
    jmp ui
flush_first:
    lda se_hot_pending
    beq execute
    lda #W_FLUSH
    jsr se_hot_call
    jcs se_editor_error
    lda #2
    sta se_e_job
    rts
wrap_dispatch:
    and #$FE
    cmp #E_PANLEFT
    bne flush_first
    lda se_mode
    cmp #3
    bne flush_first
    jmp se_geos_navigate ;merged-source pixel pan never commits pending input
mark:
    jsr se_selection_toggle
    jmp redraw
unmark:
    jsr se_selection_clear
    jmp redraw
execute:
    lda #0
    sta se_h_open_group ;resident safe point, closes typing boundary without swap
    lda se_e_command
    cmp #E_FOLD
    bcc :+
    cmp #E_REVEAL+1
    bcs :+
    sec
    sbc #E_FOLD
    sta se_overlay_frame+1
    lda #0
    jsr se_ef_dispatch
    jcs se_editor_error
    jmp fold_result
:
    cmp #E_OPEN
    bcc :+
    cmp #E_SAVEAS+1
    jcc file_begin
:
    cmp #E_UNDO
    jeq history
    cmp #E_REDO
    jeq history
    cmp #E_CLEARUNDO
    jeq clear_undo
    cmp #E_WRAP
    bcc :+
    cmp #E_WRAP_OFF+1
    jcc navigate
:
    cmp #E_COPY
    jcs block
    cmp #E_BACK
    bcc @movement
    cmp #E_INSERT+1
    jcc block ;only selected edits reach execute through flush_first
@movement:
    cmp #E_POSITION
    jeq navigate
    cmp #E_WORDLEFT
    bcc :+
    cmp #E_GOTO
    jeq navigate
    jmp search
:
    cmp #E_HOME
    jcs navigate
local:
    lda #0
    sta se_l_manual
    lda se_e_command
    cmp #E_BACK
    bcc @operation
    cmp #E_INSERT+1
    bcs @operation
    lda se_h_fault
    beq :+
    lda #$65
    jmp se_editor_error
:
    jsr se_selection_range
    jne flush_first
@operation:
    lda se_e_command
    tax
    lda hot_commands-1,x
    jsr se_hot_call
    bcc local_done
    cmp #$72
    jeq edge
    cmp #$73
    jeq gap_full
    jmp se_editor_error
local_done:
    ; Local movement has committed its pending group before entering C6.
    ; Reveal at a resident safe point, never R->C or C->same-C nesting.
    lda se_e_command
    cmp #E_BACK
    bcs @edit
    CMP24 se_hot_caret,se_v_top
    bcc se_editor_reveal
    CMP24 se_hot_caret,se_v_bottom
    bcs se_editor_reveal
    jmp redraw
@edit:
    jsr se_selection_clear ;only accepted local edits clear an empty mark
    ; Backspace across the first visible source boundary needs logical-row
    ; context. Flush this rare boundary before asking the committed index.
    CMP24 se_hot_caret,se_v_top
    bcs redraw
.export se_editor_reveal
se_editor_reveal:
    lda #3
    sta se_overlay_frame
    lda #33
    ldx #1
    jsr se_overlay_call
    jcs se_editor_error
    lsr ;only A/C are promised by overlay return; discriminate result bit0
    bcc @committed
    jmp se_geos_navigate
@committed:
    jmp flush_first

redraw:
.export se_editor_redraw
se_editor_redraw = redraw
    lda #1
    sta se_e_redraw
    rts
clear_undo:
    lda #H_CLEAR
    jsr se_history_call
    bcs undo_error
    jsr se_selection_clear
    jmp redraw
undo_error:
    jmp se_editor_error
diagnose:
    lda #D_BEGIN
    jsr se_diag_call
    bcs undo_error
    lda #8
    sta se_e_job
    rts
file_begin:
    lda se_e_command
    sta se_overlay_frame+1
    lda #6 ;C12 F_DIALOG
    jsr se_editor_file_call
    bcs undo_error
    jmp file_pending
file_key:
    lda se_f_error
    cmp #F_RECOVERY
    bne @ordinary
    lda #A_FILE_RECOVERY ;recovery keys remain usable when C12 cannot reload
    sta se_overlay_frame
    lda #AUX_ID
    ldx #1
    jsr se_overlay_call
    bcs undo_error
    jmp redraw
@ordinary:
    lda #F_KEY
    jsr se_editor_file_call
    bcs undo_error
    cmp #1
    bne redraw
file_pending:
    lda #9
    sta se_e_job
    rts
block:
    jsr se_block_begin
    bcs undo_error
    lda se_b_phase
    beq redraw
    lda #6
    sta se_e_job
    rts
block_error:
    jmp se_editor_error
history:
    ldx #2
@refresh_copy_history:
    lda se_hot_caret,x
    sta se_e_target,x
    dex
    bpl @refresh_copy_history
    lda se_e_command
    sec
    sbc #E_UNDO-H_UNDO
    jsr se_history_call
    bcs undo_error
    lda #3
    sta se_e_job
    rts
find_prompt:
    lda #U_FINDPROMPT
    jmp ui
goto_prompt:
    lda #U_GOTOPROMPT
    jmp ui
search:
    lda #S_BEGIN
    jsr se_search_call
    bcs block_error
    lda #5
    sta se_e_job
    rts
navigate:
    lda se_mode
    cmp #3
    bne @ordinary
    lda se_e_command
    cmp #E_POSITION
    beq @geos
    cmp #E_UP
    bcc @ordinary
    cmp #E_PAGEDOWN+1
    bcs @ordinary
@geos:
    jmp se_geos_navigate
@ordinary:
    lda #N_BEGIN
    jsr se_navigation_call
    bcs block_error
    lda #4
    sta se_e_job
    rts
navigation_error:
    jmp se_editor_error
edge:
    ; Private synchronous C8 planner owns no lease. Direct entry avoids async
    ; navigation cleanup on admission failure; resident retains every safe point.
    lda #N_EDGE
    sta se_overlay_frame
    lda #NAV_ID
    ldx #1
    jsr se_overlay_call
    bcs block_error
    cmp #N_EDGE_REDRAW
    jeq redraw
    cmp #N_EDGE_RELOAD
    beq reload
    jmp flush_retry
gap_full:
    lda #W_INSERT
    sta se_e_after_load
flush_retry:
    lda #W_FLUSH
    jsr se_hot_call
    jcs block_error
    lda #2
    sta se_e_job
    rts
reload:
se_editor_reload:
    ldx #2
@refresh_copy_reload:
    lda se_e_target,x
    sta se_hot_position,x
    dex
    bpl @refresh_copy_reload
    lda #W_LOAD
    jsr se_hot_call
    bcs navigation_error
    lda #1
    sta se_e_job
    rts
command_error:
    jmp se_editor_error
se_editor_service:
    lda se_e_job
    jeq @done
    cmp #1
    jeq @load
    cmp #2
    jeq @flush
    cmp #3
    jeq @history
    lda se_input_nmi_pending
    bne @cancel_nav
    ldx se_input_tail
    cpx se_input_head
    jeq @nav_step
    lda se_input_chars,x
    cmp #3
    jne @nav_step
    lda se_input_mods,x
    and #4
    jne @nav_step
@cancel_nav:
    jsr se_input_get
    jsr se_editor_latch_event
    lda se_e_job
    cmp #11
    beq @cancel_geos
    cmp #12
    bne :+
@cancel_geos:
    jsr se_geos_cancel
    lda #0
    sta se_e_job
    sta se_e_redraw ;STOP retains the last complete frame until another command
    sta se_e_draw_busy
    rts
:
    lda se_e_job
    cmp #10
    bne :+
    lda #2
    jsr se_ef_dispatch
    jcs se_editor_error
    jmp @cancel_done
:
    lda se_e_job
    cmp #9
    bne :+
    lda #F_CANCEL
    jsr se_editor_file_call
    jcs command_error
    rts ;owned file cleanup continues as job9
:
    lda se_e_job
    cmp #8
    bne :+
    jsr se_diag_cancel
    jmp @cancel_done
:
    lda se_e_job
    cmp #6
    bne :+
    jsr se_block_cancel
    jcs @done
    jmp @cancel_done
:
    jsr se_navigation_cancel
    jsr se_search_cancel
@cancel_done:
    lda se_e_job
    cmp #7
    bne :+
    lda #0
    sta se_e_job
    sta se_e_redraw ;cancelled layout retains old pixels until another command
    rts
:
    lda #0
    sta se_e_job
    jmp redraw
@nav_step:
    lda se_e_job
    cmp #11
    beq @geos_step
    cmp #12
    bne :+
@geos_step:
    jmp se_geos_service
:
    lda se_e_job
    cmp #10
    bne :+
    lda #1
    jsr se_ef_dispatch
    jcs se_editor_error
    jmp fold_result
:
    lda se_e_job
    cmp #9
    jeq @file_step
    lda se_e_job
    cmp #8
    bne :+
    lda #D_STEP
    jsr se_diag_call
    jcs se_editor_error
    cmp #0
    jne @done
    sta se_e_job
    lda #1
    sta se_e_ui
    lda #7
    sta se_e_menu
    jmp redraw
:
    lda se_e_job
    cmp #7
    bne :+
    jmp se_layout_service
:
    lda se_e_job
    cmp #6
    jeq @block_step
    lda se_e_job
    cmp #5
    jeq @search_step
    lda se_v_nav_busy
    beq @nav_done
    lda #N_STEP
    jsr se_navigation_call
    jcs se_editor_error
    rts
@nav_done:
    lda se_e_command
    cmp #E_POSITION
    bne @nav_reload
    CMP24 se_hot_caret,se_e_target
    bne @nav_reload
    lda #0
    sta se_e_job
    jmp redraw
@nav_reload:
    lda se_mode
    cmp #3
    bne :+
    lda #E_POSITION
    sta se_e_command
    jmp se_geos_navigate
:
    jmp reload
@file_step:
    jsr se_editor_file_pump
    bcs @file_finish
    cmp #0
    jne @done
@file_finish:
    lda se_f_error
    cmp #F_RECOVERY
    beq @file_done
    lda #7 ;C12 F_FINISH: directory stays modal; save may resume open
    jsr se_editor_file_call
    jcs se_editor_error
    cmp #1
    jeq @done
@file_done:
    lda #0
    sta se_e_job
    lda se_f_committed
    cmp #2
    jne redraw
    ; Consume publication state before C8 can reconstruct the index union.
    lda #0
    sta se_f_committed
    sta se_hot_ready
    sta se_hot_pending
    .assert se_v_top=se_e_target+3, lderror, "file reset fields must be adjacent"
    ldx #5
@reset_position:
    sta se_e_target,x
    dex
    bpl @reset_position
    jsr se_selection_clear
    jmp reload
@search_step:
    lda se_s_active
    beq @located
    lda #S_STEP
    jsr se_search_call
    jcs se_editor_error
    rts
@located:
    lda #E_POSITION
    sta se_e_command
    jmp navigate

@block_step:
    jsr se_block_step
    bcc @block_pending
    pha
    lda se_b_changed
    bne @applied_error
    pla
    jmp se_editor_error
@applied_error:
    pla
    jmp reload ;deferred se_b_error restored after committed source loads
@block_pending:
    lda se_b_phase
    jne @done
    lda se_b_changed
    jne reload
    lda #0
    sta se_e_job
    jmp redraw
@history:
    lda se_h_phase
    beq @history_done
    lda #H_STEP
    jsr se_history_call
    jcs se_editor_error
    rts
@history_done:
    lda #0
    sta se_r_valid ;known replay must invalidate even on generation alias
    sta se_l_valid
    lda #1
    sta se_b_reveal
    jsr se_selection_clear
    jsr se_index_changed
    lda se_h_applied
    beq @target
    ldx #2
@refresh_copy_history_done:
    lda se_h_caret,x
    sta se_e_target,x
    dex
    bpl @refresh_copy_history_done
@target:
    jmp reload
@flush:
    lda se_hot_phase
    beq @flushed
    lda #W_STEP
    jsr se_hot_call
    jcs se_editor_error
    rts
@flushed:
    jsr se_index_changed
    lda #0
    sta se_e_job
    lda se_e_after_load
    beq @execute
    ldx #2
@refresh_copy_flushed:
    lda se_hot_caret,x
    sta se_e_target,x
    dex
    bpl @refresh_copy_flushed
    jmp reload
@execute:
    jmp execute
@load:
    lda se_hot_phase
    beq @loaded
    lda #W_STEP
    jsr se_hot_call
    jcs se_editor_error
    rts
@loaded:
    lda #0
    sta se_e_job
    lda se_e_after_load
    beq @render
    sta se_e_command ;temporary operation is a hot command, not editor ID
    lda #0
    sta se_e_after_load
    lda se_e_key
    sta se_hot_byte
    lda se_e_command
    jsr se_hot_call
    jcs se_editor_error
@render:
    lda se_b_error
    beq :+
    sta se_e_error
    lda #0
    sta se_b_error
:
    lda se_b_reveal
    beq :+
    lda #0
    sta se_b_reveal
    lda #E_POSITION
    sta se_e_command
    jmp navigate ;fresh committed cache exists; this pass only reveals context
:
    jmp redraw
@done:
    rts
fold_result:
    cmp #0
    beq @finished
    lda #10
    sta se_e_job
    rts
@finished:
    jsr se_ef_motion_ack
    CMP24 se_e_target,se_hot_caret
    jne reload ;the fold action's controlled caret move preserves motion serial
    lda #0
    sta se_e_job
    jmp redraw
.segment "RODATA"
hot_commands: .byte W_LEFT,W_RIGHT,W_BACK,W_DELETE,W_INSERT
key_bytes:
    .byte $1D,$9D,$14,$94,$1A,$19,$13,$93,$05,$0A,$0C,$11,$91,$86,$87,$89,$03,$01,$17,$06,$07,$0E,$0B,$18,$16,$8A
key_end:
key_commands:
    .byte E_RIGHT,E_LEFT,E_BACK,E_INSERT,E_UNDO,E_REDO,E_HOME,E_TOP,E_END,E_JBACK,E_JFORWARD,E_DOWN,E_UP,E_PAGEUP,E_PAGEDOWN,E_MARK,E_UNMARK,E_WORDLEFT,E_WORDRIGHT,E_FINDPROMPT,E_GOTOPROMPT,E_FINDNEXT,E_COPY,E_CUT,E_PASTE,E_WRAP
