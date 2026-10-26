.ifndef SE_CACHE_EDIT_REBASE_CURRENT_PROBE
SE_CACHE_EDIT_REBASE_CURRENT_PROBE=1
.include "cache/api.inc"
.include "cache/arena/api.inc"
S=BC_FRAME
S_ABI=S
S_STATE=S+1
S_ERROR=S+2
S_LIVE=S+3
S_MODE=S+4
S_AUTH=S+8 ;live token5/ticket4/incarnation4
S_HEAD=S+21
S_TAIL=S+22
S_SLOT=S+23
S_N=S+24
S_INDEX=S+25
S_EXPECT=S+26 ;3
S_END=S+29 ;3
S_NEXT=S+32 ;3
S_CURSOR=S+35 ;3
S_USED=S+38
S_AT=S+39
S_TEMP=S+40 ;12
S_DEST=S+52
S_PSTATE=S+53
S_ORIGIN=S+54
S_PAGE_MODE=S+55
S_CRC=S+56 ;2
S_FEEDS=S+58 ;3
S_QUERY=S+61 ;3 captured input
S_ROOT=$8880 ;128
S_MAN=$8900 ;128
S_OLD=$8980 ;96
S_NEW=$89E0 ;96
S_HEADER=$8A40 ;64
S_EVENT=$8A80 ;32
S_DRAFT=$8AA0 ;128
S_INPUT=$8B20 ;query24 input only
S_READER=BC_FRAME+173
S_PACKET=BC_FRAME+259
S_CR=BC_FRAME+291
S_PROOF=$53
S_FEATURE=5 ;BASE|LEX: actual current schema, with no mapped feature acceptance
.macro CP from,to,n
 ldx #n-1
:lda from,x
 sta to,x
 dex
 bpl :-
.endmacro
.macro EQ from,to,n
 ldx #n-1
:lda from,x
 cmp to,x
 jne stale
 dex
 bpl :-
.endmacro
.macro C24 lhs,rhs
 ldx #2
:lda lhs,x
 cmp rhs,x
 bne :+
 dex
 bpl :-
 lda #0
:
.endmacro
.macro INC24 p
 inc p
 bne :+
 inc p+1
 bne :+
 inc p+2
:
.endmacro
.endif

; Private post-parser COW controller: actual SM79 is dead in publication.
E=BC_FRAME+94
E_PHASE=E
E_OLD_CR=E+1
E_OLD_LEX=E+2
E_INDEX=E+3
E_FOUND=E+4
E_NEW_CRC=E+5
E_OLD_CRC=E+7
E_EXPECT=E+9
E_CURSOR=E+11
E_LEFT=E+14
E_LEX_USED=E+16
E_LEX_COUNT=E+18
E_LEX_BODY=E+20
E_LEX_END=E+23
E_STAGE=E+26
E_NEW_PAGE=E+27
E_KIND=E+28
E_USED=E+29
E_CR_EXPECT=E+31
E_LEX_EXPECT=E+33
E_OLD_HEADER=$8900 ;64B, formerly mapped manifest
NEW_CR_PAGE=14
NEW_LEX_PAGE=15
