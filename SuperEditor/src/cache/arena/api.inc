; Arena transport owns ONLY [BC_FRAME+387,+576). First387 bytes opaque.
.ifndef SE_CACHE_ARENA_API
SE_CACHE_ARENA_API=1
.include "cache/api.inc"
BCA=BC_FRAME+BCF_ARENA_CONTROL
BCA_OFFSET=BCA+0                 ; requested absolute object offset24
BCA_LENGTH=BCA+3                 ; 1..128
BCA_PAGE=BCA+4                   ; data page1..255
BCA_KIND=BCA+5                   ; expected1..7
BCA_GENERATION=BCA+6             ; expected16, FFFF forbidden
BCA_PHASE=BCA+8
BCA_ERROR=BCA+9
BCA_BOUND=BCA+10                 ; captured/owned candidate token5
BCA_INC=BCA+15                   ; captured incarnation4
BCA_TICKET=BCA+19                ; captured observer ticket4
BCA_SEQUENCE=BCA+23              ; selected root sequence4
BCA_SELECTED=BCA+27              ; 0/128; FF no valid root
BCA_CURSOR=BCA+28                ; bounded initialization/payload cursor24
BCA_LEFT=BCA+31                  ; payload remaining16
BCA_CRC=BCA+33                   ; running payload CRC16
BCA_EXPECT=BCA+35                ; expected payload CRC16
BCA_USED=BCA+37                  ; certified payload length16
BCA_PROOF=BCA+39                 ; A5 iff complete payload checked
BCA_TEMP=BCA+40                  ; 12 temporary bytes, operation exclusive
BCA_DIRECTORY=BCA+52             ; captured entry8
BCA_BANKS=BCA+60
BCA_BAD=$C0
BCA_STALE=$C1
BCA_CORRUPT=$C2
BCA_BUSY=$C3
BCA_NONE=$C4
.global se_bc_arena_open,se_bc_arena_step,se_bc_arena_cancel,se_bc_arena_trim
.global se_bc_arena_read,se_bc_page_begin
.endif
