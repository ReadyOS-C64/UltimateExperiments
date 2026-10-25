.ifndef SE_GEOS_NATIVE_PAN_API
SE_GEOS_NATIVE_PAN_API=1
GNP_FRAME=$8F00
GNP_ROW=0                  ;physical VIC tile row2..23
GNP_ORIGIN=1               ;word0..319 orFFF9..FFFF=-7..-1
GNP_COUNT=3                ;1..64 immutable native source glyphs
GNP_CHARS=4                ;word wholeCOUNT within8D00..8EFF
GNP_ROLES=6                ;word role0..13, same checked input range
GNP_FLAGS=8                ;word inverse1,selected2,caret4; union inversion
GNP_ACTIVE=10
GNP_TILE=11
GNP_INDEX=12
GNP_RELATIVE=13
GNP_ROWBASE=14
GNP_PIXELS=16               ;8 private output bytes
GNP_HISTOGRAM=24            ;14 underlying-ink votes,<=64perrole
GNP_BEST=38
GNP_WEIGHT=39
GNP_RANK=40
GNP_ROLE=41
GNP_FLAG=42
GNP_CANDIDATE=43
GNP_X=44
GNP_MASK=45
GNP_SHIFT=46
GNP_INK=47
GNP_SIZE=48
.global se_gnp_begin,se_gnp_step
.global se_gnp_palette ;callerexports14B existing ReadyOS semantic palette
; Owner4 required before every frame access. BEGIN validates all inputs and
; returnsA1/CLC without output. STEP writes exactlyone affected8x8bitmaptile
; andattribute, returningA1whilepending/A0last. Cset/A90argument,AB2owner,
; A70inactive. Inputs remain immutable until completion; no cancellation lease.
; Native fallback4800..4BFF must be explicitly valid; no retainedfontassumption.
; Existing text_ptr/screen_ptr are temporary loans; no additional ZP/BSS/REU.
; Caller cleared affected physical strip first. Output only6000..7F3F and
; attributes4000..43BF (rows2..23), never catalog7F40/shim/neighbors.
; Glyphs use native PETSCII screenconversion. Styles are ignored. Underlying
; postinverse/preselection ink chooses semanticFG byweight/priority/lowrole tie;
; same-role votescombine, allblankrole0. Selection/caret invert as one union.
.assert GNP_FRAME+GNP_SIZE<=$9040,error,"native pan frame overlaps GSsnapshot"
.endif
