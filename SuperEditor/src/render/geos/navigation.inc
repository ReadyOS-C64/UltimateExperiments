.ifndef SE_GEOS_NAVIGATION_ABI
SE_GEOS_NAVIGATION_ABI=1
GN_ID=23
GN_BEGIN=0
GN_STEP=1
GN_CANCEL=2
GN_OWNER=4
GN_PENDING=1
GN_PAGE_LINES=19 ;176px body /9px BSW rows; retain one visible context row
GN_PAGE_PIXELS=171 ;mixed aligned8px/code and9px/prose page displacement
GN_STATE=$9134
GN_REQUEST=GN_STATE+1
GN_OPERATION=GN_STATE+2
GN_COMMAND=GN_STATE+3
GN_KEY=GN_STATE+4 ;28 bytes canonical graph/generation/revision/length/epochs
GN_SCAN=GN_STATE+32
GN_ORDINAL=GN_STATE+35
GN_TARGET_ROW=GN_STATE+38
GN_QUERY=GN_STATE+41
GN_PREFERRED=GN_STATE+44
GN_TOP=GN_STATE+47
GN_PASS=GN_STATE+50
GN_PAN=GN_STATE+51
GN_MODE=GN_STATE+54
GN_CACHE_INDEX=GN_STATE+55
GN_CACHE_COUNT=GN_STATE+56
GN_CACHE_ROW=GN_STATE+57
GN_CACHE_TARGET=GN_STATE+58
GN_DELTA=GN_STATE+59
GN_TEMP=GN_STATE+60
GN_FLAGS=GN_STATE+63 ;bit0 preferred frozen,bit1 target remains on cached page
GN_TOP_ROW=GN_STATE+64
GN_TOP_VALID=GN_STATE+67
GN_STATE_END=GN_STATE+68
; BEGIN claims owner0->4. Others require4 before any phase access. Resident
; command36..39 is vertical movement;47 reveals exact existing se_e_target.
; E47 inno-wrap also revealsits logicalpixelorigin: left→x; right→x-319.
; In-range pan staysunchanged; manual/preferred arepreserved. Rootdecides
; whetherautomaticreveal isallowed; no partialpan publication onfailure.
; Commands74/75 pan left/right20pixels; successful completion enablesno-wrap.
; PAN resolves current canonical logical START through C24 then measures its
; entire logical width with C20/C26. Clamp=max(width-320,0), all24bits. No FE
; cached width/source-bytecount assumption; GN_TEMP/TARGET_ROW are reused.
; PAN returnsA2/CLC (distinctview-onlycompletion: noW_LOAD/flush).
; PAN preservescaret/top/preferred/history/clipboard/source; only pan/mode/manual,
; layout/render invalidation and target=caret publish at successful completion.
; A1/CLC means GN_REQUEST/OP asks root job12 to call C20 or C23 sequentially.
; A0/CLC atomically publishes se_e_target/top/preferred then releases owner.
; Cset leaves owner4 for resident epoch-safe se_geos_cancel, also used when
; either image is missing. No source/selection/history mutation or new BSS/ZP.
; Cached-page fastpath inspects <=one prefix per STEP, using its HEIGHT/KIND
; without C24 scans. Cold fallback requests C24 block metrics then C20 per row.
; PAGE uses canonical global pixel origins relative16, ceil8 aligned code:
; forward firstorigin>=current+171; backward lastorigin<=current-171.
.assert GN_STATE_END=$9178,error,"GEOS navigation overlaps shared IO request"
.endif
