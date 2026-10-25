.ifndef SE_GEOS_BANDS_API
SE_GEOS_BANDS_API=1
GB_LIMIT=22
GB_DEFAULT_ALIGN_NATIVE=1
GB_COUNT=0                  ;0..22 logical source lines
GB_ALIGN_NATIVE=1           ;1(default) align height8 lines upward to8px;0stack
GB_EMPTY_SOURCE=2           ;24bit anchor for empty-list HIT
GB_INPUT_SIZE=5
GB_BUSY=5
GB_VALID=6                  ;complete validated geometry, queries permitted
GB_ERROR=7
GB_STAGE=8
GB_INDEX=9
GB_Y=10
GB_LAST_VISIBLE=11
GB_CURSOR=12
GB_OUT_VALID=13             ;fresh complete strip packet after STEP
GB_RUNS=14                  ;0..2 contributions
GB_RUN0=15                  ;logicalindex, signedYorigin, cliptop, clipbottom
GB_RUN1=19
GB_HIT_Y=23                 ;physical viewport Y0..199, input to HIT_Y
GB_HIT_VALID=24             ;1line,0empty list
GB_HIT_INDEX=25             ;logicalindex,FFempty
GB_HIT_LOCAL=26             ;clamped local row0..height-1
GB_HIT_START=27             ;three exact24bit source anchors
GB_HIT_END=30
GB_HIT_NEXT=33
GB_HIT_TOP=36               ;physical line top16..191
GB_SCAN=37
GB_OFFSET=38
GB_STRIP_TOP=39
GB_LINE_TOP=40
GB_LINE_BOTTOM=41
GB_HIT_CLAMP=42
GB_ROW=43                   ;physical strip2..23 for fresh output packet
GB_TOPS=44                  ;22 byte line tops,FF if entirely below body
GB_WORKSPACE_SIZE=66
GB_LINES=66                 ;22 immutable10byte authoritative line records
GBL_START=0                 ;24bit first source byte
GBL_END=3                   ;24bit source body end
GBL_NEXT=6                  ;24bit canonical next row; can skip folded source
GBL_HEIGHT=9                ;8 nativecode or9 BSW
GBL_SIZE=10
GB_FRAME_SIZE=286
GB_ARGUMENT=$90
GB_STATE=$91
; Pure operation-sized foreground module. Import one caller-owned frame alias;
; no resident BSS/ZP/font assets/DMA/document mutation. Inputs0..4 and all220
; line bytes remain immutable. Caller source identity/lifetime is authoritative.
; Each record must start<=end<=next, next equals following start, and a no-
; progress empty EOF row may occur only last. Heights are8/9. All24bits retained.
;
; Body is half-open[16,192), physical8px strips2..23. Default ALIGN_NATIVE1
; matches the verified GEOS probe and C64 codegrid; BSW stacks9px. Optional0
; is consecutive8/9pitch comparison, not the final editor's codegrid policy.
; BEGIN returnsA1pending/Cclear; busyBEGIN refuses without replacing active
; state. STEP validates <=one record or emits <=one strip(scans<=22lines).
; At most COUNT+22 STEPs. Every emitted packet has OUT_VALID1, ROW, RUNS and
; <=2run records(index,origin−8..7, local half-open clip[0,8]). Last strip also
; returnsA0done/BUSY0. Blank strips emit RUNS0 and still need clearing by caller.
; VALID1 after all records validate; HIT queries may occur between strip STEPs.
; On validation/state error,Cset/A90or91,VALID0/OUT_VALID0; partial tops ignored.
; No pixels are drawn; ninth-row descenders and bottom clipping are geometry.
;
; HIT_Y accepts screenY0..199, clamps to body16..191. In an alignment gap it
; selects the following visible logical line at localY0; abovefirst clampsfirst;
; belowlastvisible clampslast at its last in-body glyph row. Lines with top>=192 are
; never selected. Empty list gives HIT_VALID0/indexFF and EMPTY_SOURCE in all
; three anchors. A true empty EOF logical row is a normal8/9px row. Source HIT
; returns the logical row's exact start/end/next, not an invented character/X;
; preferredX and character hit testing belong to the line worker. Invalid HIT
; query preserves published geometry and hit outputs. A/X/Y/P clobbered,D=0.
.import se_gb_frame
.ifndef SE_GEOS_BANDS_IMPLEMENTATION
.import se_geos_bands_begin,se_geos_bands_step,se_geos_bands_hit_y
.endif
.endif
