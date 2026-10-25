.ifndef SE_GEOS_PAGE_PAINT_API
SE_GEOS_PAGE_PAINT_API=1
; Foreground owner4 only. No resident BSS/ZP; this192-byte caller-owned suffix
; survives all R21 calls (whose complete frame ends at8B40).
GPP_STATE=$8B40
GPP_BUSY=GPP_STATE
GPP_VALID=GPP_STATE+1
GPP_ERROR=GPP_STATE+2
GPP_PHASE=GPP_STATE+3
GPP_ROW=GPP_STATE+4          ;physical strips2..23,24when complete
GPP_LINE=GPP_STATE+5         ;logical cached-line scan0..22
GPP_OFFSET=GPP_STATE+6       ;word consumed source-cell offset in current line
GPP_COUNT=GPP_STATE+8        ;bounded native glyph chunk0..64
GPP_RESET=GPP_STATE+9        ;first prose call in a physical strip
GPP_X=GPP_STATE+10           ;untrimmed16-bit continuation x
GPP_Y=GPP_STATE+12           ;signed glyph origin−8..7 in current strip
GPP_CELL=GPP_STATE+13        ;native8 physical tile column0..39
GPP_KIND=GPP_STATE+14        ;0proportional,1native8code
GPP_PRIVATE=GPP_STATE+15
GPP_STATE_END=$8C00
GPP_PENDING=1
GPP_ARGUMENT=$90
GPP_CHANGED=$74
GPP_BUSY_ERROR=$B2
; BEGIN/STEP/CANCEL return A1pending/A0done,Cclear; genuine provider/leaf and
; state faults return Cset. Ownership is checked before any state/frame access.
; Each STEP performs at most8 bounded preparation/native-cell operations.
; Every R21 chunk/clear is isolated by public yields before and after the call.
; A bounded up-to8-prefix-perSTEP pass certifies ordered nonoverlapping geometry
; before any pixel write. Later strips retain a first-live-line cursor and
; skip canonical maps only when the frozen selection/caret proves them unused.
; Published page geometry/source cache must stay valid throughout the job.
.ifndef SE_GEOS_PAGE_PAINT_IMPLEMENTATION
.import se_gp_paint_begin,se_gp_paint_step,se_gp_paint_cancel
.endif
.assert GPP_STATE=$8B40 .and GPP_STATE_END=$8C00,error,"paint state must exclude R21 frame and VIEW"
.endif
