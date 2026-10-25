.ifndef SE_GEOS_SEMANTIC_LEX_ABI
SE_GEOS_SEMANTIC_LEX_ABI=1
.include "render/geos/semantic.inc"
GLEX_ID=25
GLEX_BEGIN=0
GLEX_STEP=1
GLEX_CANCEL=2
GLEX_PACKET=$90EC
GLEX_SOURCE=$8200
GLEX_ROLES=$8300
GLEX_SAVED_FS=$9040
GLEX_SOURCE_ACTIVE=$912C
GLEX_CONTEXT_VALID=$912D
; C24 frame8B40..8BFF, including its checkpoint, is immutable.
; Lexer occupies60B8D00..8D3B; this controller follows at8D3C.
GLEX_FRAME=$8D27
GLEX_ACTIVE=GLEX_FRAME+21
GLEX_INDEX=GLEX_FRAME+22
GLEX_USED=GLEX_FRAME+23
GLEX_ERROR=GLEX_FRAME+24
GLEX_LENGTH=GLEX_FRAME+25
GLEX_FINISHED=GLEX_FRAME+28
GLEX_BUDGET=GLEX_FRAME+29
GLEX_PAINT=GLEX_FRAME+30
GLEX_LANG=GLEX_FRAME+31
GLEX_QUERY=GLEX_FRAME+32
GLEX_COUNT=GLEX_FRAME+35
GLEX_BODY=GLEX_FRAME+36
GLEX_END=GLEX_FRAME+39
GLEX_VISIBLE_END=GLEX_FRAME+42
GLEX_FROM=GLEX_FRAME+45
GLEX_TO=GLEX_FRAME+48
GLEX_ROLE=GLEX_FRAME+51
GLEX_PHASE=GLEX_FRAME+52
GLEX_PAINT_END=GLEX_FRAME+53
GLEX_BYTE=GLEX_FRAME+54
GLEX_READS=GLEX_FRAME+55
GLEX_PENDING=1
; BEGIN0/STEP1/CANCEL2, owner4 before any phase/frame access. The caller's
; packet at8200 and semantic fields0..20 remain immutable. Only COUNT role
; bytes8300 are output (basecode4, actual unchanged lexer roles7..13).
; Pre-feed BODY through the visible span and logical END, then finish/drain,
; so tokens clipped at either viewport edge retain complete classification.
; Each STEP feeds<=32 native bytes, reads<=one32B R14 packet, or paints<=32
; role bytes. Queued lexer spans are drained before another feed.
; A1pending/A0done/Cclear, genuine source/argument/context faults Cset.
; Source lease snapshots at9040/912D support independent resident abort;
; parent9134..9177 is unchanged except REQUEST9135=25/OP9136=1 on pending.
.assert GLEX_READS+1<=$8EE0,error,"GEOS lexical frame overflow"
.endif
