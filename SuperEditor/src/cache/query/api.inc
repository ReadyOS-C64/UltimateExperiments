.ifndef SE_CACHE_QUERY_API
SE_CACHE_QUERY_API=1
.include "cache/api.inc"
BQ=BC_FRAME
BQ_ABI=BQ+0
BQ_STATE=BQ+1
BQ_ERROR=BQ+2
BQ_LIVE=BQ+3
BQ_READY=BQ+4
BQ_CAPS=BQ+5
BQ_LEX_CERT=BQ+6                 ; always0: no completed lexical stream
BQ_POSITION=BQ+8                 ; caller query canonical24
BQ_REMAIN=BQ+11                  ; unvisited CR records24
BQ_REF=BQ+14                     ; current CR/INLINE page/slot/gen16
BQ_EVENTS=BQ+18                  ; remaining INLINE24
BQ_EXPECT=BQ+21                  ; canonical nextSTART24
BQ_END=BQ+24                     ; absoluteEND24
BQ_NEXT=BQ+27                    ; absoluteNEXT24
BQ_CLASS=BQ+30                   ; pagekind1CR/2INLINE
BQ_WIDTH=BQ+31                   ; record96/event10
.ifdef BCQ_EDITOR_ACTIVE
; Resident unavailable-outer cleanup shares the semantic reader86 contract.
BQ_READER=BQ+BCF_READER           ; $8DAD, owned source context86
BQ_SOURCE=BQ+32                  ; root frozen identity59
BQ_LENGTH=BQ+91
BQ_AUTH=BQ+94                    ; live CPU arena5/ticket4/inc4
BQ_PAGE_NEXT=BQ+107
BQ_SLOTS=BQ+111
BQ_CACHE=BQ+112
BQ_LAST=BQ+116
BQ_TEMP=BQ+120
BQ_RECORD_REF=BQ+128
BQ_CR=BQ+259                     ; protected staged CR96
.assert BQ_READER=$8DAD,error,"editor query reader cleanup ABI"
.assert BQ_CR+96<=BQ+BCF_ARENA_CONTROL,error,"editor query/control overlap"
.else
BQ_READER=BQ+32                  ; real R14 context86
BQ_SOURCE=BQ+118                 ; root's frozen FS identity59
BQ_LENGTH=BQ+177                 ; frozen merged length24
BQ_CR=BQ+180                     ; staged complete descriptor96
BQ_AUTH=BQ+276                   ; capturedliveCPU order: arena5/ticket4/inc4
BQ_PAGE_NEXT=BQ+289               ; authenticated pageNEXTref4
BQ_SLOTS=BQ+293                  ; authenticated records count8
BQ_CACHE=BQ+294                  ; validated page/gen16/kind4
BQ_LAST=BQ+298                   ; rootLASTref4
BQ_RECORD_REF=BQ+310             ; actualfoundCRreference4
BQ_TEMP=BQ+302                   ; arithmetic/CRC transient8
.endif
; Optional one-viewport CR payload proof. No default/profile storage changes.
.ifdef BCQ_PAGE_REUSE
BQ_PROOF_VALID=BQ+132
.endif
BQ_OPEN=1
BQ_SOURCE_BEGIN=2
BQ_PAGE=3
BQ_PAGE_STEP=4
BQ_HEADER=5
BQ_READ=6
BQ_OUTPUT_CR=1
BQ_OUTPUT_INLINE=2
.global se_bc_query_begin,se_bc_query_step,se_bc_query_ack,se_bc_query_cancel
.endif
