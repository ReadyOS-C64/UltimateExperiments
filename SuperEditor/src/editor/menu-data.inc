; Same command/accelerator tables feed F1 and F7 paths. Text is renderer-only.
.ifndef SE_MENU_COUNTS_DEFINED
SE_MENU_COUNTS_DEFINED=1
menu_counts: .byte 3,4,9,15,7,2
.endif
.ifdef MENU_TEXT
menu_labels: .word menu_file,menu_edit,menu_view,menu_nav,menu_block,menu_help
menu_file:
 .asciiz "O  Open...       CTRL-O"
 .asciiz "S  Save          CTRL-S"
 .asciiz "A  Save as..."
menu_edit:
 .asciiz "U  Undo       CTRL-Z"
 .asciiz "R  Redo       CTRL-Y"
 .asciiz "D  Delete next character"
 .asciiz "C  Clear undo / recover"
menu_view:
 .asciiz "4  40 columns / source"
 .asciiz "6  60 columns / source"
 .asciiz "8  80 columns / source"
 .asciiz "H  GEOS hires"
 .asciiz "W  Toggle soft wrap     F4"
 .asciiz "L  Pan left 20 columns"
 .asciiz "R  Pan right 20 columns"
 .asciiz "P  Preview / source (GEOS)"
 .asciiz "S  Preview settings..."
menu_nav:
 .asciiz "U  Up / keep preferred column"
 .asciiz "D  Down / keep preferred column"
 .asciiz "P  Page up        F3"
 .asciiz "N  Page down      F5"
 .asciiz "H  Start of line"
 .asciiz "E  End of line"
 .asciiz "T  Top of document"
 .asciiz "B  Bottom of document"
 .asciiz "J  Jump back 40"
 .asciiz "L  Jump forward 40"
 .asciiz "V  Previous word     CTRL-A"
 .asciiz "W  Next word         CTRL-W"
 .asciiz "G  Go to line...     CTRL-G"
 .asciiz "F  Find...           CTRL-F"
 .asciiz "R  Find next         CTRL-N"
menu_block:
 .asciiz "M  Mark / unmark       F2"
 .asciiz "C  Copy               CTRL-C/K"
 .asciiz "X  Cut                CTRL-X"
 .asciiz "P  Paste              CTRL-V"
 .asciiz "F  Fold / unfold region"
 .asciiz "L  Collapse all regions"
 .asciiz "E  Expand all regions"
menu_help:
 .asciiz "H  Keyboard help       F6"
 .asciiz "D  Document diagnostics"
.else
menu_keys: .word file_keys,edit_keys,view_keys,nav_keys,block_keys,help_keys
menu_commands: .word file_commands,edit_commands,view_commands,nav_commands,block_commands,help_commands
file_keys: .byte 'o','s','a'
file_commands: .byte E_OPEN,E_SAVE,E_SAVEAS
edit_keys: .byte 'u','r','d','c'
edit_commands: .byte E_UNDO,E_REDO,E_DELETE,E_CLEARUNDO
view_keys: .byte '4','6','8','h','w','l','r','p','s'
view_commands: .byte E_MODE40,E_MODE60,E_MODE80,E_HIRES,E_WRAP,E_PANLEFT,E_PANRIGHT,E_SOURCE,E_SETTINGS
nav_keys: .byte 'u','d','p','n','h','e','t','b','j','l','v','w','g','f','r'
nav_commands: .byte E_UP,E_DOWN,E_PAGEUP,E_PAGEDOWN,E_HOME,E_END,E_TOP,E_BOTTOM,E_JBACK,E_JFORWARD,E_WORDLEFT,E_WORDRIGHT,E_GOTOPROMPT,E_FINDPROMPT,E_FINDNEXT
block_keys: .byte 'm','c','x','p','f','l','e'
block_commands: .byte E_MARK,E_COPY,E_CUT,E_PASTE,E_FOLD,E_COLLAPSEALL,E_EXPANDALL
help_keys: .byte 'h','d'
help_commands: .byte E_HELP,E_DIAG
.endif
