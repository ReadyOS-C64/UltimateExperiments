; Stable editor command IDs, independent of keys/menu/typed aliases.
.include "editor/geometry.inc"
E_LEFT=1
E_RIGHT=2
E_BACK=3
E_DELETE=4
E_INSERT=5
E_UNDO=16
E_REDO=17
E_HOME=32
E_END=33
E_TOP=34
E_BOTTOM=35
E_UP=36
E_DOWN=37
E_PAGEUP=38
E_PAGEDOWN=39
E_JBACK=40
E_JFORWARD=41
E_WORDLEFT=42
E_WORDRIGHT=43
E_GOTO=44
E_FIND=45
E_FINDNEXT=46
E_POSITION=47 ;internal located-source request, no key binding
E_FINDPROMPT=48
E_GOTOPROMPT=49
E_UNMARK=50
E_MENU=64
E_COMMAND=65
E_HELP=66
E_SOURCE=67
E_MARK=68
E_COPY=69
E_CUT=70
E_PASTE=71
E_CLEARUNDO=72
E_WRAP=73
E_PANLEFT=74
E_PANRIGHT=75
E_WRAP_ON=76
E_WRAP_OFF=77
E_DIAG=78
E_OPEN=80
E_SAVE=81
E_SAVEAS=82
E_MODE40=96
E_MODE60=97
E_MODE80=98
E_HIRES=99
E_MODENEXT=100
E_MODEPREV=101
E_PREVIEW=102
E_SETTINGS=103
E_PREVPAGE=104
E_NEXTPAGE=105
E_FOLD=112
E_COLLAPSE=113
E_EXPAND=114
E_COLLAPSEALL=115
E_EXPANDALL=116
E_REVEAL=117
EDITOR_RENDER_ID=1
EDITOR_UI_ID=7
R_DRAW=1
R_NAV_BEGIN=2
R_NAV_STEP=3
U_MENU=1
U_COMMAND=2
U_DRAW=4
U_KEY=3
U_FINDPROMPT=5
U_GOTOPROMPT=6
U_HELP=7
U_SETTINGS=8
.global se_editor_command,se_editor_input,se_editor_service,se_editor_ready
.global se_e_key,se_e_mods,se_e_matrix,se_e_command,se_e_job,se_e_after_load,se_e_error
.global se_e_draw_busy,se_e_draw_sequence
.global se_e_redraw,se_e_ui,se_e_menu,se_e_item,se_e_text,se_e_text_length,se_e_target
.global se_v_top,se_v_pos,se_v_length,se_v_hot_end,se_v_span,se_v_old_span,se_v_phys
.global se_v_cache_base,se_v_cache_end,se_v_cache_count,se_v_temp,se_v_row,se_v_col
.global se_v_caret_row,se_v_caret_col,se_v_seen,se_v_rows,se_v_bottom,se_v_cell,se_v_restart
.global se_v_nav_busy,se_v_nav_dir,se_v_nav_left,se_v_nav_kind,se_v_budget
.global se_v_menu_row,se_v_menu_count,se_v_menu_index,se_v_menu_ptr

.global se_view_init,se_view_peek,se_view_advance,se_view_retreat
