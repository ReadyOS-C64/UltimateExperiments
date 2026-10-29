.ifndef SE_GEOS_SOURCE_LINE_API
SE_GEOS_SOURCE_LINE_API=1
.include "render/geos/line.inc"
GS_BEGIN=0
GS_STEP=1
GS_CANCEL=2
GS_HIT=3
GS_BANDS_BEGIN=4
GS_BANDS_STEP=5
GS_BANDS_HIT=6
GS_OWNER=4
GS_PENDING=1
GS_FS=$9040                 ;86B retained actual reader context
GS_OVERLAP=$9096            ;86B saved GL bytes at8EE0..8F35 during reader call
GS_PACKET=$90EC             ;32B native source packet
GS_STYLES=$910C             ;32B normal styles
GS_CONTROL=$912C            ;84B reserved controller suffix through917F
GS_ACTIVE=GS_CONTROL
GS_CONTEXT_VALID=GS_CONTROL+1 ;root may restore GS_FS then resident END if C20 absent
GS_ERROR=GS_CONTROL+2
GS_ENCODING=GS_CONTROL+4     ;frozen BEGIN encoding0 proportional/1 fixed8
GS_READS=GS_CONTROL+3        ;wrapping diagnostic byte, one actual READ perSTEP
GS_CONTEXT_SIZE=86
GS_STATE_END=$9180
; BEGIN requires ACTIVE=CONTEXT_VALID=0 and initialized GL inputs0..31.
; Returns A1 pending/A0 line complete or Cset error. STEP feeds<=32 bytes and
; performs<=one source READ; guard/read calls are sequential C20->R14.
; Band ops alias se_gb_frame=$8D00 and require ACTIVE=CONTEXT_VALID=0.
; Parent C21 controller9134..917F is never written by this leaf.
; Owner4 is checked before every phase read. No source/index/REU mutation.
; Font+widths are local C20 assets. GL_NATIVE is unused metrics-only input:
; fallback advances come from widths; no fallback pixels/raster are read.
; Encoding1 uses fixed8 advances from GS_STYLES (not native glyph pixels).
; Context exchange preserves all86 overlapping GL bytes around every R14/END.
; Root missing-C20 cleanup must owner4-check, preserve overlap, restore GS_FS,
; call resident se_fs_end, capture cleared FS, restore overlap, clear both flags.
.endif
